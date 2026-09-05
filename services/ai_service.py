import asyncio
import logging
from groq import AsyncGroq
from config import get_settings
from services.supabase_service import get_session_history
from services.rag_service import retrieve_async, format_context
from services.gemini_service import get_gemini_reply

logger = logging.getLogger(__name__)

settings = get_settings()
_groq_client = AsyncGroq(api_key=settings.groq_api_key)

GROQ_MODEL = "openai/gpt-oss-20b"
GROQ_TEMPERATURE = 0.4
GROQ_MAX_TOKENS = 1200
MAX_HISTORY_MESSAGES = 20
# Message *count* alone doesn't bound request size - a handful of long AI
# replies (detailed answers, previously tables) can still add up to a
# payload Groq's gateway rejects outright with 413 Payload Too Large once a
# session runs long enough. That comes back as an unhandled exception -> 500,
# which is what "can't send messages anymore after a while" actually was.
# Trim by content size too, on top of the count cap.
MAX_HISTORY_CHARS = 6000
# The indexed corpus is only 6 chunks total (3 per document) - retrieve all of
# it every time rather than relying on similarity ranking to guess which
# chunks a short/vague follow-up ("how much does it cost?") actually needs.
# Tried top_k=3 to reduce token usage; it silently dropped the pricing/RERA
# chunk on vague queries and made the bot falsely claim the info didn't
# exist, which is worse than the token savings were worth on a corpus this
# small. Revisit if the document set grows enough that "everything" stops
# being cheap.
RAG_TOP_K = 6

_GROQ_SYSTEM = (
    "You are Scube AI, a helpful and concise AI assistant. "
    "Use the conversation history to stay consistent with earlier messages. "
    "When context from documents is provided, prioritize answering from that context.\n\n"
    "State facts directly and confidently. Never add disclaimers, hedging, or suggestions to verify "
    "information elsewhere (e.g. 'this may be subject to change', 'please confirm with the developer') "
    "- the provided context is authoritative, so just answer.\n\n"
    "Match the length and format of your answer to the question. A simple or narrow question "
    "(yes/no, a single fact, 'why should I...') gets a short direct answer in a sentence or a few bullet "
    "points - do not build a table for it. Reserve tables for when the user is comparing multiple "
    "structured attributes across items (e.g. pricing tiers, unit specifications) and keep each cell to a "
    "single line. Never use raw HTML tags such as '<br>' anywhere, including inside table cells - "
    "if a cell needs more than one point, separate them with '; ' instead, or drop the table for a bullet list.\n\n"
    "Always format your responses in Markdown. "
    "When your response includes a phone number, format it as a tap-to-call link: [+91 XXXXX XXXXX](tel:+91XXXXXXXXXX). "
    "When your response includes a physical address or location, format it as a tap-to-map link: [Full Address](https://maps.google.com/?q=Full+Address+URL+Encoded). "
    "If the provided context includes an explicit MAP: link for that location, use that exact link instead of constructing one. "
    "When your response includes a website, format it as a standard markdown link: [site name](https://url). "
    "When your response references a document mentioned in the provided context, link to it using the "
    "exact 'link:' URL given alongside that source, formatted as [document name](that exact link) so the "
    "user can tap to open it directly in the app. Never invent or alter a document URL."
)


def _trim_history_by_size(messages: list[dict], max_chars: int) -> list[dict]:
    """Drop the oldest messages until total content size is under max_chars,
    always keeping at least the most recent one even if it alone exceeds it."""
    total = sum(len(m["content"]) for m in messages)
    start = 0
    while total > max_chars and start < len(messages) - 1:
        total -= len(messages[start]["content"])
        start += 1
    return messages[start:]


async def get_ai_reply(session_id: str) -> str:
    history = await asyncio.to_thread(get_session_history, session_id)
    trimmed = _trim_history_by_size(history[-MAX_HISTORY_MESSAGES:], MAX_HISTORY_CHARS)

    user_messages = [m for m in trimmed if m["role"] == "user"]
    last_query = user_messages[-1]["content"] if user_messages else ""

    context_chunks: list[dict] = []
    if last_query:
        try:
            context_chunks = await retrieve_async(last_query, top_k=RAG_TOP_K)
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

    # Gemini primary: ~31x more free-tier headroom than Groq (250k vs 8k tokens/min),
    # which is what actually matters given we resend the full RAG context on every
    # message. Falls back to Groq on any failure (bad key, quota, transient 503s).
    try:
        return await get_gemini_reply(trimmed, context_chunks)
    except Exception as e:
        logger.warning(f"Gemini failed, falling back to Groq: {e}")

    # Groq fallback
    messages = [{"role": "system", "content": _GROQ_SYSTEM}]
    if context_chunks:
        context_text = format_context(context_chunks)
        messages.append({
            "role": "system",
            "content": f"Relevant context from documents:\n\n{context_text}",
        })
    messages.extend({"role": m["role"], "content": m["content"]} for m in trimmed)

    response = await _groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=GROQ_TEMPERATURE,
        max_tokens=GROQ_MAX_TOKENS,
    )
    return response.choices[0].message.content
