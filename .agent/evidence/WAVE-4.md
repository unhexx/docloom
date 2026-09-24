# Волна 4 — API и worker

Дата: 2026-09-24.

## Команды

```bash
source .venv/bin/activate
pytest -q
```

## Результат

- `14 passed`
- `POST /api/projects` на `samples/demo-lib`, `POST /builds`, `drain`, статус `success_with_warnings` (у `helper` нет docstring), `index.html` в каталоге публикации
- Чистое дерево гайдов заканчивается статусом `success`
- Два билда одной версии не берутся одновременно; другая версия собирается
- Webhook с фикстурой push без GitHub: без подписи 401, с `X-Hub-Signature-256` ставится билд `main`
- `git_url` на локальный репозиторий клонируется и публикуется
- Путь вне allowlist отклоняется

Чекпоинт C4 пройден. Redis не поднимался: очередь в SQLite.
