from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class TeaDiseaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    scientific_name: Optional[str] = None
    symptoms: Optional[str] = None
    causes: Optional[str] = None
    prevention: Optional[str] = None
    treatment: Optional[str] = None
    severity: Optional[str] = None
    created_at: datetime
