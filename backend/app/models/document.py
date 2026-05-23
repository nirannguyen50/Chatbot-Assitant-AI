from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | processing | ready | error
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    chatbot_id = Column(Integer, ForeignKey("chatbots.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    chatbot = relationship("Chatbot", back_populates="documents")
