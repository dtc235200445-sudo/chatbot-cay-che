import pytest
import unittest.mock as mock
import httpx
from fastapi.testclient import TestClient
from backend.main import app
from database.connection import engine
from database.models import Base, User, ChatSession, ChatMessage
from backend.services.assistant_service import classify_assistant_intent, TASK_KNOWLEDGE, TASK_WEATHER, TASK_HYBRID, TASK_GENERAL

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def get_auth_header(email: str = "usera_assistant@example.com", username: str = "usera_asst"):
    client.post("/api/v1/auth/register", json={
        "email": email, "username": username, "password": "password123"
    })
    resp = client.post("/api/v1/auth/login", json={
        "username_or_email": email, "password": "password123"
    })
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}

MOCK_WEATHER_RETURN = {
    "temperature": 26.5,
    "humidity": 82.0,
    "rainfall": 0.0,
    "wind_speed": 3.2,
    "weather_condition": "Ít mây",
    "recorded_at": "2026-09-16T17:00:00Z"
}

# ============================================================
# INTENT CLASSIFICATION UNIT TEST
# ============================================================
def test_intent_classification():
    res1 = classify_assistant_intent("Bệnh thối búp trên cây chè có triệu chứng gì?")
    assert res1["task_type"] == TASK_KNOWLEDGE

    res2 = classify_assistant_intent("Thời tiết Thái Nguyên hôm nay thế nào?")
    assert res2["task_type"] == TASK_WEATHER
    assert res2["detected_region"] == "Thái Nguyên"

    res3 = classify_assistant_intent("Thời tiết Thái Nguyên hiện tại có điều kiện thuận lợi cho bệnh thối búp không?")
    assert res3["task_type"] == TASK_HYBRID

    res4 = classify_assistant_intent("Xin chào bạn là ai?")
    assert res4["task_type"] == TASK_GENERAL

# ============================================================
# TEST 1 — KNOWLEDGE QUERY
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_1_knowledge_query(mock_llm):
    mock_llm.return_value = "Bệnh thối búp hại chè do nấm Colletotrichum gây ra."

    response = client.post("/api/v1/chat/query", json={
        "message": "Bệnh thối búp trên cây chè có triệu chứng gì?"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
    assert len(data["sources"]) > 0
    assert "Colletotrichum" in data["answer"]
    mock_llm.assert_called_once()

# ============================================================
# TEST 2 — WEATHER QUERY
# ============================================================
@mock.patch("backend.services.assistant_service.fetch_and_sync_live_weather")
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_2_weather_query(mock_llm, mock_weather):
    mock_weather.return_value = mock.MagicMock(
        region="Thái Nguyên", temperature=26.5, humidity=82.0,
        rainfall=0.0, wind_speed=3.2, weather_condition="Ít mây",
        recorded_at=None
    )
    mock_llm.return_value = "Thời tiết Thái Nguyên hiện tại ít mây, nhiệt độ 26.5°C."

    response = client.post("/api/v1/chat/query", json={
        "message": "Thời tiết Thái Nguyên hôm nay thế nào?"
    })

    assert response.status_code == 200
    data = response.json()
    assert "26.5" in data["answer"] or "Thái Nguyên" in data["answer"]
    mock_weather.assert_called_once()

# ============================================================
# TEST 3 — HYBRID QUERY (WEATHER + RAG)
# ============================================================
@mock.patch("backend.services.assistant_service.fetch_and_sync_live_weather")
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_3_hybrid_query(mock_llm, mock_weather):
    mock_weather.return_value = mock.MagicMock(
        region="Thái Nguyên", temperature=28.0, humidity=90.0,
        rainfall=15.0, wind_speed=2.5, weather_condition="Mưa rào",
        recorded_at=None
    )
    mock_llm.return_value = "Độ ẩm 90% và mưa rào tại Thái Nguyên là điều kiện rất thuận lợi cho nấm thối búp bùng phát."

    response = client.post("/api/v1/chat/query", json={
        "message": "Thời tiết Thái Nguyên hiện tại có điều kiện thuận lợi cho bệnh thối búp không?"
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["sources"]) > 0  # RAG sources preserved
    mock_weather.assert_called_once()
    mock_llm.assert_called_once()

# ============================================================
# TEST 4 — GENERAL CHAT
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_4_general_chat(mock_llm):
    mock_llm.return_value = "Xin chào! Tôi là Tea Scholar AI, trợ lý chuyên sâu về cây chè Việt Nam."

    response = client.post("/api/v1/chat/query", json={
        "message": "Xin chào bạn là ai?"
    })

    assert response.status_code == 200
    data = response.json()
    assert "Tea Scholar AI" in data["answer"]

# ============================================================
# TEST 5 — SESSION HISTORY PRESERVATION
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_5_session_history_preservation(mock_llm):
    mock_llm.return_value = "Bệnh chấm xám xuất hiện ở lá chè bánh tẻ."

    res1 = client.post("/api/v1/chat/query", json={
        "message": "Bệnh chấm xám xuất hiện ở đâu?"
    })
    session_id = res1.json()["session_id"]

    mock_llm.return_value = "Cách phòng trừ là tỉa lá và phun thuốc sinh học."
    res2 = client.post("/api/v1/chat/query", json={
        "session_id": session_id,
        "message": "Cách phòng trừ nó thế nào?"
    })
    assert res2.status_code == 200
    assert res2.json()["session_id"] == session_id

# ============================================================
# TEST 6 — SESSION OWNERSHIP SECURITY
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_6_ownership_security(mock_llm):
    mock_llm.return_value = "OK"

    hdr_a = get_auth_header("asst_usera@example.com", "asst_a")
    hdr_b = get_auth_header("asst_userb@example.com", "asst_b")

    res_a = client.post("/api/v1/chat/query", json={
        "message": "Kỹ thuật đốn chè"
    }, headers=hdr_a)
    session_id = res_a.json()["session_id"]

    res_b = client.post("/api/v1/chat/query", json={
        "session_id": session_id,
        "message": "Hack session"
    }, headers=hdr_b)

    assert res_b.status_code == 403

# ============================================================
# TEST 7 — LOW SIMILARITY FALLBACK
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_7_low_similarity_fallback(mock_llm):
    response = client.post("/api/v1/chat/query", json={
        "message": "Cách làm bánh mì kẹp thịt bò"
    })
    assert response.status_code == 200
    assert "chưa tìm thấy nguồn thông tin đủ phù hợp" in response.json()["answer"]
    mock_llm.assert_not_called()

# ============================================================
# TEST 8 — WEATHER ERROR HANDLING
# ============================================================
def test_8_weather_error_unknown_region():
    response = client.get("/api/v1/weather/live?region=ThànhPhốKhôngTồnTại999")
    assert response.status_code == 404
    assert "coordinate" in response.json()["detail"].lower()
