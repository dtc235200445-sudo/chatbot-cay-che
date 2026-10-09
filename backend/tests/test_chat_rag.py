import pytest
import unittest.mock as mock
import openai
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings
from database.connection import engine
from database.models import Base, User, ChatSession, ChatMessage
from backend.dependencies.db import get_db
from backend.services.auth_service import create_access_token

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def get_auth_header(email: str = "testuser_chat@example.com", username: str = "chatuser"):
    # Register/Login helper for tests
    client.post("/api/v1/auth/register", json={
        "email": email, "username": username, "password": "password123"
    })
    resp = client.post("/api/v1/auth/login", json={
        "username_or_email": email, "password": "password123"
    })
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}

# ============================================================
# TEST 1 — NEW SESSION
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_1_new_session(mock_llm):
    mock_llm.return_value = "Bệnh thối búp do nấm Colletotrichum gây ra."
    
    response = client.post("/api/v1/chat/query", json={
        "message": "Bệnh thối búp hại chè có nguyên nhân là gì?"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] is not None
    assert data["role"] == "assistant"
    assert "Colletotrichum" in data["answer"]
    assert len(data["sources"]) > 0
    mock_llm.assert_called_once()

# ============================================================
# TEST 2 — MULTI-TURN CONVERSATION
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_2_multi_turn_conversation(mock_llm):
    mock_llm.return_value = "Triệu chứng bệnh chấm xám là các vết chấm màu xám trên lá chè."
    
    # Turn 1
    res1 = client.post("/api/v1/chat/query", json={
        "message": "Bệnh chấm xám trên cây chè có triệu chứng gì?"
    })
    assert res1.status_code == 200
    session_id = res1.json()["session_id"]
    
    # Turn 2 using same session_id
    mock_llm.return_value = "Biện pháp phòng trừ bệnh chấm xám bao gồm phun thuốc thối búp và dọn dẹp tàn dư."
    res2 = client.post("/api/v1/chat/query", json={
        "session_id": session_id,
        "message": "Cách phòng trừ nó như thế nào?"
    })
    assert res2.status_code == 200
    assert res2.json()["session_id"] == session_id
    assert mock_llm.call_count == 2
    
    # Check history passed to mock in Turn 2
    args, kwargs = mock_llm.call_args
    history = kwargs.get("history_turns") or args[2]
    assert len(history) >= 2  # Turn 1 user + assistant msgs

# ============================================================
# TEST 3 — OOD / LOW SIMILARITY (FALLBACK)
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_3_low_similarity_fallback(mock_llm):
    # Query completely unrelated to tea knowledge
    response = client.post("/api/v1/chat/query", json={
        "message": "Cách làm bánh pizza hải sản tại nhà"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "chưa tìm thấy nguồn thông tin đủ phù hợp" in data["answer"]
    # Verify OpenAI was NOT called
    mock_llm.assert_not_called()

# ============================================================
# TEST 4 — OWNERSHIP SECURITY
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_4_ownership_security(mock_llm):
    mock_llm.return_value = "Câu trả lời mẫu."
    
    headers_a = get_auth_header("usera@example.com", "usera")
    headers_b = get_auth_header("userb@example.com", "userb")
    
    # User A creates a session
    res_a = client.post("/api/v1/chat/query", json={
        "message": "Bệnh phồng lá chè"
    }, headers=headers_a)
    session_id = res_a.json()["session_id"]
    
    # User B attempts to access User A's session -> Expected 403
    res_b = client.post("/api/v1/chat/query", json={
        "session_id": session_id,
        "message": "Cách chữa bệnh này"
    }, headers=headers_b)
    
    assert res_b.status_code == 403
    assert "Forbidden" in res_b.json()["detail"]

# ============================================================
# TEST 5 — ANONYMOUS / AUTHENTICATED ISOLATION
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_5_anonymous_isolation(mock_llm):
    mock_llm.return_value = "Phản hồi anonymous."
    
    # Anonymous query creates session with user_id = NULL
    res = client.post("/api/v1/chat/query", json={
        "message": "Cây chè cần tưới bao nhiêu nước?"
    })
    assert res.status_code == 200
    anon_session_id = res.json()["session_id"]
    
    # Anonymous session is accessible (MVP Limitation)
    res2 = client.post("/api/v1/chat/query", json={
        "session_id": anon_session_id,
        "message": "Thời điểm tưới nước thích hợp?"
    })
    assert res2.status_code == 200

# ============================================================
# TEST 6 — SOURCES CITATIONS
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_6_sources_citations(mock_llm):
    mock_llm.return_value = "Phòng trừ bọ cánh tơ bằng phun thuốc sinh học."
    
    response = client.post("/api/v1/chat/query", json={
        "message": "Cách phòng trừ bọ cánh tơ hại chè"
    })
    
    assert response.status_code == 200
    sources = response.json()["sources"]
    assert len(sources) > 0
    first_source = sources[0]
    assert "chunk_id" in first_source
    assert "title" in first_source
    assert "source" in first_source
    assert "similarity_score" in first_source
    assert first_source["similarity_score"] >= 0.42

# ============================================================
# TEST 7 — RATE LIMIT ERROR (HTTP 503)
# ============================================================
@mock.patch("backend.services.llm_service.AsyncOpenAI")
def test_7_rate_limit_error(mock_async_openai):
    # Mock RateLimitError from openai client (used as Groq HTTP client)
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create = mock.AsyncMock(
        side_effect=openai.RateLimitError("Rate limit exceeded", response=mock.MagicMock(), body={})
    )
    mock_async_openai.return_value = mock_client

    with mock.patch("backend.config.settings.GROQ_API_KEY", "gsk-test-key-12345"):
        response = client.post("/api/v1/chat/query", json={
            "message": "Bệnh dán cao hại chè"
        })
        assert response.status_code == 503
        assert "hạn mức" in response.json()["detail"].lower()

# ============================================================
# TEST 7b — MẤT KẾT NỐI TỚI GROQ (HTTP 503, thông báo tiếng Việt)
# ============================================================
@mock.patch("backend.services.llm_service.AsyncOpenAI")
def test_7b_connection_error_returns_clear_503(mock_async_openai):
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create = mock.AsyncMock(
        side_effect=openai.APIConnectionError(request=mock.MagicMock())
    )
    mock_async_openai.return_value = mock_client

    with mock.patch("backend.config.settings.GROQ_API_KEY", "gsk-test-key-12345"):
        response = client.post("/api/v1/chat/query", json={"message": "Bệnh dán cao hại chè"})
    assert response.status_code == 503
    assert "kết nối" in response.json()["detail"].lower()
    # Client được tạo với số lần thử lại và thời gian chờ cấu hình được
    kwargs = mock_async_openai.call_args.kwargs
    assert kwargs["max_retries"] >= 1 and kwargs["timeout"] > 0

# ============================================================
# TEST 7c — NỘI DUNG RỖNG: thử lại một lần, rồi mới báo lỗi
# ============================================================
def _completion(content):
    msg = mock.MagicMock(); msg.content = content
    choice = mock.MagicMock(); choice.message = msg; choice.finish_reason = "length"
    resp = mock.MagicMock(); resp.choices = [choice]
    return resp


@mock.patch("backend.services.llm_service.AsyncOpenAI")
def test_7c_empty_completion_is_retried_once_with_larger_budget(mock_async_openai):
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create = mock.AsyncMock(side_effect=[_completion(""), _completion("Đã có nội dung.")])
    mock_async_openai.return_value = mock_client

    with mock.patch("backend.config.settings.GROQ_API_KEY", "gsk-test-key-12345"):
        response = client.post("/api/v1/chat/query", json={"message": "Bệnh dán cao hại chè"})
    assert response.status_code == 200
    calls = mock_client.chat.completions.create.call_args_list
    assert len(calls) == 2
    assert calls[1].kwargs["max_tokens"] == 2 * calls[0].kwargs["max_tokens"]


@mock.patch("backend.services.llm_service.AsyncOpenAI")
def test_7d_persistent_empty_completion_returns_502(mock_async_openai):
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create = mock.AsyncMock(side_effect=[_completion(""), _completion("   ")])
    mock_async_openai.return_value = mock_client

    with mock.patch("backend.config.settings.GROQ_API_KEY", "gsk-test-key-12345"):
        response = client.post("/api/v1/chat/query", json={"message": "Bệnh dán cao hại chè"})
    assert response.status_code == 502


@mock.patch("backend.services.llm_service.AsyncOpenAI")
def test_7e_reasoning_effort_only_for_gpt_oss_models(mock_async_openai):
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create = mock.AsyncMock(return_value=_completion("Nội dung."))
    mock_async_openai.return_value = mock_client

    with mock.patch("backend.config.settings.GROQ_API_KEY", "gsk-test-key-12345"):
        with mock.patch("backend.config.settings.GROQ_MODEL", "openai/gpt-oss-120b"):
            client.post("/api/v1/chat/query", json={"message": "Bệnh dán cao hại chè"})
        with mock.patch("backend.config.settings.GROQ_MODEL", "qwen/qwen3.8-27b"):
            client.post("/api/v1/chat/query", json={"message": "Bệnh dán cao hại chè"})
    first, second = mock_client.chat.completions.create.call_args_list
    assert first.kwargs["reasoning_effort"] == "medium"
    assert "reasoning_effort" not in second.kwargs

# ============================================================
# TEST 7f — NHÀ CUNG CẤP DỰ PHÒNG (LLM_FALLBACKS)
# ============================================================
def _ratelimit():
    return openai.RateLimitError("Rate limit exceeded", response=mock.MagicMock(), body={})


@mock.patch("backend.services.llm_service.AsyncOpenAI")
def test_7f_falls_back_to_next_provider_on_rate_limit(mock_async_openai, monkeypatch):
    groq_client = mock.MagicMock()
    groq_client.chat.completions.create = mock.AsyncMock(side_effect=_ratelimit())
    other_client = mock.MagicMock()
    other_client.chat.completions.create = mock.AsyncMock(return_value=_completion("Trả lời từ dự phòng."))
    mock_async_openai.side_effect = [groq_client, other_client]
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-cerebras-key")

    with mock.patch("backend.config.settings.GROQ_API_KEY", "gsk-test-key-12345"), \
         mock.patch("backend.config.settings.LLM_FALLBACKS", "cerebras:some-model"):
        response = client.post("/api/v1/chat/query", json={"message": "Bệnh dán cao hại chè"})
    assert response.status_code == 200
    assert "dự phòng" in response.json()["answer"]
    urls = [c.kwargs["base_url"] for c in mock_async_openai.call_args_list]
    assert "cerebras" in urls[1]
    # Khi có dự phòng, nhà cung cấp chính chỉ thử lại ít để chuyển nhanh
    assert mock_async_openai.call_args_list[0].kwargs["max_retries"] <= 1
    # Không gửi tham số reasoning_effort của Groq sang nhà cung cấp khác
    assert "reasoning_effort" not in other_client.chat.completions.create.call_args.kwargs


@mock.patch("backend.services.llm_service.AsyncOpenAI")
def test_7g_all_providers_fail_returns_primary_error(mock_async_openai, monkeypatch):
    failing = mock.MagicMock()
    failing.chat.completions.create = mock.AsyncMock(side_effect=_ratelimit())
    mock_async_openai.return_value = failing
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-cerebras-key")

    with mock.patch("backend.config.settings.GROQ_API_KEY", "gsk-test-key-12345"), \
         mock.patch("backend.config.settings.LLM_FALLBACKS", "cerebras:some-model"):
        response = client.post("/api/v1/chat/query", json={"message": "Bệnh dán cao hại chè"})
    assert response.status_code == 503
    assert "Groq" in response.json()["detail"]


@mock.patch("backend.services.llm_service.AsyncOpenAI")
def test_7h_fallback_without_key_or_unknown_provider_is_skipped(mock_async_openai, monkeypatch):
    groq_client = mock.MagicMock()
    groq_client.chat.completions.create = mock.AsyncMock(side_effect=_ratelimit())
    mock_async_openai.return_value = groq_client
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)

    with mock.patch("backend.config.settings.GROQ_API_KEY", "gsk-test-key-12345"), \
         mock.patch("backend.config.settings.LLM_FALLBACKS", "cerebras:m,khong-ton-tai:m,gemini"):
        response = client.post("/api/v1/chat/query", json={"message": "Bệnh dán cao hại chè"})
    assert response.status_code == 503
    assert mock_async_openai.call_count == 1  # chỉ Groq; các mục dự phòng đều bị bỏ qua


@mock.patch("backend.services.llm_service.AsyncOpenAI")
def test_7i_ollama_provider_runs_locally_without_api_key(mock_async_openai):
    local_client = mock.MagicMock()
    local_client.chat.completions.create = mock.AsyncMock(return_value=_completion("Trả lời từ model trên máy."))
    mock_async_openai.return_value = local_client

    with mock.patch("backend.config.settings.LLM_PROVIDER", "ollama"), \
         mock.patch("backend.config.settings.GROQ_API_KEY", ""), \
         mock.patch("backend.config.settings.LLM_FALLBACKS", ""):
        response = client.post("/api/v1/chat/query", json={"message": "Bệnh dán cao hại chè"})
    assert response.status_code == 200
    assert "trên máy" in response.json()["answer"]
    kwargs = mock_async_openai.call_args.kwargs
    assert kwargs["base_url"] == settings.OLLAMA_BASE_URL
    assert kwargs["timeout"] == settings.OLLAMA_TIMEOUT_S
    sent = local_client.chat.completions.create.call_args.kwargs
    assert sent["model"] == settings.OLLAMA_MODEL
    assert "reasoning_effort" not in sent  # tham số riêng của Groq

# ============================================================
# TEST 8 — HISTORY TRUNCATION
# ============================================================
@mock.patch("backend.services.chat_service.generate_rag_response")
def test_8_history_truncation(mock_llm):
    mock_llm.return_value = "OK"
    
    # Create session
    res = client.post("/api/v1/chat/query", json={"message": "Bệnh thối búp hại chè là gì? (lần 1)"})
    session_id = res.json()["session_id"]
    
    # Send 6 turns to exceed MAX_HISTORY_TURNS (5)
    for i in range(2, 7):
        client.post("/api/v1/chat/query", json={
            "session_id": session_id,
            "message": f"Bệnh thối búp hại chè là gì? (lần {i})"
        })
        
    args, kwargs = mock_llm.call_args
    history = kwargs.get("history_turns") or args[2]
    # Verify history passed to LLM is truncated to max 5 turns
    assert len(history) <= 10  # 5 turns * 2 msgs per turn


def test_retry_after_text_is_translated_to_vietnamese():
    from backend.services.llm_service import _retry_after_text
    assert _retry_after_text("Limit 200000, Used 199494. Please try again in 11m22.56s. Need more") == "11 phút 22 giây"
    assert _retry_after_text("Please try again in 1h5m3s.") == "1 giờ 5 phút"
    assert _retry_after_text("Please try again in 45.5s.") == "45 giây"
    assert _retry_after_text("không có gợi ý") == ""
