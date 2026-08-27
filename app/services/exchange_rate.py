import logging
import math

from app.services.utils import fetch_json

URL = "https://www.cbr-xml-daily.ru/daily_json.js"

logger = logging.getLogger(__name__)


async def get_exchange_rate() -> dict:
    """Курсы евро и доллара на сегодня — берём с официального сайта ЦБ РФ.

    ЦБ отдаёт JSON с кучей валют, а виджету нужны только две самые популярные,
    поэтому забираем EUR и USD, округляем до целых рублей. Сбой ЦБ не должен ронять весь сервис —
    тогда вернём пустой словарь, и виджет просто покажет без курсов.
    """
    try:
        data = await fetch_json(URL, {}, "ЦБ РФ")
    except Exception as error:
        logger.warning("ЦБ РФ недоступен: %s", error)
        return {}

    try:
        return {
            "eur": {
                "name": data["Valute"]["EUR"]["Name"],
                "value": math.floor(float(data["Valute"]["EUR"]["Value"])),
            },
            "usd": {
                "name": data["Valute"]["USD"]["Name"],
                "value": math.floor(float(data["Valute"]["USD"]["Value"])),
            },
        }
    except (KeyError, TypeError, ValueError) as error:
        logger.warning("Некорректный ответ ЦБ РФ: %s", error)
        return {}
