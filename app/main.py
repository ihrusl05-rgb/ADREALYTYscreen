from cachetools import TTLCache
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import asyncio

from app.services.exchange_rate import get_exchange_rate
from app.services.weather_hour import get_weather_hour
from app.services.weather_week import get_weather_week

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
async def weather(city: str, request: Request):
    """Главный метод: по названию города отдаём неделю, сутки и курсы валют.

    Сначала смотрим в кэш — если город уже просили в последний час, отдаём
    сохранённое. Иначе тянем всё параллельно из трёх источников, кладём в кэш
    и возвращаем. Если города мы не знаем или внешние API молчат — честно
    говорим об этом кодом 502 и отдаём то, что удалось собрать.
    """
    change_city = city.strip().lower()

    if change_city == "favicon.ico":
        return Response(status_code=204)

    base_url = f"{request.url.scheme}://{request.headers.get('host')}"

    cache_key = f"DATA:{change_city}"
    if cache_key not in weather_cache:
        print("Данные получены с API")
        data_weather_week, data_weather_day, exchange_rate = await asyncio.gather(
            get_weather_week(change_city, base_url),
            get_weather_hour(change_city, base_url),
            get_exchange_rate(),)

        if not data_weather_week or not data_weather_day:
            return JSONResponse(
                status_code=502,
                content={
                    "error": "Weather API city not found",
                    "result": {
                        "dataWeatherWeek": data_weather_week,
                        "dataWeatherDay": data_weather_day,
                        "exchangeRate": exchange_rate,
                    },
                },
            )

        weather_cache[cache_key] = {
            "dataWeatherWeek": data_weather_week,
            "dataWeatherDay": data_weather_day,
            "exchangeRate": exchange_rate,
        }
    else:
        print("Данные из кэша")

    return {"result": weather_cache[cache_key]}