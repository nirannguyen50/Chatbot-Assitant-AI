from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    status: str
    chunk_count: int
    error_message: Optional[str]
    chatbot_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
