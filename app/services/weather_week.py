from datetime import datetime
import logging
from zoneinfo import ZoneInfo

from app.services.errors import UpstreamBadResponseError
from app.services.utils import FORECAST_URL, ICONS, fetch_json, find_city

logger = logging.getLogger(__name__)

WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

WEEKDAYS_SHORT = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]

MONTHS_GENITIVE = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


async def get_weather_week(city: str) -> list:
    """Получить и преобразовать прогноз Open-Meteo на 7 дней."""
    current_city = find_city(city)
    if not current_city:
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
        data = await fetch_json(FORECAST_URL, params, "Open-Meteo")
    except Exception:
        raise

    try:
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
                "weather_code": ICONS.get(fields["weather_code"][index]),
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
