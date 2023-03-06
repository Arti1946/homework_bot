"""My custom Exceptions."""


class KeyError(Exception):
    """Ошибка получения ожидаемых ключей из ответа API."""

    pass


class StatusCodeError(Exception):
    """Ошибка статус кода в ответе API."""

    pass


class HomeworksErrors(Exception):
    """Ошибка получения ожидаемых ключей в словаре Домашки."""

    pass
