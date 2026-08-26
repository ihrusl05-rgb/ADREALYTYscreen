import logging
import asyncio

from cachetools import TTLCache
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles


from app.services.exchange_rate import get_exchange_rate
from app.services.errors import (
    UpstreamBadResponseError,
    UpstreamUnavailableError,
)
from app.services.utils import find_city
from app.services.weather_hour import get_weather_hour
from app.services.weather_week import get_weather_week


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

logger = logging.getLogger(__name__)

app = FastAPI(title="Weather API", docs_url=None, redoc_url=None)
"""Точка входа виджета: единственный API, который будет видеть внешний мир."""

app.mount("/weather-icons", StaticFiles(directory="public/weather-icons"), name="weather-icons")

weather_cache = TTLCache(maxsize=100, ttl=60 * 60)
"""Память на час: повторные запросы не долбят внешние сервисы, пока данные не устарели."""


@app.get("/")
def root():
    """Приветствие для ручной проверки: жив ли сервис и отвечает ли вообще."""
    return {"status": "ok", "message": "Weather API"}


@app.get("/{city}")
async def weather(city: str):
    """Главный метод: по названию города отдаём неделю, сутки и курсы валют.

    Сначала смотрим в кэш — если город уже просили в последний час, отдаём
    сохранённое. Иначе тянем всё параллельно из трёх источников, кладём в кэш
    и возвращаем. Неизвестный город получает 404, временная недоступность
    внешнего сервиса — 503, а некорректный ответ — 502."""
    change_city = city.strip().lower()

    if change_city == "favicon.ico":
        return Response(status_code=204)

    if not find_city(change_city):
        raise HTTPException(
            status_code=404,
            detail=f"Город '{change_city}' не поддерживается", )

    cache_key = f"DATA:{change_city}"
    if cache_key not in weather_cache:
        logger.debug("Данные получены с API")
        try:
            data_weather_week, data_weather_day, exchange_rate = await asyncio.gather(
                get_weather_week(change_city),
                get_weather_hour(change_city),
                get_exchange_rate(),
            )
        except UpstreamUnavailableError as error:
            logger.exception("Внешний сервис временно недоступен")
            raise HTTPException(
                status_code=503,
                detail="Сервис погоды временно недоступен",
            ) from error
        except UpstreamBadResponseError as error:
            logger.exception("Внешний сервис вернул некорректные данные")
            raise HTTPException(
                status_code=502,
                detail="Сервис погоды вернул некорректные данные",
            ) from error

        if not data_weather_week or not data_weather_day:
            return JSONResponse(status_code=502, content={
                    "error": "No data from weather service",
                    "result": {
                        "dataWeatherWeek": data_weather_week,
                        "dataWeatherDay": data_weather_day,
                        "exchangeRate": exchange_rate,},
                },
            )

        weather_cache[cache_key] = {
            "dataWeatherWeek": data_weather_week,
            "dataWeatherDay": data_weather_day,
            "exchangeRate": exchange_rate,
        }
    else:
        logger.debug("Данные из кэша")

    return {"result": weather_cache[cache_key]}
