import pytest

from backend.services.intent_classifier import (
    TASK_GENERAL,
    TASK_HYBRID,
    TASK_KNOWLEDGE,
    TASK_WEATHER,
    build_retrieval_query,
    classify_assistant_intent,
)
from backend.services.regions import find_region_in_text, resolve_coordinates


@pytest.mark.parametrize("query, expected", [
    ("Bệnh thối búp trên cây chè có triệu chứng gì?", TASK_KNOWLEDGE),
    ("Thời tiết Thái Nguyên hôm nay thế nào?", TASK_WEATHER),
    ("Thời tiết Thái Nguyên hiện tại có điều kiện thuận lợi cho bệnh thối búp không?", TASK_HYBRID),
    ("Xin chào bạn là ai?", TASK_GENERAL),
    ("Cảm ơn bạn nhiều", TASK_GENERAL),
    ("Hi", TASK_GENERAL),
    # "hi" không được khớp vào giữa từ như "chi", "thi", "khi"
    ("Chi phí đầu tư một ha chè là bao nhiêu?", TASK_KNOWLEDGE),
    ("Khi nào thì nên hái chè?", TASK_KNOWLEDGE),
    # Giúp tôi + nội dung chuyên môn vẫn là câu hỏi tri thức
    ("Giúp tôi cách bón phân cho chè", TASK_KNOWLEDGE),
    # Từ "nhiệt độ", "độ ẩm", "mưa" xuất hiện trong câu hỏi kiến thức không được chuyển sang nhánh thời tiết
    ("Nhiệt độ bao nhiêu thì cây chè bị chết?", TASK_KNOWLEDGE),
    ("Độ ẩm bao nhiêu thì phù hợp cho cây chè?", TASK_KNOWLEDGE),
    ("Lượng mưa tối thiểu hằng năm cho chè là bao nhiêu?", TASK_KNOWLEDGE),
    ("Trời mưa có nên hái chè không?", TASK_KNOWLEDGE),
    # Từ yếu đi kèm vùng hoặc thời điểm hiện tại vẫn là hỏi thời tiết
    ("Nhiệt độ Thái Nguyên bây giờ là bao nhiêu?", TASK_WEATHER),
    ("Độ ẩm Đà Lạt", TASK_WEATHER),
    ("Nhiệt độ hiện tại có thuận lợi cho bệnh thối búp không?", TASK_HYBRID),
])
def test_intent_classification(query, expected):
    assert classify_assistant_intent(query)["task_type"] == expected


def test_region_mention_alone_does_not_trigger_weather():
    """Nêu tên vùng trong câu hỏi kỹ thuật không được kéo theo lời gọi API thời tiết."""
    result = classify_assistant_intent("Kỹ thuật đốn chè ở Thái Nguyên")
    assert result["task_type"] == TASK_KNOWLEDGE


def test_region_follow_up_after_weather_question_is_weather():
    history = "Thời tiết Thái Nguyên hôm nay thế nào? Nhiệt độ 26°C."
    result = classify_assistant_intent("Còn ở Phú Thọ thì sao?", history_text=history)
    assert result["task_type"] == TASK_WEATHER
    assert result["detected_region"] == "Phú Thọ"


def test_long_question_naming_region_after_weather_is_knowledge_not_weather():
    """Hồi quy: hỏi về chè Tân Cương (Thái Nguyên) sau câu hỏi thời tiết không được xếp vào thời tiết."""
    history = "Thời tiết Thái Nguyên hôm nay thế nào? Nhiệt độ 28.8°C."
    result = classify_assistant_intent("tôi muốn tìm hiểu thêm về chè tân cương thái nguyên", history_text=history)
    assert result["task_type"] == TASK_KNOWLEDGE


def test_region_prefers_current_query_over_history():
    result = classify_assistant_intent("Thời tiết Lâm Đồng thế nào?", history_text="Thái Nguyên")
    assert result["detected_region"] == "Lâm Đồng"


def test_region_falls_back_to_history_then_default():
    with_history = classify_assistant_intent("Trời có mưa không?", history_text="Thời tiết Sơn La")
    assert with_history["detected_region"] == "Sơn La"
    assert classify_assistant_intent("Trời có mưa không?")["detected_region"] == "Thái Nguyên"


def test_build_retrieval_query_merges_follow_up():
    merged = build_retrieval_query("Cách phòng trừ nó thế nào?", ["Bệnh chấm xám có triệu chứng gì?"])
    assert "chấm xám" in merged and "phòng trừ" in merged


def test_build_retrieval_query_keeps_self_contained_question():
    question = "Bệnh thối búp trên cây chè có triệu chứng gì?"
    assert build_retrieval_query(question, ["Rầy xanh gây hại như thế nào?"]) == question


def test_build_retrieval_query_without_history():
    assert build_retrieval_query("Cách phòng trừ nó?", []) == "Cách phòng trừ nó?"


def test_find_region_returns_earliest_mention():
    assert find_region_in_text("So sánh Phú Thọ với Thái Nguyên") == "Phú Thọ"
    assert find_region_in_text("Không có địa danh") is None


def test_resolve_coordinates():
    assert resolve_coordinates("thái nguyên") is not None
    assert resolve_coordinates("Thành phố không tồn tại 999") is None
