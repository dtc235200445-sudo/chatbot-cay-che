import math
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database.models import TeaDisease

def get_diseases(db: Session, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    query = db.query(TeaDisease)
    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    items = query.order_by(TeaDisease.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    }

def get_disease_by_id(db: Session, disease_id: int) -> Optional[TeaDisease]:
    return db.query(TeaDisease).filter_by(id=disease_id).first()

def search_diseases(db: Session, q: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    pattern = f"%{q.strip()}%"
    query = db.query(TeaDisease).filter(
        or_(
            TeaDisease.name.ilike(pattern),
            TeaDisease.scientific_name.ilike(pattern),
            TeaDisease.symptoms.ilike(pattern)
        )
    )
    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    items = query.order_by(TeaDisease.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    }
