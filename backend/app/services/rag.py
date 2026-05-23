"""
RAG pipeline với Query Expansion + Running Summary + Multi-language Auto-detect.

Luồng:
1. Language Detection: Detect ngôn ngữ từ nội dung tin nhắn (regex) + browser hint
2. Query Expansion: DeepSeek sinh 2-3 câu hỏi đồng nghĩa → search rộng hơn
3. Retrieve: ChromaDB tìm top chunks từ tất cả các query variants
4. Summarize (nếu cần): Khi history dài, tóm tắt phần cũ thành summary ngắn
5. Answer: DeepSeek trả lời đúng ngôn ngữ dựa trên context + summary + recent history
"""
from __future__ import annotations
import json
import re
from typing import AsyncGenerator, List, Optional, Set, Tuple
import httpx
from app.config import settings
from app.services.embeddings import embed_texts
from app.services.vector import search_similar_chunks

# ── Ngưỡng tóm tắt ────────────────────────────────────────────────────────
RECENT_LIMIT = 6       # Số tin nhắn gần nhất giữ nguyên (không tóm tắt)
SUMMARIZE_AT = 8       # Khi history >= 8 tin → tóm tắt phần cũ

# ── Language detection ────────────────────────────────────────────────────
# Map mã ngôn ngữ → tên đầy đủ để đưa vào prompt
_LANG_NAMES: dict[str, str] = {
    "vi": "tiếng Việt",
    "en": "English",
    "zh": "中文 (Chinese)",
    "ja": "日本語 (Japanese)",
    "ko": "한국어 (Korean)",
    "fr": "Français (French)",
    "de": "Deutsch (German)",
    "es": "Español (Spanish)",
    "th": "ภาษาไทย (Thai)",
    "id": "Bahasa Indonesia",
    "ms": "Bahasa Melayu (Malay)",
    "ar": "العربية (Arabic)",
    "pt": "Português (Portuguese)",
    "ru": "Русский (Russian)",
    "it": "Italiano (Italian)",
}

# Regex nhận dạng script / ký tự đặc trưng — theo thứ tự ưu tiên
_VIET_RE = re.compile(
    r"[àáảãạăắặẳẵằâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ"
    r"ÀÁẢÃẠĂẮẶẲẴẰÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]"
)
_KO_RE = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
_JA_RE = re.compile(r"[぀-ヿㇰ-ㇿ]")
_TH_RE = re.compile(r"[฀-๿]")
_AR_RE = re.compile(r"[؀-ۿݐ-ݿ]")
_ZH_RE = re.compile(r"[一-鿿㐀-䶿]")
_CYR_RE = re.compile(r"[Ѐ-ӿ]")  # Cyrillic (Russian, etc.)


def _detect_lang(message: str, lang_hint: str = "") -> str:
    """
    Phát hiện ngôn ngữ từ nội dung tin nhắn.
    Ưu tiên: nội dung > browser hint.
    """
    msg = message.strip()

    # Script detection (priority order)
    if _VIET_RE.search(msg):  return "vi"
    if _KO_RE.search(msg):    return "ko"
    if _JA_RE.search(msg):    return "ja"
    if _TH_RE.search(msg):    return "th"
    if _AR_RE.search(msg):    return "ar"
    if _ZH_RE.search(msg):    return "zh"
    if _CYR_RE.search(msg):   return "ru"

    # Pure ASCII / Latin → dùng browser hint nếu có
    if lang_hint:
        code = lang_hint.split("-")[0].lower()   # "en-US" → "en"
        return code if code in _LANG_NAMES else "en"

    return "vi"  # default — đa số user là người Việt


# ── Prompt templates ──────────────────────────────────────────────────────
_SYSTEM_TEMPLATE = """\
{lang_rule}

Bạn là trợ lý AI của doanh nghiệp, được huấn luyện dựa trên tài liệu nội bộ.

{custom_prompt}
{summary_block}
== THÔNG TIN TỪ TÀI LIỆU ==
{context}
== HẾT THÔNG TIN ==

Nguyên tắc:
- Chỉ trả lời dựa trên thông tin từ tài liệu trên.
- Nếu không tìm thấy thông tin liên quan, hãy thành thật thông báo cho khách (dùng đúng ngôn ngữ đã chỉ định).
- Ngắn gọn, rõ ràng, thân thiện.\
"""

_EXPAND_PROMPT = """\
Người dùng hỏi: "{query}"

Viết lại câu hỏi trên theo đúng 3 cách khác nhau, dùng từ đồng nghĩa hoặc \
cách diễn đạt khác nhưng giữ nguyên ý nghĩa. Cùng ngôn ngữ với câu gốc.
Chỉ trả về 3 câu, mỗi câu 1 dòng, không đánh số, không giải thích.\
"""

_SUMMARIZE_PROMPT = """\
Tóm tắt nội dung cuộc hội thoại dưới đây thành 1 đoạn ngắn gọn (tối đa 120 từ).
Giữ lại: thông tin quan trọng đã trao đổi, vấn đề khách đã hỏi, thông tin đã cung cấp.
{prev_summary}

Tin nhắn cần tóm tắt:
{messages}

Chỉ trả về đoạn tóm tắt, không giải thích thêm.\
"""


# ── Query Expansion ───────────────────────────────────────────────────────
async def _expand_query(query: str, client: httpx.AsyncClient) -> List[str]:
    if not settings.DEEPSEEK_API_KEY:
        return [query]
    try:
        resp = await client.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
            json={
                "model": settings.DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": _EXPAND_PROMPT.format(query=query)}],
                "max_tokens": 200,
                "temperature": 0.4,
            },
            timeout=10.0,
        )
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            variants = [q.strip() for q in text.split("\n") if q.strip()][:3]
            return [query] + variants
    except Exception:
        pass
    return [query]


# ── Retrieval with expansion ──────────────────────────────────────────────
async def _retrieve(
    chatbot_id: int,
    query: str,
    client: httpx.AsyncClient,
    top_k: int = 5,
) -> List[str]:
    queries = await _expand_query(query, client)
    vectors = embed_texts(queries)

    seen: Set[str] = set()
    merged: List[str] = []
    for vec in vectors:
        for chunk in search_similar_chunks(chatbot_id, vec, top_k=top_k):
            key = chunk.strip()
            if key not in seen:
                seen.add(key)
                merged.append(chunk)

    return merged[: top_k * 2]


# ── Summarization ─────────────────────────────────────────────────────────
async def _summarize(
    old_messages: List[dict],
    current_summary: str,
    client: httpx.AsyncClient,
) -> str:
    """Tóm tắt old_messages (+ summary hiện tại nếu có) thành 1 đoạn ngắn."""
    lines = "\n".join(
        f"{'Khách' if m['role'] == 'user' else 'Bot'}: {m['content']}"
        for m in old_messages
    )
    prev_block = (
        f"\nTóm tắt trước đó:\n{current_summary}\n"
        if current_summary else ""
    )
    prompt = _SUMMARIZE_PROMPT.format(prev_summary=prev_block, messages=lines)

    try:
        resp = await client.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
            json={
                "model": settings.DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.3,
            },
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass

    return current_summary  # fallback: giữ summary cũ nếu lỗi


# ── Streaming RAG function ────────────────────────────────────────────────
async def get_rag_answer_stream(
    chatbot_id: int,
    user_message: str,
    system_prompt: str = "",
    history: Optional[List[dict]] = None,
    summary: str = "",
    lang: str = "",
) -> AsyncGenerator[str, None]:
    """
    Async generator yielding SSE strings.
    Events: {"token": "..."} per LLM token, then {"done": true, "answer": "...", "summary": "..."}
    """
    if not settings.DEEPSEEK_API_KEY:
        yield 'data: {"error": "Chưa cấu hình DEEPSEEK_API_KEY."}\n\n'
        yield 'data: {"done": true, "answer": "", "summary": null}\n\n'
        return

    history = history or []
    new_summary: Optional[str] = None
    full_answer = ""

    detected = _detect_lang(user_message, lang)
    lang_name = _LANG_NAMES.get(detected, detected)
    lang_rule = (
        f"🌐 LANGUAGE RULE (HIGHEST PRIORITY): "
        f"The customer is communicating in {lang_name}. "
        f"You MUST reply ENTIRELY in {lang_name}. "
        f"Do NOT use any other language in your response, even for technical terms."
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        if len(history) >= SUMMARIZE_AT:
            old_msgs = history[:-RECENT_LIMIT]
            history  = history[-RECENT_LIMIT:]
            new_summary = await _summarize(old_msgs, summary, client)
            summary = new_summary

        chunks = await _retrieve(chatbot_id, user_message, client)
        context = "\n\n---\n\n".join(chunks) if chunks else "Không có tài liệu liên quan."

        summary_block = (
            f"\n== TÓM TẮT HỘI THOẠI TRƯỚC ==\n{summary}\n== HẾT TÓM TẮT ==\n\n"
            if summary else ""
        )
        final_system = _SYSTEM_TEMPLATE.format(
            custom_prompt=system_prompt.strip() + "\n" if system_prompt else "",
            summary_block=summary_block,
            context=context,
            lang_rule=lang_rule,
        )

        messages = [{"role": "system", "content": final_system}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        try:
            async with client.stream(
                "POST",
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.3,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        token = chunk["choices"][0]["delta"].get("content", "")
                        if token:
                            full_answer += token
                            yield f"data: {json.dumps({'token': token})}\n\n"
                    except Exception:
                        continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    yield f"data: {json.dumps({'done': True, 'answer': full_answer, 'summary': new_summary})}\n\n"


# ── Main RAG function ─────────────────────────────────────────────────────
async def get_rag_answer(
    chatbot_id: int,
    user_message: str,
    system_prompt: str = "",
    history: Optional[List[dict]] = None,
    summary: str = "",
    lang: str = "",           # Browser language hint ("vi", "en", "ja", ...)
) -> Tuple[str, Optional[str]]:
    """
    Trả về (answer, new_summary).
    new_summary = None nếu không có gì thay đổi.
    new_summary = string nếu vừa tóm tắt xong.
    """
    if not settings.DEEPSEEK_API_KEY:
        return "Chưa cấu hình DEEPSEEK_API_KEY.", None

    history = history or []
    new_summary: Optional[str] = None

    # 0. Language detection
    detected = _detect_lang(user_message, lang)
    lang_name = _LANG_NAMES.get(detected, detected)
    lang_rule = (
        f"🌐 LANGUAGE RULE (HIGHEST PRIORITY): "
        f"The customer is communicating in {lang_name}. "
        f"You MUST reply ENTIRELY in {lang_name}. "
        f"Do NOT use any other language in your response, even for technical terms."
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Tóm tắt nếu history quá dài
        if len(history) >= SUMMARIZE_AT:
            old_msgs = history[:-RECENT_LIMIT]
            history  = history[-RECENT_LIMIT:]
            new_summary = await _summarize(old_msgs, summary, client)
            summary = new_summary

        # 2. Retrieve context từ tài liệu
        chunks = await _retrieve(chatbot_id, user_message, client)
        context = "\n\n---\n\n".join(chunks) if chunks else "Không có tài liệu liên quan."

        # 3. Build system prompt
        summary_block = (
            f"\n== TÓM TẮT HỘI THOẠI TRƯỚC ==\n{summary}\n== HẾT TÓM TẮT ==\n\n"
            if summary else ""
        )
        final_system = _SYSTEM_TEMPLATE.format(
            custom_prompt=system_prompt.strip() + "\n" if system_prompt else "",
            summary_block=summary_block,
            context=context,
            lang_rule=lang_rule,
        )

        # 4. Build messages
        messages = [{"role": "system", "content": final_system}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        # 5. Gọi DeepSeek
        resp = await client.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.DEEPSEEK_MODEL,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"]

    return answer, new_summary
