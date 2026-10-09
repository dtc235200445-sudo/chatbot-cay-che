from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class TeaRegionResponse(BaseModel):
    name: str
    province: str
    latitude: float
    longitude: float
    area_ha: Optional[float] = None
    altitude_m: Optional[float] = None


class WeatherDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    region: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    wind_speed: Optional[float] = None
    weather_condition: Optional[str] = None
    recorded_at: Optional[datetime] = None
    created_at: datetime
