from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.dependencies.db import get_db
from backend.schemas.weather import TeaRegionResponse, WeatherDataResponse
from backend.services.regions import list_regions
from backend.services.weather_service import (
    get_weather_data_list,
    get_weather_data_by_id,
    fetch_and_sync_live_weather
)

router = APIRouter(prefix="/api/v1/weather", tags=["Agricultural Weather"])

@router.get("", response_model=List[WeatherDataResponse], summary="List Weather Records from Database")
def list_weather_data(
    region: Optional[str] = Query(None, description="Filter by region name (e.g. Phú Thọ, Thái Nguyên, Lâm Đồng)"),
    db: Session = Depends(get_db)
):
    return get_weather_data_list(db, region=region)

@router.get("/regions", response_model=List[TeaRegionResponse], summary="List Tea-growing Regions Supported for Weather Queries")
def list_tea_regions():
    """Danh mục vùng chè (data/tea_regions.json) mà API thời tiết và trợ lý hỗ trợ."""
    return [
        TeaRegionResponse(
            name=r.name, province=r.province, latitude=r.latitude, longitude=r.longitude,
            area_ha=r.area_ha, altitude_m=r.altitude_m,
        )
        for r in list_regions()
    ]


@router.get("/live", response_model=WeatherDataResponse, summary="Fetch Live Weather Data from Open-Meteo Provider")
async def get_live_weather(
    region: str = Query(..., description="Tea-growing region name (e.g. Thái Nguyên, Phú Thọ, Lâm Đồng, Mộc Châu)"),
    db: Session = Depends(get_db)
):
    """
    Fetch current live weather from Open-Meteo, normalize data, save/update in database and return.
    """
    return await fetch_and_sync_live_weather(db=db, region=region)

@router.get("/{weather_id}", response_model=WeatherDataResponse, summary="Get Weather Detail by ID")
def get_weather_detail(weather_id: int, db: Session = Depends(get_db)):
    weather = get_weather_data_by_id(db, weather_id=weather_id)
    if not weather:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Weather record with ID {weather_id} not found")
    return weather
