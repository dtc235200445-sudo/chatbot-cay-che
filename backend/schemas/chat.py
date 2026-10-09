from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(default="Cuộc trò chuyện mới")

class ChatMessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)
    sources_json: Optional[str] = None

class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    sources_json: Optional[str] = None
    created_at: datetime

class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    title: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[ChatMessageResponse]] = []

class ChatQueryRequest(BaseModel):
    session_id: Optional[int] = Field(default=None, description="ID của phiên trò chuyện. Nếu None, hệ thống tự khởi tạo session mới.")
    message: str = Field(..., min_length=1, max_length=2000, description="Câu hỏi của người dùng")

class ChatSourceItem(BaseModel):
    chunk_id: str
    title: str
    source: str
    similarity_score: float

class ChatQueryResponse(BaseModel):
    session_id: int
    message_id: int
    role: str = "assistant"
    answer: str
    sources: List[ChatSourceItem] = []
    created_at: datetime
