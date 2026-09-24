# Docloom

[![Версия](https://img.shields.io/github/v/release/unhexx/docloom?style=flat-square&label=release)](https://github.com/unhexx/docloom/releases/tag/v0.1.0)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Лицензия MIT](https://img.shields.io/github/license/unhexx/docloom?style=flat-square)](LICENSE)
[![Compose](https://img.shields.io/badge/run-docker%20compose-2496ED?style=flat-square&logo=docker&logoColor=white)](docker-compose.yml)
[![API](https://img.shields.io/badge/API-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](docs/http-api.md)
[![Очередь](https://img.shields.io/badge/queue-SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)](docs/architecture.md)

Самостоятельная платформа документации: GitBook-подобный читатель и конвейер сборки в духе Read the Docs. Версия 0.1.0, Python 3.11 и новее, лицензия MIT.

Инженер кладёт в репозиторий код и, по желанию, `docloom.yml`. Docloom забирает ревизию, собирает гайды из Markdown, справочник Python из AST и страницы методов из OpenAPI, публикует версию и отдаёт сайт.

*Documentation that weaves itself from source.*

Человек пишет нарратив. Справочник перезаписывается при каждой сборке. Python проекта разбирается через `ast`, пакет не импортируется. Команды сборки из yaml не запускаются. Репозиторий: [unhexx/docloom](https://github.com/unhexx/docloom).

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

Команды CLI: `build`, `serve`, `worker`, `watch`. Подробности — в [разработке](docs/development.md).

## Автосборка одного репозитория

Сервис `watch` сам опрашивает одну ветку. Новый коммит ставит билд в очередь, worker публикует сайт. Кнопку нажимать не нужно. Если сервер Git — Bitbucket по адресу `/scm/ПРОЕКТ/репозиторий.git` и задан HTTP-токен, Docloom забирает файлы книги через REST, а не полным `git clone`.

Адрес, ветка, интервал и токен лежат в `.env`. Образец — [`.env.example`](.env.example). Разбор опроса, webhook и смены репозитория — в [Bitbucket](docs/bitbucket.md).

## Что попадает в книгу

| Источник | Страницы |
| --- | --- |
| `README.md` | первая страница, если файл есть |
| `docs/**/*.md` и `SUMMARY.md` | руководства, порядок задаёт summary |
| `src/**/*.py` | модули, классы, функции и методы из AST |
| `openapi.yaml` или `openapi.yml` | по странице на операцию OpenAPI 3 |

Файл `docloom.yml` сужает или расширяет этот набор. Без него Docloom смотрит каталоги `docs/` и `src/` и спецификацию в корне. Пустой docstring и битая спецификация оставляют книгу со статусом `success_with_warnings`.

## Документация

| Документ | О чём |
| --- | --- |
| [Обзор](docs/index.md) | Оглавление и порядок чтения |
| [Архитектура](docs/architecture.md) | API, worker, watch, nginx, тома |
| [Конфигурация](docs/configuration.md) | `docloom.yml`, обнаружение файлов, окружение |
| [Генерация](docs/generation.md) | AST, OpenAPI, гайды, коды предупреждений |
| [Публикация](docs/publishing.md) | Тема, поиск, `llms.txt`, манифест |
| [HTTP API](docs/http-api.md) | Проекты, билды, webhook |
| [Bitbucket](docs/bitbucket.md) | Автосборка одного репозитория |
| [Эксплуатация](docs/operations.md) | Свой репозиторий и разбор сбоев |
| [Разработка](docs/development.md) | Карта кода, CLI и тесты |

Рядом в корне: `RESEARCH.md` (срез рынка), `DESIGN.md` (контракт продукта), `PLAN.md` (волны MVP), `samples/demo-lib` (витрина).

## Границы 0.1.0

В поставке одна встроенная тема, очередь SQLite и поиск по `search-index.json` в браузере. Редактора, SSO, PDF и произвольных генераторов нет. Тема своя, рендерер GitBook в поставку не входит.
