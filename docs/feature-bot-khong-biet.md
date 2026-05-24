# Feature: "Bot khong biet" Detector

## Summary

Khi bot tra loi bang cach thua nhan khong co thong tin, he thong tu dong danh dau tin nhan do la is_unanswered=True. Tab Analytics hien thi them section "Cau hoi chua duoc tra loi" de owner biet can bo sung tai lieu gi.

## User Flow

1. Khach chat hoi dieu bot khong co trong tai lieu
2. Bot tra loi kieu "Toi khong co thong tin ve van de nay"
3. He thong phat hien pattern -> danh dau tin nhan is_unanswered=True trong DB
4. Owner vao Dashboard -> chon chatbot -> tab Analytics
5. Ben duoi chart thay section "Cau hoi chua duoc tra loi (N)"
6. Danh sach hien thi: cau hoi goc cua khach | ngay gio | link mo conversation
7. Owner doc -> biet can upload them tai lieu gi

## Data Model Changes

Bang conv_messages -- them 1 cot:
- is_unanswered: Boolean, default False
- Chi set True cho role="assistant" messages

Migration: alembic revision --autogenerate -m "add is_unanswered to conv_messages"

## API Changes

1. GET /api/chatbots/{id}/analytics -- them field total_unanswered: int
2. GET /api/chatbots/{id}/unanswered?limit=50 -- danh sach cau hoi chua tra loi
   - Auth: JWT owner-only
   - Response: [{question, asked_at, conv_id, session_id}]

## Detection Patterns (regex, case-insensitive)

- "khong co thong tin"
- "khong tim thay thong tin"
- "khong co trong tai lieu"
- "tai lieu khong de cap"
- "chua co thong tin"
- "ngoai pham vi"
- "khong the tra loi"
- "xin loi...khong (co|the|biet)"
- "i don't have information"
- "i'm not sure"
- "not in/within documents/knowledge"
- "unable to answer/find/provide"

## Frontend Changes

File: dashboard/index.html -- tab #dtab-analytics

1. Stat card thu 5: "Chua tra loi" (do nhat)
2. Section #unanswered-section ben duoi chart
3. JS loadUnanswered() -- fetch /unanswered, render danh sach

## Security Checklist

| # | Item | Applies? | How to handle |
|---|------|----------|---------------|
| 1 | Public endpoints -- rate limiting? | No | Endpoint owner-only (JWT) |
| 2 | Credentials moi? | No | Khong co secret moi |
| 3 | Token/session expiry? | No | Dung JWT auth da co |
| 4 | Sensitive data tich luy? | Partial | is_unanswered chi la boolean, khong luu them PII |
| 5 | Config chua set -> fail? | No | Khong co config moi |
| 6 | Input validation? | Yes | limit param: clamp ve [1, 200] |
| 7 | Auth/permission? | Yes | Dung _check_owner() da co -- 404 neu khong phai owner |
| 8 | Error messages leak? | No | HTTPException standard |

## Documentation Changes

- README.md -- changelog v1.9, feature description, API ref cho endpoint moi va field moi

## Definition of Done

- [ ] Alembic migration chay duoc (upgrade + downgrade)
- [ ] is_unanswered duoc set dung khi bot tra loi "khong biet"
- [ ] GET /api/chatbots/{id}/unanswered tra dung danh sach
- [ ] Analytics endpoint tra them total_unanswered
- [ ] Dashboard hien thi section cau hoi chua tra loi dung data
- [ ] Tat ca E2E test cases pass (/verify)
- [ ] README cap nhat
- [ ] Commit 1 lan voi /conventional-commit

## Tasks

### Phase 1: Data Layer
- [x] Them is_unanswered column vao ConvMessage model (backend/app/models/conversation.py)
- [x] Chay alembic revision --autogenerate va review migration
- [x] Chay alembic upgrade head

### Phase 2: Backend -- Detection Logic
- [x] Them _UNANSWERED_RE regex va ham _is_unanswered() vao backend/app/api/chat.py
- [x] Sua _save_messages(): set is_unanswered=_is_unanswered(bot_answer) cho assistant message

### Phase 3: Backend -- API
- [x] Them schema UnansweredQuestion vao conversations.py
- [x] Them field total_unanswered vao AnalyticsOut va tinh trong get_analytics()
- [x] Them endpoint GET /{chatbot_id}/unanswered

### Phase 4: Frontend
- [x] Them stat card "Chua tra loi" vao #analytics-cards
- [x] Them section #unanswered-section ben duoi chart
- [x] Viet JS loadUnanswered() va goi trong loadAnalytics()

### Phase 5: Docs
- [x] Update README.md: changelog v1.9, feature description, API ref

### Phase 6: Verify & Commit
- [x] Run /verify
- [ ] Run /conventional-commit

## E2E Test Cases

- [ ] [Detection match] Chat cau hoi khong co trong tai lieu -> bot "khong co thong tin" -> /unanswered tra ve cau hoi do
- [ ] [Detection no match] Chat cau hoi co trong tai lieu -> bot tra loi dung -> /unanswered khong co entry moi
- [ ] [Analytics count] GET /analytics co field total_unanswered dung so
- [ ] [Auth] GET /unanswered khong co token -> 403
- [ ] [Auth] GET /unanswered cua chatbot nguoi khac -> 404
- [ ] [Limit] GET /unanswered?limit=2 chi tra toi da 2 items
- [ ] [UI] Tab Analytics hien thi stat card "Chua tra loi" va section danh sach dung data
