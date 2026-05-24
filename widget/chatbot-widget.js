/**
 * Chatbot Embed Widget
 * Cách dùng: <script src="widget.js" data-api-key="YOUR_KEY" data-api-url="https://yourserver.com"></script>
 *
 * Tính năng:
 * - Render Markdown (marked.js)
 * - Running Summary (nhớ hội thoại dài)
 * - File Upload (ảnh JPG/PNG/WEBP/GIF, tối đa 5MB)
 * - Multi-language Auto-detect (Việt, Anh, Nhật, Hàn, ...)
 */
(function () {
  "use strict";

  const script  = document.currentScript;
  const API_KEY = script?.getAttribute("data-api-key") || "";
  const API_URL = (script?.getAttribute("data-api-url") || "http://localhost:8000").replace(/\/$/, "");

  if (!API_KEY) {
    console.error("[ChatbotWidget] Thiếu data-api-key");
    return;
  }

  // ─── State ───────────────────────────────────────────────────────────────
  let config  = { name: "Chatbot", welcome_message: "Xin chào! Tôi có thể giúp gì?", primary_color: "#4F46E5" };
  let history = [];
  let summary = "";

  // Persist sessionId across page refreshes so lead isn't re-asked
  const LS_SESSION_KEY = `cw_session_${API_KEY}`;
  const LS_LEAD_KEY    = `cw_lead_${API_KEY}`;
  let sessionId = localStorage.getItem(LS_SESSION_KEY) || genId();
  if (!localStorage.getItem(LS_SESSION_KEY)) localStorage.setItem(LS_SESSION_KEY, sessionId);
  let leadSubmitted = !!localStorage.getItem(LS_LEAD_KEY);

  let attachedImgUrl  = "";   // URL ảnh đã upload, chờ gửi
  let isOpen    = false;
  let isLoading = false;

  // Detect browser language — dùng làm hint cho server
  const userLang = ((navigator.language || navigator.userLanguage || "vi").split("-")[0]).toLowerCase();

  function genId() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      return (c === "x" ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }

  // ─── Styles ──────────────────────────────────────────────────────────────
  const css = `
    #cw-root * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    #cw-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      width: 56px; height: 56px; border-radius: 50%; border: none; cursor: pointer;
      background: var(--cw-color); color: #fff; font-size: 24px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25); transition: transform .2s, box-shadow .2s;
      display: flex; align-items: center; justify-content: center;
    }
    #cw-btn:hover { transform: scale(1.08); box-shadow: 0 6px 20px rgba(0,0,0,0.3); }
    #cw-window {
      position: fixed; bottom: 92px; right: 24px; z-index: 9998;
      width: 360px; max-height: 580px; border-radius: 16px;
      background: #fff; box-shadow: 0 8px 40px rgba(0,0,0,0.18);
      display: flex; flex-direction: column; overflow: hidden;
      transition: opacity .2s, transform .2s;
    }
    #cw-window.cw-hidden { opacity: 0; transform: translateY(12px) scale(0.97); pointer-events: none; }
    #cw-header {
      padding: 16px 20px; background: var(--cw-color); color: #fff;
      display: flex; align-items: center; gap: 10px; flex-shrink: 0;
    }
    #cw-header .cw-avatar {
      width: 36px; height: 36px; border-radius: 50%; background: rgba(255,255,255,0.25);
      display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;
    }
    #cw-header .cw-title { font-weight: 600; font-size: 15px; }
    #cw-header .cw-subtitle { font-size: 12px; opacity: .8; }
    #cw-header .cw-close {
      margin-left: auto; background: none; border: none; color: #fff;
      cursor: pointer; font-size: 20px; opacity: .8; padding: 4px; line-height: 1;
    }
    #cw-messages {
      flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px;
      scroll-behavior: smooth;
    }
    .cw-msg {
      max-width: 82%; padding: 10px 14px; border-radius: 14px;
      font-size: 14px; line-height: 1.5; word-wrap: break-word;
    }
    .cw-msg.cw-user { align-self: flex-end; background: var(--cw-color); color: #fff; border-bottom-right-radius: 4px; }
    .cw-msg.cw-bot  { align-self: flex-start; background: #f1f5f9; color: #1e293b; border-bottom-left-radius: 4px; }
    .cw-msg.cw-typing { color: #94a3b8; font-style: italic; }
    .cw-msg.cw-user img {
      max-width: 200px; max-height: 180px; border-radius: 8px;
      display: block; margin-bottom: 4px; cursor: pointer;
    }

    /* ── Markdown (bot messages) ── */
    .cw-msg.cw-bot p { margin: 3px 0; }
    .cw-msg.cw-bot ul, .cw-msg.cw-bot ol { padding-left: 18px; margin: 4px 0; }
    .cw-msg.cw-bot li { margin: 2px 0; }
    .cw-msg.cw-bot h1, .cw-msg.cw-bot h2, .cw-msg.cw-bot h3 { font-size: 14px; font-weight: 700; margin: 6px 0 2px; }
    .cw-msg.cw-bot code { background: rgba(0,0,0,0.09); border-radius: 3px; padding: 1px 5px; font-family: monospace; font-size: 12px; }
    .cw-msg.cw-bot pre { background: #0f172a; color: #e2e8f0; border-radius: 8px; padding: 10px; margin: 6px 0; overflow-x: auto; font-size: 12px; line-height: 1.5; }
    .cw-msg.cw-bot pre code { background: none; padding: 0; color: inherit; }
    .cw-msg.cw-bot table { border-collapse: collapse; width: 100%; font-size: 12px; margin: 6px 0; }
    .cw-msg.cw-bot th, .cw-msg.cw-bot td { border: 1px solid #cbd5e1; padding: 4px 8px; text-align: left; }
    .cw-msg.cw-bot th { background: rgba(0,0,0,0.06); font-weight: 600; }
    .cw-msg.cw-bot a { color: var(--cw-color); }
    .cw-msg.cw-bot strong { font-weight: 700; }
    .cw-msg.cw-bot blockquote { border-left: 3px solid #cbd5e1; padding-left: 10px; margin: 4px 0; color: #64748b; font-style: italic; }

    /* ── Footer ── */
    #cw-footer { border-top: 1px solid #e2e8f0; display: flex; flex-direction: column; flex-shrink: 0; }

    /* ── Attach preview bar ── */
    #cw-attach-bar {
      display: none; align-items: center; gap: 8px;
      padding: 8px 14px 4px; background: #f8fafc; border-bottom: 1px solid #f1f5f9;
    }
    #cw-attach-bar.show { display: flex; }
    #cw-attach-thumb {
      width: 44px; height: 44px; object-fit: cover; border-radius: 6px;
      border: 1.5px solid #e2e8f0; flex-shrink: 0;
    }
    #cw-attach-name {
      flex: 1; min-width: 0; font-size: 12px; color: #64748b;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    #cw-attach-spinner { font-size: 13px; animation: cw-spin .8s linear infinite; flex-shrink: 0; }
    @keyframes cw-spin { to { transform: rotate(360deg); } }
    #cw-attach-rm {
      background: #fee2e2; border: none; border-radius: 50%; cursor: pointer;
      width: 20px; height: 20px; font-size: 11px; color: #dc2626;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }
    #cw-attach-rm:hover { background: #fecaca; }

    /* ── Input row ── */
    #cw-input-row { padding: 10px 14px; display: flex; gap: 8px; align-items: flex-end; }
    #cw-clip {
      width: 34px; height: 34px; border-radius: 8px; border: 1.5px solid #e2e8f0;
      cursor: pointer; background: #f8fafc; color: #64748b; font-size: 15px;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      transition: background .15s, border-color .15s;
    }
    #cw-clip:hover:not(:disabled) { background: #EEF2FF; border-color: var(--cw-color); color: var(--cw-color); }
    #cw-clip:disabled { opacity: .4; cursor: not-allowed; }
    #cw-input {
      flex: 1; border: 1.5px solid #e2e8f0; border-radius: 10px;
      padding: 8px 11px; font-size: 14px; resize: none; outline: none;
      max-height: 100px; min-height: 36px; line-height: 1.4; transition: border-color .2s;
    }
    #cw-input:focus { border-color: var(--cw-color); }
    #cw-send {
      width: 36px; height: 36px; border-radius: 10px; border: none; cursor: pointer;
      background: var(--cw-color); color: #fff; font-size: 16px;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; transition: opacity .2s;
    }
    #cw-send:disabled { opacity: .4; cursor: not-allowed; }

    .cw-cursor::after { content: "▌"; animation: cw-blink 0.7s steps(1) infinite; }
    @keyframes cw-blink { 50% { opacity: 0; } }

    /* ── Lead form ── */
    #cw-lead-form {
      flex: 1; padding: 20px 20px 16px; display: flex; flex-direction: column; gap: 12px;
      overflow-y: auto;
    }
    #cw-lead-form.cw-hidden { display: none; }
    #cw-lead-intro { font-size: 13px; color: #475569; line-height: 1.5; }
    .cw-field { display: flex; flex-direction: column; gap: 4px; }
    .cw-field label { font-size: 12px; font-weight: 600; color: #374151; }
    .cw-field label span { color: #ef4444; margin-left: 2px; }
    .cw-field input {
      border: 1.5px solid #e2e8f0; border-radius: 8px;
      padding: 8px 11px; font-size: 14px; outline: none; transition: border-color .2s;
    }
    .cw-field input:focus { border-color: var(--cw-color); }
    .cw-field input.cw-error { border-color: #ef4444; }
    .cw-field-hint { font-size: 11px; color: #94a3b8; }
    #cw-lead-submit {
      margin-top: 4px; padding: 10px; border: none; border-radius: 10px; cursor: pointer;
      background: var(--cw-color); color: #fff; font-size: 14px; font-weight: 600;
      transition: opacity .2s;
    }
    #cw-lead-submit:disabled { opacity: .5; cursor: not-allowed; }
    #cw-lead-error { font-size: 12px; color: #ef4444; text-align: center; min-height: 16px; }

    @media (max-width: 420px) {
      #cw-window { right: 8px; left: 8px; width: auto; bottom: 84px; }
      #cw-btn { bottom: 16px; right: 16px; }
    }
  `;

  // ─── Helpers ─────────────────────────────────────────────────────────────
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\n/g, "<br>");
  }

  function renderMarkdown(text) {
    if (window.marked) {
      try { return window.marked.parse(text); } catch (_) {}
    }
    return escapeHtml(text);
  }

  // Thêm tin nhắn vào khung chat
  // role: "user" | "bot"
  // imageUrl: optional — chỉ dùng cho user message (ảnh đính kèm)
  function appendMessage(role, text, imageUrl) {
    const msgs = document.getElementById("cw-messages");
    const div  = document.createElement("div");
    div.className = `cw-msg cw-${role === "user" ? "user" : "bot"}`;

    if (imageUrl && role === "user") {
      const img = document.createElement("img");
      img.src = imageUrl;
      img.alt = "Ảnh đính kèm";
      img.title = "Click để xem ảnh đầy đủ";
      img.addEventListener("click", () => window.open(imageUrl, "_blank"));
      div.appendChild(img);
    }

    if (text) {
      const span = document.createElement("span");
      span.style.display = "block";
      if (role === "user") {
        span.innerHTML = escapeHtml(text);
      } else {
        span.innerHTML = renderMarkdown(text);
      }
      div.appendChild(span);
    }

    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function setTyping(show) {
    let el = document.getElementById("cw-typing");
    if (show && !el) {
      const msgs = document.getElementById("cw-messages");
      el = document.createElement("div");
      el.id = "cw-typing";
      el.className = "cw-msg cw-bot cw-typing";
      el.textContent = "Đang soạn…";
      msgs.appendChild(el);
      msgs.scrollTop = msgs.scrollHeight;
    } else if (!show && el) {
      el.remove();
    }
  }

  // ─── API calls ───────────────────────────────────────────────────────────
  async function loadConfig() {
    try {
      const res = await fetch(`${API_URL}/api/chatbots/widget/${API_KEY}/config`);
      if (res.ok) config = await res.json();
    } catch (_) {}
  }

  async function loadMarked() {
    if (window.marked) return;
    await new Promise(resolve => {
      const s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/marked@9/marked.min.js";
      s.onload = resolve;
      s.onerror = resolve;
      document.head.appendChild(s);
    });
    if (window.marked) window.marked.setOptions({ breaks: true, gfm: true });
  }

  async function uploadImage(file) {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${API_URL}/api/widget/${API_KEY}/upload`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) throw new Error("Upload failed");
    const data = await res.json();
    return `${API_URL}${data.url}`;   // full URL
  }

  async function sendMessage(text) {
    const hasImg  = !!attachedImgUrl;
    const hasText = !!text.trim();
    if (isLoading || (!hasText && !hasImg)) return;

    isLoading = true;
    const input   = document.getElementById("cw-input");
    const sendBtn = document.getElementById("cw-send");
    const clipBtn = document.getElementById("cw-clip");
    input.disabled   = true;
    sendBtn.disabled = true;
    if (clipBtn) clipBtn.disabled = true;

    const imgUrl = attachedImgUrl;
    attachedImgUrl = "";
    const attachBar = document.getElementById("cw-attach-bar");
    if (attachBar) attachBar.classList.remove("show");

    appendMessage("user", text.trim(), imgUrl);

    let apiMsg = text.trim();
    if (imgUrl) {
      apiMsg = apiMsg
        ? `${apiMsg}\n\n[Khách đính kèm ảnh: ${imgUrl}]`
        : `[Khách đính kèm ảnh: ${imgUrl}]`;
    }

    history.push({ role: "user", content: apiMsg });
    setTyping(true);

    try {
      const res = await fetch(`${API_URL}/api/widget/${API_KEY}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message:    apiMsg,
          history:    history.slice(-10),
          summary,
          session_id: sessionId,
          lang:       userLang,
        }),
      });

      setTyping(false);

      if (!res.ok || !res.body) {
        appendMessage("bot", "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.");
        return;
      }

      // Create bot bubble immediately for streaming into
      const msgs   = document.getElementById("cw-messages");
      const bubble = document.createElement("div");
      bubble.className = "cw-msg cw-bot";
      const span = document.createElement("span");
      span.style.display = "block";
      span.className = "cw-cursor";
      bubble.appendChild(span);
      msgs.appendChild(bubble);
      msgs.scrollTop = msgs.scrollHeight;

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buf     = "";
      let rawText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        // SSE events are separated by double-newline
        const parts = buf.split("\n\n");
        buf = parts.pop(); // keep incomplete last chunk

        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data: ")) continue;
          let evt;
          try { evt = JSON.parse(line.slice(6)); } catch (_) { continue; }

          if (evt.token) {
            rawText += evt.token;
            span.textContent = rawText;
            span.className = "cw-cursor"; // keep blinking cursor
            msgs.scrollTop = msgs.scrollHeight;
          }

          if (evt.done) {
            span.className = ""; // remove cursor
            span.innerHTML = renderMarkdown(rawText || evt.answer || "");
            msgs.scrollTop = msgs.scrollHeight;

            const finalAnswer = evt.answer || rawText;
            history.push({ role: "assistant", content: finalAnswer });

            if (evt.summary) {
              summary = evt.summary;
              history = history.slice(-6);
            }
          }

          if (evt.error) {
            span.className = "";
            span.textContent = "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.";
          }
        }
      }

      // Handle any partial last buffer after stream closes
      if (buf.trim().startsWith("data: ")) {
        try {
          const evt = JSON.parse(buf.trim().slice(6));
          if (evt.done && rawText) {
            span.className = "";
            span.innerHTML = renderMarkdown(rawText);
          }
        } catch (_) {}
      }

      // Fallback: if no done event arrived but we have text, render it
      if (rawText && span.className === "cw-cursor") {
        span.className = "";
        span.innerHTML = renderMarkdown(rawText);
        history.push({ role: "assistant", content: rawText });
      }

    } catch (_) {
      setTyping(false);
      appendMessage("bot", "Không thể kết nối đến server. Vui lòng thử lại.");
    } finally {
      isLoading = false;
      input.disabled   = false;
      sendBtn.disabled = false;
      if (clipBtn) clipBtn.disabled = false;
      input.focus();
    }
  }

  // ─── UI Build ─────────────────────────────────────────────────────────────
  function buildWidget() {
    const style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);

    const root = document.createElement("div");
    root.id = "cw-root";
    root.style.setProperty("--cw-color", config.primary_color);

    root.innerHTML = `
      <button id="cw-btn" aria-label="Mở chat">💬</button>
      <div id="cw-window" class="cw-hidden" role="dialog" aria-label="Chat hỗ trợ">
        <div id="cw-header">
          <div class="cw-avatar">🤖</div>
          <div>
            <div class="cw-title">${escapeHtml(config.name)}</div>
            <div class="cw-subtitle">Trực tuyến</div>
          </div>
          <button class="cw-close" id="cw-close" aria-label="Đóng">✕</button>
        </div>
        <div id="cw-lead-form" class="cw-hidden" role="form" aria-label="Thông tin liên hệ">
          <p id="cw-lead-intro">Để hỗ trợ bạn tốt hơn, vui lòng cho biết thông tin liên hệ 😊</p>
          <div class="cw-field">
            <label for="cw-lead-name">Họ tên<span>*</span></label>
            <input id="cw-lead-name" type="text" placeholder="Nguyễn Văn A" autocomplete="name" maxlength="100">
          </div>
          <div class="cw-field">
            <label for="cw-lead-email">Email<span>*</span></label>
            <input id="cw-lead-email" type="email" placeholder="email@example.com" autocomplete="email" maxlength="200">
          </div>
          <div class="cw-field">
            <label for="cw-lead-phone">Số điện thoại <span style="color:#94a3b8;font-weight:400">(tùy chọn)</span></label>
            <input id="cw-lead-phone" type="tel" placeholder="0901 234 567" autocomplete="tel" maxlength="20">
          </div>
          <div id="cw-lead-error"></div>
          <button id="cw-lead-submit">Bắt đầu chat →</button>
        </div>
        <div id="cw-messages"></div>
        <div id="cw-footer">
          <div id="cw-attach-bar">
            <img id="cw-attach-thumb" src="" alt="">
            <span id="cw-attach-name"></span>
            <button id="cw-attach-rm" title="Xóa ảnh">✕</button>
          </div>
          <div id="cw-input-row">
            <button id="cw-clip" title="Đính kèm ảnh">📎</button>
            <textarea id="cw-input" placeholder="Nhập câu hỏi..." rows="1" aria-label="Tin nhắn"></textarea>
            <button id="cw-send" aria-label="Gửi">➤</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(root);
    // Welcome message hiện ngay nếu đã submit lead, hoặc sau khi submit lead form
    if (leadSubmitted) {
      appendMessage("bot", config.welcome_message);
    }

    // ── Element refs ─────────────────────────────────────────────────────
    const btn        = root.querySelector("#cw-btn");
    const win        = root.querySelector("#cw-window");
    const close      = root.querySelector("#cw-close");
    const input      = root.querySelector("#cw-input");
    const send       = root.querySelector("#cw-send");
    const clip       = root.querySelector("#cw-clip");
    const attachBar  = root.querySelector("#cw-attach-bar");
    const attachThumb = root.querySelector("#cw-attach-thumb");
    const attachName  = root.querySelector("#cw-attach-name");
    const attachRm    = root.querySelector("#cw-attach-rm");
    const leadForm    = root.querySelector("#cw-lead-form");
    const leadNameEl  = root.querySelector("#cw-lead-name");
    const leadEmailEl = root.querySelector("#cw-lead-email");
    const leadPhoneEl = root.querySelector("#cw-lead-phone");
    const leadSubmitEl = root.querySelector("#cw-lead-submit");
    const leadErrorEl  = root.querySelector("#cw-lead-error");
    const messages    = root.querySelector("#cw-messages");
    const footer      = root.querySelector("#cw-footer");

    // Hidden file input
    const fileInput = document.createElement("input");
    fileInput.type   = "file";
    fileInput.accept = "image/jpeg,image/png,image/webp,image/gif";
    fileInput.style.display = "none";
    document.body.appendChild(fileInput);

    function showChat() {
      leadForm.classList.add("cw-hidden");
      messages.style.display = "";
      footer.style.display = "";
    }

    function showLeadForm() {
      messages.style.display = "none";
      footer.style.display = "none";
      leadForm.classList.remove("cw-hidden");
      setTimeout(() => leadNameEl.focus(), 200);
    }

    // ── Lead form submit ──────────────────────────────────────────────────
    async function submitLead() {
      const name  = leadNameEl.value.trim();
      const email = leadEmailEl.value.trim();
      const phone = leadPhoneEl.value.trim();

      leadErrorEl.textContent = "";
      leadNameEl.classList.remove("cw-error");
      leadEmailEl.classList.remove("cw-error");

      if (!name) {
        leadNameEl.classList.add("cw-error");
        leadErrorEl.textContent = "Vui lòng nhập họ tên.";
        leadNameEl.focus();
        return;
      }
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        leadEmailEl.classList.add("cw-error");
        leadErrorEl.textContent = "Email không hợp lệ.";
        leadEmailEl.focus();
        return;
      }

      leadSubmitEl.disabled = true;
      leadSubmitEl.textContent = "Đang xử lý…";

      try {
        const res = await fetch(`${API_URL}/api/widget/${API_KEY}/lead`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, name, email, phone: phone || null }),
        });

        if (!res.ok && res.status !== 400) {
          throw new Error("server_error");
        }

        localStorage.setItem(LS_LEAD_KEY, "1");
        leadSubmitted = true;
        showChat();
        appendMessage("bot", `Xin chào ${escapeHtml(name)}! 👋 ${escapeHtml(config.welcome_message)}`);
        setTimeout(() => input.focus(), 200);

      } catch (_) {
        leadErrorEl.textContent = "Có lỗi xảy ra. Vui lòng thử lại.";
        leadSubmitEl.disabled = false;
        leadSubmitEl.textContent = "Bắt đầu chat →";
      }
    }

    leadSubmitEl.addEventListener("click", submitLead);
    [leadNameEl, leadEmailEl, leadPhoneEl].forEach(el => {
      el.addEventListener("keydown", e => { if (e.key === "Enter") submitLead(); });
    });

    // ── Toggle open/close ─────────────────────────────────────────────────
    function toggle() {
      isOpen = !isOpen;
      win.classList.toggle("cw-hidden", !isOpen);
      btn.textContent = isOpen ? "✕" : "💬";
      if (isOpen) {
        if (!leadSubmitted) {
          showLeadForm();
        } else {
          setTimeout(() => input.focus(), 200);
        }
      }
    }
    btn.addEventListener("click", toggle);
    close.addEventListener("click", toggle);

    // ── Send message ──────────────────────────────────────────────────────
    function doSend() {
      const text = input.value.trim();
      if (text || attachedImgUrl) {
        input.value = "";
        input.style.height = "auto";
        sendMessage(text);
      }
    }
    send.addEventListener("click", doSend);
    input.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); doSend(); }
    });
    input.addEventListener("input", () => {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 100) + "px";
    });

    // ── File upload ───────────────────────────────────────────────────────
    clip.addEventListener("click", () => fileInput.click());

    attachRm.addEventListener("click", () => {
      attachedImgUrl = "";
      attachBar.classList.remove("show");
      fileInput.value = "";
    });

    fileInput.addEventListener("change", async () => {
      const file = fileInput.files[0];
      if (!file) return;
      fileInput.value = "";

      // Check size client-side
      if (file.size > 5 * 1024 * 1024) {
        appendMessage("bot", "⚠️ Ảnh quá lớn. Vui lòng chọn ảnh dưới 5MB.");
        return;
      }

      // Show preview immediately with spinner
      const localUrl = URL.createObjectURL(file);
      attachThumb.src = localUrl;
      attachName.innerHTML = `<span id="cw-attach-spinner">⏳</span> Đang tải...`;
      attachBar.classList.add("show");
      clip.disabled = true;

      try {
        const serverUrl = await uploadImage(file);
        attachedImgUrl  = serverUrl;
        attachName.textContent = file.name;
      } catch (_) {
        attachedImgUrl = "";
        attachBar.classList.remove("show");
        appendMessage("bot", "⚠️ Không upload được ảnh. Vui lòng thử lại.");
      } finally {
        clip.disabled = false;
      }
    });
  }

  // ─── Init ────────────────────────────────────────────────────────────────
  async function init() {
    await Promise.all([loadConfig(), loadMarked()]);
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", buildWidget);
    } else {
      buildWidget();
    }
  }

  init();
})();
