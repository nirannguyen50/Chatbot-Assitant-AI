"""
Widget image upload — public endpoint, xác thực bằng api_key.
Lưu ảnh vào uploads/widget/{chatbot_id}/ và trả về URL tĩnh.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.chatbot import Chatbot

router = APIRouter(tags=["Uploads"])

# Chỉ chấp nhận ảnh
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_EXT  = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE     = 5 * 1024 * 1024  # 5 MB


@router.post("/widget/{api_key}/upload")
async def widget_upload(
    api_key: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload ảnh từ widget chat — không cần JWT, chỉ cần api_key hợp lệ."""
    bot = db.query(Chatbot).filter(Chatbot.api_key == api_key).first()
    if not bot:
        raise HTTPException(status_code=401, detail="API key không hợp lệ")

    mime   = (file.content_type or "").lower()
    suffix = Path(file.filename or "image.jpg").suffix.lower()

    if mime not in ALLOWED_MIME and suffix not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ ảnh: JPG, PNG, WEBP, GIF")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Ảnh quá lớn (tối đa 5 MB)")

    # Lưu file
    save_dir = Path(settings.UPLOAD_DIR) / "widget" / str(bot.id)
    save_dir.mkdir(parents=True, exist_ok=True)

    ext       = suffix if suffix in ALLOWED_EXT else ".jpg"
    unique    = f"{uuid.uuid4().hex}{ext}"
    file_path = save_dir / unique

    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "url":      f"/uploads/widget/{bot.id}/{unique}",
        "filename": file.filename,
        "size":     len(content),
        "type":     "image",
    }
