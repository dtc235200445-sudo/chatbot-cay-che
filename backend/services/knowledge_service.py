import math
import re
import unicodedata
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from database.models import KnowledgeChunk

def build_chunk_response_dict(chunk: KnowledgeChunk) -> Dict[str, Any]:
    return {
        "id": chunk.id,
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "title": chunk.title,
        "content": chunk.content,
        "source": chunk.source,
        "source_type": chunk.source_type,
        "category": chunk.category,
        "topic": chunk.topic,
        "disease": chunk.disease or "",
        "dataset": chunk.dataset,
        "version": chunk.version,
        "language": chunk.language,
        "region": chunk.region,
        "section": chunk.section,
        "page": chunk.page,
        "year": chunk.year,
        "original_chunk_id": chunk.original_chunk_id,
        "metadata": {
            "document": chunk.document_rel.title if chunk.document_rel else chunk.source,
            "section": chunk.section,
            "page": chunk.page,
            "region": chunk.region,
            "year": chunk.year,
            "original_chunk_id": chunk.original_chunk_id
        }
    }

def get_knowledge_chunks(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    topic: Optional[str] = None,
    disease: Optional[str] = None,
    source: Optional[str] = None
) -> Dict[str, Any]:
    query = db.query(KnowledgeChunk)
    
    if category:
        query = query.filter(KnowledgeChunk.category == category)
    if topic:
        query = query.filter(KnowledgeChunk.topic.ilike(f"%{topic}%"))
    if disease:
        query = query.filter(KnowledgeChunk.disease.ilike(f"%{disease}%"))
    if source:
        query = query.filter(KnowledgeChunk.source.ilike(f"%{source}%"))
        
    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    
    chunks = query.order_by(KnowledgeChunk.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [build_chunk_response_dict(c) for c in chunks]
    
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    }

def get_knowledge_chunk_by_id(db: Session, chunk_id: str) -> Optional[Dict[str, Any]]:
    chunk = db.query(KnowledgeChunk).filter_by(chunk_id=chunk_id).first()
    if not chunk:
        return None
    return build_chunk_response_dict(chunk)

def normalize_text(text: str) -> str:
    """Chuẩn hóa Unicode (NFC) và chữ thường; giữ nguyên dấu."""
    return unicodedata.normalize("NFC", text).lower()


def fold_text(text: str) -> str:
    """Chữ thường và bỏ dấu tiếng Việt (đ -> d)."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.replace("đ", "d")


def _contains_word(haystack: str, term: str) -> bool:
    """Khớp theo từ nguyên vẹn để "tan" không khớp vào giữa từ như "tán"."""
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", haystack) is not None


def _rank_matches(chunks: List[KnowledgeChunk], phrase: str, prepare) -> List[tuple]:
    terms = phrase.split()
    ranked = []
    for chunk in chunks:
        title = prepare(chunk.title)
        body = prepare(chunk.content)
        extra = prepare(f"{chunk.topic or ''} {chunk.disease or ''}")
        haystack = f"{title} {body} {extra}"
        if not all(_contains_word(haystack, term) for term in terms):
            continue
        score = 4 * (phrase in title) + 2 * (phrase in body) + sum(_contains_word(title, t) for t in terms)
        ranked.append((score, chunk))
    ranked.sort(key=lambda pair: (-pair[0], pair[1].id))
    return ranked


def search_knowledge_keyword(
    db: Session,
    q: str,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Tìm kiếm từ khóa: một chunk khớp khi chứa MỌI từ của truy vấn (khớp từ nguyên vẹn, không phân biệt
    hoa/thường) ở tiêu đề, nội dung, chủ đề hoặc bệnh. Ưu tiên khớp có dấu; nếu không có kết quả thì thử
    lại không phân biệt dấu (để gõ "thoi bup" vẫn tìm được "thối búp").
    Xếp hạng: khớp nguyên cụm ở tiêu đề > ở nội dung > nhiều từ khớp ở tiêu đề.

    So khớp thực hiện ở Python vì LIKE của SQLite chỉ không phân biệt hoa/thường với chữ ASCII
    (ví dụ "Đà" và "đà" bị coi là khác nhau). Kho tri thức cỡ vài trăm chunk nên chi phí không đáng kể.
    """
    clean_q = q.strip()
    if not clean_q:
        return get_knowledge_chunks(db, page=page, page_size=page_size)

    chunks = db.query(KnowledgeChunk).order_by(KnowledgeChunk.id.asc()).all()
    ranked = _rank_matches(chunks, normalize_text(clean_q), normalize_text)
    if not ranked:
        ranked = _rank_matches(chunks, fold_text(clean_q), fold_text)

    total = len(ranked)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    start = (page - 1) * page_size
    items = [build_chunk_response_dict(chunk) for _, chunk in ranked[start:start + page_size]]

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    }


# ---------------------------------------------------------------------------
# Gợi ý từ khóa khi gõ (autocomplete)
# ---------------------------------------------------------------------------
_SUGGEST_MAX_WORDS = 8
# Không dùng các từ này làm từ đầu/cuối của cụm gợi ý ("và thối", "bệnh của" đều vô nghĩa)
_SUGGEST_EDGE_STOPWORDS = frozenset(
    "và của cho các theo trong với là một những để tại từ do bởi hoặc khi như đến".split()
)
_FRAGMENT_SPLIT = re.compile(r"\s+[—–-]\s+|[()\[\],:;/]")
_WORD = re.compile(r"\w+", re.UNICODE)


def _suggest_index(db: Session) -> Dict[str, Dict[str, Any]]:
    """
    Chỉ mục cụm từ gợi ý: các cụm 1–4 từ liền nhau trong tiêu đề chunk và tên bệnh.
    Trả về {khóa_không_dấu: {"text", "df" (số chunk chứa cụm), "words", "complete"}}; `complete` là True
    nếu cụm từng kết thúc đúng ở cuối một đoạn tiêu đề (tức là một cụm hoàn chỉnh, không bị cắt giữa chừng).
    """
    rows = db.query(KnowledgeChunk.chunk_id, KnowledgeChunk.title, KnowledgeChunk.disease).all()
    phrases: Dict[str, Dict[str, Any]] = {}
    for chunk_id, title, disease in rows:
        fragments = _FRAGMENT_SPLIT.split(title or "")
        fragments += [d.strip() for d in (disease or "").split(",") if d.strip()]
        seen_in_chunk = set()
        for fragment in fragments:
            words = _WORD.findall(normalize_text(fragment))
            for i in range(len(words)):
                for n in range(1, _SUGGEST_MAX_WORDS + 1):
                    gram = words[i:i + n]
                    if len(gram) < n:
                        break
                    if gram[0] in _SUGGEST_EDGE_STOPWORDS or gram[-1] in _SUGGEST_EDGE_STOPWORDS:
                        continue
                    text = " ".join(gram)
                    key = fold_text(text)
                    entry = phrases.setdefault(
                        key, {"text": text, "df": 0, "words": n, "complete": False, "nexts": set()}
                    )
                    if key not in seen_in_chunk:
                        entry["df"] += 1
                        seen_in_chunk.add(key)
                    if i + n == len(words):
                        entry["complete"] = True
                    else:
                        entry["nexts"].add(words[i + n])
    return phrases


def _is_good_suggestion(entry: Dict[str, Any]) -> bool:
    """
    Cụm 1 từ luôn dùng được. Cụm dài hơn chỉ hợp lệ khi:
    - là cụm hoàn chỉnh (từng kết thúc đúng ở cuối một đoạn tiêu đề), hoặc
    - "rẽ nhánh": được nối tiếp bởi từ ít nhất hai cách khác nhau. Cụm luôn bị nối tiếp bởi cùng một từ là
      bản cắt cụt của cụm dài hơn ("bón phân chè kinh doanh theo năng" thay vì "... năng suất ...").
    Cụm từ 3 từ trở lên còn phải lặp lại (df >= 2) hoặc hoàn chỉnh.
    """
    if entry["words"] == 1:
        return True
    if not (entry["complete"] or len(entry["nexts"]) >= 2):
        return False
    return entry["words"] <= 2 or entry["df"] >= 2 or entry["complete"]


_suggest_cache: Dict[int, Dict[str, Dict[str, Any]]] = {}


def suggest_keywords(db: Session, q: str, limit: int = 8) -> List[Dict[str, Any]]:
    """
    Gợi ý cụm từ bắt đầu bằng những gì người dùng đã gõ (không phân biệt hoa/thường và dấu).
    Xếp theo độ phổ biến trong tiêu đề, ưu tiên cụm nhiều từ (cụ thể hơn); khớp đúng dấu người dùng gõ được xếp trước, khớp không dấu bổ sung sau; bỏ cụm là tiền tố của một cụm
    dài hơn có cùng độ phổ biến để danh sách không lặp ("bệnh thối" và "bệnh thối búp").
    """
    prefix = fold_text(q.lstrip())
    if not prefix.strip():
        return []

    # Chỉ mục phụ thuộc số chunk hiện có nên tự làm mới khi kho tri thức thay đổi
    total = db.query(KnowledgeChunk).count()
    index = _suggest_cache.get(total)
    if index is None:
        _suggest_cache.clear()
        index = _suggest_cache.setdefault(total, _suggest_index(db))

    typed = normalize_text(q.lstrip())

    def rank(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(entries, key=lambda e: (-(e["df"] + 0.15 * e["words"]), e["text"]))

    good = [e for e in index.values() if _is_good_suggestion(e)]
    # Tầng 1: khớp đúng cả dấu như người dùng đã gõ; tầng 2: khớp không phân biệt dấu ("thoi" -> "thối")
    exact = rank([e for e in good if e["text"].startswith(typed) and e["text"] != typed.strip()])
    loose = rank([
        e for key, e in index.items()
        if _is_good_suggestion(e) and key.startswith(prefix) and key != prefix.strip()
        and not e["text"].startswith(typed)
    ])
    matches = exact + loose

    chosen: List[Dict[str, Any]] = []
    for entry in matches:
        folded = fold_text(entry["text"])
        # Bỏ cụm là tiền tố của một cụm dài hơn có cùng (hoặc hơn) độ phổ biến
        if any(
            len(other["text"]) > len(entry["text"])
            and fold_text(other["text"]).startswith(folded + " ")
            and other["df"] >= entry["df"]
            for other in matches
        ):
            continue
        chosen.append({"text": entry["text"], "count": entry["df"]})
        if len(chosen) >= limit:
            break
    return chosen
