from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict

class MetadataSchema(BaseModel):
    document: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    region: Optional[str] = None
    year: Optional[int] = None
    original_chunk_id: Optional[str] = None

class KnowledgeChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_id: str
    document_id: int
    title: str
    content: str
    source: str
    source_type: str
    category: str
    topic: Optional[str] = None
    disease: Optional[str] = ""
    dataset: Optional[str] = None
    version: Optional[str] = None
    language: str
    region: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    year: Optional[int] = None
    original_chunk_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
