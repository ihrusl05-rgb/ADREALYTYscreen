# adRealytyWidget v2.0

Бэкенд-сервис «виджета погоды»: отдаёт JSON с прогнозом погоды и курсом валют для внешних экранов/виджетов.

## Возможности

- Прогноз на 7 дней и почасовой на 24 часа (бесплатный API Open-Meteo)
- Курс EUR/USD (ЦБ РФ)
- Русские названия погоды и иконки для каждого состояния
- Кэширование ответов на 1 час (не дёргает внешние API при каждом запросе)
- Статическая раздача иконок `/weather-icons/*.png`

## Запуск

Требуется [uv](https://docs.astral.sh/uv/) и Python 3.11+.

```bash
uv sync        # установить зависимости (один раз)
uv run uvicorn app.main:app --port 7500
```

Сервер запустится на порту 7500.

## API

### `GET /`

Проверка работы сервиса.

```json
{ "status": "ok", "message": "Weather API" }
```

### `GET /{city}`

Погода для города (код из `regions.json`): прогноз на неделю, по часам и курс валют.

```json
{
  "result": {
    "dataWeatherWeek": [
      {
        "time": "10:09",
        "date": "среда, 19 августа",
        "week": "СР",
        "day": 19,
        "weather_code": { "label": "Туман", "icon": "http://host/weather-icons/45-fog.png" },
        "temperature_2m_max": 23,
        "temperature_2m_min": 14,
        "apparent_temperature_max": 23,
        "apparent_temperature_min": 15,
        "apparent_temperature_mean": 19
      }
    ],
    "dataWeatherDay": [
      {
        "time": "10:00",
        "temperature_2m": 16,
        "weather_code": { "label": "Пасмурно", "icon": "http://host/weather-icons/3-overcast.png" },
        "precipitation_probability": 40,
        "date": "19.08.2026"
      }
    ],
    "exchangeRate": {
      "eur": { "name": "Евро", "value": 98 },
      "usd": { "name": "Доллар США", "value": 85 }
    }
  }
}
```

Ответы кэшируются на 1 час (ключ `DATA:{city}`).

Ошибки:

| Код | Ситуация |
|---|---|
| `502` | Город не найден в `regions.json` или недоступен внешний API (в теле — частичные данные) |
| `204` | Запрос `/favicon.ico` |

## Поддерживаемые города

Задаются в `regions.json` (код, координаты, часовой пояс). Сейчас: `ufa`, `nn`, `msk`, `oren`, `kazan`, `str`, `putilkovo`, `odintsovo`, `lyubertsy`.

## Структура

```
app/
├── main.py                # FastAPI: роуты, кэш, статика
├── weather_codes.py       # коды погоды → название и иконка
└── services/
    ├── weather_week.py    # прогноз на 7 дней (Open-Meteo)
    ├── weather_hour.py    # почасовой прогноз (Open-Meteo)
    └── exchange_rate.py   # курс EUR/USD (ЦБ РФ)
public/weather-icons/      # PNG-иконки погоды
regions.json               # справочник городов
```

## Полезное

- Отладочные логи: `uv run uvicorn app.main:app --reload --port 7500`
- Проверка: `curl http://localhost:7500/ufa`