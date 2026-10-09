import re
import unicodedata
from typing import Dict, List

def fold_diacritics(text: str) -> str:
    """Chữ thường và bỏ dấu tiếng Việt (đ -> d). Dùng để BM25 không phụ thuộc việc người dùng gõ có dấu hay không."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.replace("đ", "d")


# Từ dừng tiếng Việt thường gặp trong câu hỏi; "cây chè" xuất hiện ở hầu hết chunk nên không phân biệt được.
# So khớp theo dạng CÓ dấu rồi mới bỏ dấu các từ còn lại: nếu bỏ dấu cả danh sách từ dừng thì "cỏ" (cỏ dại) sẽ trùng
# "có" và bị xóa nhầm.
VI_STOPWORDS = frozenset(
    "là và của có cho các một những được trong khi để với này đó thì bị như thế nào gì ra sao "
    "cần nên không cây chè".split()
)

_WORD_RE = re.compile(r"\w+")


def normalize_text(text: str) -> str:
    """Chuẩn hóa Unicode (NFC) và chữ thường."""
    return unicodedata.normalize("NFC", text).lower()


def tokenize(text: str) -> List[str]:
    """
    Token hóa cho BM25: các từ đơn (bỏ từ dừng) cùng các cặp từ liền kề (bigram), đã bỏ dấu.
    Tiếng Việt là ngôn ngữ đa âm tiết nên bigram giữ được cụm như "thối búp", "nhện đỏ".
    Bỏ dấu để câu hỏi gõ không dấu ("thoi bup") vẫn khớp tài liệu có dấu; trên bộ đánh giá, Hit@3 cho câu không dấu
    tăng từ 0,36 lên 0,93 mà câu có dấu không bị giảm (xem docs/RAG_EVALUATION.md, mục 3c).
    """
    words = _WORD_RE.findall(normalize_text(text))
    unigrams = [fold_diacritics(w) for w in words if w not in VI_STOPWORDS]
    bigrams = [f"{fold_diacritics(a)}_{fold_diacritics(b)}" for a, b in zip(words, words[1:])]
    return unigrams + bigrams


def is_unaccented(text: str) -> bool:
    """Câu không chứa chữ có dấu nào (ví dụ "benh thoi bup tren cay che"): dùng chỉ mục vector bỏ dấu."""
    return any(ch.isalpha() for ch in text) and fold_diacritics(text) == text.lower()


def build_index_text(title: str, content: str) -> str:
    """Văn bản dùng để tạo embedding: tiêu đề mang chủ đề của chunk nên được ghép cùng nội dung."""
    return f"{title}\n{content}"


def build_bm25_text(title: str, content: str, title_boost: int) -> str:
    return " ".join([title] * title_boost + [content])


def min_max(values: Dict[str, float]) -> Dict[str, float]:
    if not values:
        return {}
    top = max(values.values())
    if top <= 0:
        return {k: 0.0 for k in values}
    return {k: v / top for k, v in values.items()}
