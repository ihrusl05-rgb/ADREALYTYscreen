from datetime import datetime
import logging

import httpx

from app.services.errors import UpstreamBadResponseError, UpstreamUnavailableError
from app.services.utils import find_city, icon_map

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 10.0

logger = logging.getLogger(__name__)


async def get_weather_hour(city: str) -> list:
    """Получить и преобразовать почасовой прогноз на ближайшие 24 часа."""
    current_city = find_city(city)
    if not current_city:
        # Обычно город проверяется в main.py до вызова сервиса.
        return []

    params = {
        "latitude": current_city["lat"],
        "longitude": current_city["lon"],
        "hourly": "temperature_2m,weather_code,precipitation_probability",
        "forecast_hours": "24",
        "timezone": current_city["timezone"],
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(FORECAST_URL, params=params)
    except (httpx.TimeoutException, httpx.NetworkError) as error:
        logger.warning("Open-Meteo недоступен для %s: %s", city, error)
        raise UpstreamUnavailableError("Open-Meteo недоступен") from error
    except httpx.RequestError as error:
        logger.warning("Ошибка запроса Open-Meteo для %s: %s", city, error)
        raise UpstreamUnavailableError("Open-Meteo недоступен") from error

    if response.status_code == 429 or response.status_code >= 500:
        logger.warning("Open-Meteo временно недоступен: HTTP %s", response.status_code)
        raise UpstreamUnavailableError("Open-Meteo временно недоступен")
    if response.status_code != 200:
        logger.error("Open-Meteo вернул неожиданный HTTP %s", response.status_code)
        raise UpstreamBadResponseError(
            f"Open-Meteo вернул HTTP {response.status_code}"
        )

    try:
        data = response.json()
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
