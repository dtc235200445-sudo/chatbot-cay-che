from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_code: str
    title: str
    source: str
    source_type: str
    dataset: Optional[str] = None
    version: Optional[str] = None
    language: str
    region: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime
