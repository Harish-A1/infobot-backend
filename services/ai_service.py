from groq import AsyncGroq
from config import get_settings
from services.supabase_service import get_session_history

settings = get_settings()
client = AsyncGroq(api_key=settings.groq_api_key)

MODEL = "llama-3.3-70b-versatile"
MAX_HISTORY_MESSAGES = 20

SYSTEM_PROMPT = (
    "You are InfoBot, a helpful and concise AI assistant. "
    "Use the conversation history to stay consistent with earlier messages."
)


async def get_ai_reply(session_id: str) -> str:
    """
    Generates a reply from Groq using the session's stored conversation
    history. The caller is expected to have already saved the latest user
    message to the session before calling this.
    """
    history = get_session_history(session_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(
        {"role": entry["role"], "content": entry["content"]}
        for entry in history[-MAX_HISTORY_MESSAGES:]
    )

    response = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )
    return response.choices[0].message.content
