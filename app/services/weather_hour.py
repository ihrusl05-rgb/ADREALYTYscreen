from datetime import datetime
import logging

from app.services.errors import UpstreamBadResponseError
from app.services.utils import FORECAST_URL, ICONS, fetch_json, find_city

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

        result = []
        for index, item in enumerate(times):
            dt = datetime.strptime(item, "%Y-%m-%dT%H:%M")
            result.append({
                "time": dt.strftime("%H:%M"),
                "temperature_2m": int(temperatures[index]),
                "weather_code": ICONS.get(weather_codes[index]),
                "precipitation_probability": precipitation[index],
                "date": dt.strftime("%d.%m.%Y"),
            })
        return result
    except (ValueError, TypeError, KeyError, IndexError) as error:
        logger.exception("Некорректный ответ Open-Meteo для %s", city)
        raise UpstreamBadResponseError(
            "Open-Meteo вернул данные в неожиданном формате"
        ) from error
