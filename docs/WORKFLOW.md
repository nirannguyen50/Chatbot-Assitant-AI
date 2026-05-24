# Chatbot AI — Development Workflow

> Playbook cho solo developer. Mọi tính năng mới đều đi theo quy trình này, không bỏ bước.

---

## Tổng quan

```
IDEA → /brainstorm → /feature-planner → IMPLEMENT → /verify → /conventional-commit → DONE
```

Mỗi bước có skill hoặc checklist cụ thể. Không commit nếu verify chưa pass. Không verify nếu implement chưa xong hết phases. Không implement nếu chưa có plan.

---

## Phase 0 — Discovery (khi chưa biết làm gì tiếp)

**Skill:** `/brainstorm`

- Sinh ra 15–20 feature ideas theo categories: Growth, Retention, UX, AI, Integrations
- Có đánh giá Impact × Effort
- Chọn 1 idea → chuyển sang Phase 1

**Output cần có:** Tên feature + 1 câu mô tả lý do chọn

---

## Phase 1 — Planning

**Skill:** `/feature-planner`

Tạo file `docs/feature-<tên>.md` với đầy đủ:

- [ ] Summary + User Flow
- [ ] Data Model Changes (table, fields, migration notes)
- [ ] API Changes (endpoints, auth, business logic)
- [ ] Frontend Changes (pages, components, JS)
- [ ] Third-party Dependencies (lý do chọn)
- [ ] Edge Cases & Gotchas
- [ ] **Security Checklist** (8 items — xem bên dưới)
- [ ] **Documentation Changes** (liệt kê trước khi code)
- [ ] **E2E Test Cases** (define now, run in Phase 4)
- [ ] **Definition of Done**

> Rule: Nếu Security Checklist có item nào chưa có answer → chưa được implement.

### Security Checklist (8 items)

| # | Item | Áp dụng? | Xử lý thế nào? |
|---|------|----------|----------------|
| 1 | Public endpoints — cần rate limiting? | | |
| 2 | Credentials mới — nhận và lưu thế nào? | | |
| 3 | Token/session expiry + single-use enforcement | | |
| 4 | Sensitive data tích lũy trong DB (cần cleanup job?) | | |
| 5 | Config chưa set → fail silent hay warn loud khi startup? | | |
| 6 | Input validation tại mọi boundary (user input, external API) | | |
| 7 | Auth/permission trên mọi endpoint mới | | |
| 8 | Error messages có leak internal info không? | | |

**Output cần có:** File `docs/feature-<tên>.md` đầy đủ, user confirm plan trước khi code

---

## Phase 2 — Implementation

Thực hiện theo task breakdown trong feature plan. Thứ tự chuẩn:

### Phase 2a — Backend / Data Layer
- Tạo/sửa SQLAlchemy models
- Tạo Alembic migration: `alembic revision --autogenerate -m "<mô tả>"`
- Apply migration: `alembic upgrade head` (dev dùng `stamp head` nếu table đã tồn tại)
- Update `app/models/__init__.py`

### Phase 2b — API / Business Logic
- Thêm Pydantic schemas vào `app/schemas/`
- Viết route trong `app/api/`
- Thêm vào `app/main.py` nếu cần (middleware, startup hook)
- Rate limiting: dùng `@limiter.limit("X/hour")` từ `app/core/limiter.py`

### Phase 2c — Frontend
- Sửa `dashboard/index.html` hoặc tạo page mới
- JS thuần, không dùng framework
- Test trên browser (không chỉ dựa vào API test)

### Phase 2d — Docs
- Update `README.md`: changelog, API ref, architecture, config section
- Update `.env.example`: thêm env vars mới (ASCII-only comments)
- Update feature plan doc: tick checkbox các tasks đã done

**Constraint quan trọng:**
- `.env` và `alembic.ini` phải ASCII-only — không dùng tiếng Việt, không dùng em dash (—)
- JSON test payload phải write ra temp file, không inline trong PowerShell
- `bcrypt==4.2.1` — không upgrade lên 5.x

---

## Phase 3 — Verification

**Skill:** `/verify`

1. Tìm E2E test cases trong `docs/feature-<tên>.md`
2. Khởi động server nếu chưa chạy
3. Chạy từng test case bằng curl/PowerShell
4. Report pass/fail cho từng case

**Rule:** Không commit nếu còn bất kỳ test case nào fail.

### E2E Test Case Template
Mỗi case cần: input → expected HTTP status + response field

```
- [ ] [Happy path]     POST /api/... + valid data    → 200 + {"message": "..."}
- [ ] [Unauthorized]   GET /api/...  + no token      → 401
- [ ] [Validation]     POST /api/... + missing field  → 422
- [ ] [Not found]      GET /api/.../99999             → 404
- [ ] [Rate limit]     POST /api/... x4 rapid        → 429  (nếu có rate limiting)
- [ ] [Edge case]      ...specific to feature...
```

---

## Phase 4 — Commit

**Skill:** `/conventional-commit`

1. `git diff HEAD` — review toàn bộ changes
2. Stage tất cả files liên quan đến feature (code + docs cùng nhau)
3. **Không stage:** `.env`, `*.db`, `chroma_db/`, `uploads/`, `__pycache__/`
4. Draft commit message theo format:

```
feat(scope): mô tả ngắn gọn, imperative mood

Body (nếu cần): giải thích WHY, không giải thích WHAT.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

5. Show commit message → user confirm → execute

**Rule:** Code + docs trong 1 commit duy nhất. Không tách riêng.

---

## Definition of Done (checklist cuối)

Feature được coi là DONE khi TẤT CẢ các điều sau đều true:

- [ ] Tất cả task phases trong feature plan đã implement
- [ ] Security checklist đã address đủ 8 items
- [ ] Tất cả E2E test cases đều pass (chạy qua `/verify`)
- [ ] README.md đã update (changelog, API ref, config)
- [ ] `.env.example` đã thêm env vars mới nếu có
- [ ] Commit đã tạo với `/conventional-commit` (code + docs cùng nhau)

---

## Stack Reference (nhanh)

| Layer | Tech |
|---|---|
| Backend | FastAPI + Python 3.11 |
| ORM | SQLAlchemy + Alembic |
| DB | SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT via python-jose |
| Password hashing | `bcrypt==4.2.1` (không upgrade) |
| AI | DeepSeek API + ChromaDB + BAAI/bge-m3 |
| Email | aiosmtplib + Gmail SMTP |
| Rate limiting | slowapi==0.1.9 |
| Frontend | Vanilla JS + HTML |
| Config | python-dotenv, `.env` ASCII-only |

---

## Secrets Convention

- Secrets luôn vào `.env` trực tiếp — không qua chat, không qua code comment
- `.env` trong `.gitignore`, không bao giờ commit
- `.env.example` có đủ keys nhưng giá trị là placeholder
- Comments trong `.env` và `.ini` phải ASCII-only (Windows cp1252)

---

## Skill Map

| Khi nào | Skill |
|---|---|
| Không biết làm feature gì tiếp | `/brainstorm` |
| Bắt đầu implement feature mới | `/feature-planner` |
| Xong implement, cần test | `/verify` |
| Verify pass, cần commit | `/conventional-commit` |
| Muốn review code trước commit | `/code-review` |
