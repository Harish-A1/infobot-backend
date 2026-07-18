import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from models.schemas import ChatRequest, ChatResponse, MessageModel, SessionPreview
from services.ai_service import get_ai_reply
from services.supabase_service import (
    save_message, get_session_history, get_all_sessions,
    delete_session, delete_all_sessions,
)
from typing import List

DATA_DIR = Path(__file__).parent.parent / "data"

router = APIRouter()

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

def _validate_session_id(session_id: str) -> None:
    if not session_id or not _UUID_RE.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id: must be a UUID.")


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    _validate_session_id(request.session_id)
    try:
        save_message(request.session_id, "user", request.message)
        ai_reply = await get_ai_reply(request.session_id)
        save_message(request.session_id, "assistant", ai_reply)
        return ChatResponse(reply=ai_reply)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}", response_model=List[MessageModel])
async def get_history(session_id: str):
    _validate_session_id(session_id)
    try:
        return get_session_history(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=List[SessionPreview])
async def get_sessions():
    try:
        return get_all_sessions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def remove_session(session_id: str):
    _validate_session_id(session_id)
    try:
        delete_session(session_id)
        return {"status": "success", "message": f"Session {session_id} deleted."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions")
async def remove_all_sessions():
    try:
        delete_all_sessions()
        return {"status": "success", "message": "All sessions deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index")
async def trigger_indexing():
    try:
        from services.rag_service import index_documents_async
        result = await index_documents_async()
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents():
    pdfs = sorted(f.name for f in DATA_DIR.glob("*.pdf") if f.is_file())
    return {"documents": pdfs}


@router.get("/documents/{filename}")
async def get_document(filename: str):
    if not filename.endswith(".pdf") or "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    file_path = DATA_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found.")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
    )
