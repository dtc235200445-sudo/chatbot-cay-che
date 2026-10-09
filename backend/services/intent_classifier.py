import re
from typing import Any, Dict, List, Optional

from backend.services.regions import DEFAULT_REGION, find_region_in_text

TASK_KNOWLEDGE = "KNOWLEDGE_QUERY"
TASK_WEATHER = "WEATHER_QUERY"
TASK_HYBRID = "HYBRID_QUERY"
TASK_GENERAL = "GENERAL_CHAT"

# Từ khóa thời tiết "mạnh": tự nó cho thấy người dùng hỏi thời tiết thực tế.
WEATHER_STRONG_KEYWORDS = ["thời tiết", "dự báo"]
# Từ "yếu": cũng xuất hiện trong câu hỏi kiến thức ("nhiệt độ bao nhiêu thì chè chết?"), chỉ tính là thời tiết
# khi đi kèm tên vùng hoặc từ chỉ thời điểm hiện tại.
WEATHER_WEAK_KEYWORDS = ["nhiệt độ", "độ ẩm", "lượng mưa", "nắng", "mưa", "tốc độ gió"]
WEATHER_TIME_HINTS = ["hôm nay", "hiện tại", "bây giờ", "hiện nay", "ngày mai", "tuần này", "lúc này", "đang"]

KNOWLEDGE_KEYWORDS = [
    "bệnh", "triệu chứng", "phòng trừ", "sâu", "bọ", "rệp", "nấm", "thối búp",
    "chấm xám", "phồng lá", "đốm nâu", "dán cao", "giống chè", "canh tác",
    "chăm sóc", "bón phân", "cắt tỉa", "hái chè", "chế biến", "trồng",
]

# Lời chào/xã giao được khớp theo ranh giới từ để "hi" không khớp nhầm vào "chi", "thi", "khi"...
GREETING_PATTERN = re.compile(
    r"(?<!\w)(xin chào|chào bạn|chào|bạn là ai|giúp tôi|cảm ơn|tạm biệt|hello|hi)(?!\w)",
    re.IGNORECASE,
)

# Câu hỏi nối tiếp thường chứa đại từ chỉ định hoặc rất ngắn; cần ghép với câu trước để truy xuất.
FOLLOW_UP_PATTERN = re.compile(
    r"(?<!\w)(nó|đó|này|ấy|kia|vậy|thế thì|như vậy)(?!\w)", re.IGNORECASE
)
SHORT_QUERY_WORDS = 4
# Câu nêu vùng để hỏi tiếp về thời tiết thường rất ngắn ("Còn ở Phú Thọ thì sao?"); câu dài là chủ đề mới.
WEATHER_FOLLOW_UP_MAX_WORDS = 7


def _has_weather_keyword(text: str) -> bool:
    """Có từ khóa thời tiết (mạnh hoặc yếu); dùng để nhận biết hội thoại trước đó nói về thời tiết."""
    lowered = text.lower()
    return any(kw in lowered for kw in WEATHER_STRONG_KEYWORDS + WEATHER_WEAK_KEYWORDS)


def _is_weather_request(query: str, query_region: Optional[str]) -> bool:
    """Câu hỏi hiện tại có phải yêu cầu về thời tiết thực tế không."""
    lowered = query.lower()
    if any(kw in lowered for kw in WEATHER_STRONG_KEYWORDS):
        return True
    has_weak = any(kw in lowered for kw in WEATHER_WEAK_KEYWORDS)
    has_time_hint = any(hint in lowered for hint in WEATHER_TIME_HINTS)
    return has_weak and (query_region is not None or has_time_hint)


def extract_region_from_text(text: str) -> Optional[str]:
    return find_region_in_text(text)


def classify_assistant_intent(query: str, history_text: str = "") -> Dict[str, Any]:
    """
    Phân loại ý định bằng luật (không gọi LLM nên nhanh, xác định và dễ kiểm thử).

    - Tín hiệu thời tiết: có từ khóa thời tiết trong câu hỏi hiện tại, hoặc câu NGẮN nêu vùng khi hội thoại
      trước đó nói về thời tiết ("Còn ở Phú Thọ thì sao?"). Câu dài nêu vùng là chủ đề mới.
    - Vùng: ưu tiên vùng trong câu hỏi hiện tại, sau đó tới lịch sử, cuối cùng là vùng mặc định.
    """
    query_lower = query.lower()
    query_region = find_region_in_text(query)
    history_region = find_region_in_text(history_text) if history_text else None

    is_region_follow_up = (
        query_region is not None
        and len(query.split()) <= WEATHER_FOLLOW_UP_MAX_WORDS
        and _has_weather_keyword(history_text)
    )
    has_weather_signal = _is_weather_request(query, query_region) or is_region_follow_up
    has_knowledge_kw = any(kw in query_lower for kw in KNOWLEDGE_KEYWORDS)
    has_greeting = GREETING_PATTERN.search(query) is not None

    if has_weather_signal and has_knowledge_kw:
        task_type = TASK_HYBRID
    elif has_weather_signal:
        task_type = TASK_WEATHER
    elif has_greeting and not has_knowledge_kw:
        task_type = TASK_GENERAL
    else:
        task_type = TASK_KNOWLEDGE

    return {
        "task_type": task_type,
        "detected_region": query_region or history_region or DEFAULT_REGION,
        "query": query,
    }


def build_retrieval_query(message: str, previous_user_messages: List[str]) -> str:
    """
    Làm rõ câu hỏi nối tiếp trước khi truy xuất: "Cách phòng trừ nó thế nào?" không tự mang chủ đề,
    nên ghép với câu hỏi trước của người dùng. Câu hỏi đầy đủ ý được giữ nguyên.
    """
    if not previous_user_messages:
        return message
    is_short = len(message.split()) <= SHORT_QUERY_WORDS
    if is_short or FOLLOW_UP_PATTERN.search(message):
        return f"{previous_user_messages[-1]} {message}"
    return message
