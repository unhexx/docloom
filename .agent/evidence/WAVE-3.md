# Волна 3 — издатель

Дата: 2026-09-24.

## Команды

```bash
source .venv/bin/activate
pytest -q
```

## Результат

- `9 passed`
- `index.html` демо содержит имя проекта и ссылку на страницу класса `Client`
- Подсветка кода через Pygments, своя тема (светлая и тёмная), поиск по `search-index.json`
- Пишутся `llms.txt`, `llms-full.txt`, `build.json`, `404.html`
- Покрытие docstring в манифесте видит символ без описания

Чекпоинт C3 пройден. Meilisearch и PDF не подключались.
