import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from app.weather_codes import WEATHER_CODES
from app.services.utils import find_city, icon_map

REGIONS = json.loads(
    Path(__file__).resolve().parents[2].joinpath("regions.json").read_text(encoding="utf-8")
)["data"]
"""Наш справочник городов: кто живёт в проекте, с координатами и часовым поясом."""

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


async def get_weather_week(city: str, base_url: str) -> list:
    """Прогноз на неделю: запрашиваем Open-Meteo и делаем из «сырых» данных понятный вид.

    Результат — список из 7 дней, где вместо сухих кодов уже русские названия
    («среда, 19 августа»), готовые ссылки на иконки и округлённые температуры.
    Если города нет в справочнике или API не ответил — возвращаем пустой список: пусть вызывающий код решает, как поступить.
    """
    try:
        find_current_city = find_city(city)
        if not find_current_city:
            print("Параметр города на найден в списке город на получение данных о погоде на неделю")
            return []

        params = {
            "latitude": find_current_city["lat"],
            "longitude": find_current_city["lon"],
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,apparent_temperature_mean",
            "timezone": find_current_city["timezone"],
            "forecast_days": "7",
            "current": "weather_code,is_day",
        }

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(FORECAST_URL, params=params)

        if response.status_code != 200:
            print(f"Open-Meteo HTTP error: {response.status_code}")
            return []

        data = response.json()
        icons = icon_map(base_url)
        current_time = datetime.now(ZoneInfo(find_current_city["timezone"])).strftime("%H:%M")

        new_data = []
        for index, day in enumerate(data["daily"]["time"]):
            date = datetime.strptime(day, "%Y-%m-%d").date()
            weekday_short = WEEKDAYS_SHORT[date.weekday()]
            weekday_full = WEEKDAYS[date.weekday()]
            item = {
                "time": current_time,
                "date": f"{weekday_full[0].lower()}{weekday_full[1:]}, {date.day} {MONTHS_GENITIVE[date.month - 1]}",
                "week": weekday_short,
                "day": date.day,
                "weather_code": icons.get(data["daily"]["weather_code"][index]),
                "temperature_2m_max": int(data["daily"]["temperature_2m_max"][index]),
                "temperature_2m_min": int(data["daily"]["temperature_2m_min"][index]),
                "apparent_temperature_max": int(data["daily"]["apparent_temperature_max"][index]),
                "apparent_temperature_min": int(data["daily"]["apparent_temperature_min"][index]),
                "apparent_temperature_mean": int(data["daily"]["apparent_temperature_mean"][index]),
            }
            new_data.append(item)

        return new_data

    except Exception as error:
        print(f"Ошибка API open-meteo {getattr(error, 'name', type(error).__name__)}: {error}")
        return []