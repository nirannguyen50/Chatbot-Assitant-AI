"""
Conversation history API — chỉ dành cho chủ chatbot xem lại.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased, joinedload

from app.database import get_db
from app.models.chatbot import Chatbot
from app.models.conversation import Conversation, ConvMessage
from app.models.lead import Lead
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/chatbots", tags=["Conversations"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    session_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    lead_name: Optional[str] = None
    lead_email: Optional[str] = None
    lead_phone: Optional[str] = None


class DailyCount(BaseModel):
    date: str
    count: int


class AnalyticsOut(BaseModel):
    total_conversations: int
    total_messages: int
    total_leads: int
    total_unanswered: int
    avg_messages_per_conv: float
    daily_conversations: List[DailyCount]


class UnansweredQuestion(BaseModel):
    question: str
    asked_at: datetime
    conv_id: int
    session_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_owner(chatbot_id: int, user: User, db: Session) -> Chatbot:
    bot = db.query(Chatbot).filter(
        Chatbot.id == chatbot_id,
        Chatbot.owner_id == user.id,
    ).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot không tồn tại")
    return bot


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{chatbot_id}/conversations", response_model=List[ConversationOut])
def list_conversations(
    chatbot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Danh sách các phiên hội thoại (mới nhất lên trước)."""
    _check_owner(chatbot_id, current_user, db)

    rows = (
        db.query(Conversation, Lead)
        .outerjoin(Lead, Lead.session_id == Conversation.session_id)
        .filter(Conversation.chatbot_id == chatbot_id)
        .options(joinedload(Conversation.messages))
        .order_by(Conversation.updated_at.desc())
        .limit(200)
        .all()
    )

    return [
        ConversationOut(
            id=c.id,
            session_id=c.session_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=len(c.messages),
            lead_name=lead.name if lead else None,
            lead_email=lead.email if lead else None,
            lead_phone=lead.phone if lead else None,
        )
        for c, lead in rows
    ]


@router.get("/{chatbot_id}/conversations/{conv_id}/messages", response_model=List[MessageOut])
def get_conversation_messages(
    chatbot_id: int,
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy toàn bộ tin nhắn của 1 phiên."""
    _check_owner(chatbot_id, current_user, db)

    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conv_id, Conversation.chatbot_id == chatbot_id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Cuộc hội thoại không tồn tại")

    return conv.messages


@router.delete("/{chatbot_id}/conversations/{conv_id}", status_code=204)
def delete_conversation(
    chatbot_id: int,
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xóa 1 phiên hội thoại."""
    _check_owner(chatbot_id, current_user, db)

    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.chatbot_id == chatbot_id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Cuộc hội thoại không tồn tại")

    db.delete(conv)
    db.commit()


@router.get("/{chatbot_id}/analytics", response_model=AnalyticsOut)
def get_analytics(
    chatbot_id: int,
    days: int = Query(default=7, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Thống kê conversations, messages, leads và daily chart."""
    _check_owner(chatbot_id, current_user, db)

    total_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.chatbot_id == chatbot_id
    ).scalar() or 0

    total_messages = (
        db.query(func.count(ConvMessage.id))
        .join(Conversation, ConvMessage.conversation_id == Conversation.id)
        .filter(Conversation.chatbot_id == chatbot_id)
        .scalar() or 0
    )

    total_leads = db.query(func.count(Lead.id)).filter(
        Lead.chatbot_id == chatbot_id
    ).scalar() or 0

    total_unanswered = (
        db.query(func.count(ConvMessage.id))
        .join(Conversation, ConvMessage.conversation_id == Conversation.id)
        .filter(
            Conversation.chatbot_id == chatbot_id,
            ConvMessage.is_unanswered == True,
        )
        .scalar() or 0
    )

    avg_msgs = round(total_messages / total_conversations, 1) if total_conversations else 0.0

    since = (datetime.utcnow().date() - timedelta(days=days - 1))

    rows = (
        db.query(
            func.date(Conversation.created_at).label("day"),
            func.count(Conversation.id).label("cnt"),
        )
        .filter(
            Conversation.chatbot_id == chatbot_id,
            Conversation.created_at >= since,
        )
        .group_by(func.date(Conversation.created_at))
        .all()
    )

    counts = {str(row.day): row.cnt for row in rows}
    daily = [
        DailyCount(date=str(since + timedelta(days=i)), count=counts.get(str(since + timedelta(days=i)), 0))
        for i in range(days)
    ]

    return AnalyticsOut(
        total_conversations=total_conversations,
        total_messages=total_messages,
        total_leads=total_leads,
        total_unanswered=total_unanswered,
        avg_messages_per_conv=avg_msgs,
        daily_conversations=daily,
    )


@router.get("/{chatbot_id}/unanswered", response_model=List[UnansweredQuestion])
def get_unanswered_questions(
    chatbot_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Danh sach cau hoi ma bot khong tra loi duoc."""
    _check_owner(chatbot_id, current_user, db)

    # alias de join conv_messages 2 lan (user question + unanswered assistant reply)
    AssistantMsg = aliased(ConvMessage)
    UserMsg = aliased(ConvMessage)

    rows = (
        db.query(
            UserMsg.content.label("question"),
            UserMsg.created_at.label("asked_at"),
            Conversation.id.label("conv_id"),
            Conversation.session_id.label("session_id"),
        )
        .select_from(AssistantMsg)
        .join(Conversation, AssistantMsg.conversation_id == Conversation.id)
        .join(
            UserMsg,
            (UserMsg.conversation_id == AssistantMsg.conversation_id)
            & (UserMsg.role == "user")
            & (UserMsg.id == AssistantMsg.id - 1),
        )
        .filter(
            Conversation.chatbot_id == chatbot_id,
            AssistantMsg.is_unanswered == True,
            AssistantMsg.role == "assistant",
        )
        .order_by(AssistantMsg.id.desc())
        .limit(limit)
        .all()
    )

    return [
        UnansweredQuestion(
            question=r.question,
            asked_at=r.asked_at,
            conv_id=r.conv_id,
            session_id=r.session_id,
        )
        for r in rows
    ]
