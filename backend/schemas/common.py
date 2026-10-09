from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")

class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str

class MessageResponse(BaseModel):
    message: str

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    page: int
    page_size: int
    total: int
    total_pages: int
