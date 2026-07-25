import logging
from config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "You are Scube AI, a helpful and concise AI assistant. "
    "Use the conversation history to stay consistent with earlier messages. "
    "When context from documents is provided, prioritize answering from that context.\n\n"
    "State facts directly and confidently. Never add disclaimers, hedging, or suggestions to verify "
    "information elsewhere (e.g. 'this may be subject to change', 'please confirm with the developer') "
    "- the provided context is authoritative, so just answer.\n\n"
    "Always format your responses in Markdown. "
    "When your response includes a phone number, format it as a tap-to-call link: [+91 XXXXX XXXXX](tel:+91XXXXXXXXXX). "
    "When your response includes a physical address or location, format it as a tap-to-map link using the exact text as the label and a Google Maps URL: [Full Address](https://maps.google.com/?q=Full+Address+URL+Encoded). "
    "If the provided context includes an explicit MAP: link for that location, use that exact link instead of constructing one. "
    "When your response includes a website, format it as a standard markdown link: [site name](https://url). "
    "When your response references a document mentioned in the provided context, link to it using the "
    "exact 'link:' URL given alongside that source, formatted as [document name](that exact link) so the "
    "user can tap to open it directly in the app. Never invent or alter a document URL."
)

_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=get_settings().gemini_api_key)
    return _client


async def get_gemini_reply(history: list[dict], context_chunks: list[dict]) -> str:
    if not get_settings().gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")

    from google.genai import types
    client = _get_client()

    # Build full conversation as contents (all but the last message)
    contents = []
    for entry in history[:-1]:
        role = "user" if entry["role"] == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=entry["content"])])
        )

    # Inject RAG context into the final user message
    last_message = history[-1]["content"] if history else ""
    if context_chunks:
        from services.rag_service import format_context
        context_text = format_context(context_chunks)
        prompt = (
            f"Relevant context from documents:\n\n{context_text}"
            f"\n\n---\n\nUser question: {last_message}"
        )
    else:
        prompt = last_message

    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    )

    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
    )
    return response.text
