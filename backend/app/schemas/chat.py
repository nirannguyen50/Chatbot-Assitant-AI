from pydantic import BaseModel
from typing import List, Optional


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    summary: Optional[str] = ""       # Tóm tắt hội thoại cũ (widget tự quản lý)
    session_id: Optional[str] = None  # UUID phiên trò chuyện để lưu history
    lang: Optional[str] = None        # Ngôn ngữ từ browser (VD: "vi", "en", "ja")


class ChatResponse(BaseModel):
    answer: str
    summary: Optional[str] = None  # Trả về summary mới nếu vừa tóm tắt
