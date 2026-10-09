import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database.models import Document
from backend.dependencies.db import get_db
from backend.schemas.common import PaginatedResponse
from backend.schemas.document import DocumentResponse

router = APIRouter(prefix="/api/v1/documents", tags=["Source Documents"])

@router.get("", response_model=PaginatedResponse[DocumentResponse], summary="List Source Documents")
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_type: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Document)
    if source_type:
        query = query.filter(Document.source_type == source_type)
    if language:
        query = query.filter(Document.language == language)
        
    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    items = query.order_by(Document.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    }

@router.get("/{document_id}", response_model=DocumentResponse, summary="Get Document Detail by ID")
def get_document_detail(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID {document_id} not found")
    return doc
