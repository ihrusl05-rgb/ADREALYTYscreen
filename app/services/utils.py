import json
from pathlib import Path

from app.weather_codes import WEATHER_CODES

REGIONS = json.loads(Path(__file__).resolve().parents[2].joinpath("regions.json").read_text(encoding="utf-8"))["data"]
"""Наш справочник городов: кто живёт в проекте, с координатами и часовым поясом."""

def find_city(city: str) -> dict | None:
    """Ищем город в regions; не нашли — вернём None"""
    for item in REGIONS:
        if item["city"] == city:
            return item
    return None


def icon_map() -> dict:
    """Собираем словарь «код погоды → картинка» """
    return {
        int(code): data.copy()
        for code, data in WEATHER_CODES.items()
    }
