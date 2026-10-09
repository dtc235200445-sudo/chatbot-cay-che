from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class TeaCultivationTopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_name: str
    category: str
    summary: Optional[str] = None
    created_at: datetime
