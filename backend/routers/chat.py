from typing import Optional, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database.models import User
from backend.dependencies.db import get_db
from backend.dependencies.auth import get_optional_user
from backend.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatQueryRequest,
    ChatQueryResponse
)
from backend.services.chat_service import (
    create_chat_session,
    get_chat_sessions,
    delete_chat_session,
    resolve_and_authorize_session,
    create_chat_message,
    get_chat_messages,
    process_chat_query
)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat Sessions & Messages"])

@router.post("/query", response_model=ChatQueryResponse, summary="Chatbot RAG Query Endpoint")
async def chat_query(
    req: ChatQueryRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Core Chatbot Endpoint:
    Processes user query with RAG retrieval (Top-3) & AsyncOpenAI LLM response.
    """
    return await process_chat_query(
        db=db,
        session_id=req.session_id,
        message=req.message,
        current_user=current_user
    )

@router.get("/sessions", response_model=List[ChatSessionResponse], summary="List Chat Sessions")
def list_sessions(
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    # Người dùng chưa đăng nhập không được liệt kê phiên nào (tránh lộ hội thoại của người khác)
    if current_user is None:
        return []
    return get_chat_sessions(db, user_id=current_user.id)

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED, summary="Create New Chat Session")
def create_session(
    session_in: ChatSessionCreate,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    return create_chat_session(db, user_id=user_id, title=session_in.title or "Cuộc trò chuyện mới")

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse, summary="Get Chat Session Detail with Messages")
def get_session_detail(
    session_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    return resolve_and_authorize_session(db, session_id=session_id, current_user=current_user)

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Chat Session")
def delete_session(
    session_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    resolve_and_authorize_session(db, session_id=session_id, current_user=current_user)
    delete_chat_session(db, session_id=session_id)

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse], summary="List Chat Session Messages")
def list_session_messages(
    session_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    resolve_and_authorize_session(db, session_id=session_id, current_user=current_user)
    return get_chat_messages(db, session_id=session_id)

@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED, summary="Add Message to Chat Session")
def add_message_to_session(
    session_id: int,
    msg_in: ChatMessageCreate,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    resolve_and_authorize_session(db, session_id=session_id, current_user=current_user)
    return create_chat_message(
        db, session_id=session_id,
        role=msg_in.role, content=msg_in.content,
        sources_json=msg_in.sources_json
    )
