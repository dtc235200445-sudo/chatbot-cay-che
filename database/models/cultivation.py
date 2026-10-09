from typing import Optional
from sqlalchemy import String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import Base, TimestampMixin

class TeaCultivationTopic(Base, TimestampMixin):
    __tablename__ = "tea_cultivation_topics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<TeaCultivationTopic id={self.id} name='{self.topic_name}'>"
