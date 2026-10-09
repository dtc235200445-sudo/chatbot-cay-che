import json
import unittest.mock as mock

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.regions import REGIONS_FILE, TEA_REGIONS, find_region_in_text, list_regions, resolve_coordinates
from database.connection import SessionLocal, engine
from database.models import Base, WeatherData

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_regions_file_is_well_formed():
    raw = json.loads(REGIONS_FILE.read_text(encoding="utf-8"))
    names = [r["name"] for r in raw["regions"]]
    assert len(names) == len(set(names)) == 12
    for r in raw["regions"]:
        assert -90 <= r["latitude"] <= 90 and -180 <= r["longitude"] <= 180
        assert r["province"] and r["is_tea_region"] is True
        # Việt Nam nằm khoảng 8–24°B, 102–110°Đ: bắt lỗi nhập nhầm tọa độ
        assert 8 <= r["latitude"] <= 24 and 102 <= r["longitude"] <= 110, r["name"]


def test_loaded_regions_match_file():
    assert len(TEA_REGIONS) == 12
    assert "thái nguyên" in TEA_REGIONS and TEA_REGIONS["mộc châu"].province == "Sơn La"
    assert len(list_regions()) == 12


def test_son_la_and_moc_chau_have_distinct_coordinates():
    """Cấu hình cũ dùng tọa độ Mộc Châu cho Sơn La; hai vùng phải khác nhau."""
    assert resolve_coordinates("Sơn La") != resolve_coordinates("Mộc Châu")


def test_find_region_and_resolve():
    assert find_region_in_text("Thời tiết Đà Lạt hôm nay") == "Đà Lạt"
    assert resolve_coordinates("không tồn tại 999") is None


def test_regions_endpoint():
    res = client.get("/api/v1/weather/regions")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 12
    assert {"name", "province", "latitude", "longitude"} <= body[0].keys()
    assert "Thái Nguyên" in [r["name"] for r in body]


@mock.patch("backend.services.weather_service.fetch_open_meteo_current_weather")
def test_catalog_coordinates_override_stale_db_record(mock_fetch):
    """Tọa độ trong danh mục vùng chè phải được dùng thay cho tọa độ cũ đã lưu trong DB."""
    mock_fetch.return_value = {
        "temperature": 25.0, "humidity": 80.0, "rainfall": 0.0, "wind_speed": 1.0,
        "weather_condition": "Ít mây", "recorded_at": None,
    }
    db = SessionLocal()
    try:
        db.query(WeatherData).filter(WeatherData.region == "Sơn La").delete()
        db.add(WeatherData(region="Sơn La", latitude=20.8437, longitude=104.6366))  # tọa độ cũ sai
        db.commit()
    finally:
        db.close()

    res = client.get("/api/v1/weather/live", params={"region": "Sơn La"})
    assert res.status_code == 200
    _, kwargs = mock_fetch.call_args
    lat, lon = resolve_coordinates("Sơn La")
    assert (kwargs["latitude"], kwargs["longitude"]) == (lat, lon)
