# Docloom

[![Версия](https://img.shields.io/github/v/release/unhexx/docloom?style=flat-square&label=release)](https://github.com/unhexx/docloom/releases/tag/v0.1.0)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Лицензия MIT](https://img.shields.io/github/license/unhexx/docloom?style=flat-square)](LICENSE)
[![Compose](https://img.shields.io/badge/run-docker%20compose-2496ED?style=flat-square&logo=docker&logoColor=white)](docker-compose.yml)

Самостоятельная платформа документации: GitBook-подобный читатель и конвейер сборки в духе Read the Docs.

Инженер кладёт в репозиторий код и `docloom.yml`. Docloom забирает ревизию, собирает гайды из Markdown, справочник Python из AST и страницы методов из OpenAPI, публикует версию и отдаёт сайт.

*Documentation that weaves itself from source.*

Человек пишет только нарратив. Справочник перезаписывается при каждой сборке. Пользовательский Python не импортируется. Команды сборки из yaml не запускаются. Репозиторий: [unhexx/docloom](https://github.com/unhexx/docloom).

## Быстрый старт

Нужны Docker и Docker Compose. Снаружи слушает nginx, порт `8080`. API внутри сети compose — `8000`.

```bash
docker compose up -d --build --wait
curl -fsS http://127.0.0.1:8080/health
bash scripts/compose-smoke.sh
```

Демо-книга: [http://127.0.0.1:8080/sites/demo-lib/latest/](http://127.0.0.1:8080/sites/demo-lib/latest/)

Повторный `docker compose up -d --wait` не пересоздаёт контейнеры, пока файлы и образ те же. Тома `data`, `publish` и `sources` хранят базу, сайты и клоны. `docker compose down -v` их удаляет. Остановка без удаления: `docker compose stop`.

Локально, без Docker:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest -q
docloom build --root samples/demo-lib --out /tmp/demo-lib
```

## Документация

| Документ | О чём |
| --- | --- |
| [Обзор](docs/index.md) | Оглавление |
| [Архитектура](docs/architecture.md) | API, worker, nginx, тома |
| [Конфигурация](docs/configuration.md) | `docloom.yml` и окружение |
| [Генерация](docs/generation.md) | AST, OpenAPI, гайды |
| [Публикация](docs/publishing.md) | Тема, поиск, `llms.txt`, манифест |
| [HTTP API](docs/http-api.md) | Проекты, билды, webhook |
| [Bitbucket](docs/bitbucket.md) | Автосборка одного репозитория |
| [Эксплуатация](docs/operations.md) | Свой репозиторий и разбор сбоев |
| [Разработка](docs/development.md) | Карта кода и тесты |

Рядом в корне: `RESEARCH.md` (срез рынка), `DESIGN.md` (контракт продукта), `PLAN.md` (волны MVP), `samples/demo-lib` (витрина).

## Границы 0.1.0

Нет редактора, SSO, PDF и произвольных генераторов. Поиск читает `search-index.json` в браузере. Очередь — SQLite. Битый OpenAPI и пустой `src/` оставляют книгу со статусом `success_with_warnings`. Тема своя, рендерер GitBook не входит в поставку.
