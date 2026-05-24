# Feature: Lead Capture Form trong Widget

> **Trạng thái:** Đang lên kế hoạch
> **Ước tính:** ~1 ngày (M effort)

---

## Tóm tắt

Trước khi chat lần đầu, widget hiện form thu thập thông tin liên hệ: Tên (bắt buộc), Email (bắt buộc), Số điện thoại (tùy chọn). Lead được lưu vào DB, gắn với `session_id`. Chatbot owner xem lead info trong tab History — mỗi conversation hiện badge tên/email/phone của khách.

---

## Luồng người dùng

1. Khách click mở widget lần đầu (hoặc session mới)
2. Form hiện: "Để hỗ trợ bạn tốt hơn, vui lòng cho biết thông tin liên hệ"
3. Nhập **Tên*** + **Email*** + Số điện thoại (optional) → nhấn **Bắt đầu chat**
4. Lead POST đến API → form ẩn → chat hiện với lời chào "Xin chào {name}! 👋"
5. `sessionId` + flag `leadSubmitted` lưu vào `localStorage` → mở lại trang form không hiện lại
6. Dashboard History: mỗi conversation row có badge tên/email/phone phía trên

---

## Data Model

### Bảng mới: `leads`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `id` | Integer PK | |
| `chatbot_id` | Integer FK → chatbots | Để query nhanh per-chatbot |
| `session_id` | String(64) UNIQUE | Khớp với `conversations.session_id` |
| `name` | String(100) | Bắt buộc |
| `email` | String(200) | Bắt buộc, validate format |
| `phone` | String(20) nullable | Tùy chọn |
| `created_at` | DateTime | |

> `session_id` là UNIQUE — mỗi session chỉ có 1 lead. Nếu gửi lại cùng session → 400.

---

## API

| Method | Endpoint | Auth | Mô tả |
|--------|----------|------|-------|
| `POST` | `/api/widget/{api_key}/lead` | — (public) | Widget submit lead info |
| `GET`  | `/api/chatbots/{id}/conversations` | JWT | Giữ nguyên nhưng thêm `lead_name`, `lead_email`, `lead_phone` |

### POST /api/widget/{api_key}/lead
**Request body:**
```json
{
  "session_id": "uuid",
  "name": "Nguyễn Văn A",
  "email": "vana@gmail.com",
  "phone": "0901234567"
}
```
**Response 200:**
```json
{ "ok": true }
```
**Response 400:** session_id đã có lead
**Response 422:** validation error (email sai format, name thiếu)
**Rate limit:** `@limiter.limit("10/minute")`

---

## Widget Changes

### localStorage keys (per API_KEY)
- `cw_session_{API_KEY}` — lưu `sessionId` để persist qua refresh
- `cw_lead_{API_KEY}` — `"1"` nếu đã submit lead

### Flow khi mở widget
```
openWidget()
  ↓
leadSubmitted? ──YES──→ show chat (behavior hiện tại)
     ↓ NO
  show #cw-lead-form (ẩn #cw-messages + #cw-footer)
     ↓ user submit
  POST /lead
     ↓ success
  localStorage.setItem(LS_LEAD_KEY, "1")
  ẩn form → hiện chat → appendMessage("bot", "Xin chào {name}! 👋 ...")
```

---

## Dashboard Changes

`ConversationOut` schema thêm 3 fields nullable:
- `lead_name: Optional[str]`
- `lead_email: Optional[str]`
- `lead_phone: Optional[str]`

`list_conversations` query: LEFT JOIN `leads` theo `session_id`.

History tab UI: mỗi conversation item hiện chip/badge `👤 {name} · {email}` (nếu có lead).

---

## Security Checklist

| # | Item | Áp dụng? | Xử lý |
|---|------|----------|-------|
| 1 | Public endpoints — rate limiting? | **YES** | `@limiter.limit("10/minute")` trên `POST /lead` |
| 2 | Credentials mới? | Không | — |
| 3 | Token/session expiry? | Không | — |
| 4 | PII tích lũy trong DB? | **YES** | Leads chứa name/email/phone — PII. MVP chưa cần cleanup job, nhưng cần note trong README. |
| 5 | Config chưa set → fail silent? | Không | Không có env vars mới |
| 6 | Input validation? | **YES** | `EmailStr` (Pydantic), `name` max 100 chars, `phone` max 20 chars |
| 7 | Auth/permission trên endpoints mới? | **YES** | `POST /lead` public (đúng — widget không có auth). `GET conversations` đã có owner auth. |
| 8 | Error messages leak internal info? | **YES** | Chỉ trả 400/422 generic, không expose DB errors |

---

## E2E Test Cases

- [ ] `[Happy path]` POST /widget/{key}/lead + valid data → 200 `{"ok": true}`
- [ ] `[Invalid email]` POST /widget/{key}/lead + `email: "notanemail"` → 422
- [ ] `[Missing name]` POST /widget/{key}/lead + thiếu `name` → 422
- [ ] `[Missing phone]` POST /widget/{key}/lead + không có `phone` → 200 (phone optional)
- [ ] `[Duplicate session]` POST /widget/{key}/lead cùng session_id 2 lần → 400
- [ ] `[Invalid api_key]` POST /widget/INVALID_KEY/lead → 401
- [ ] `[Rate limit]` POST /widget/{key}/lead x11 rapid → 429
- [ ] `[Widget UX]` Mở widget lần đầu → form hiện, chat ẩn
- [ ] `[Widget UX]` Submit form valid → form ẩn, chat mở với "Xin chào {name}!"
- [ ] `[Widget UX]` Refresh trang → form không hiện lại (localStorage flag)
- [ ] `[Widget UX]` Xóa localStorage → mở widget → form hiện lại
- [ ] `[Dashboard]` History tab: conversation có lead hiện badge tên + email

---

## Definition of Done

- [x] Tất cả task phases đã implement
- [x] Security checklist 8/8 addressed
- [x] Tất cả E2E test cases pass
- [x] README.md đã update (changelog + PII note)
- [x] `.env.example` không đổi (không có env vars mới)
- [ ] Commit với `/conventional-commit`

---

## Tasks

### Phase 1 — Data Layer
- [x] Tạo `backend/app/models/lead.py` với model `Lead` (S)
- [x] Import `Lead` vào `backend/app/models/__init__.py` (S)
- [x] Chạy `alembic revision --autogenerate -m "add leads table"` (S)
- [x] Chạy `alembic upgrade head` (S)

### Phase 2 — API / Business Logic
- [x] Thêm schema `LeadCreate` vào `backend/app/schemas/chat.py` (S)
- [x] Thêm `POST /api/widget/{api_key}/lead` vào `backend/app/api/chat.py`, rate limit 10/min (S)
- [x] Cập nhật `ConversationOut` trong `backend/app/api/conversations.py`: thêm `lead_name`, `lead_email`, `lead_phone` (S)
- [x] Cập nhật `list_conversations` query: LEFT JOIN `leads` theo `session_id` (S)

### Phase 3 — Widget JS
- [x] Persist `sessionId` trong `localStorage` (key `cw_session_{API_KEY}`) (S)
- [x] Thêm CSS cho `#cw-lead-form` vào `widget/chatbot-widget.js` (S)
- [x] Thêm HTML cho lead form vào `buildWidget()` (S)
- [x] Logic: khi open widget, nếu chưa submit lead → show form (ẩn messages + footer) (M)
- [x] `submitLead()`: validate client-side → POST → lưu localStorage → ẩn form → show chat với lời chào (M)

### Phase 4 — Dashboard UI
- [x] Update History tab trong `dashboard/index.html`: hiện lead badge trên mỗi conversation row (S)

### Phase 5 — Docs
- [x] Update `README.md`: changelog v1.6, mô tả feature, PII note (S)
