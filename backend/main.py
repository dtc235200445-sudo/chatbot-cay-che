import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.config import settings

logger = logging.getLogger("tea_scholar.main")

from backend.routers import (
    health_router,
    auth_router,
    knowledge_router,
    documents_router,
    diseases_router,
    cultivation_router,
    weather_router,
    chat_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Nạp sẵn model embedding + vector store để request chat đầu tiên không bị chậm.
    # Nếu lỗi (thiếu model, chưa ingest...) server vẫn chạy, retriever sẽ khởi tạo lười ở request đầu.
    try:
        from backend.services.assistant_service import get_default_retriever
        get_default_retriever()
    except Exception as err:
        logger.warning("RAG retriever warm-up failed: %s", err)
    yield


# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RESTful API Backend cho Hệ thống Trợ lý Tri thức & Hỏi đáp Cây chè Việt Nam (Tea Scholar AI).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact administrator."}
    )

# Register Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(knowledge_router)
app.include_router(documents_router)
app.include_router(diseases_router)
app.include_router(cultivation_router)
app.include_router(weather_router)
app.include_router(chat_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8001, reload=True)
