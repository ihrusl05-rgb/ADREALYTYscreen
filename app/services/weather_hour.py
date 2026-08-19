import json
from datetime import datetime
from pathlib import Path

import httpx

from app.weather_codes import WEATHER_CODES

REGIONS = json.loads(
    Path(__file__).resolve().parents[2].joinpath("regions.json").read_text(encoding="utf-8")
)["data"]

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 10.0


def _find_city(city: str) -> dict | None:
    """Ищем город в нашем справочнике; вернём None, если такого не держим."""
    for item in REGIONS:
        if item["city"] == city:
            return item
    return None


def _icon_map(base_url: str) -> dict:
    """Код погоды → картинка с полным адресом сервера (та же шпаргалка, что у недели)."""
    return {
        int(code): {**data, "icon": f"{base_url}{data['icon']}"}
        for code, data in WEATHER_CODES.items()
    }


async def get_weather_hour(city: str, base_url: str) -> list:
    """Почасовой прогноз на ближайшие сутки: температура, погода и шанс дождя.

    Как и неделя, запрашивается у Open-Meteo, только с почасовой разбивкой.
    На выходе 24 записи вида «09:00, +15°, Пасмурно, 40% осадков» — удобно
    для ленты прогноза на экране. Если город неизвестен или API сбоит —
    возвращаем пустой список вместо исключения.
    """
    try:
        find_current_city = _find_city(city)
        if not find_current_city:
            print("Параметр города на найден в списке город на получение данных о погоде на день")
            return []

        params = {
            "latitude": find_current_city["lat"],
            "longitude": find_current_city["lon"],
            "hourly": "temperature_2m,weather_code,precipitation_probability",
            "forecast_hours": "24",
            "timezone": find_current_city["timezone"],
        }

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(FORECAST_URL, params=params)

        if response.status_code != 200:
            print(f"Error ошибка API {response.status_code} - {response.reason_phrase}")
            return []

        data = response.json()
        icons = _icon_map(base_url)

        new_data = []
        for index, item in enumerate(data["hourly"]["time"]):
            hour_weather_code = data["hourly"]["weather_code"][index]
            new_data.append(
                {
                    "time": datetime.strptime(item, "%Y-%m-%dT%H:%M").strftime("%H:%M"),
                    "temperature_2m": int(data["hourly"]["temperature_2m"][index]),
                    "weather_code": icons.get(hour_weather_code),
                    "precipitation_probability": data["hourly"]["precipitation_probability"][index],
                    "date": datetime.strptime(item, "%Y-%m-%dT%H:%M").strftime("%d.%m.%Y"),
                }
            )

        return new_data

    except Exception as error:
        print(f"Ошибка API open-meteo {getattr(error, 'name', type(error).__name__)}: {error}")
        return []