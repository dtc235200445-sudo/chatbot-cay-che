import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Cho phép chạy trực tiếp: python rag/ingest.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.config import KNOWLEDGE_BASE_PATH
from rag.text_utils import build_index_text, fold_diacritics
from rag.vector_store import VectorStoreManager


def _scalar(value: Any, default: Any = "") -> Any:
    """ChromaDB chỉ chấp nhận metadata dạng str/int/float/bool."""
    return default if value is None else value


def chunk_to_record(item: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any], str]:
    """Chuyển một chunk trong knowledge_base.json thành (id, nội dung, metadata, văn bản embedding)."""
    meta = item.get("metadata") or {}
    metadata = {
        "title": item["title"],
        "source": item["source"],
        "source_type": item["source_type"],
        "category": item["category"],
        "topic": item.get("topic") or item["title"],
        "disease": item.get("disease") or "",
        "dataset": item.get("dataset", ""),
        "version": str(item.get("version", "")),
        "language": item.get("language", "vi"),
        "region": item.get("region") or meta.get("region", ""),
        "section": meta.get("section", ""),
        "page": _scalar(meta.get("page"), -1),
        "year": _scalar(meta.get("year"), -1),
        "original_chunk_id": meta.get("original_chunk_id", ""),
    }
    return item["chunk_id"], item["content"], metadata, build_index_text(item["title"], item["content"])


def ingest_knowledge_base(kb_path: Path = KNOWLEDGE_BASE_PATH) -> int:
    kb_file = Path(kb_path)
    if not kb_file.exists():
        raise FileNotFoundError(f"Không tìm thấy {kb_file}")

    chunks: List[Dict[str, Any]] = json.loads(kb_file.read_text(encoding="utf-8"))
    records = [chunk_to_record(item) for item in chunks]
    ids, documents, metadatas, embed_texts = (list(x) for x in zip(*records))
    folded_embed_texts = [fold_diacritics(t) for t in embed_texts]

    print(f"Nạp {len(chunks)} chunk từ {kb_file.name} ...")
    indexed = VectorStoreManager().rebuild(ids, documents, metadatas, embed_texts, folded_embed_texts)
    print(f"Hoàn tất: đã lập chỉ mục {indexed}/{len(chunks)} chunk")
    return indexed


if __name__ == "__main__":
    # Console Windows mặc định không phải UTF-8 nên in tiếng Việt sẽ lỗi nếu không cấu hình
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ingest_knowledge_base()
