import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import require_approved_user
from ..db import get_db
from ..models import ChatMessage, User
from ..services.assistant import chat_stream

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class SendMessageRequest(BaseModel):
    message: str


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/messages", response_model=list[ChatMessageOut])
def list_messages(db: Session = Depends(get_db), user: User = Depends(require_approved_user)):
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [ChatMessageOut(id=r.id, role=r.role.value, content=r.content, created_at=r.created_at) for r in rows]


@router.post("/messages")
def send_message(
    req: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_approved_user),
):
    return StreamingResponse(
        chat_stream(db, user, req.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/messages", status_code=status.HTTP_204_NO_CONTENT)
def clear_messages(db: Session = Depends(get_db), user: User = Depends(require_approved_user)):
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.commit()
