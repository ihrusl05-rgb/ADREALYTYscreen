import json
import math

import httpx

URL = "https://www.cbr-xml-daily.ru/daily_json.js"
TIMEOUT = 10.0


async def get_exchange_rate() -> dict:
    """Курсы евро и доллара на сегодня — берём с официального сайта ЦБ РФ.

    ЦБ отдаёт JSON с кучей валют, а виджету нужны только две самые популярные,
    поэтому забираем EUR и USD, округляем до целых рублей (лишняя копеечная
    точность экрану не нужна). Сбой ЦБ не должен ронять весь сервис —
    тогда вернём пустой словарь, и виджет просто покажет без курсов.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(URL)

        if response.status_code != 200:
            print(f"Error ошибка API {response.status_code} - {response.reason_phrase}")
            return {}

        data = json.loads(response.content.decode("utf-8-sig"))
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

    except Exception as error:
        print(f"Ошибка API cbr-xml-daily {type(error).__name__}: {error}")
        return {}