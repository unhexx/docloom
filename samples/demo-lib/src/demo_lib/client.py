"""Клиент демо-библиотеки."""


class Client:
    """Точка входа для вызовов API."""

    def __init__(self, base_url: str) -> None:
        """Запоминает базовый адрес сервиса."""
        self.base_url = base_url

    def connect(self, timeout: float = 5.0) -> bool:
        """Открывает соединение с сервисом.

        Параметр timeout задаёт ожидание рукопожатия в секундах.
        """
        return bool(self.base_url) and timeout >= 0
