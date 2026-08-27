import json
import logging
from pathlib import Path

import httpx

from app.services.errors import UpstreamBadResponseError, UpstreamUnavailableError
from app.weather_codes import WEATHER_CODES

logger = logging.getLogger(__name__)

REGIONS = json.loads(Path(__file__).resolve().parents[2].joinpath("regions.json").read_text(encoding="utf-8"))["data"]

TIMEOUT = 10.0
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

ICONS = {
    int(code): data.copy()
    for code, data in WEATHER_CODES.items()
}


def find_city(city: str) -> dict | None:
    for item in REGIONS:
        if item["city"] == city:
            return item
    return None


async def fetch_json(url: str, params: dict, service_name: str = "сервис") -> dict:
    """Делает GET-запрос и возвращает JSON.

    Сетевые ошибки и таймауты → UpstreamUnavailableError.
    HTTP 429/5xx → UpstreamUnavailableError.
    Другие не-200 → UpstreamBadResponseError.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url, params=params)
    except (httpx.TimeoutException, httpx.NetworkError) as error:
        logger.warning("%s недоступен: %s", service_name, error)
        raise UpstreamUnavailableError(f"{service_name} недоступен") from error
    except httpx.RequestError as error:
        logger.warning("Ошибка запроса к %s: %s", service_name, error)
        raise UpstreamUnavailableError(f"{service_name} недоступен") from error

    if response.status_code == 429 or response.status_code >= 500:
        logger.warning("%s временно недоступен: HTTP %s", service_name, response.status_code)
        raise UpstreamUnavailableError(f"{service_name} временно недоступен")
    if response.status_code != 200:
        logger.error("%s вернул неожиданный HTTP %s", service_name, response.status_code)
        raise UpstreamBadResponseError(f"{service_name} вернул HTTP {response.status_code}")

    return response.json()
