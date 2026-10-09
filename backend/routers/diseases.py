from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.dependencies.db import get_db
from backend.schemas.common import PaginatedResponse
from backend.schemas.disease import TeaDiseaseResponse
from backend.services.disease_service import get_diseases, get_disease_by_id, search_diseases

router = APIRouter(prefix="/api/v1/diseases", tags=["Tea Diseases"])

@router.get("", response_model=PaginatedResponse[TeaDiseaseResponse], summary="List Tea Diseases")
def list_diseases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return get_diseases(db, page=page, page_size=page_size)

@router.get("/search", response_model=PaginatedResponse[TeaDiseaseResponse], summary="Search Tea Diseases by Keyword")
def search_disease_list(
    q: str = Query(..., min_length=1, description="Keyword search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return search_diseases(db, q=q, page=page, page_size=page_size)

@router.get("/{disease_id}", response_model=TeaDiseaseResponse, summary="Get Disease Detail by ID")
def get_disease_detail(disease_id: int, db: Session = Depends(get_db)):
    disease = get_disease_by_id(db, disease_id=disease_id)
    if not disease:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Disease with ID {disease_id} not found")
    return disease
