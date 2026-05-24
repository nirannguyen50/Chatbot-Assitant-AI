# Feature: Conversation Analytics Dashboard

> **Trạng thái:** Đang lên kế hoạch
> **Ước tính:** ~half day (M effort)

---

## Tóm tắt

Tab "Analytics" mới trong chatbot detail hiển thị 4 metrics từ dữ liệu đã có sẵn: tổng conversations, tổng messages, tổng leads, và avg messages/conversation. Kèm biểu đồ bar chart số conversations theo ngày (7 hoặc 30 ngày). Không cần migration — toàn bộ tính toán từ bảng `conversations`, `conv_messages`, `leads`.

---

## Luồng người dùng

1. Mở chatbot detail → click tab **"📊 Analytics"**
2. Dashboard tải số liệu từ `GET /api/chatbots/{id}/analytics?days=7`
3. Hiện 4 stat cards: Conversations | Messages | Leads | Avg msgs/conv
4. Biểu đồ bar chart: số conversations mỗi ngày trong 7 ngày gần nhất
5. Click **"30 ngày"** → chart cập nhật (không reload trang)

---

## Data Model

**Không cần migration mới.** Tất cả tính từ bảng hiện có:

| Metric | Nguồn dữ liệu |
|--------|---------------|
| Total conversations | `COUNT(*) FROM conversations WHERE chatbot_id=X` |
| Total messages | `COUNT(*) FROM conv_messages JOIN conversations` |
| Total leads | `COUNT(*) FROM leads WHERE chatbot_id=X` |
| Avg msgs/conv | `total_messages / total_conversations` |
| Daily conversations | `GROUP BY DATE(created_at)` trong N ngày gần nhất |

---

## API

### GET `/api/chatbots/{chatbot_id}/analytics`

**Auth:** JWT (owner only)
**Query param:** `days=7` (default 7, clamp 7–90)

**Response 200:**
```json
{
  "total_conversations": 42,
  "total_messages": 187,
  "total_leads": 15,
  "avg_messages_per_conv": 4.5,
  "daily_conversations": [
    {"date": "2026-05-18", "count": 3},
    {"date": "2026-05-19", "count": 7},
    ...
  ]
}
```

---

## Frontend

### Tab mới trong chatbot detail
- Thêm nút `<button class="tab" onclick="switchDetailTab('analytics')">📊 Analytics</button>`
- Thêm `<div id="dtab-analytics" style="display:none">` với:
  - 4 stat cards (grid 2×2 hoặc 4 cột)
  - Bộ chọn thời gian: `[7 ngày] [30 ngày]`
  - `<canvas id="analytics-chart">` cho Chart.js

### Chart.js
- Dùng CDN: `cdn.jsdelivr.net/npm/chart.js@4`
- Bar chart: trục X là date, trục Y là số conversations
- Primary color từ `currentBot.primary_color`
- Chart instance lưu trong biến để destroy/re-render khi đổi range

### `switchDetailTab` update
```js
// Thêm "analytics" vào array
["docs","chat","embed","history","analytics"]
// Thêm trigger:
if (tab === "analytics") loadAnalytics(7);
```

---

## Dependencies

| Thư viện | Cách thêm | Lý do |
|----------|-----------|-------|
| Chart.js v4 | CDN `<script>` | Bar chart nhẹ, không cần build step. Đã dùng pattern CDN tương tự marked.js |

---

## Edge Cases & Gotchas

| Tình huống | Xử lý |
|-----------|-------|
| Chatbot chưa có conversation | `total_conversations=0`, chart rỗng — hiện empty state |
| `days` param ngoài range | Clamp về `[7, 90]` phía backend |
| `total_conversations=0` → avg div/0 | Return `0.0` thay vì lỗi |
| Đổi tab nhanh, chart cũ còn render | Destroy chart cũ trước khi tạo mới |
| Ngày trong daily_conversations thiếu (không có conv) | Fill 0 cho các ngày missing |

---

## Security Checklist

| # | Item | Áp dụng? | Xử lý |
|---|------|----------|-------|
| 1 | Public endpoint? | Không | Endpoint có `get_current_user` + `_check_owner` |
| 2 | Credentials mới? | Không | — |
| 3 | Token expiry? | Không | — |
| 4 | PII? | Không | Chỉ aggregate counts, không expose tên/email |
| 5 | Config fail? | Không | Không env vars mới |
| 6 | Input validation? | **YES** | `days` clamp về [7, 90] |
| 7 | Auth/permission? | **YES** | Owner-only via `_check_owner` |
| 8 | Error leak? | **YES** | Chỉ 401/404 generic |

---

## E2E Test Cases

- [ ] `[Happy path]` GET /chatbots/{id}/analytics + token → 200 + tất cả fields có mặt
- [ ] `[days=30]` GET /chatbots/{id}/analytics?days=30 → 200 + daily_conversations.length=30
- [ ] `[Unauthorized]` GET /chatbots/{id}/analytics (no token) → 401
- [ ] `[Not owner]` GET /chatbots/{other_id}/analytics + valid token → 404
- [ ] `[days out of range]` GET analytics?days=200 → 200 với days clamped về 90
- [ ] `[Empty chatbot]` analytics cho chatbot chưa có chat → total_conversations=0, daily all zeros
- [ ] `[Dashboard]` Click tab Analytics → 4 stat cards render đúng số
- [ ] `[Dashboard]` Click "30 ngày" → chart cập nhật, không crash

---

## Definition of Done

- [x] Tất cả task phases đã implement
- [x] Security checklist 8/8 addressed
- [x] Tất cả E2E test cases pass
- [x] README.md đã update (changelog)
- [x] `.env.example` không đổi
- [ ] Commit với `/conventional-commit`

---

## Tasks

### Phase 1 — API
- [x] Thêm `AnalyticsOut` schema (inline trong `conversations.py`) (S)
- [x] Implement `GET /api/chatbots/{id}/analytics?days=7` trong `backend/app/api/conversations.py` (M)
  - COUNT conversations, messages, leads
  - Tính avg_messages_per_conv (guard div/0)
  - daily_conversations: GROUP BY DATE, fill zeros cho ngày missing

### Phase 2 — Dashboard Frontend
- [x] Thêm Chart.js CDN vào `dashboard/index.html` (S)
- [x] Thêm tab button "📊 Analytics" và `dtab-analytics` div (S)
- [x] Thêm CSS cho stat cards và time-range selector (S)
- [x] Cập nhật `switchDetailTab()` để include "analytics" (S)
- [x] Viết `loadAnalytics(days)`: fetch → render cards + chart (M)
- [x] Time-range selector: click "7 ngày" / "30 ngày" → gọi lại `loadAnalytics(N)` (S)

### Phase 3 — Docs
- [x] Update `README.md`: changelog v1.7 (S)
