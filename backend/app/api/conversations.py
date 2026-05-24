"""
Conversation history API — chỉ dành cho chủ chatbot xem lại.
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

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
