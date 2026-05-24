# Chatbot Platform — Tài liệu đầy đủ

> **GitHub Repository:** https://github.com/nirannguyen50/Chatbot-Assitant-AI

Nền tảng SaaS tạo chatbot AI cho doanh nghiệp, hoạt động như Chatbase:
- Business owner upload tài liệu → chatbot học từ tài liệu đó
- Nhúng widget vào website → khách hàng chat, AI trả lời dựa trên tài liệu
- Toàn bộ lịch sử hội thoại được lưu lại, chủ doanh nghiệp đọc lại được

---

## Mục lục

1. [Kiến trúc hệ thống](#1-kiến-trúc-hệ-thống)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [Cài đặt & Chạy local](#3-cài-đặt--chạy-local)
4. [Cấu hình .env](#4-cấu-hình-env)
5. [Luồng sử dụng](#5-luồng-sử-dụng)
6. [API Reference](#6-api-reference)
7. [RAG Pipeline — Cách hoạt động](#7-rag-pipeline--cách-hoạt-động)
8. [Tính năng nổi bật](#8-tính-năng-nổi-bật)
9. [Nhúng Widget vào Website](#9-nhúng-widget-vào-website)
10. [Expose ra Internet bằng ngrok](#10-expose-ra-internet-bằng-ngrok)
11. [Deploy lên Production](#11-deploy-lên-production)
12. [Tech Stack & Chi phí](#12-tech-stack--chi-phí)
13. [Troubleshooting](#13-troubleshooting)
14. [Changelog](#14-changelog)

---

## 1. Kiến trúc hệ thống

```
┌──────────────────────────────────────────────────────────────────┐
│  DASHBOARD  localhost:8000/dashboard                             │
│  HTML + CSS + Vanilla JS + marked.js                            │
│  - Đăng ký / Đăng nhập / Đặt lại mật khẩu qua email (JWT)     │
│  - Tạo & quản lý chatbot                                        │
│  - Upload tài liệu PDF/DOCX/XLSX/CSV/TXT                        │
│  - Test chat trực tiếp (render Markdown)                         │
│  - Xem lịch sử hội thoại (tab Lịch sử)                         │
│  - Lấy embed code nhúng vào website                             │
└───────────────────────────┬──────────────────────────────────────┘
                            │ REST API
┌───────────────────────────▼──────────────────────────────────────┐
│  BACKEND  FastAPI (Python)                                       │
│                                                                  │
│  Auth:       JWT (python-jose + bcrypt 4.2.1)                   │
│  Documents:  pdfplumber / python-docx / openpyxl → chunk → embed│
│  Embeddings: sentence-transformers BAAI/bge-m3 (local, free)    │
│  Vector:     ChromaDB (cosine similarity, per-chatbot collection)│
│  LLM:        DeepSeek API (deepseek-chat)                       │
│  Memory:     Running Summary (tóm tắt hội thoại dài)            │
│  History:    Lưu toàn bộ hội thoại vào SQLite                   │
└──────────┬────────────────────────┬─────────────────────────────┘
           │                        │
    ┌──────▼──────┐        ┌────────▼────────┐
    │  SQLite DB  │        │   ChromaDB      │
    │  - users    │        │   Vector store  │
    │  - chatbots │        │   Per-chatbot   │
    │  - documents│        │   collection    │
    │  - convers. │        │   (1024-dim)    │
    │  - messages │        └─────────────────┘
    └─────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  WIDGET  /widget/chatbot-widget.js                               │
│  Vanilla JS — nhúng vào website bằng 1 thẻ <script>            │
│  - Render Markdown (marked.js CDN)                               │
│  - Session ID tự động (lưu history vào DB)                      │
│  - Running Summary (nhớ hội thoại dài)                          │
│  - File Upload (ảnh JPG/PNG/WEBP/GIF, tối đa 5MB)              │
│  - Multi-language Auto-detect (15+ ngôn ngữ, không cần thư viện)│
└──────────────────────────────────────────────────────────────────┘
```

**Luồng dữ liệu khi chat (Streaming):**
```
Khách hỏi → Widget (kèm session_id + summary)
    → API /chat/stream
    → Query Expansion (DeepSeek sinh 3 biến thể câu hỏi)
    → Embed tất cả variants → ChromaDB tìm top-5 chunk / variant
    → Merge + dedup context
    → Running Summary (nếu history ≥ 8 tin)
    → DeepSeek API stream từng token (SSE)
    → Widget nhận token → hiển thị typewriter effect
    → Khi xong: render Markdown + lưu vào DB
```

---

## 2. Cấu trúc thư mục

```
D:\Chatbot AI\
│
├── backend/                      ← FastAPI server
│   ├── app/
│   │   ├── main.py               ← FastAPI app, CORS, static files, routers
│   │   ├── config.py             ← Settings từ .env (Pydantic BaseSettings)
│   │   ├── database.py           ← SQLAlchemy engine + SessionLocal + create_tables()
│   │   │
│   │   ├── models/               ← SQLAlchemy ORM models
│   │   │   ├── user.py           ← Bảng users
│   │   │   ├── chatbot.py        ← Bảng chatbots (api_key, primary_color, ...)
│   │   │   ├── document.py       ← Bảng documents (status, chunk_count, ...)
│   │   │   ├── conversation.py   ← Bảng conversations + conv_messages
│   │   │   └── password_reset.py ← Bảng password_reset_tokens (1h TTL, single-use)
│   │   │
│   │   ├── schemas/              ← Pydantic request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── chatbot.py
│   │   │   ├── document.py
│   │   │   └── chat.py           ← ChatRequest (message, history, summary, session_id)
│   │   │
│   │   ├── core/
│   │   │   ├── security.py       ← JWT tạo/decode, bcrypt hash password
│   │   │   └── deps.py           ← FastAPI dependency: get_current_user
│   │   │
│   │   ├── services/             ← Business logic
│   │   │   ├── processor.py      ← Parse PDF/DOCX/XLSX/CSV/TXT → text → chunks
│   │   │   ├── embeddings.py     ← BAAI/bge-m3 embed text (local, free)
│   │   │   ├── vector.py         ← ChromaDB CRUD (add/search/delete)
│   │   │   ├── rag.py            ← RAG pipeline: Query Expansion + Running Summary
│   │   │   └── email.py          ← Gửi email SMTP (reset password link)
│   │   │
│   │   └── api/                  ← Route handlers
│   │       ├── auth.py           ← POST /api/auth/register|login|me
│   │       ├── chatbots.py       ← CRUD /api/chatbots + widget config
│   │       ├── documents.py      ← Upload/delete /api/chatbots/{id}/documents
│   │       ├── chat.py           ← POST /api/chat, /api/widget/{key}/chat
│   │       ├── conversations.py  ← GET/DELETE /api/chatbots/{id}/conversations
│   │       └── uploads.py        ← POST /api/widget/{key}/upload (ảnh từ widget)
│   │
│   ├── uploads/                  ← File upload (tạo tự động)
│   │   └── widget/               ← Ảnh chat widget (public, serve qua /uploads)
│   ├── chroma_db/                ← ChromaDB vector data (tạo tự động)
│   ├── chatbot.db                ← SQLite database (tạo tự động)
│   ├── venv/                     ← Python virtual environment
│   ├── requirements.txt
│   ├── run.py                    ← Chạy uvicorn server
│   ├── start.bat                 ← Script chạy nhanh (Windows)
│   ├── .env                      ← Config thực tế (không commit git)
│   └── .env.example              ← Template config
│
├── dashboard/
│   ├── index.html                ← UI quản lý (HTML + CSS + Vanilla JS)
│   └── reset-password.html       ← Trang đặt lại mật khẩu (từ email link)
│
├── widget/
│   ├── chatbot-widget.js         ← Embeddable chat widget
│   └── demo.html                 ← Trang demo test widget
│
├── ngrok.exe                     ← Tool expose local ra internet
└── README.md                     ← File này
```

---

## 3. Cài đặt & Chạy local

### Yêu cầu
- Python 3.10+
- Git
- DeepSeek API key — đăng ký tại: https://platform.deepseek.com
- RAM tối thiểu 4GB (model BAAI/bge-m3 ~1.1GB)

### Bước 0 — Clone từ GitHub
```powershell
git clone https://github.com/nirannguyen50/Chatbot-Assitant-AI.git "Chatbot AI"
cd "Chatbot AI"
```

### Bước 1 — Tạo virtual environment
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
```

### Bước 2 — Cài dependencies
```powershell
pip install -r requirements.txt
pip install "bcrypt==4.2.1" "python-jose[cryptography]" httpx aiofiles email-validator
```

> **Lưu ý bcrypt:** Phải dùng đúng version `4.2.1`. Version 5.x không tương thích, gây lỗi khi đăng nhập.

### Bước 3 — Cấu hình .env
```powershell
copy .env.example .env
# Mở .env và điền DEEPSEEK_API_KEY
```

### Bước 4 — Chạy server
```powershell
# Cách 1: Script có sẵn
start.bat

# Cách 2: Trực tiếp
venv\Scripts\python run.py
```

**Kiểm tra:** Mở browser → http://localhost:8000/dashboard

Lần đầu khởi động, model `BAAI/bge-m3` sẽ tự động download (~570MB). Các lần sau load từ cache.

---

## 4. Cấu hình .env

```env
# ── App ─────────────────────────────────────────
APP_NAME="Chatbot Platform"
DEBUG=false

# ── Database ────────────────────────────────────
# SQLite (development — đơn giản, không cần cài gì thêm)
DATABASE_URL=sqlite:///./chatbot.db

# PostgreSQL (production — thay khi deploy)
# DATABASE_URL=postgresql://user:password@host:5432/chatbot_db

# ── JWT Security ────────────────────────────────
# QUAN TRỌNG: Đổi thành chuỗi random dài khi deploy production
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=10080   # 7 ngày

# ── DeepSeek API ────────────────────────────────
# Lấy tại: https://platform.deepseek.com/api_keys
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# ── Embedding Model (chạy local, miễn phí) ──────
# Download tự động lần đầu ~570MB, tốt nhất cho tiếng Việt
EMBEDDING_MODEL=BAAI/bge-m3

# ── Storage ─────────────────────────────────────
CHROMA_PERSIST_DIR=./chroma_db      # Lưu vector embeddings
UPLOAD_DIR=./uploads                 # Lưu file upload
MAX_FILE_SIZE=52428800               # 50MB tối đa mỗi file

# ── Email (SMTP) — Dùng để gửi link đặt lại mật khẩu ──
# Hướng dẫn Gmail App Password:
#   1. Bật 2FA tại myaccount.google.com/security
#   2. Tạo App Password tại myaccount.google.com/apppasswords
#   3. Dùng 16 ký tự đó làm SMTP_PASSWORD (không phải mật khẩu Gmail thường)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM=your@gmail.com

# URL gốc của server (dùng để tạo reset link trong email)
# Local:      http://localhost:8000
# Production: https://yourdomain.com
BASE_URL=http://localhost:8000
```

> **Không thêm** `ANONYMIZED_TELEMETRY` vào `.env` — sẽ gây lỗi Pydantic.
> Telemetry đã được tắt trong code (`vector.py` set qua `os.environ`).

---

## 5. Luồng sử dụng

### Dành cho khách hàng doanh nghiệp (Business Owner)

**Bước 1 — Đăng ký tài khoản**
- Truy cập `http://your-server/dashboard`
- Nhấn "Đăng ký" → nhập họ tên + email + mật khẩu

**Bước 2 — Tạo chatbot**
- Nhấn **"➕ Tạo chatbot mới"**
- Điền thông tin:
  - **Tên chatbot:** VD "Trợ lý CSKH Công ty ABC"
  - **System prompt:** Hướng dẫn cho AI về vai trò, giới hạn, phong cách
  - **Lời chào:** Tin nhắn đầu tiên khi khách mở chat
  - **Màu sắc:** Màu chủ đạo của widget

**Bước 3 — Upload tài liệu**
- Chọn chatbot → tab **"📄 Tài liệu"**
- Kéo thả hoặc click upload file
- Định dạng hỗ trợ: **PDF, DOCX, XLSX, XLS, CSV, TXT**
- Chờ status chuyển: `Chờ xử lý` → `Đang xử lý...` → `✅ X đoạn`
- Có thể upload nhiều file, xóa file cũ bất kỳ lúc nào

**Bước 4 — Test chat**
- Tab **"💬 Test Chat"** → thử hỏi nội dung trong tài liệu
- Bot trả lời có **Markdown** (bold, danh sách, bảng, code block)
- Nếu trả lời sai → kiểm tra lại tài liệu, thêm FAQ rõ ràng hơn

**Bước 5 — Xem lịch sử**
- Tab **"📋 Lịch sử"** → xem tất cả cuộc hội thoại của khách
- Click vào từng phiên để đọc toàn bộ nội dung
- Nút 🗑️ để xóa phiên không cần thiết

**Bước 6 — Nhúng vào website**
- Tab **"🔗 Nhúng Widget"** → copy đoạn `<script>`
- Dán vào website trước thẻ `</body>`

### Dành cho khách hàng cuối (End User)
- Vào website của doanh nghiệp
- Nhấn chat bubble 💬 góc phải màn hình
- Chat bình thường — AI trả lời theo tài liệu của doanh nghiệp, có Markdown

---

## 6. API Reference

### Authentication
| Method | Endpoint | Auth | Body | Mô tả |
|--------|----------|------|------|-------|
| POST | `/api/auth/register` | — | `{email, full_name, password}` | Đăng ký |
| POST | `/api/auth/login` | — | `{email, password}` | Đăng nhập → JWT |
| GET  | `/api/auth/me` | JWT | — | Thông tin user hiện tại |
| POST | `/api/auth/forgot-password` | — | `{email}` | Gửi link đặt lại mật khẩu |
| POST | `/api/auth/reset-password` | — | `{token, new_password}` | Đặt lại mật khẩu bằng token |
| GET  | `/reset-password` | — | — | Trang HTML đặt lại mật khẩu |

### Chatbots
| Method | Endpoint | Auth | Body | Mô tả |
|--------|----------|------|------|-------|
| GET    | `/api/chatbots` | JWT | — | Danh sách chatbot |
| POST   | `/api/chatbots` | JWT | `{name, description, system_prompt, welcome_message, primary_color}` | Tạo |
| GET    | `/api/chatbots/{id}` | JWT | — | Chi tiết |
| PUT    | `/api/chatbots/{id}` | JWT | (các field muốn update) | Cập nhật |
| DELETE | `/api/chatbots/{id}` | JWT | — | Xóa chatbot + tài liệu + hội thoại |
| POST   | `/api/chatbots/{id}/regenerate-key` | JWT | — | Tạo API key mới |
| GET    | `/api/chatbots/widget/{api_key}/config` | — | — | Config public cho widget |

### Documents
| Method | Endpoint | Auth | Body | Mô tả |
|--------|----------|------|------|-------|
| GET    | `/api/chatbots/{id}/documents` | JWT | — | Danh sách tài liệu |
| POST   | `/api/chatbots/{id}/documents` | JWT | `form-data: file` | Upload (PDF/DOCX/XLSX/CSV/TXT) |
| DELETE | `/api/chatbots/{id}/documents/{doc_id}` | JWT | — | Xóa tài liệu |

**Document status lifecycle:**
```
pending → processing → ready (chunk_count > 0)
                    ↘ error  (kèm error_message)
```

### Chat
| Method | Endpoint | Auth | Body | Mô tả |
|--------|----------|------|------|-------|
| POST | `/api/chat` | Header `X-API-Key` | xem bên dưới | Chat (custom integration) |
| POST | `/api/widget/{api_key}/chat` | URL param | xem bên dưới | Chat cho widget (public) |

**Chat request body:**
```json
{
  "message": "Câu hỏi của khách",
  "history": [
    {"role": "user", "content": "câu hỏi trước"},
    {"role": "assistant", "content": "câu trả lời trước"}
  ],
  "summary": "Tóm tắt hội thoại cũ (widget tự quản lý, gửi lại mỗi request)",
  "session_id": "uuid-phien-chat",
  "lang": "en"
}
```

**Chat response:**
```json
{
  "answer": "Câu trả lời từ AI (Markdown, đúng ngôn ngữ khách)",
  "summary": "Summary mới nếu vừa tóm tắt, null nếu chưa"
}
```

> `session_id` bắt buộc để lưu history. Widget tự sinh UUID lúc khởi tạo.
> `lang` là browser language code ("vi", "en", "ja", ...). Server dùng làm fallback khi không detect được từ nội dung tin nhắn.
> `summary` là optional — widget gửi kèm để server nhớ context hội thoại dài.

### Widget Image Upload
| Method | Endpoint | Auth | Body | Mô tả |
|--------|----------|------|------|-------|
| POST | `/api/widget/{api_key}/upload` | URL param | `form-data: file` | Upload ảnh từ widget |

**Constraints:** JPG / PNG / WEBP / GIF, tối đa 5MB

**Response:**
```json
{
  "url": "/uploads/widget/{chatbot_id}/abc123.jpg",
  "filename": "product.jpg",
  "size": 102400,
  "type": "image"
}
```

Ảnh được serve tại `GET /uploads/widget/{chatbot_id}/{filename}` (static, public).

### Conversation History
| Method | Endpoint | Auth | Mô tả |
|--------|----------|------|-------|
| GET    | `/api/chatbots/{id}/conversations` | JWT | Danh sách phiên (mới nhất lên trước, tối đa 200) |
| GET    | `/api/chatbots/{id}/conversations/{cid}/messages` | JWT | Toàn bộ tin nhắn của 1 phiên |
| DELETE | `/api/chatbots/{id}/conversations/{cid}` | JWT | Xóa 1 phiên hội thoại |

**Conversation response:**
```json
{
  "id": 1,
  "session_id": "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx",
  "created_at": "2024-01-15T14:30:00",
  "updated_at": "2024-01-15T14:45:00",
  "message_count": 12
}
```

### Swagger UI
Truy cập **http://localhost:8000/docs** để test API trực tiếp.

---

## 7. RAG Pipeline — Cách hoạt động

### Khi upload tài liệu
```
File upload (PDF / DOCX / XLSX / CSV / TXT)
    ↓
processor.py → Trích xuất toàn bộ text
  • PDF   → pdfplumber (page by page)
  • DOCX  → python-docx (paragraphs)
  • XLSX  → openpyxl (all sheets → "col1 | col2 | col3")
  • CSV   → encoding auto-detect (utf-8, latin-1, cp1252)
  • TXT   → đọc thẳng
    ↓
chunk_text() → Cắt thành đoạn ~400 từ, overlap 60 từ
    ↓
BAAI/bge-m3 → Mỗi chunk → vector 1024 chiều
    ↓
ChromaDB → Lưu vào collection "chatbot_{id}"
    ↓
Document.status = "ready", chunk_count = N
```

### Khi khách hỏi (Query Expansion + RAG)
```
Câu hỏi gốc: "Bộ phận service gồm có ai?"
    ↓
[Query Expansion] DeepSeek sinh 3 biến thể đồng nghĩa:
  • "Phòng ban service có những ai?"
  • "Nhân sự trong bộ phận dịch vụ?"
  • "Ai làm việc ở phòng service?"
    ↓
Embed 4 câu (gốc + 3 biến thể) bằng BAAI/bge-m3
    ↓
ChromaDB.query() × 4 → top-5 chunk / query → merge + dedup
    ↓
[Running Summary] Nếu history ≥ 8 tin:
  • Tóm tắt phần cũ thành ≤120 từ
  • Chỉ giữ 6 tin gần nhất + summary trong request
    ↓
DeepSeek API:
  System = custom_prompt + summary_block + context
  History = 6 tin gần nhất
  User = câu hỏi gốc
    ↓
Câu trả lời Markdown → Lưu DB → Widget render
```

### Tại sao BAAI/bge-m3?
| Model | Kích thước | Vector | Tiếng Việt | Chi phí |
|-------|-----------|--------|------------|---------|
| all-MiniLM-L6-v2 | 90MB | 384 | Trung bình | Free |
| paraphrase-multilingual | 480MB | 384 | Tốt | Free |
| **BAAI/bge-m3** | **570MB** | **1024** | **Tốt nhất** | **Free** |

`BAAI/bge-m3` là model embedding đa ngôn ngữ mạnh nhất hiện tại: hỗ trợ 100+ ngôn ngữ, vector 1024 chiều, đặc biệt tốt cho tiếng Việt và kỹ thuật tìm từ đồng nghĩa.

---

## 8. Tính năng nổi bật

### 🧠 Query Expansion
Khi khách dùng từ khác với từ trong tài liệu (VD: "bộ phận" vs "phòng ban"), DeepSeek tự động sinh 3 biến thể đồng nghĩa rồi tìm kiếm song song → tăng khả năng tìm đúng chunk liên quan.

### 💾 Running Summary — Bộ nhớ dài hạn
Khi hội thoại đạt **≥ 8 tin nhắn**:
1. Server tóm tắt phần cũ (tất cả trừ 6 tin gần nhất) thành ≤120 từ
2. Trả về `summary` cho widget
3. Widget lưu summary, trim history về 6 tin
4. Mỗi request tiếp theo gửi kèm summary → server đưa vào system prompt

```
Hội thoại 1–8:   history tích lũy bình thường
Tin thứ 9:        → tóm tắt tin 1–2, giữ 3–8
Tin thứ 10+:      mỗi request = summary + 6 tin gần nhất
```
Bot nhớ được nội dung từ đầu cuộc trò chuyện dù hội thoại kéo dài hàng chục tin.

### 🎨 Markdown Rendering
Bot responses render đầy đủ Markdown thông qua `marked.js`:
- **Bold**, *italic*, ~~gạch ngang~~
- Danh sách bullet & numbered
- Bảng (table) tự căn chỉnh
- Code inline `code` và block code (nền tối)
- Blockquote, link, heading

Hoạt động ở cả **widget** (nhúng vào website) và **Test Chat** trong dashboard.

### 📋 Conversation History
Mỗi tin nhắn từ widget được lưu vào DB với:
- `session_id`: UUID tự sinh lúc widget load
- `role`: `user` | `assistant`
- `content`: nội dung tin nhắn

Chủ doanh nghiệp xem trong tab **"📋 Lịch sử"** của dashboard:
- Danh sách phiên với ngày giờ và số tin nhắn
- Click để mở và đọc toàn bộ nội dung (render Markdown)
- Xóa phiên không cần thiết

### 📎 File Upload trong Widget
Khách có thể đính kèm ảnh trực tiếp trong cửa sổ chat:

1. Nhấn nút 📎 trong widget → chọn ảnh (JPG / PNG / WEBP / GIF)
2. Ảnh hiển thị thumbnail ngay lập tức (preview trước khi upload xong)
3. Upload lên server → lưu tại `uploads/widget/{chatbot_id}/`
4. Ảnh được hiển thị trong chat bubble của khách
5. Khi khách gửi tin nhắn: URL ảnh được đính kèm vào nội dung → AI nhận được context đầy đủ

**Giới hạn:** 5MB / ảnh · Định dạng: JPG, PNG, WEBP, GIF

> **Lưu ý:** DeepSeek-chat là model text-only, không phân tích được nội dung ảnh. AI sẽ nhận URL ảnh trong message context và trả lời dựa trên text question của khách. Nếu muốn AI phân tích ảnh, cần nâng cấp lên model vision (ví dụ GPT-4o, Gemini Pro Vision).

### 🌐 Multi-language Auto-detect
Bot tự động nhận diện ngôn ngữ của khách và trả lời đúng ngôn ngữ đó — **không cần cài thêm thư viện**.

**Cơ chế 2 lớp:**
1. **Nội dung tin nhắn** (ưu tiên cao hơn): Dùng regex nhận diện script/ký tự đặc trưng
2. **Browser language hint** (fallback): Widget gửi `navigator.language` → server dùng khi không detect được từ nội dung

**Ngôn ngữ hỗ trợ:**
| Nhóm | Ngôn ngữ | Phát hiện bằng |
|------|----------|----------------|
| Đông Nam Á | Tiếng Việt, Thai, Indonesia, Malay | Unicode diacritics / Thai script |
| Đông Á | Tiếng Nhật, Hàn, Trung | Hiragana/Katakana / Hangul / CJK |
| Châu Âu | Anh, Pháp, Đức, Tây Ban Nha, Bồ, Ý | Browser hint (ASCII text) |
| Trung Đông | Ả Rập | Arabic script |
| Đông Âu | Nga | Cyrillic script |

**Ví dụ:**
```
Khách gõ: "Hello, what are your working hours?"
→ Detect: English (browser hint "en")
→ Bot trả lời: "Our working hours are Monday to Friday, 8AM–5PM."

Khách gõ: "こんにちは、営業時間を教えてください。"
→ Detect: Japanese (Hiragana characters)
→ Bot trả lời: "営業時間は月曜日から金曜日、午前8時から午後5時までです。"
```

### 📁 Đa dạng định dạng tài liệu
| Định dạng | Thư viện | Ghi chú |
|-----------|----------|---------|
| `.pdf` | pdfplumber | Text-based PDF (không hỗ trợ PDF scan) |
| `.docx` | python-docx | Microsoft Word |
| `.xlsx`, `.xls` | openpyxl | Excel — đọc tất cả sheets, format `col1 \| col2` |
| `.csv` | built-in csv | Auto-detect encoding (utf-8/latin-1/cp1252) |
| `.txt` | built-in | Plain text |

### 🔐 Đặt lại mật khẩu qua Email

Khi người dùng quên mật khẩu:

1. Click **"Quên mật khẩu?"** ở màn hình đăng nhập
2. Nhập email → nhận link trong hộp thư (hợp lệ **1 giờ**)
3. Click link → nhập mật khẩu mới → đăng nhập lại

**Cơ chế bảo mật:**
- Token được lưu dạng SHA-256 hash — không bao giờ lưu token gốc vào DB
- Mỗi token chỉ dùng được **1 lần**, tự hết hạn sau 1 giờ
- Gửi email trong **background** — response API không bị delay
- Luôn trả `200` dù email có tồn tại hay không — tránh lộ danh sách tài khoản

**Cấu hình:** Xem mục [SMTP trong `.env`](#4-cấu-hình-env)

---

## 9. Nhúng Widget vào Website

### Cách nhúng cơ bản
```html
<!-- Dán vào trước </body> -->
<script
  src="https://your-server.com/widget/chatbot-widget.js"
  data-api-key="YOUR_API_KEY_HERE"
  data-api-url="https://your-server.com">
</script>
```

### Lấy embed code tự động
Dashboard → Chọn chatbot → Tab **"🔗 Nhúng Widget"** → Chọn platform (Website / WordPress / Haravan) → Copy code

### Hướng dẫn cài đặt theo platform
| Platform | Cách nhúng |
|----------|-----------|
| Website thông thường | Dán script tag trước `</body>` |
| WordPress | Plugin "Insert Headers and Footers" (khuyến nghị) hoặc chỉnh `footer.php` |
| Haravan | Vào Theme → Edit code → `theme.liquid` → dán trước `</body>` |

### Widget hỗ trợ
| Tính năng | Chi tiết |
|-----------|---------|
| Giao diện | Chat bubble góc phải, responsive mobile |
| Markdown | Bold, italic, danh sách, bảng, code block |
| File Upload | 📎 Đính kèm ảnh (JPG/PNG/WEBP/GIF, max 5MB) |
| Multi-language | Tự detect tiếng Việt/Anh/Nhật/Hàn/... và trả lời đúng ngôn ngữ |
| Memory | Running Summary — nhớ hội thoại dài |
| History | Session ID tự sinh, lưu vào DB server |
| Tùy chỉnh | Màu sắc, tên, lời chào từ dashboard |
| Phím tắt | Enter gửi, Shift+Enter xuống dòng |
| Typing indicator | "Đang soạn…" khi chờ AI |

### Bảo mật API key
- Mỗi chatbot có 1 API key riêng
- Key bị lộ → Dashboard → **"🔄 Tạo API key mới"** → cập nhật embed code
- API key chỉ cho phép chat, không thể đọc/xóa tài liệu

---

## 10. Expose ra Internet bằng ngrok

Dùng để demo cho khách hàng mà không cần deploy lên server.

### Cài đặt (1 lần)
1. Tải ngrok: https://ngrok.com/download (hoặc đã có tại `D:\Chatbot AI\ngrok.exe`)
2. Đăng ký tài khoản free: https://dashboard.ngrok.com/signup
3. Lấy authtoken: https://dashboard.ngrok.com/get-started/your-authtoken

### Cấu hình authtoken (1 lần)
```powershell
cd "D:\Chatbot AI"
.\ngrok.exe config add-authtoken YOUR_TOKEN_HERE
```

### Mỗi lần muốn share
```powershell
# Terminal 1: Chạy backend
cd "D:\Chatbot AI\backend"
.\start.bat

# Terminal 2: Chạy ngrok
cd "D:\Chatbot AI"
.\ngrok.exe http 8000
```

ngrok sẽ hiện URL dạng:
```
Forwarding   https://abc123def456.ngrok-free.app → http://localhost:8000
```

**Chia sẻ cho khách:**
- Dashboard: `https://abc123def456.ngrok-free.app/dashboard`
- Widget embed: `data-api-url="https://abc123def456.ngrok-free.app"`

> **Lưu ý:** Các API call từ browser phải có header `ngrok-skip-browser-warning: true`.
> Dashboard đã tự thêm header này. Widget gọi thẳng backend nên không cần.

### So sánh ngrok free vs paid
| | Free | Paid ($10/tháng) |
|---|---|---|
| URL | Thay đổi mỗi lần restart | Cố định (custom domain) |
| Số tunnel | 1 | Nhiều |
| Bandwidth | Không giới hạn | Không giới hạn |
| Phù hợp | Demo, test | Production nhỏ |

---

## 11. Deploy lên Production

### Option A — Railway (khuyến nghị, ~$5/tháng)

**Chuẩn bị Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
RUN pip install "bcrypt==4.2.1" "python-jose[cryptography]" httpx aiofiles email-validator
COPY backend/ ./backend/
COPY dashboard/ ./dashboard/
COPY widget/ ./widget/
WORKDIR /app/backend
CMD ["python", "run.py"]
```

**Biến môi trường cần set trên Railway:**
```
DEEPSEEK_API_KEY=sk-xxx
SECRET_KEY=<64-char-random-string>
DATABASE_URL=postgresql://...   ← Railway tự cấp
EMBEDDING_MODEL=BAAI/bge-m3
```

**Đổi storage cho production:**
- SQLite → PostgreSQL (Railway tự cung cấp)
- ChromaDB local → Qdrant Cloud (free tier 1GB)
- File upload → Cloudflare R2 hoặc AWS S3

### Option B — Render.com (free tier)
- Tạo Web Service → chọn repo
- Build command: `pip install -r backend/requirements.txt`
- Start command: `python backend/run.py`
- **Nhược điểm:** Sleep sau 15 phút không có request (free plan)

### Option C — VPS (DigitalOcean $6/tháng)
```bash
# Trên VPS Ubuntu
git clone https://github.com/nirannguyen50/Chatbot-Assitant-AI.git "Chatbot AI"
cd "Chatbot AI/backend"
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# Cài nginx làm reverse proxy
# Dùng systemd giữ server chạy liên tục
```

### Đổi sang PostgreSQL
```env
DATABASE_URL=postgresql://user:password@host:5432/chatbot_db
```
```powershell
pip install psycopg2-binary
```
Không cần đổi code — SQLAlchemy tự xử lý.

### Bảo mật production
```python
# app/main.py — giới hạn CORS
allow_origins=["https://yourdomain.com"]
```
```env
SECRET_KEY=<64-char-random-string>
DEBUG=false
```

---

## 12. Tech Stack & Chi phí

| Layer | Công nghệ | Phiên bản | Chi phí |
|-------|-----------|-----------|---------|
| LLM Chat | DeepSeek `deepseek-chat` | latest | ~$0.14/1M tokens |
| LLM Summarize | DeepSeek (Query Expansion + Summary) | latest | Tính vào trên |
| Embeddings | BAAI/bge-m3 (sentence-transformers) | local | **Miễn phí** |
| Vector DB | ChromaDB | local | **Miễn phí** |
| Database | SQLite (dev) / PostgreSQL (prod) | — | **Miễn phí** |
| Backend | FastAPI + Python | 3.10+ | **Miễn phí** |
| Markdown | marked.js | v9 (CDN) | **Miễn phí** |
| Server | Railway Hobby | — | $5/tháng |
| Domain | Cloudflare | — | $10/năm |

**Ước tính chi phí DeepSeek cho 1 chatbot hoạt động:**
```
Mỗi cuộc chat ~1 lần hỏi:
  - Query Expansion:  ~200 tokens
  - Câu trả lời:     ~800 tokens input + 300 output
  Tổng: ~1,300 tokens/chat

1,000 chat/tháng = 1.3M tokens = ~$0.18/tháng
So với GPT-4o: ~$10/tháng cùng lượng → tiết kiệm 50×
```

---

## 13. Troubleshooting

### Server không khởi động
```powershell
# Kiểm tra Python version (cần 3.10+)
python --version

# Kiểm tra .env có DEEPSEEK_API_KEY không
type .env

# Xem log lỗi chi tiết
venv\Scripts\python run.py
```

### Màn hình trắng khi vào dashboard
- Mở DevTools (F12) → tab Console → xem lỗi đỏ
- Hard refresh: Ctrl + Shift + R
- Kiểm tra server đang chạy: http://localhost:8000/health

### Upload tài liệu lỗi status "error"
```
Nguyên nhân thường gặp:
• PDF scan (ảnh) → không đọc được text → convert sang DOCX trước
• File bị password protect → remove password trước
• File quá lớn (>50MB) → chia nhỏ file
• Excel có cell merge phức tạp → flatten trước khi upload
```

### Chatbot không trả lời đúng
```
Kiểm tra theo thứ tự:
1. Document status = "ready"? (chunk_count > 0)
2. Hỏi lại đúng từ trong tài liệu — Query Expansion giúp nhưng không phải 100%
3. Thêm tài liệu dạng FAQ: "Q: ... A: ..." — dễ match nhất
4. System prompt có đủ context về vai trò chatbot chưa?
5. Thử tab Test Chat để xem câu trả lời trực tiếp
```

### ChromaDB lỗi dimension mismatch
```
Lỗi: "Collection dimension X ≠ Y"
Nguyên nhân: Đổi EMBEDDING_MODEL làm vector dimensions thay đổi
Giải pháp:
1. Xóa thư mục: D:\Chatbot AI\backend\chroma_db\
2. Reset tất cả documents về "pending" trong DB
3. Restart server
4. Upload lại tài liệu
```

### bcrypt lỗi khi đăng ký/đăng nhập
```powershell
pip install "bcrypt==4.2.1"
# Không dùng passlib — không tương thích với bcrypt 5.x
```

### Lịch sử hội thoại không lưu
```
Kiểm tra widget có gửi session_id không:
• Mở DevTools → Network → xem request body của /chat
• session_id phải là UUID string, không phải null
• Nếu thiếu → kiểm tra chatbot-widget.js có hàm genId() không
```

### ngrok "tunnel not found"
```
• Authtoken chưa cấu hình → chạy lại: .\ngrok.exe config add-authtoken TOKEN
• Free plan chỉ cho 1 tunnel → đóng tunnel cũ trước khi mở tunnel mới
• URL ngrok thay đổi mỗi lần restart → cập nhật lại data-api-url trong embed code
```

### DeepSeek API lỗi
```
401 Unauthorized  → Sai API key, kiểm tra .env
429 Too Many Req  → Rate limit, đợi hoặc upgrade plan
500 Server Error  → DeepSeek bị lỗi tạm thời, thử lại sau
Kiểm tra credit:  https://platform.deepseek.com/usage
```

### Upload ảnh trong widget không hoạt động
```
Kiểm tra:
1. Server có mount /uploads không?
   → Truy cập: http://localhost:8000/uploads/ (phải trả 200, không phải 404)
2. Thư mục uploads/ có tồn tại không?
   → Kiểm tra: D:\Chatbot AI\backend\uploads\
3. Ảnh có đúng định dạng không? (chỉ JPG, PNG, WEBP, GIF)
4. Ảnh có vượt 5MB không?
5. CORS: Widget trên domain khác cần server allow_origins đúng
```

### Bot không trả lời đúng ngôn ngữ
```
Nguyên nhân:
• Tin nhắn quá ngắn/ký tự ASCII thuần → không detect được → fallback về browser lang
• Browser lang không được gửi → fallback về tiếng Việt

Giải pháp:
• Widget luôn gửi navigator.language — kiểm tra DevTools → Network → request body
• Với tiếng Anh: dùng browser ngôn ngữ Anh hoặc gõ câu đủ dài
• Model DeepSeek có thể không tuân thủ tuyệt đối với ngôn ngữ ít phổ biến
```

### Email đặt lại mật khẩu không gửi được
```
Kiểm tra theo thứ tự:

1. SMTP_USER và SMTP_PASSWORD có trong .env chưa?
   → type .env | findstr SMTP

2. Dùng Gmail → phải là App Password (16 ký tự), KHÔNG phải mật khẩu Gmail thường
   → Bật 2FA: myaccount.google.com/security
   → Tạo App Password: myaccount.google.com/apppasswords

3. Lỗi "Username and Password not accepted"
   → App Password sai hoặc 2FA chưa bật

4. Lỗi "Connection refused" hoặc timeout
   → Kiểm tra SMTP_HOST=smtp.gmail.com, SMTP_PORT=587

5. Email gửi OK nhưng không nhận được
   → Kiểm tra thư mục Spam
   → BASE_URL trong .env phải đúng để link trong email hoạt động

6. Xem log server để debug:
   → Tìm dòng "Reset email sent to" hoặc "Failed to send reset email"
```

---

## 14. Changelog

### v1.8 — Widget Installer Guides
- **[Dashboard] Platform Selector**: Tab "Nhúng Widget" nay có 3 platform — Website, WordPress, Haravan
- **[Dashboard] WordPress Guide**: Hướng dẫn 2 cách — plugin "Insert Headers and Footers" (khuyến nghị) và chỉnh sửa `footer.php` trực tiếp
- **[Dashboard] Haravan Guide**: Hướng dẫn 5 bước cụ thể — vào Theme Editor, mở `theme.liquid`, dán code trước `</body>`

### v1.7 — Conversation Analytics Dashboard
- **[Dashboard] Tab Analytics**: Tab mới trong chatbot detail hiển thị 4 stat cards + bar chart theo ngày
- **[Backend] `GET /api/chatbots/{id}/analytics?days=7`**: Trả về tổng conversations, messages, leads, avg msgs/conv và daily breakdown
- **[Frontend] Chart.js v4**: Bar chart số conversations mỗi ngày, toggle 7/30 ngày
- **[Security]** Endpoint chỉ dành cho owner (JWT), `days` param clamp về [7, 90]

### v1.6 — Lead Capture Form trong Widget
- **[Widget] Lead Form**: Trước tin nhắn đầu tiên, widget hiện form thu thập Tên + Email (bắt buộc) + Số điện thoại (tùy chọn)
- **[Backend] Model `Lead`**: Bảng mới lưu lead, gắn với `session_id` (UNIQUE), cascade xóa theo chatbot
- **[Backend] `POST /api/widget/{api_key}/lead`**: Endpoint public nhận lead info, rate limit 10/minute, validate email qua Pydantic `EmailStr`
- **[Backend] `GET /api/chatbots/{id}/conversations`**: Enriched với `lead_name`, `lead_email`, `lead_phone` qua LEFT JOIN
- **[Widget] localStorage**: `sessionId` được persist qua refresh; flag `cw_lead_{key}` ngăn form hiện lại sau khi đã submit
- **[Dashboard] History tab**: Mỗi conversation row hiện badge `👤 Tên · email` nếu có lead
- **[Security] PII note**: Bảng `leads` chứa dữ liệu cá nhân (tên, email, phone) — khi deploy production cần tuân thủ chính sách bảo mật dữ liệu

### v1.5 — Đặt lại mật khẩu qua Email
- **[Auth] Forgot Password**: Luồng quên mật khẩu hoàn chỉnh — nhập email → nhận link → đặt mật khẩu mới
- **[Backend] Model `PasswordResetToken`**: Bảng mới lưu token hash (SHA-256), tự hết hạn sau 1 giờ, chỉ dùng 1 lần
- **[Backend] `POST /api/auth/forgot-password`**: Tạo token + gửi email trong background (không lộ email có tồn tại hay không)
- **[Backend] `POST /api/auth/reset-password`**: Validate token → cập nhật mật khẩu → đánh dấu token đã dùng
- **[Backend] `GET /reset-password`**: Serve trang HTML đặt lại mật khẩu
- **[Service] `email.py`**: Gửi email HTML qua SMTP bất đồng bộ (`aiosmtplib`), hỗ trợ Gmail App Password
- **[Config]** Thêm `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `BASE_URL` vào `.env`
- **[Dashboard] Link "Quên mật khẩu?"**: Hiển thị dưới form đăng nhập, chuyển sang view nhập email
- **[Dashboard] `reset-password.html`**: Trang riêng xử lý token từ URL, validate mật khẩu mới, redirect về login

### v1.4 — GitHub & Git Setup
- **[Repo]** Publish lên GitHub: https://github.com/nirannguyen50/Chatbot-Assitant-AI
- **[Git]** `.gitignore` loại trừ: `.env`, `venv/`, `chatbot.db`, `chroma_db/`, `uploads/`, `.claude/`
- **[Docs]** Thêm hướng dẫn clone từ GitHub vào mục Cài đặt
- **[Docs]** Sửa cấu trúc README (các mục troubleshooting bị lạc ra ngoài section)

### v1.3 — File Upload + Multi-language
- **[Widget] File Upload**: Nút 📎 đính kèm ảnh (JPG/PNG/WEBP/GIF, 5MB), thumbnail preview, upload lên server
- **[Widget] Multi-language Auto-detect**: Nhận diện 15+ ngôn ngữ từ nội dung tin nhắn (regex, không cần thư viện), kết hợp browser language hint
- **[Backend] `/api/widget/{key}/upload`**: Endpoint upload ảnh mới, lưu vào `uploads/widget/{chatbot_id}/`
- **[Backend] `/uploads`**: Static file serving cho ảnh chat
- **[Backend] Language detection**: `_detect_lang()` trong `rag.py`, inject explicit language rule vào system prompt
- **[Schema] `lang`**: Thêm field `lang` vào `ChatRequest`

### v1.2 — Markdown + Conversation History
- **[Widget/Dashboard] Markdown Rendering**: `marked.js` render bold, italic, bảng, code block cho bot messages
- **[Backend] Conversation History**: Bảng `conversations` + `conv_messages`, lưu mọi phiên chat
- **[Dashboard] Tab "📋 Lịch sử"**: Xem/xóa hội thoại, tin nhắn render Markdown
- **[API]** 3 endpoints mới: GET conversations, GET messages, DELETE conversation
- **[Widget]** Session ID tự sinh (UUID), gửi kèm mọi request để lưu history

### v1.1 — Running Summary + Query Expansion
- **[Backend] Running Summary**: Tóm tắt hội thoại dài (>8 tin) thành ≤120 từ bằng DeepSeek
- **[Backend] Query Expansion**: Sinh 3 biến thể đồng nghĩa của câu hỏi → search rộng hơn
- **[Backend] BAAI/bge-m3**: Nâng cấp embedding model (1024-dim, tốt nhất cho tiếng Việt)
- **[Backend] Excel/CSV support**: Parser cho `.xlsx`, `.xls`, `.csv`

### v1.0 — MVP
- RAG pipeline: upload → chunk → embed → ChromaDB → DeepSeek
- Multi-tenant: mỗi chatbot có collection riêng trong ChromaDB
- JWT auth, dashboard HTML, embeddable widget JS
