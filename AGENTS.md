# AGENTS.md — Docloom

Инструкции для разработки в этом репозитории.

## Цель

On-prem платформа документации: из `docloom.yml`, Markdown-гайдов, Python AST и OpenAPI 3 собирается статическая книга в духе GitBook. Источник истины по продукту — `DESIGN.md`. Порядок работ — `PLAN.md` и `.agent/TODO.md`.

## Текущий статус

Волны 0–6 плана. Пока не закрыт чекпоинт, следующую волну не начинать.

## Стек

- Python 3.11+, пакет в `src/docloom/`
- FastAPI, SQLite, Jinja2, Markdown, Pygments
- Тесты: pytest
- С волны 5: Docker Compose (api, worker, nginx)

## Команды

```bash
bash Agent-Init.sh
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Compose — только с волны 5:

```bash
docker compose up -d --build
curl -fsS http://localhost:8080/health
```

## Прокси контекста

Живые запросы к модели идут через шлюз Agentix `http://127.0.0.1:8110/v1`, перед ним host pxpipe `http://127.0.0.1:8100`. Переменные прописывает `python -m memory.proxy install-venv` в `.venv/bin/activate`. Отключение: `AGENTIX_PROXY=0`. В процесс Docloom pxpipe не входит: это только контур разработки.

## Definition of Done

- Тесты на изменённое поведение, прежний набор зелёный
- Повторная генерация Markdown на том же дереве байт-в-байт
- Секреты не коммитить (`.env`, `.env.agentic`)
- Коммиты на русском, языком разработчика
- В конце спринта: merge `--no-ff` в `main` и `git push origin main`

## Нельзя

- Форкать рендерер `GitbookIO/gitbook`
- Импортировать или исполнять Python собираемого проекта
- Выполнять произвольные команды сборки из `docloom.yml`
- Копировать дерево `agentic_loop_template` внутрь репозитория (только симлинк на SSOT)
- Писать в коммитах, что работу сделала нейросеть
