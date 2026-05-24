# Feature: Widget Installer Guides (WordPress / Haravan)

## Summary

Mo rong tab "Nhung Widget" trong dashboard -- hien chi co 1 doan script tag -- thanh mot trang huong dan co chon platform. User chon WordPress hoac Haravan, nhan ngay huong dan tung buoc bang tieng Viet kem embed code da tich hop san API key cua bot do. Khong co backend changes.

## User Flow

1. User vao Dashboard -> chon mot chatbot -> tab "Nhung Widget"
2. Thay 3 lua chon: Website thuong / WordPress / Haravan
3. Mac dinh la "Website thuong" (hanh vi hien tai)
4. Khi chon WordPress -> hien thi huong dan tung buoc
5. Khi chon Haravan -> hien thi huong dan Haravan
6. Embed code tu dong hien thi dung api_key cua bot dang chon
7. Nut "Copy code" hoat dong o moi platform

## Data Model Changes

Khong co. Pure frontend feature.

## API / Backend Changes

Khong co. Embed code duoc generate o client (dashboard/index.html line 741-743).

## Frontend Changes

File: `dashboard/index.html` -- khu vuc `#dtab-embed`

1. Platform selector -- 3 buttons: Website | WordPress | Haravan
2. Panel "Website" (default): giu nguyen embed code block + copy + security note
3. Panel "WordPress": huong dan 3 buoc + embed code + copy button
4. Panel "Haravan": huong dan 3 buoc + embed code + copy button

## Security Checklist

| # | Item | Applies? | How to handle |
|---|------|----------|---------------|
| 1 | Public endpoints -- rate limiting? | No | Khong co endpoint moi |
| 2 | Credentials moi? | No | API key da co |
| 3 | Token/session expiry? | No | N/A |
| 4 | Sensitive data? | No | Khong luu gi them |
| 5 | Config chua set -> fail? | No | Khong co config moi |
| 6 | Input validation? | No | Khong co user input moi |
| 7 | Auth/permission? | No | Tab embed da sau auth |
| 8 | Error messages leak? | No | Khong co API call moi |

## Documentation Changes

- `README.md` -- them vao changelog v1.6, muc Widget Installation trong Features section

## Definition of Done

- [ ] Platform selector hien thi dung 3 tab
- [ ] Moi platform hien huong dan tung buoc bang tieng Viet
- [ ] Embed code (voi API key dung) hien thi va copy duoc o ca 3 platform
- [ ] Switch bot trong khi o tab WordPress/Haravan -> embed code van dung
- [ ] README cap nhat
- [x] /verify pass toan bo E2E cases
- [ ] Commit 1 lan voi /conventional-commit

## Tasks

### Phase 1: Frontend -- Platform Selector UI
- [x] Them 3 buttons platform selector vao #dtab-embed
- [x] Tao 3 panel div: #embed-panel-web, #embed-panel-wordpress, #embed-panel-haravan
- [x] Viet JS function switchEmbedPlatform(platform) -- toggle panel visibility

### Phase 2: Frontend -- Noi dung huong dan
- [x] Viet noi dung panel WordPress: 2 cach (plugin + manual), 3 buoc, code highlight
- [x] Viet noi dung panel Haravan: 3 buoc, luu y ve theme.liquid
- [x] Dam bao embed code block hien thi dung trong ca 3 panel, copyEmbed() copy dung panel active

### Phase 3: Docs
- [x] Update README.md: them changelog, muc Widget Installation trong Features

### Phase 4: Verify & Commit
- [ ] Run /verify -- kiem tra toan bo E2E cases
- [ ] Run /conventional-commit -- code + docs cung 1 commit

## E2E Test Cases

- [ ] [Happy path - Web] Mo tab Embed, platform mac dinh = Website, embed code hien thi dung api_key
- [ ] [Switch platform] Click "WordPress" -> panel WordPress hien thi, panel Web an, embed code dung
- [ ] [Switch platform] Click "Haravan" -> panel Haravan hien thi, noi dung dung
- [ ] [Copy - WordPress] Dang o panel WordPress, click Copy -> clipboard co dung script tag
- [ ] [Switch bot] Dang xem WordPress guide -> switch sang bot khac -> embed code refresh dung api_key moi
- [ ] [Switch back] Click "Website" -> ve trang thai ban dau
