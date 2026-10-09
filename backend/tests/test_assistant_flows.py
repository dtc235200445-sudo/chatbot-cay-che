import unittest.mock as mock

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from database.connection import engine
from database.models import Base
from rag.vector_store import IndexNotReadyError

client = TestClient(app)

LLM_PATH = "backend.services.chat_service.generate_rag_response"
RETRIEVER_PATH = "backend.services.assistant_service.get_default_retriever"
WEATHER_PATH = "backend.services.assistant_service.fetch_and_sync_live_weather"


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def _fake_retriever(relevant: bool, chunk_id: str = "tea_000032"):
    fake = mock.Mock()
    fake.retrieve.return_value = {
        "context_text": "NGỮ CẢNH GIẢ",
        "retrieved_chunks": [{
            "chunk_id": chunk_id,
            "metadata": {"title": "Tiêu đề giả", "source": "TL1"},
            "similarity_score": 0.8,
        }],
        "is_relevant": relevant,
    }
    return fake


def _weather(region="Thái Nguyên"):
    return mock.MagicMock(
        region=region, temperature=26.5, humidity=82.0, rainfall=0.0,
        wind_speed=3.2, weather_condition="Ít mây", recorded_at=None,
    )


@pytest.mark.parametrize("message, expected", [
    ("Xin chào", "Tea Scholar AI"),
    ("Cảm ơn bạn", "vui được hỗ trợ"),
    ("Tạm biệt", "Tạm biệt"),
])
@mock.patch(LLM_PATH)
def test_small_talk_is_answered_without_llm_or_retrieval(mock_llm, message, expected):
    with mock.patch(RETRIEVER_PATH) as get_retriever:
        res = client.post("/api/v1/chat/query", json={"message": message})
    assert res.status_code == 200
    assert expected in res.json()["answer"]
    assert res.json()["sources"] == []
    mock_llm.assert_not_called()
    get_retriever.assert_not_called()


@mock.patch(LLM_PATH)
def test_relevant_question_passes_context_and_sources_to_llm(mock_llm):
    mock_llm.return_value = "Trả lời"
    with mock.patch(RETRIEVER_PATH, return_value=_fake_retriever(True)):
        res = client.post("/api/v1/chat/query", json={"message": "Bệnh thối búp có triệu chứng gì?"})
    body = res.json()
    assert [s["chunk_id"] for s in body["sources"]] == ["tea_000032"]
    assert mock_llm.call_args.kwargs["context_text"] == "NGỮ CẢNH GIẢ"
    assert mock_llm.call_args.kwargs["weather_context"] is None


@mock.patch(WEATHER_PATH)
@mock.patch(LLM_PATH)
def test_hybrid_without_relevant_knowledge_does_not_leak_irrelevant_context(mock_llm, mock_weather):
    """Câu hỏi lai mà cơ sở tri thức không có nội dung phù hợp: chỉ dùng thời tiết, không đưa chunk lạc đề vào LLM."""
    mock_weather.return_value = _weather()
    mock_llm.return_value = "Trả lời"
    with mock.patch(RETRIEVER_PATH, return_value=_fake_retriever(False)):
        res = client.post(
            "/api/v1/chat/query",
            json={"message": "Thời tiết Thái Nguyên có hợp để trồng cà phê không?"},
        )
    assert res.status_code == 200
    assert res.json()["sources"] == []
    kwargs = mock_llm.call_args.kwargs
    assert kwargs["context_text"] == ""
    assert "Thái Nguyên" in kwargs["weather_context"]


@mock.patch(WEATHER_PATH)
@mock.patch(LLM_PATH)
def test_region_in_technical_question_does_not_call_weather(mock_llm, mock_weather):
    mock_llm.return_value = "Trả lời"
    with mock.patch(RETRIEVER_PATH, return_value=_fake_retriever(True)):
        client.post("/api/v1/chat/query", json={"message": "Kỹ thuật đốn chè ở Thái Nguyên"})
    mock_weather.assert_not_called()


@mock.patch(LLM_PATH)
def test_follow_up_question_is_expanded_with_previous_question_for_retrieval(mock_llm):
    mock_llm.return_value = "Trả lời"
    fake = _fake_retriever(True)
    with mock.patch(RETRIEVER_PATH, return_value=fake):
        first = client.post("/api/v1/chat/query", json={"message": "Bệnh chấm xám có triệu chứng gì?"})
        client.post("/api/v1/chat/query", json={
            "session_id": first.json()["session_id"],
            "message": "Cách phòng trừ nó thế nào?",
        })
    queries = [c.kwargs["query"] for c in fake.retrieve.call_args_list]
    assert queries[0] == "Bệnh chấm xám có triệu chứng gì?"
    assert "chấm xám" in queries[1] and "phòng trừ" in queries[1]
    # Câu hỏi gửi cho LLM vẫn là câu gốc của người dùng
    assert mock_llm.call_args.kwargs["query"] == "Cách phòng trừ nó thế nào?"


def test_missing_rag_index_returns_503_with_instruction():
    fake = mock.Mock()
    fake.retrieve.side_effect = IndexNotReadyError("Chưa có chỉ mục vector. Chạy: python -m rag.ingest")
    with mock.patch(RETRIEVER_PATH, return_value=fake):
        res = client.post("/api/v1/chat/query", json={"message": "Bệnh thối búp có triệu chứng gì?"})
    assert res.status_code == 503
    assert "rag.ingest" in res.json()["detail"]


@mock.patch(WEATHER_PATH)
def test_weather_question_surfaces_provider_error(mock_weather):
    from fastapi import HTTPException
    mock_weather.side_effect = HTTPException(status_code=502, detail="Open-Meteo lỗi")
    res = client.post("/api/v1/chat/query", json={"message": "Thời tiết Thái Nguyên hôm nay?"})
    assert res.status_code == 502


@mock.patch(LLM_PATH)
def test_session_title_is_set_from_first_question(mock_llm):
    mock_llm.return_value = "Trả lời"
    with mock.patch(RETRIEVER_PATH, return_value=_fake_retriever(True)):
        res = client.post("/api/v1/chat/query", json={
            "message": "Bệnh thối búp trên cây chè có triệu chứng gì và cách phòng trừ ra sao?"
        })
    session = client.get(f"/api/v1/chat/sessions/{res.json()['session_id']}").json()
    assert session["title"] == "Bệnh thối búp trên cây chè có triệu chứng "[:40]


@mock.patch(LLM_PATH)
def test_llm_refusal_hides_irrelevant_sources(mock_llm):
    """Câu hỏi lọt qua cổng truy xuất nhưng LLM từ chối: không kèm nguồn lạc đề."""
    mock_llm.return_value = "Hiện tại cơ sở tri thức chưa có đủ thông tin để trả lời chính xác câu hỏi này của bạn."
    with mock.patch(RETRIEVER_PATH, return_value=_fake_retriever(True)):
        res = client.post("/api/v1/chat/query", json={"message": "Cách sửa xe máy bị chết máy"})
    assert res.status_code == 200
    assert res.json()["sources"] == []


@mock.patch(LLM_PATH)
def test_partial_answer_keeps_sources(mock_llm):
    """Câu trả lời dài chỉ nhắc thiếu một phần thông tin vẫn phải giữ nguồn."""
    mock_llm.return_value = (
        "Bệnh thối búp gây hại ở lá non và cành non, vết bệnh đầu kim màu nâu đen. "
        "Tuy nhiên cơ sở tri thức chưa có đủ thông tin về liều lượng thuốc cụ thể cho từng vùng trồng, "
        "bạn nên tham khảo cán bộ kỹ thuật địa phương để được hướng dẫn chi tiết hơn."
    )
    with mock.patch(RETRIEVER_PATH, return_value=_fake_retriever(True)):
        res = client.post("/api/v1/chat/query", json={"message": "Bệnh thối búp có triệu chứng gì?"})
    assert len(res.json()["sources"]) == 1
