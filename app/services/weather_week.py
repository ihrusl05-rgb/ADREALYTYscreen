from datetime import datetime
import logging
from zoneinfo import ZoneInfo

import httpx

from app.services.errors import UpstreamBadResponseError, UpstreamUnavailableError
from app.services.utils import find_city, icon_map

logger = logging.getLogger(__name__)

WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
"""Полные русские названия дней — чтобы виджет показывал «Среда», а не номер 2."""

WEEKDAYS_SHORT = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
"""Короткие метки для компактных карточек на экране."""

MONTHS_GENITIVE = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 10.0


async def get_weather_week(city: str) -> list:
    """Получить и преобразовать прогноз Open-Meteo на 7 дней."""
    current_city = find_city(city)
    if not current_city:
        # Обычно город проверяется в main.py до вызова сервиса.
        return []

    params = {
        "latitude": current_city["lat"],
        "longitude": current_city["lon"],
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,apparent_temperature_mean",
        "timezone": current_city["timezone"],
        "forecast_days": "7",
        "current": "weather_code,is_day",
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
        daily = data["daily"]
        dates = daily["time"]
        fields = {
            name: daily[name]
            for name in (
                "weather_code", "temperature_2m_max", "temperature_2m_min",
                "apparent_temperature_max", "apparent_temperature_min",
                "apparent_temperature_mean",
            )
        }
        if not all(len(values) == len(dates) for values in fields.values()):
            raise ValueError("массивы daily имеют разную длину")

        icons = icon_map()
        current_time = datetime.now(ZoneInfo(current_city["timezone"])).strftime("%H:%M")
        result = []
        for index, day in enumerate(dates):
            date = datetime.strptime(day, "%Y-%m-%d").date()
            weekday_full = WEEKDAYS[date.weekday()]
            result.append({
                "time": current_time,
                "date": f"{weekday_full[0].lower()}{weekday_full[1:]}, {date.day} {MONTHS_GENITIVE[date.month - 1]}",
                "week": WEEKDAYS_SHORT[date.weekday()],
                "day": date.day,
                "weather_code": icons.get(fields["weather_code"][index]),
                "temperature_2m_max": int(fields["temperature_2m_max"][index]),
                "temperature_2m_min": int(fields["temperature_2m_min"][index]),
                "apparent_temperature_max": int(fields["apparent_temperature_max"][index]),
                "apparent_temperature_min": int(fields["apparent_temperature_min"][index]),
                "apparent_temperature_mean": int(fields["apparent_temperature_mean"][index]),
            })
        return result
    except (ValueError, TypeError, KeyError, IndexError) as error:
        logger.exception("Некорректный ответ Open-Meteo для %s", city)
        raise UpstreamBadResponseError("Open-Meteo вернул данные в неожиданном формате") from error
