from backend.routers.health import router as health_router
from backend.routers.auth import router as auth_router
from backend.routers.knowledge import router as knowledge_router
from backend.routers.documents import router as documents_router
from backend.routers.diseases import router as diseases_router
from backend.routers.cultivation import router as cultivation_router
from backend.routers.weather import router as weather_router
from backend.routers.chat import router as chat_router

__all__ = [
    "health_router",
    "auth_router",
    "knowledge_router",
    "documents_router",
    "diseases_router",
    "cultivation_router",
    "weather_router",
    "chat_router",
]
