import hashlib
import secrets
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

    @staticmethod
    def generate() -> tuple[str, str]:
        """Trả về (raw_token, token_hash). Chỉ lưu hash vào DB."""
        raw = secrets.token_urlsafe(32)
        hashed = hashlib.sha256(raw.encode()).hexdigest()
        return raw, hashed

    @staticmethod
    def hash(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    def is_valid(self) -> bool:
        return not self.used and datetime.utcnow() < self.expires_at
