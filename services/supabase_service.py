from supabase import create_client, Client
from config import get_settings

def get_supabase_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError("Supabase credentials are not set in the environment.")
    return create_client(settings.supabase_url, settings.supabase_key)

supabase = get_supabase_client()

def save_message(session_id: str, role: str, content: str):
    try:
        data = {
            "session_id": session_id,
            "role": role,
            "content": content
        }
        response = supabase.schema("public").table("messages").insert(data).execute()
        print(f"Save response: {response.data}")
        return response.data
    except Exception as e:
        print(f"SAVE ERROR: {e}")
        raise

def get_session_history(session_id: str):
    response = supabase.schema("public").table("messages").select("*").eq("session_id", session_id).order("created_at").execute()
    return response.data

def get_all_sessions():
    response = supabase.schema("public").table("session_previews").select("*").order("last_updated", desc=True).execute()
    return response.data

def delete_session(session_id: str):
    response = supabase.schema("public").table("messages").delete().eq("session_id", session_id).execute()
    return response.data