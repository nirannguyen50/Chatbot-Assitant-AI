from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ChatbotCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    welcome_message: str = "Xin chào! Tôi có thể giúp gì cho bạn?"
    primary_color: str = "#4F46E5"


class ChatbotUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    primary_color: Optional[str] = None


class ChatbotResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    system_prompt: Optional[str]
    welcome_message: str
    api_key: str
    primary_color: str
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WidgetConfig(BaseModel):
    name: str
    welcome_message: str
    primary_color: str
