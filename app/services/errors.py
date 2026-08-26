class UpstreamUnavailableError(Exception):
    """Внешний сервис временно недоступен (сеть, timeout, 429 или 5xx)."""


class UpstreamBadResponseError(Exception):
    """Внешний сервис ответил, но прислал неожиданные/некорректные данные."""
