from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: Optional[List[ChatMessage]] = Field(default=[], max_length=50)
    summary: Optional[str] = Field(default="", max_length=2000)
    session_id: Optional[str] = Field(default=None, max_length=128)
    lang: Optional[str] = Field(default=None, max_length=10)


class ChatResponse(BaseModel):
    answer: str
    summary: Optional[str] = None  # Trả về summary mới nếu vừa tóm tắt


class LeadCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=20)
