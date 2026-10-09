from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.dependencies.db import get_db
from backend.schemas.common import PaginatedResponse
from backend.schemas.knowledge import KnowledgeChunkResponse
from backend.services.knowledge_service import (
    get_knowledge_chunks,
    get_knowledge_chunk_by_id,
    search_knowledge_keyword,
    suggest_keywords
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Base"])

@router.get("", response_model=PaginatedResponse[KnowledgeChunkResponse], summary="List Knowledge Chunks (Paginated)")
def list_knowledge(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=500, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    disease: Optional[str] = Query(None, description="Filter by disease"),
    source: Optional[str] = Query(None, description="Filter by source"),
    db: Session = Depends(get_db)
):
    return get_knowledge_chunks(
        db, page=page, page_size=page_size,
        category=category, topic=topic, disease=disease, source=source
    )

@router.get("/search", response_model=PaginatedResponse[KnowledgeChunkResponse], summary="Search Knowledge Base by Keyword")
def search_knowledge(
    q: str = Query(..., min_length=1, description="Keyword search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=500, description="Items per page"),
    db: Session = Depends(get_db)
):
    return search_knowledge_keyword(db, q=q, page=page, page_size=page_size)

@router.get("/suggest", summary="Autocomplete Suggestions for the Search Box")
def suggest_knowledge(
    q: str = Query(..., max_length=100, description="Prefix typed so far"),
    limit: int = Query(8, ge=1, le=20, description="Maximum number of suggestions"),
    db: Session = Depends(get_db)
):
    """Gợi ý cụm từ bắt đầu bằng phần người dùng đã gõ, lấy từ tiêu đề chunk và tên bệnh."""
    return {"query": q, "suggestions": suggest_keywords(db, q=q, limit=limit)}


@router.get("/{chunk_id}", response_model=KnowledgeChunkResponse, summary="Get Knowledge Chunk Detail by ID")
def get_knowledge_detail(chunk_id: str, db: Session = Depends(get_db)):
    chunk = get_knowledge_chunk_by_id(db, chunk_id=chunk_id)
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge Chunk '{chunk_id}' not found")
    return chunk
