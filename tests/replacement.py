"""Заглушки вместо реального интернета: поддельный ответ и поддельный HTTP-клиент.

Тесты не должны ходить в open-meteo и ЦБ РФ, поэтому здесь живут объекты,
которые выглядят как настоящий httpx, но возвращают заранее заготовленные данные.
"""


class FakeResponse:
    """Прикидывается ответом сервера: статус, текст статуса и готовый JSON."""

    def __init__(self, payload, status_code = 200, content = None):
        self.payload = payload
        self.status_code = status_code
        self.content = content if content is not None else b""

    def json(self):
        return self.payload
    
class FakeClient:
    """Прикидывается HTTP-клиентом httpx: внутри держит один готовый ответ."""

    def __init__(self, payload, status_code = 200, content = None):
        self.response = FakeResponse(payload, status_code, content)    

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        return self.response