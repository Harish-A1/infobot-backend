from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str

class MessageModel(BaseModel):
    id: UUID
    session_id: str
    role: str
    content: str
    created_at: datetime

class SessionPreview(BaseModel):
    session_id: str
    last_message: str
    last_updated: datetime
