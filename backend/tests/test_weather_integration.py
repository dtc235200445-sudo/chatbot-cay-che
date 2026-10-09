import pytest
import unittest.mock as mock
import httpx
from fastapi.testclient import TestClient
from backend.main import app
from database.connection import engine
from database.models import Base, WeatherData

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

MOCK_OPEN_METEO_RESPONSE = {
    "latitude": 21.59,
    "longitude": 105.84,
    "current": {
        "time": "2026-09-16T17:00",
        "interval": 900,
        "temperature_2m": 26.5,
        "relative_humidity_2m": 82.0,
        "rain": 0.0,
        "weather_code": 1,
        "wind_speed_10m": 3.2
    }
}

# ============================================================
# TEST 1 — LIVE WEATHER SUCCESS
# ============================================================
@mock.patch("backend.services.external_weather_service.httpx.AsyncClient")
def test_1_live_weather_success(mock_async_client_cls):
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_OPEN_METEO_RESPONSE
    mock_response.raise_for_status = mock.MagicMock()
    mock_client.get = mock.AsyncMock(return_value=mock_response)
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client

    response = client.get("/api/v1/weather/live?region=Thái Nguyên")
    assert response.status_code == 200
    data = response.json()
    assert data["region"] == "Thái Nguyên"
    assert data["temperature"] == 26.5
    assert data["humidity"] == 82.0
    assert data["rainfall"] == 0.0
    assert data["wind_speed"] == 3.2
    assert data["weather_condition"] == "Ít mây"

# ============================================================
# TEST 2 — REGION FILTER CURRENT WEATHER
# ============================================================
@mock.patch("backend.services.external_weather_service.httpx.AsyncClient")
def test_2_region_filter(mock_async_client_cls):
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_OPEN_METEO_RESPONSE
    mock_response.raise_for_status = mock.MagicMock()
    mock_client.get = mock.AsyncMock(return_value=mock_response)
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client

    response = client.get("/api/v1/weather/live?region=Phú Thọ")
    assert response.status_code == 200
    data = response.json()
    assert data["region"] == "Phú Thọ"

# ============================================================
# TEST 3 — PROVIDER TIMEOUT -> 504
# ============================================================
@mock.patch("backend.services.external_weather_service.httpx.AsyncClient")
def test_3_provider_timeout(mock_async_client_cls):
    mock_client = mock.MagicMock()
    mock_client.get = mock.AsyncMock(side_effect=httpx.TimeoutException("Connection timed out"))
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client

    response = client.get("/api/v1/weather/live?region=Thái Nguyên")
    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()

# ============================================================
# TEST 4 — PROVIDER HTTP ERROR -> 502
# ============================================================
@mock.patch("backend.services.external_weather_service.httpx.AsyncClient")
def test_4_provider_http_error(mock_async_client_cls):
    mock_client = mock.MagicMock()
    req = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
    resp = httpx.Response(500, request=req)
    mock_client.get = mock.AsyncMock(side_effect=httpx.HTTPStatusError("Server Error", request=req, response=resp))
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client

    response = client.get("/api/v1/weather/live?region=Thái Nguyên")
    assert response.status_code == 502
    assert "500" in response.json()["detail"]

# ============================================================
# TEST 5 — MALFORMED RESPONSE -> 502
# ============================================================
@mock.patch("backend.services.external_weather_service.httpx.AsyncClient")
def test_5_malformed_response(mock_async_client_cls):
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"invalid": "payload"}
    mock_response.raise_for_status = mock.MagicMock()
    mock_client.get = mock.AsyncMock(return_value=mock_response)
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client

    response = client.get("/api/v1/weather/live?region=Thái Nguyên")
    assert response.status_code == 502
    assert "malformed" in response.json()["detail"].lower()

# ============================================================
# TEST 6 — UNKNOWN REGION -> 404
# ============================================================
def test_6_unknown_region():
    response = client.get("/api/v1/weather/live?region=ThànhPhốKhôngTồnTại123")
    assert response.status_code == 404
    assert "coordinate" in response.json()["detail"].lower()

# ============================================================
# TEST 7 — NORMALIZED FIELDS CORRECTNESS
# ============================================================
@mock.patch("backend.services.external_weather_service.httpx.AsyncClient")
def test_7_normalized_fields(mock_async_client_cls):
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.status_code = 200
    custom_resp = {
        "current": {
            "temperature_2m": 31.4,
            "relative_humidity_2m": 90.5,
            "rain": 12.5,
            "weather_code": 63, # Mưa vừa
            "wind_speed_10m": 4.5
        }
    }
    mock_response.json.return_value = custom_resp
    mock_response.raise_for_status = mock.MagicMock()
    mock_client.get = mock.AsyncMock(return_value=mock_response)
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client

    response = client.get("/api/v1/weather/live?region=Lâm Đồng")
    assert response.status_code == 200
    data = response.json()
    assert data["temperature"] == 31.4
    assert data["humidity"] == 90.5
    assert data["rainfall"] == 12.5
    assert data["wind_speed"] == 4.5
    assert data["weather_condition"] == "Mưa vừa"

# ============================================================
# TEST 8 — WEATHER DATA SAVED / UPDATED IN DB
# ============================================================
@mock.patch("backend.services.external_weather_service.httpx.AsyncClient")
def test_8_db_upsert(mock_async_client_cls):
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_OPEN_METEO_RESPONSE
    mock_response.raise_for_status = mock.MagicMock()
    mock_client.get = mock.AsyncMock(return_value=mock_response)
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client

    # First Live query -> Inserts or Updates
    res1 = client.get("/api/v1/weather/live?region=Mộc Châu")
    assert res1.status_code == 200
    db_id1 = res1.json()["id"]

    # Second Live query -> Updates same record ID
    res2 = client.get("/api/v1/weather/live?region=Mộc Châu")
    assert res2.status_code == 200
    db_id2 = res2.json()["id"]
    assert db_id1 == db_id2

# ============================================================
# TEST 9 — EXISTING GET /api/v1/weather WORKS
# ============================================================
def test_9_existing_list_weather():
    response = client.get("/api/v1/weather")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# ============================================================
# TEST 10 — EXISTING GET /api/v1/weather/{weather_id} WORKS
# ============================================================
def test_10_existing_get_weather_by_id():
    response = client.get("/api/v1/weather/1")
    assert response.status_code in (200, 404)
