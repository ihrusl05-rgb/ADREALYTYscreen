def test_root(client):
    """Главная страница жива: отдаёт 200 и приветствие — значит, сервер вообще поднялся."""
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "message": "Weather API"}


def test_favicon(client):
    """Браузер сам лезет за favicon — молча отвечаем 204, не тащим его в погоду."""
    assert client.get("/favicon.ico").status_code == 204


def test_unknown_city_returns_502(client, monkeypatch):
    """Неизвестный город — вежливый отказ: 502 и честное «такого города у нас нет».

    Курс валют мокаем, чтобы тест не ходил в интернет: сами погодные сервисы
    вернут пустые списки и без сети.
    """
    async def fake_rate():
        return {}

    monkeypatch.setattr("app.main.get_exchange_rate", fake_rate)
    r = client.get("/london")
    assert r.status_code == 502
    data = r.json()
    assert data["error"] == "Weather API city not found"
    assert "exchangeRate" in data["result"]


def test_city_response_structure(client, monkeypatch):
    """Договор с виджетом: всегда три блока, 7 дней, 24 часа и иконки с адресом.

    Данные подменяем заглушками — здесь мы проверяем не погоду,
    а форму ответа: не потеряет ли сервер блоки и количество записей.
    """
    async def fake_week(*a, **k):
        return [
            {"weather_code": {"label": "Ясно", "icon": "http://testserver/weather-icons/0-clear.png"}}
        ] * 7

    async def fake_hour(*a, **k):
        return [{"time": "10:00"}] * 24

    async def fake_rate():
        return {"eur": {"name": "Евро", "value": 98}}

    monkeypatch.setattr("app.main.get_weather_week", fake_week)
    monkeypatch.setattr("app.main.get_weather_hour", fake_hour)
    monkeypatch.setattr("app.main.get_exchange_rate", fake_rate)

    r = client.get("/ufa")
    assert r.status_code == 200
    result = r.json()["result"]
    assert set(result) == {"dataWeatherWeek", "dataWeatherDay", "exchangeRate"}
    assert len(result["dataWeatherWeek"]) == 7
    assert len(result["dataWeatherDay"]) == 24
    assert "weather-icons" in r.text


def test_cache_used_on_second_request(client, monkeypatch):
    """Кэш работает: второй запрос того же города не лезет в «интернет».

    Считаем вызовы подменённого сервиса: если их один (а не два),
    значит второй ответ пришёл из кэша, как задумано.
    """
    calls = {"n": 0}

    async def fake_week(*a, **k):
        calls["n"] += 1
        return [{"day": 1}]

    async def fake_hour(*a, **k):
        return [{"time": "10:00"}]

    async def fake_rate():
        return {}

    monkeypatch.setattr("app.main.get_weather_week", fake_week)
    monkeypatch.setattr("app.main.get_weather_hour", fake_hour)
    monkeypatch.setattr("app.main.get_exchange_rate", fake_rate)

    client.get("/msk")
    client.get("/msk")
    assert calls["n"] == 1  # второй запрос — из кэша


def test_static_icons(client):
    """Иконки погоды доходят до клиента: по адресу лежит настоящая PNG-картинка."""
    r = client.get("/weather-icons/0-clear.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"