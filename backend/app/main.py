from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.database import create_tables
from app.api import auth, chatbots, documents, chat, conversations, uploads


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo DB tables khi startup
    create_tables()
    # Đảm bảo thư mục uploads tồn tại (cần cho StaticFiles)
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="RAG-powered chatbot platform với DeepSeek API",
    version="1.0.0",
    lifespan=lifespan,
)

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


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/health")
def health():
    return {"status": "healthy"}
