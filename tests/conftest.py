import pytest
from fastapi.testclient import TestClient

from app.main import app, weather_cache

@pytest.fixture(autouse=True)
def clean_cache():
    """Между тестами — чистый кэш, чтобы один тест не «подкармливал» другой."""
    weather_cache.clear()
    yield
    weather_cache.clear()


@pytest.fixture
def client():
    """Готовый HTTP-клиент к нашему приложению без запуска реального сервера."""
    return TestClient(app)
