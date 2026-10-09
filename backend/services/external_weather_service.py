import logging
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import HTTPException, status
import httpx
from backend.config import settings

logger = logging.getLogger("tea_scholar.external_weather_service")

# WMO Weather Interpretation Codes (WW) mapping to Vietnamese descriptions
WMO_WEATHER_CODES: Dict[int, str] = {
    0: "Trời quang",
    1: "Ít mây",
    2: "Mây rải rác",
    3: "Nhiều mây",
    45: "Sương mù",
    48: "Sương mù đóng băng",
    51: "Mưa phun nhẹ",
    53: "Mưa phun vừa",
    55: "Mưa phun nặng hạt",
    56: "Mưa phun lạnh giá nhẹ",
    57: "Mưa phun lạnh giá nặng",
    61: "Mưa nhẹ",
    63: "Mưa vừa",
    65: "Mưa to",
    66: "Mưa rào lạnh giá",
    67: "Mưa rào lạnh nặng hạt",
    71: "Tuyết nhẹ",
    73: "Tuyết vừa",
    75: "Tuyết dày",
    77: "Hạt tuyết",
    80: "Mưa rào nhẹ",
    81: "Mưa rào vừa",
    82: "Mưa rào rất to",
    85: "Mưa rào tuyết nhẹ",
    86: "Mưa rào tuyết nặng",
    95: "Dông mưa nhẹ",
    96: "Dông kèm mưa đá nhỏ",
    99: "Dông kèm mưa đá lớn"
}

def map_wmo_code_to_condition(code: int) -> str:
    return WMO_WEATHER_CODES.get(code, f"Thời tiết bình thường (Code {code})")

async def fetch_open_meteo_current_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Fetch live weather data from Open-Meteo API for given coordinates.
    Parameters requested: temperature_2m, relative_humidity_2m, rain, wind_speed_10m, weather_code.
    """
    if not settings.WEATHER_BASE_URL:
        logger.error("[ExternalWeatherService] WEATHER_BASE_URL is unconfigured!")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weather service base URL is unconfigured."
        )

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,rain,wind_speed_10m,weather_code",
        "wind_speed_unit": "ms"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.WEATHER_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

    except httpx.TimeoutException as err:
        logger.error(f"[ExternalWeatherService] Timeout fetching weather: {err}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Weather provider request timed out."
        )
    except httpx.HTTPStatusError as err:
        logger.error(f"[ExternalWeatherService] Provider HTTP Error {err.response.status_code}: {err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather provider returned HTTP error {err.response.status_code}"
        )
    except httpx.RequestError as err:
        logger.error(f"[ExternalWeatherService] Request Error: {err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to weather provider: {str(err)}"
        )
    except Exception as err:
        logger.error(f"[ExternalWeatherService] Unexpected error: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected weather service error: {str(err)}"
        )

    # Validate Response Payload
    if not isinstance(data, dict) or "current" not in data:
        logger.error(f"[ExternalWeatherService] Malformed JSON response: {data}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Weather provider returned malformed JSON response."
        )

    current_data = data["current"]
    try:
        temp = float(current_data["temperature_2m"])
        humidity = float(current_data["relative_humidity_2m"])
        rainfall = float(current_data.get("rain", 0.0))
        wind_speed = float(current_data.get("wind_speed_10m", 0.0))
        weather_code = int(current_data.get("weather_code", 0))
    except (KeyError, ValueError, TypeError) as err:
        logger.error(f"[ExternalWeatherService] Failed to parse current weather variables: {err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather provider response missing required variables: {err}"
        )

    weather_condition = map_wmo_code_to_condition(weather_code)

    return {
        "temperature": round(temp, 1),
        "humidity": round(humidity, 1),
        "rainfall": round(rainfall, 1),
        "wind_speed": round(wind_speed, 1),
        "weather_condition": weather_condition,
        "recorded_at": datetime.now(timezone.utc)
    }
