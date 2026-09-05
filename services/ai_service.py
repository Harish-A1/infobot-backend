import asyncio
import logging
from groq import AsyncGroq
from config import get_settings
from services.supabase_service import get_session_history
from services.rag_service import retrieve_async, format_context
# from services.gemini_service import get_gemini_reply  # disabled: GEMINI_API_KEY currently returns 401. Re-enable import + call below once fixed.

logger = logging.getLogger(__name__)

settings = get_settings()
_groq_client = AsyncGroq(api_key=settings.groq_api_key)

GROQ_MODEL = "openai/gpt-oss-120b"
MAX_HISTORY_MESSAGES = 20

_GROQ_SYSTEM = (
    "You are Scube AI, a helpful and concise AI assistant. "
    "Use the conversation history to stay consistent with earlier messages. "
    "When context from documents is provided, prioritize answering from that context.\n\n"
    "State facts directly and confidently. Never add disclaimers, hedging, or suggestions to verify "
    "information elsewhere (e.g. 'this may be subject to change', 'please confirm with the developer') "
    "- the provided context is authoritative, so just answer.\n\n"
    "Always format your responses in Markdown. "
    "When your response includes a phone number, format it as a tap-to-call link: [+91 XXXXX XXXXX](tel:+91XXXXXXXXXX). "
    "When your response includes a physical address or location, format it as a tap-to-map link: [Full Address](https://maps.google.com/?q=Full+Address+URL+Encoded). "
    "If the provided context includes an explicit MAP: link for that location, use that exact link instead of constructing one. "
    "When your response includes a website, format it as a standard markdown link: [site name](https://url). "
    "When your response references a document mentioned in the provided context, link to it using the "
    "exact 'link:' URL given alongside that source, formatted as [document name](that exact link) so the "
    "user can tap to open it directly in the app. Never invent or alter a document URL."
)


async def get_ai_reply(session_id: str) -> str:
    history = await asyncio.to_thread(get_session_history, session_id)
    trimmed = history[-MAX_HISTORY_MESSAGES:]

    user_messages = [m for m in trimmed if m["role"] == "user"]
    last_query = user_messages[-1]["content"] if user_messages else ""

    context_chunks: list[dict] = []
    if last_query:
        try:
            context_chunks = await retrieve_async(last_query, top_k=5)
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

    # Gemini disabled: GEMINI_API_KEY currently returns 401. Uncomment to re-enable.
    # try:
    #     return await get_gemini_reply(trimmed, context_chunks)
    # except Exception as e:
    #     logger.warning(f"Gemini failed, falling back to Groq: {e}")

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
    )
    return response.choices[0].message.content
