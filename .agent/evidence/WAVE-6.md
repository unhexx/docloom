# Волна 6 — регрессия и выпуск

Дата: 2026-09-24.

## Команды и коды

| Команда | Код |
| --- | --- |
| `pytest -q` на хосте | 0, `15 passed` |
| `docker compose --profile test run --rm --build test` | 0, `15 passed` |
| `docker compose up -d --build --wait` | 0, сервисы healthy |
| `curl -fsS http://127.0.0.1:8080/health` | 0 |
| `curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/sites/demo-lib/latest/` | 200 |

## Что закрыто

- Пустой `src/` и битый OpenAPI: `tests/test_regression.py`, статус `success_with_warnings`, страница диагностики
- Webhook: фикстура push в `tests/test_api_build.py`, без живого GitHub
- README: быстрый старт compose, подключение своего репозитория, ограничения MVP

## Не вошло в 0.1.0

Редактор, PDF, SSO, произвольные команды сборки, поиск отдельной службой, Postgres, превью различий.
