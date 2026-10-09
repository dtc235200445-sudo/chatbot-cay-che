from typing import Optional
from sqlalchemy import String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import Base, TimestampMixin

class TeaDisease(Base, TimestampMixin):
    __tablename__ = "tea_diseases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    scientific_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    symptoms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    causes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prevention: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    treatment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'low', 'medium', 'high', 'critical'

    def __repr__(self) -> str:
        return f"<TeaDisease id={self.id} name='{self.name}'>"
