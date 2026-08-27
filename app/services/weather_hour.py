from datetime import datetime
import logging

from app.services.errors import UpstreamBadResponseError
from app.services.utils import fetch_json, find_city, icon_map

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

logger = logging.getLogger(__name__)


async def get_weather_hour(city: str) -> list:
    """Получить и преобразовать почасовой прогноз на ближайшие 24 часа."""
    current_city = find_city(city)
    if not current_city:
        return []

    params = {
        "latitude": current_city["lat"],
        "longitude": current_city["lon"],
        "hourly": "temperature_2m,weather_code,precipitation_probability",
        "forecast_hours": "24",
        "timezone": current_city["timezone"],
    }

    try:
        data = await fetch_json(FORECAST_URL, params, "Open-Meteo")
    except Exception:
        raise

    try:
        hourly = data["hourly"]
        times = hourly["time"]
        temperatures = hourly["temperature_2m"]
        weather_codes = hourly["weather_code"]
        precipitation = hourly["precipitation_probability"]
        if not all(len(values) == len(times) for values in (
            temperatures, weather_codes, precipitation
        )):
            raise ValueError("массивы hourly имеют разную длину")

        icons = icon_map()
        return [
            {
                "time": datetime.strptime(item, "%Y-%m-%dT%H:%M").strftime("%H:%M"),
                "temperature_2m": int(temperatures[index]),
                "weather_code": icons.get(weather_codes[index]),
                "precipitation_probability": precipitation[index],
                "date": datetime.strptime(item, "%Y-%m-%dT%H:%M").strftime("%d.%m.%Y"),
            }
            for index, item in enumerate(times)
        ]
    except (ValueError, TypeError, KeyError, IndexError) as error:
        logger.exception("Некорректный ответ Open-Meteo для %s", city)
        raise UpstreamBadResponseError(
            "Open-Meteo вернул данные в неожиданном формате"
        ) from error
