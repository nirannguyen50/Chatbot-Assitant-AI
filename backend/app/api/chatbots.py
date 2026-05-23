import secrets
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.chatbot import Chatbot
from app.schemas.chatbot import ChatbotCreate, ChatbotUpdate, ChatbotResponse, WidgetConfig
from app.core.deps import get_current_user
from app.services.vector import delete_chatbot_collection

router = APIRouter(prefix="/chatbots", tags=["Chatbots"])


def _get_chatbot_or_404(chatbot_id: int, user: User, db: Session) -> Chatbot:
    bot = db.query(Chatbot).filter(
        Chatbot.id == chatbot_id,
        Chatbot.owner_id == user.id,
    ).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot không tồn tại")
    return bot


@router.get("", response_model=List[ChatbotResponse])
def list_chatbots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Chatbot).filter(Chatbot.owner_id == current_user.id).all()


@router.post("", response_model=ChatbotResponse, status_code=201)
def create_chatbot(
    data: ChatbotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot = Chatbot(**data.model_dump(), owner_id=current_user.id)
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot


@router.get("/{chatbot_id}", response_model=ChatbotResponse)
def get_chatbot(
    chatbot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_chatbot_or_404(chatbot_id, current_user, db)


@router.put("/{chatbot_id}", response_model=ChatbotResponse)
def update_chatbot(
    chatbot_id: int,
    data: ChatbotUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot = _get_chatbot_or_404(chatbot_id, current_user, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(bot, field, value)
    db.commit()
    db.refresh(bot)
    return bot


@router.delete("/{chatbot_id}", status_code=204)
def delete_chatbot(
    chatbot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot = _get_chatbot_or_404(chatbot_id, current_user, db)
    delete_chatbot_collection(chatbot_id)
    db.delete(bot)
    db.commit()


@router.post("/{chatbot_id}/regenerate-key", response_model=ChatbotResponse)
def regenerate_api_key(
    chatbot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot = _get_chatbot_or_404(chatbot_id, current_user, db)
    bot.api_key = secrets.token_urlsafe(32)
    db.commit()
    db.refresh(bot)
    return bot


# Public endpoint — widget dùng để load config
@router.get("/widget/{api_key}/config", response_model=WidgetConfig)
def widget_config(api_key: str, db: Session = Depends(get_db)):
    bot = db.query(Chatbot).filter(Chatbot.api_key == api_key).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot không tồn tại")
    return WidgetConfig(
        name=bot.name,
        welcome_message=bot.welcome_message,
        primary_color=bot.primary_color,
    )
