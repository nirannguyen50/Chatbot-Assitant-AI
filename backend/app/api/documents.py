"""
Document upload API với background processing:
Upload → lưu file → tạo DB record → background task xử lý RAG pipeline
"""
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.chatbot import Chatbot
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.core.deps import get_current_user
from app.services.processor import extract_text, chunk_text
from app.services.embeddings import embed_texts
from app.services.vector import add_document_chunks, delete_document_chunks

router = APIRouter(tags=["Documents"])

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",                                            # .xls
    "text/plain",
    "text/csv",
    "application/csv",
}

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".csv", ".txt"}


def _get_chatbot_or_404(chatbot_id: int, user: User, db: Session) -> Chatbot:
    bot = db.query(Chatbot).filter(
        Chatbot.id == chatbot_id,
        Chatbot.owner_id == user.id,
    ).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot không tồn tại")
    return bot


def _process_document(document_id: int, file_path: str, mime_type: str, chatbot_id: int):
    """Chạy trong background: parse → chunk → embed → lưu vào ChromaDB."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        doc.status = "processing"
        db.commit()

        # Parse text
        text = extract_text(file_path, mime_type)
        if not text.strip():
            raise ValueError("Không đọc được nội dung từ file")

        # Chunk
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("Không thể chia nhỏ tài liệu")

        # Embed (batch để tránh OOM)
        batch_size = 32
        all_embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i: i + batch_size]
            all_embeddings.extend(embed_texts(batch))

        # Lưu vào ChromaDB
        add_document_chunks(chatbot_id, document_id, chunks, all_embeddings)

        doc.status = "ready"
        doc.chunk_count = len(chunks)
        db.commit()

    except Exception as exc:
        db.query(Document).filter(Document.id == document_id).update(
            {"status": "error", "error_message": str(exc)}
        )
        db.commit()
    finally:
        db.close()


@router.get("/chatbots/{chatbot_id}/documents", response_model=List[DocumentResponse])
def list_documents(
    chatbot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_chatbot_or_404(chatbot_id, current_user, db)
    return db.query(Document).filter(Document.chatbot_id == chatbot_id).all()


@router.post("/chatbots/{chatbot_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    chatbot_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_chatbot_or_404(chatbot_id, current_user, db)

    # Kiểm tra loại file
    mime = file.content_type or ""
    suffix = Path(file.filename or "").suffix.lower()

    if mime not in ALLOWED_TYPES and suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ PDF, DOCX, XLSX, XLS, CSV, TXT",
        )

    # Đọc file và kiểm tra kích thước
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File quá lớn (tối đa 50MB)")

    # Lưu file
    upload_dir = Path(settings.UPLOAD_DIR) / str(chatbot_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = upload_dir / unique_name

    with open(file_path, "wb") as f:
        f.write(content)

    # Tạo record trong DB
    doc = Document(
        filename=unique_name,
        original_filename=file.filename or unique_name,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=mime or f"application/{suffix.lstrip('.')}",
        chatbot_id=chatbot_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Xử lý background
    background_tasks.add_task(
        _process_document,
        doc.id,
        str(file_path),
        doc.mime_type,
        chatbot_id,
    )

    return doc


@router.delete("/chatbots/{chatbot_id}/documents/{document_id}", status_code=204)
def delete_document(
    chatbot_id: int,
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_chatbot_or_404(chatbot_id, current_user, db)

    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.chatbot_id == chatbot_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document không tồn tại")

    # Xóa khỏi ChromaDB
    delete_document_chunks(chatbot_id, document_id)

    # Xóa file vật lý
    try:
        os.remove(doc.file_path)
    except FileNotFoundError:
        pass

    db.delete(doc)
    db.commit()
