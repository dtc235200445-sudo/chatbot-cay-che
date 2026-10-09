import json
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from database.models import ChatSession, ChatMessage, User
from backend.config import settings
from backend.schemas.chat import ChatQueryResponse, ChatSourceItem
from backend.services.llm_service import generate_rag_response
from rag.retriever import RAGRetriever

def create_chat_session(db: Session, user_id: Optional[int] = None, title: str = "Cuộc trò chuyện mới") -> ChatSession:
    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_chat_sessions(db: Session, user_id: Optional[int] = None) -> List[ChatSession]:
    query = db.query(ChatSession)
    if user_id:
        query = query.filter(ChatSession.user_id == user_id)
    return query.order_by(ChatSession.updated_at.desc()).all()

def get_chat_session_by_id(db: Session, session_id: int) -> Optional[ChatSession]:
    return db.query(ChatSession).filter_by(id=session_id).first()

def delete_chat_session(db: Session, session_id: int) -> bool:
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        return False
    db.delete(session)
    db.commit()
    return True

def create_chat_message(db: Session, session_id: int, role: str, content: str, sources_json: Optional[str] = None) -> ChatMessage:
    msg = ChatMessage(session_id=session_id, role=role, content=content, sources_json=sources_json)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

def get_chat_messages(db: Session, session_id: int) -> List[ChatMessage]:
    return db.query(ChatMessage).filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).all()

def resolve_and_authorize_session(
    db: Session,
    session_id: Optional[int],
    current_user: Optional[User]
) -> ChatSession:
    """
    Resolve session by ID and enforce strict ownership rules.
    CASE 1: session_id is None -> Create new session bound to current_user (or None if anonymous).
    CASE 2: session exists & user_id is NULL -> Accessible by anyone (MVP limitation).
    CASE 3: session exists & user_id is set -> Must match current_user.id or raise HTTP 403.
    CASE 4: session_id provided but not found -> Raise HTTP 404.
    """
    if session_id is None:
        user_id = current_user.id if current_user else None
        return create_chat_session(db, user_id=user_id, title="Cuộc trò chuyện mới")

    session = get_chat_session_by_id(db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found"
        )

    # Ownership check
    if session.user_id is not None:
        if not current_user or current_user.id != session.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not own this chat session"
            )

    return session

async def process_chat_query(
    db: Session,
    session_id: Optional[int],
    message: str,
    current_user: Optional[User],
    retriever: Optional[RAGRetriever] = None
) -> ChatQueryResponse:
    """
    Delegate chat query processing to Phase 9 Option A AI Assistant Orchestrator.
    Maintains 100% backward compatibility with POST /api/v1/chat/query contract.
    """
    from backend.services.assistant_service import orchestrate_assistant_response
    return await orchestrate_assistant_response(
        db=db,
        session_id=session_id,
        message=message,
        current_user=current_user,
        retriever=retriever
    )
