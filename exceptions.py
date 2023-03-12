"""My custom Exceptions."""


class KeyError(Exception):
    """Ошибка получения ожидаемых ключей из ответа API."""


class StatusCodeError(Exception):
    """Ошибка статус кода в ответе API."""


class HomeworksErrors(Exception):
    """Ошибка получения ожидаемых ключей в словаре Домашки."""


class RequestError(Exception):
    """Ошибка получения ответа  от API."""
