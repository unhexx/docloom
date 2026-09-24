"""Дымовая проверка: пакет импортируется без сети и Docker."""

import docloom


def test_version_is_set() -> None:
    assert docloom.__version__ == "0.1.0"
