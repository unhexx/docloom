# Волна 1 — Python autodoc

Дата: 2026-09-24.

## Команды

```bash
source .venv/bin/activate
pytest -q tests/test_smoke_imports.py tests/test_python_ast.py
```

## Результат

- `6 passed`
- `ProjectConfig.load` читает `samples/demo-lib/docloom.yml`
- Повторный `extract_python` даёт тот же Markdown
- Есть страница класса `Client` и метод `Client.connect` с сигнатурой и ссылкой на `src/demo_lib/client.py`
- `helper` без docstring попадает в warnings, `_hidden` не попадает в справочник
- Пакет `demo_lib` не импортируется
- Синтаксическая ошибка в исходнике — warning, не исключение

Чекпоинт C1 пройден. HTML, API и очередь не делались.
