import uuid
import unittest.mock as mock

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.assistant_service import get_default_retriever
from database.connection import engine
from database.models import Base

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def _auth_header() -> dict:
    """Tạo user mới với hậu tố ngẫu nhiên để test không phụ thuộc dữ liệu cũ trong DB."""
    suffix = uuid.uuid4().hex[:10]
    email = f"sec_{suffix}@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email, "username": f"sec_{suffix}", "password": "password123"
    })
    resp = client.post("/api/v1/auth/login", json={
        "username_or_email": email, "password": "password123"
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@mock.patch("backend.services.chat_service.generate_rag_response")
def _create_owned_session(headers: dict, mock_llm) -> int:
    mock_llm.return_value = "Bệnh thối búp do nấm gây ra."
    res = client.post(
        "/api/v1/chat/query",
        json={"message": "Bệnh thối búp hại chè có nguyên nhân là gì?"},
        headers=headers,
    )
    assert res.status_code == 200
    return res.json()["session_id"]


def test_owner_can_read_own_session():
    owner = _auth_header()
    session_id = _create_owned_session(owner)

    assert client.get(f"/api/v1/chat/sessions/{session_id}", headers=owner).status_code == 200
    assert client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=owner).status_code == 200


def test_other_user_cannot_access_session():
    owner = _auth_header()
    intruder = _auth_header()
    session_id = _create_owned_session(owner)

    assert client.get(f"/api/v1/chat/sessions/{session_id}", headers=intruder).status_code == 403
    assert client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=intruder).status_code == 403
    assert client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"role": "user", "content": "xin chào"},
        headers=intruder,
    ).status_code == 403
    assert client.delete(f"/api/v1/chat/sessions/{session_id}", headers=intruder).status_code == 403

    # Phiên vẫn còn nguyên sau khi kẻ lạ thử xóa
    assert client.get(f"/api/v1/chat/sessions/{session_id}", headers=owner).status_code == 200


def test_anonymous_cannot_access_owned_session():
    owner = _auth_header()
    session_id = _create_owned_session(owner)

    assert client.get(f"/api/v1/chat/sessions/{session_id}").status_code == 403
    assert client.delete(f"/api/v1/chat/sessions/{session_id}").status_code == 403


def test_owner_can_delete_session():
    owner = _auth_header()
    session_id = _create_owned_session(owner)

    assert client.delete(f"/api/v1/chat/sessions/{session_id}", headers=owner).status_code == 204
    assert client.get(f"/api/v1/chat/sessions/{session_id}", headers=owner).status_code == 404


def test_anonymous_session_list_is_empty():
    assert client.get("/api/v1/chat/sessions").json() == []


def test_session_list_only_returns_own_sessions():
    owner = _auth_header()
    other = _auth_header()
    session_id = _create_owned_session(owner)

    own_ids = [s["id"] for s in client.get("/api/v1/chat/sessions", headers=owner).json()]
    other_ids = [s["id"] for s in client.get("/api/v1/chat/sessions", headers=other).json()]
    assert session_id in own_ids
    assert session_id not in other_ids


def test_message_over_limit_is_rejected():
    res = client.post("/api/v1/chat/query", json={"message": "a" * 2001})
    assert res.status_code == 422


@mock.patch("backend.services.chat_service.generate_rag_response")
def test_fallback_answer_returns_no_sources(mock_llm):
    """Khi độ tương đồng thấp hơn ngưỡng, không hiển thị các chunk không liên quan như nguồn tham khảo."""
    fake_retriever = mock.Mock()
    fake_retriever.retrieve.return_value = {
        "context_text": "",
        "retrieved_chunks": [{
            "chunk_id": "tea_000001",
            "metadata": {"title": "Không liên quan", "source": "TL1"},
            "similarity_score": 0.1,
        }],
    }
    with mock.patch(
        "backend.services.assistant_service.get_default_retriever",
        return_value=fake_retriever,
    ):
        res = client.post("/api/v1/chat/query", json={"message": "Kỹ thuật ghép cành cây sầu riêng?"})

    assert res.status_code == 200
    assert res.json()["sources"] == []
    assert "chưa tìm thấy nguồn" in res.json()["answer"]
    mock_llm.assert_not_called()


def test_default_retriever_is_shared_instance():
    """RAGRetriever (model embedding + ChromaDB) chỉ được khởi tạo một lần cho cả tiến trình."""
    assert get_default_retriever() is get_default_retriever()
