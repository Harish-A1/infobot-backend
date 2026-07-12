from supabase import create_client, Client
from config import get_settings
from typing import Optional

_supabase: Optional[Client] = None

def get_supabase_client() -> Client:
    global _supabase
    if _supabase is None:
        settings = get_settings()
        # Prefer the service role key — it bypasses RLS so deletes/writes always work.
        # Falls back to the anon key if service key is not provided.
        key = settings.supabase_service_key or settings.supabase_key
        _supabase = create_client(settings.supabase_url, key)
    return _supabase

def save_message(session_id: str, role: str, content: str):
    db = get_supabase_client()
    response = db.schema("public").table("messages").insert(
        {"session_id": session_id, "role": role, "content": content}
    ).execute()
    return response.data

def get_session_history(session_id: str):
    db = get_supabase_client()
    response = (
        db.schema("public")
        .table("messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
    )
    return response.data

def get_all_sessions():
    db = get_supabase_client()
    response = (
        db.schema("public")
        .table("session_previews")
        .select("*")
        .order("last_updated", desc=True)
        .execute()
    )
    return response.data

def delete_session(session_id: str):
    db = get_supabase_client()
    response = (
        db.schema("public")
        .table("messages")
        .delete()
        .eq("session_id", session_id)
        .execute()
    )
    return response.data

def delete_all_sessions():
    db = get_supabase_client()
    response = (
        db.schema("public")
        .table("messages")
        .delete()
        .neq("session_id", "")
        .execute()
    )
    return response.data
