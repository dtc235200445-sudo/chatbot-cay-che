import math
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from database.models import TeaCultivationTopic

def get_cultivation_topics(db: Session, category: Optional[str] = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    query = db.query(TeaCultivationTopic)
    if category:
        query = query.filter(TeaCultivationTopic.category == category)
    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    items = query.order_by(TeaCultivationTopic.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    }

def get_cultivation_topic_by_id(db: Session, topic_id: int) -> Optional[TeaCultivationTopic]:
    return db.query(TeaCultivationTopic).filter_by(id=topic_id).first()
