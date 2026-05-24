import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.core.limiter import limiter
from app.database import create_tables, get_db
from app.models.password_reset import PasswordResetToken
from app.api import auth, chatbots, documents, chat, conversations, uploads

logger = logging.getLogger(__name__)


def _startup_checks():
    if not settings.SMTP_USER:
        logger.warning(
            "SMTP chưa cấu hình (SMTP_USER trống) — "
            "tính năng đặt lại mật khẩu sẽ KHÔNG gửi được email. "
            "Thêm SMTP_USER, SMTP_PASSWORD, SMTP_FROM vào file .env."
        )
    if settings.BASE_URL == "http://localhost:8000":
        logger.warning(
            "BASE_URL đang là localhost — link đặt lại mật khẩu trong email sẽ "
            "không hoạt động khi deploy production. Cập nhật BASE_URL trong .env."
        )


def _cleanup_expired_tokens():
    """Xóa token quá 24h (đã dùng hoặc đã hết hạn) khỏi DB."""
    from datetime import datetime, timedelta
    db = next(get_db())
    try:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=24)
        deleted = db.query(PasswordResetToken).filter(
            PasswordResetToken.created_at < cutoff
        ).delete()
        db.commit()
        if deleted:
            logger.info("Đã xóa %d token reset password hết hạn.", deleted)
    except Exception as exc:
        logger.error("Lỗi khi cleanup token: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    _startup_checks()
    _cleanup_expired_tokens()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="RAG-powered chatbot platform với DeepSeek API",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Thay bằng domain cụ thể khi production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api")
app.include_router(chatbots.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")

# Serve static UI files
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # D:\Chatbot AI

dashboard_dir = BASE_DIR / "dashboard"
widget_dir    = BASE_DIR / "widget"

if dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")

if widget_dir.exists():
    app.mount("/widget", StaticFiles(directory=str(widget_dir)), name="widget")

# Serve uploaded files (images from widget chat)
upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")


@app.get("/reset-password", include_in_schema=False)
def reset_password_page():
    page = BASE_DIR / "dashboard" / "reset-password.html"
    return FileResponse(str(page))


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/health")
def health():
    return {"status": "healthy"}
