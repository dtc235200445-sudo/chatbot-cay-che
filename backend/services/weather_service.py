from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from database.models import WeatherData
from backend.services.external_weather_service import fetch_open_meteo_current_weather
from backend.services.regions import resolve_coordinates

def get_weather_data_list(db: Session, region: Optional[str] = None) -> List[WeatherData]:
    query = db.query(WeatherData)
    if region:
        query = query.filter(WeatherData.region.ilike(f"%{region}%"))
    return query.order_by(WeatherData.id.asc()).all()

def get_weather_data_by_id(db: Session, weather_id: int) -> Optional[WeatherData]:
    return db.query(WeatherData).filter_by(id=weather_id).first()

async def fetch_and_sync_live_weather(db: Session, region: Optional[str]) -> WeatherData:
    """
    Fetch live weather data for given region from Open-Meteo, normalize and upsert into SQLite DB.
    """
    if not region or not region.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Region parameter is required for live weather query"
        )

    clean_region = region.strip()

    # 1. Tọa độ lấy từ danh mục vùng chè (data/tea_regions.json) trước, để việc sửa tọa độ trong danh mục
    #    có hiệu lực ngay; chỉ dùng tọa độ đã lưu trong DB cho vùng không có trong danh mục.
    existing_record = db.query(WeatherData).filter(WeatherData.region.ilike(clean_region)).first()
    lat, lon = None, None

    coordinates = resolve_coordinates(clean_region)
    if coordinates:
        lat, lon = coordinates
    elif existing_record and existing_record.latitude and existing_record.longitude:
        lat = existing_record.latitude
        lon = existing_record.longitude

    if lat is None or lon is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region '{clean_region}' does not have coordinate information for weather queries"
        )

    # 2. Fetch live data from Open-Meteo Provider
    live_data = await fetch_open_meteo_current_weather(latitude=lat, longitude=lon)

    # 3. Database Upsert (Update existing or Create new)
    if existing_record:
        existing_record.latitude = lat
        existing_record.longitude = lon
        existing_record.temperature = live_data["temperature"]
        existing_record.humidity = live_data["humidity"]
        existing_record.rainfall = live_data["rainfall"]
        existing_record.wind_speed = live_data["wind_speed"]
        existing_record.weather_condition = live_data["weather_condition"]
        existing_record.recorded_at = live_data["recorded_at"]
        weather_obj = existing_record
    else:
        weather_obj = WeatherData(
            region=clean_region,
            latitude=lat,
            longitude=lon,
            temperature=live_data["temperature"],
            humidity=live_data["humidity"],
            rainfall=live_data["rainfall"],
            wind_speed=live_data["wind_speed"],
            weather_condition=live_data["weather_condition"],
            recorded_at=live_data["recorded_at"]
        )
        db.add(weather_obj)

    db.commit()
    db.refresh(weather_obj)
    return weather_obj
