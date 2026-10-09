import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

# --- Lưu trữ ---
VECTOR_STORE_DIR = BASE_DIR / "database" / "chroma_db"
COLLECTION_NAME = "tea_scholar_knowledge"
# Chỉ mục thứ hai: embedding của văn bản đã BỎ DẤU, dùng cho câu hỏi người dùng gõ không dấu
FOLDED_COLLECTION_NAME = COLLECTION_NAME + "_folded"
KNOWLEDGE_BASE_PATH = BASE_DIR / "data" / "knowledge_base.json"

# Tăng số này mỗi khi thay đổi cách tạo văn bản/embedding để retriever phát hiện chỉ mục cũ.
INDEX_VERSION = "4-bkai-dual-folded"

# --- Embedding ---
# Model embedding chuyên tiếng Việt (PhoBERT, Apache-2.0). Trên bộ đánh giá của dự án, model này cho cổng từ chối
# câu ngoài phạm vi tốt hơn hẳn model đa ngữ nhỏ trước đây (paraphrase-multilingual-MiniLM-L12-v2); xem docs/RAG_EVALUATION.md.
MODEL_NAME = os.getenv("RAG_EMBEDDING_MODEL", "bkai-foundation-models/vietnamese-bi-encoder")
# Các model tiếng Việt dựa trên PhoBERT cần văn bản đã được tách từ (pyvi) cho cả đoạn tài liệu lẫn câu hỏi.
SEGMENT_WORDS = os.getenv("RAG_SEGMENT_WORDS", "1" if "vietnamese-bi-encoder" in MODEL_NAME else "0") == "1"
MAX_SEQ_LENGTH = int(os.getenv("RAG_MAX_SEQ_LENGTH", "256"))

# --- Truy xuất ---
DEFAULT_TOP_K = 3

# Hybrid: điểm = HYBRID_ALPHA * cosine + (1 - HYBRID_ALPHA) * BM25 (chuẩn hóa theo điểm BM25 cao nhất).
HYBRID_ALPHA = 0.7

# BM25
BM25_K1 = 1.5
BM25_B = 0.75
BM25_TITLE_BOOST = 2  # tiêu đề được lặp lại số lần này khi lập chỉ mục BM25

# Cổng "có liên quan": câu hỏi thuộc cơ sở tri thức nếu cosine >= STRONG_COSINE, hoặc cả cosine >= MIN_COSINE
# và BM25 >= MIN_BM25. Hiệu chỉnh bằng rag/evaluation (xem docs/RAG_EVALUATION.md).
MIN_COSINE = float(os.getenv("RAG_MIN_COSINE", "0.38"))
MIN_BM25 = float(os.getenv("RAG_MIN_BM25", "10.0"))
# Bằng chứng ngữ nghĩa đủ mạnh thì chấp nhận dù điểm BM25 thấp (câu hỏi chung chung như "Sâu hại chính trên cây chè"
# có cosine cao nhưng ít từ khóa đặc thù). Điểm cosine cao nhất của câu ngoài phạm vi trong bộ đánh giá là 0,47.
STRONG_COSINE = float(os.getenv("RAG_STRONG_COSINE", "0.55"))

# Cổng cho câu hỏi gõ không dấu: cosine so với chỉ mục bỏ dấu có thang điểm thấp hơn và nhiễu hơn nên dùng ngưỡng riêng.
# Chọn nghiêng về việc KHÔNG từ chối nhầm người dùng thật (nhận đúng 94%, từ chối đúng 75% trên bộ đánh giá); câu ngoài
# phạm vi còn lọt qua sẽ bị lớp phòng thủ thứ hai (prompt ràng buộc của LLM) chặn. Nâng UNACCENTED_MIN_COSINE lên 0,45
# thì từ chối đúng 100% nhưng nhận đúng chỉ 86%.
UNACCENTED_STRONG_COSINE = float(os.getenv("RAG_UNACCENTED_STRONG_COSINE", "0.60"))
UNACCENTED_MIN_COSINE = float(os.getenv("RAG_UNACCENTED_MIN_COSINE", "0.40"))
