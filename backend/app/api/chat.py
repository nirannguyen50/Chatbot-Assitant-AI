"""
Public chat endpoint — xác thực bằng API key.
Hỗ trợ Running Summary + lưu Conversation History vào DB.
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chatbot import Chatbot
from app.models.conversation import Conversation, ConvMessage
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag import get_rag_answer, get_rag_answer_stream

router = APIRouter(tags=["Chat"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_chatbot_by_key(api_key: str, db: Session) -> Chatbot:
    bot = db.query(Chatbot).filter(Chatbot.api_key == api_key).first()
    if not bot:
        raise HTTPException(status_code=401, detail="API key không hợp lệ")
    return bot


def _save_messages(
    db: Session,
    chatbot_id: int,
    session_id: str,
    user_message: str,
    bot_answer: str,
) -> None:
    """Tìm hoặc tạo Conversation, rồi lưu cặp (user, assistant) messages."""
    conv = db.query(Conversation).filter(
        Conversation.chatbot_id == chatbot_id,
        Conversation.session_id == session_id,
    ).first()

    if not conv:
        conv = Conversation(chatbot_id=chatbot_id, session_id=session_id)
        db.add(conv)
        db.flush()  # lấy conv.id trước khi commit

    db.add(ConvMessage(conversation_id=conv.id, role="user", content=user_message))
    db.add(ConvMessage(conversation_id=conv.id, role="assistant", content=bot_answer))
    conv.updated_at = datetime.utcnow()
    db.commit()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """Dashboard / API trực tiếp dùng X-API-Key header."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Thiếu X-API-Key header")

    bot = _get_chatbot_by_key(x_api_key, db)
    history = [{"role": m.role, "content": m.content} for m in (request.history or [])]

    answer, new_summary = await get_rag_answer(
        chatbot_id=bot.id,
        user_message=request.message,
        system_prompt=bot.system_prompt or "",
        history=history,
        summary=request.summary or "",
        lang=request.lang or "",
    )

    if request.session_id:
        _save_messages(db, bot.id, request.session_id, request.message, answer)

    return ChatResponse(answer=answer, summary=new_summary)


@router.post("/widget/{api_key}/chat", response_model=ChatResponse)
async def widget_chat(
    api_key: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """Widget nhúng vào website dùng api_key trong URL."""
    bot = _get_chatbot_by_key(api_key, db)
    history = [{"role": m.role, "content": m.content} for m in (request.history or [])]

    answer, new_summary = await get_rag_answer(
        chatbot_id=bot.id,
        user_message=request.message,
        system_prompt=bot.system_prompt or "",
        history=history,
        summary=request.summary or "",
        lang=request.lang or "",
    )

    if request.session_id:
        _save_messages(db, bot.id, request.session_id, request.message, answer)

    return ChatResponse(answer=answer, summary=new_summary)


# ── Streaming endpoints ───────────────────────────────────────────────────────

_STREAM_HEADERS = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


@router.post("/widget/{api_key}/chat/stream")
async def widget_chat_stream(
    api_key: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """Streaming variant of widget_chat — returns SSE token events."""
    bot = _get_chatbot_by_key(api_key, db)
    history = [{"role": m.role, "content": m.content} for m in (request.history or [])]

    async def generate():
        full_answer = ""
        async for event in get_rag_answer_stream(
            chatbot_id=bot.id,
            user_message=request.message,
            system_prompt=bot.system_prompt or "",
            history=history,
            summary=request.summary or "",
            lang=request.lang or "",
        ):
            yield event
            if '"done"' in event:
                try:
                    data = json.loads(event[6:])
                    full_answer = data.get("answer", "")
                except Exception:
                    pass

        if request.session_id and full_answer:
            _save_messages(db, bot.id, request.session_id, request.message, full_answer)

    return StreamingResponse(generate(), headers=_STREAM_HEADERS)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """Streaming variant of /chat — uses X-API-Key header."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Thiếu X-API-Key header")

    bot = _get_chatbot_by_key(x_api_key, db)
    history = [{"role": m.role, "content": m.content} for m in (request.history or [])]

    async def generate():
        full_answer = ""
        async for event in get_rag_answer_stream(
            chatbot_id=bot.id,
            user_message=request.message,
            system_prompt=bot.system_prompt or "",
            history=history,
            summary=request.summary or "",
            lang=request.lang or "",
        ):
            yield event
            if '"done"' in event:
                try:
                    data = json.loads(event[6:])
                    full_answer = data.get("answer", "")
                except Exception:
                    pass

        if request.session_id and full_answer:
            _save_messages(db, bot.id, request.session_id, request.message, full_answer)

    return StreamingResponse(generate(), headers=_STREAM_HEADERS)
