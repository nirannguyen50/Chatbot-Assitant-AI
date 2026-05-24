# Feature: Đặt Lại Mật Khẩu Qua Email

> **Trạng thái:** ✅ Hoàn thành (Phase 1–4) — còn Phase 5 QA
> **Ước tính:** ~1 ngày (6–7 giờ)

---

## Tóm tắt

Thêm luồng quên mật khẩu chuẩn: người dùng nhập email → nhận link có token hợp lệ trong 1 giờ → click link → nhập mật khẩu mới. Token chỉ dùng được 1 lần và tự hết hạn.

---

## Luồng người dùng

1. Màn hình đăng nhập → click **"Quên mật khẩu?"**
2. Nhập địa chỉ email → nhấn **"Gửi link đặt lại"**
3. Nhận email có link dạng `https://domain.com/reset-password?token=xxxx`
4. Click link → mở trang nhập mật khẩu mới
5. Nhập mật khẩu mới + xác nhận → nhấn **"Đặt lại mật khẩu"**
6. Thành công → tự chuyển về màn hình đăng nhập

> **Bảo mật UX:** Bước 2 luôn hiện thông báo thành công dù email có tồn tại hay không.

---

## Data Model

### Bảng mới: `password_reset_tokens`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `id` | Integer PK | |
| `user_id` | Integer FK → users | |
| `token_hash` | String unique | SHA-256 của token gốc |
| `expires_at` | DateTime | `now + 1 giờ` |
| `used` | Boolean | default False |
| `created_at` | DateTime | |

> Lưu `token_hash` thay vì token thật — nếu DB bị lộ, token gốc vẫn an toàn.

---

## API

| Method | Endpoint | Auth | Mô tả |
|--------|----------|------|-------|
| `POST` | `/api/auth/forgot-password` | — | Nhận email, tạo token, gửi email |
| `POST` | `/api/auth/reset-password` | — | Nhận token + mật khẩu mới, cập nhật |
| `GET`  | `/reset-password` | — | Serve trang HTML đặt lại mật khẩu |

---

## Config mới (`.env`)

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your@gmail.com
BASE_URL=http://localhost:8000
```

**Thư viện mới:** `aiosmtplib`

---

## Edge Cases

| Tình huống | Xử lý |
|-----------|-------|
| Email không tồn tại | Trả `200` giả, không tiết lộ |
| Token hết hạn | `400 "Link đã hết hạn"` |
| Token đã dùng | `400 "Link đã được sử dụng"` |
| Spam forgot-password | Chỉ tạo token mới nếu token cũ hết hạn hoặc đã dùng |
| SMTP lỗi | Log lỗi, vẫn trả `200` |

---

## Tasks

### Phase 1 — Data Layer
- [x] Tạo `backend/app/models/password_reset.py`
- [x] Import vào `backend/app/models/__init__.py`
- [x] Thêm settings email vào `config.py` và `.env.example`

### Phase 2 — Email Service
- [x] Cài `aiosmtplib==3.0.2`, thêm vào `requirements.txt`
- [x] Tạo `backend/app/services/email.py`

### Phase 3 — API
- [x] Thêm schemas `ForgotPasswordRequest`, `ResetPasswordRequest`
- [x] Implement `POST /api/auth/forgot-password`
- [x] Implement `POST /api/auth/reset-password`
- [x] Thêm route `GET /reset-password` trong `main.py`

### Phase 4 — Frontend
- [x] Link "Quên mật khẩu?" trong form đăng nhập (`dashboard/index.html`)
- [x] View forgot-password + hàm `showForgot()`, `showLogin()`, `doForgot()`
- [x] Trang `dashboard/reset-password.html`

### Phase 5 — QA & Polish
- [ ] Test đủ luồng end-to-end
- [ ] Test edge cases (token hết hạn, đã dùng, email không tồn tại)
- [ ] Kiểm tra với ngrok (cập nhật BASE_URL)

---

## Files đã thay đổi

| File | Thay đổi |
|------|---------|
| `backend/app/models/password_reset.py` | **Mới** — model `PasswordResetToken` |
| `backend/app/models/__init__.py` | Import model mới |
| `backend/app/config.py` | Thêm `SMTP_*` và `BASE_URL` settings |
| `backend/app/.env.example` | Thêm hướng dẫn config email |
| `backend/app/schemas/auth.py` | Thêm `ForgotPasswordRequest`, `ResetPasswordRequest` |
| `backend/app/api/auth.py` | Thêm 2 endpoint forgot/reset password |
| `backend/app/main.py` | Thêm route `GET /reset-password` |
| `backend/app/services/email.py` | **Mới** — service gửi email SMTP |
| `backend/requirements.txt` | Thêm `aiosmtplib==3.0.2` |
| `dashboard/index.html` | Link quên mật khẩu + view forgot + JS functions |
| `dashboard/reset-password.html` | **Mới** — trang đặt lại mật khẩu |
