import json
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.main import app
from database.connection import engine
from database.models import Base

client = TestClient(app)

def test_health_endpoints():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    response_health = client.get("/api/v1/health")
    assert response_health.status_code == 200
    assert response_health.json()["status"] == "ok"

def test_knowledge_base_endpoints():
    # List all knowledge chunks (page_size=200 to fetch all)
    res = client.get("/api/v1/knowledge?page=1&page_size=200")
    assert res.status_code == 200
    data = res.json()
    expected_total = len(json.loads(Path(__file__).resolve().parents[2].joinpath("data", "knowledge_base.json").read_text(encoding="utf-8")))
    assert data["total"] == expected_total
    assert len(data["items"]) == expected_total

    # Fetch chunk detail tea_000001
    res_detail = client.get("/api/v1/knowledge/tea_000001")
    assert res_detail.status_code == 200
    chunk = res_detail.json()
    assert chunk["chunk_id"] == "tea_000001"
    assert "metadata" in chunk
    assert chunk["metadata"]["original_chunk_id"] == "TL1-A00"

    # Search keyword search
    res_search = client.get("/api/v1/knowledge/search?q=đất")
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["total"] > 0

def test_knowledge_base_integrity_with_json():
    # Compare knowledge_base.json vs API output
    kb_path = BASE_DIR / "data" / "knowledge_base.json"
    with open(kb_path, "r", encoding="utf-8") as f:
        json_chunks = json.load(f)

    res = client.get("/api/v1/knowledge?page=1&page_size=200")
    api_items = {item["chunk_id"]: item for item in res.json()["items"]}

    assert len(json_chunks) >= 162  # 162 chunk gốc + các chunk từ nguồn ngoài (data/external)
    assert len(api_items) == len(json_chunks)

    lost_chunks = 0
    mismatch_content = 0

    for item in json_chunks:
        cid = item["chunk_id"]
        if cid not in api_items:
            lost_chunks += 1
        else:
            if item["content"].strip() != api_items[cid]["content"].strip():
                mismatch_content += 1

    assert lost_chunks == 0
    assert mismatch_content == 0

def test_documents_endpoints():
    res = client.get("/api/v1/documents")
    assert res.status_code == 200
    # 3 tài liệu gốc + mỗi tệp trong data/external là một tài liệu nguồn
    external_docs = len(list((BASE_DIR / "data" / "external").glob("*.json")))
    assert res.json()["total"] == 3 + external_docs

def test_diseases_endpoints():
    res = client.get("/api/v1/diseases")
    assert res.status_code == 200
    assert res.json()["total"] >= 12

    res_search = client.get("/api/v1/diseases/search?q=rệp")
    assert res_search.status_code == 200
    assert res_search.json()["total"] > 0

def test_cultivation_endpoints():
    res = client.get("/api/v1/cultivation")
    assert res.status_code == 200

def test_weather_endpoints():
    res = client.get("/api/v1/weather")
    assert res.status_code == 200
    assert len(res.json()) >= 4

def test_auth_and_chat_flow():
    # Register test user
    user_payload = {
        "username": "test_user_api",
        "email": "test_user_api@teascholar.ai",
        "password": "password123",
        "full_name": "Test API User"
    }
    res_reg = client.post("/api/v1/auth/register", json=user_payload)
    if res_reg.status_code != 409:  # If already registered
        assert res_reg.status_code == 201

    # Login
    login_payload = {
        "username_or_email": "test_user_api",
        "password": "password123"
    }
    res_login = client.post("/api/v1/auth/login", json=login_payload)
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]

    # Get /me
    headers = {"Authorization": f"Bearer {token}"}
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["username"] == "test_user_api"

    # Chat session flow
    res_sess = client.post("/api/v1/chat/sessions", json={"title": "Hỏi về bệnh rệp xanh"}, headers=headers)
    assert res_sess.status_code == 201
    sess_id = res_sess.json()["id"]

    # Post user message
    msg_payload = {
        "role": "user",
        "content": "Làm thế nào để trị rệp xanh trên cây chè?"
    }
    res_msg = client.post(f"/api/v1/chat/sessions/{sess_id}/messages", json=msg_payload, headers=headers)
    assert res_msg.status_code == 201

    # Fetch messages
    res_get_msgs = client.get(f"/api/v1/chat/sessions/{sess_id}/messages", headers=headers)
    assert res_get_msgs.status_code == 200
    assert len(res_get_msgs.json()) >= 1

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))


# ============================================================
# KNOWLEDGE KEYWORD SEARCH — nhiều từ, không phân biệt hoa/thường và dấu
# ============================================================
def _search_ids(q: str):
    res = client.get("/api/v1/knowledge/search", params={"q": q, "page_size": 50})
    assert res.status_code == 200
    return [item["chunk_id"] for item in res.json()["items"]]


def test_search_multi_word_query_matches_terms_not_only_exact_phrase():
    # "chè tân cương" không xuất hiện nguyên cụm nhưng các từ đều có trong các đoạn về Tân Cương
    ids = _search_ids("chè tân cương")
    assert {"tea_000048", "tea_000049", "tea_000073"} <= set(ids)


def test_search_ignores_diacritics_and_case():
    assert "tea_000032" in _search_ids("thoi bup")
    assert "tea_000032" in _search_ids("THỐI BÚP")
    assert _search_ids("đốn chè") and _search_ids("đốn chè") == _search_ids("ĐỐN CHÈ")


def test_search_ranks_title_matches_first():
    ids = _search_ids("bệnh thối búp")
    assert ids[0] == "tea_000032"


def test_search_matches_whole_words_only():
    # "tan" không được khớp vào giữa các từ như "tán" khi bỏ dấu; tìm có dấu cho kết quả chính xác
    assert _search_ids("tân cương") == ["tea_000048", "tea_000049", "tea_000073"]


def test_search_no_match_returns_empty_page():
    res = client.get("/api/v1/knowledge/search", params={"q": "xyzkhongtontai"})
    body = res.json()
    assert body["total"] == 0 and body["items"] == [] and body["total_pages"] == 1


# ============================================================
# AUTOCOMPLETE — gợi ý từ khóa khi gõ
# ============================================================
def _suggest(q: str, limit: int = 8):
    res = client.get("/api/v1/knowledge/suggest", params={"q": q, "limit": limit})
    assert res.status_code == 200
    return [s["text"] for s in res.json()["suggestions"]]


def test_suggest_returns_phrases_starting_with_typed_prefix():
    texts = _suggest("c")
    assert texts and all(t.startswith("c") for t in texts)


def test_suggest_prefers_matching_diacritics_then_falls_back_to_unaccented():
    # Gõ có dấu: chỉ khớp đúng dấu trước ("hái" không lẫn "hại")
    hai = _suggest("hái")
    assert hai and all(t.startswith("hái") for t in hai[:3])
    # Gõ không dấu: vẫn tìm được "thối búp", "thời vụ"
    thoi = _suggest("thoi", limit=20)
    assert any(t.startswith("thối") for t in thoi) and any(t.startswith("thời") for t in thoi)


def test_suggest_completes_disease_names():
    assert any("thối búp" in t for t in _suggest("bệnh th"))
    assert any(t.startswith("nhện đỏ") for t in _suggest("nhện"))


def test_suggest_respects_limit_and_has_no_duplicates():
    texts = _suggest("ch", limit=5)
    assert len(texts) <= 5 and len(texts) == len(set(texts))


def test_suggest_empty_or_unknown_prefix_returns_nothing():
    assert _suggest(" ") == []
    assert _suggest("zzzqq") == []


def test_suggest_does_not_return_prefix_only_duplicates():
    texts = _suggest("bón")
    # "bón phân" phổ biến hơn các cụm dài nên xuất hiện; không có cụm bị cắt cụt vô nghĩa nào trùng đầu và ít phổ biến hơn
    assert "bón phân" in texts
