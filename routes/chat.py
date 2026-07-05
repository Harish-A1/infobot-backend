from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse, MessageModel, SessionPreview
from services.ai_service import get_ai_reply
from services.supabase_service import save_message, get_session_history, get_all_sessions, delete_session
from typing import List

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Save user message
        save_message(request.session_id, "user", request.message)
        
        # Get AI Reply
        ai_reply = await get_ai_reply(request.session_id)
        
        # Save AI reply
        save_message(request.session_id, "assistant", ai_reply)
        
        return ChatResponse(reply=ai_reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}")
async def get_history(session_id: str):
    try:
        data = get_session_history(session_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_sessions():
    try:
        data = get_all_sessions()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}")
async def remove_session(session_id: str):
    try:
        delete_session(session_id)
        return {"status": "success", "message": f"Session {session_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
