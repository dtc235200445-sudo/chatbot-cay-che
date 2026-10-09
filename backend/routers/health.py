from fastapi import APIRouter
from backend.schemas.common import HealthResponse

router = APIRouter(tags=["Health Check"])

@router.get("/", response_model=HealthResponse, summary="Root Endpoint")
def root():
    return {
        "status": "ok",
        "app_name": "Tea Scholar AI Backend API",
        "version": "1.0.0"
    }

@router.get("/api/v1/health", response_model=HealthResponse, summary="API Health Check")
def health_check():
    return {
        "status": "ok",
        "app_name": "Tea Scholar AI Backend API",
        "version": "1.0.0"
    }
