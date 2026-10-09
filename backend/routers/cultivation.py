from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.dependencies.db import get_db
from backend.schemas.common import PaginatedResponse
from backend.schemas.cultivation import TeaCultivationTopicResponse
from backend.services.cultivation_service import get_cultivation_topics, get_cultivation_topic_by_id

router = APIRouter(prefix="/api/v1/cultivation", tags=["Tea Cultivation"])

@router.get("", response_model=PaginatedResponse[TeaCultivationTopicResponse], summary="List Cultivation Topics")
def list_cultivation_topics(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return get_cultivation_topics(db, category=category, page=page, page_size=page_size)

@router.get("/{topic_id}", response_model=TeaCultivationTopicResponse, summary="Get Cultivation Topic Detail by ID")
def get_cultivation_detail(topic_id: int, db: Session = Depends(get_db)):
    topic = get_cultivation_topic_by_id(db, topic_id=topic_id)
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cultivation Topic with ID {topic_id} not found")
    return topic
