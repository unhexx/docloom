# Разработка

Python 3.11 и новее. Пакет живёт в `src/docloom`, версия в `src/docloom/__init__.py`, ставится editable. Точка входа: `docloom = docloom.cli:main`.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest -q
docloom build --root samples/demo-lib --out /tmp/demo-lib
```

`--root` может быть относительным: перед чтением файлов путь приводится к абсолютному. Команда печатает каталог публикации и возвращает 0.

Тесты в образе, с тем же `git`, что у runtime:

```bash
docker compose --profile test run --rm --build test
make test
make compose-up
make compose-smoke
```

Команда внутри образа: `pytest -q -p no:cacheprovider`. Кэш pytest в каталог приложения не пишется: пользователь образа не владеет исходниками.

## Команды

| Команда | Что делает |
| --- | --- |
| `docloom build --root PATH --out PATH [--version NAME]` | Собрать книгу в каталог, минуя очередь. SHA в манифесте — отпечаток дерева |
| `docloom serve [--host H] [--port N]` | HTTP API. Хост и порт по умолчанию из окружения |
| `docloom worker` | Крутить очередь, пока процесс жив. Пишет `worker-heartbeat` в каталог данных |
| `docloom watch [--url URL] [--ref REF] [--once]` | Опросить одну ветку. Без `--once` спит `DOCLOOM_WATCH_INTERVAL` и пишет heartbeat |

`--url` и `--ref` перекрывают `DOCLOOM_WATCH_URL` и `DOCLOOM_WATCH_REF` на этот запуск.

## Карта кода

| Путь | Ответственность |
| --- | --- |
| `config.py` | Разбор `docloom.yml` и обнаружение книги без файла |
| `generators/python_ast.py` | Справочник из AST |
| `generators/openapi.py` | Страницы операций |
| `generators/guides.py` | Гайды и `SUMMARY.md` |
| `book.py` | Склейка книги, README и статус |
| `textfmt.py` | `md_label`: экранирование `_` и `*` в заголовках |
| `publisher/html.py` | HTML, индекс, llms, манифест, префикс ассетов от пути файла |
| `publisher/templates/` | Вёрстка, стили, поиск |
| `hooks.py` | GitHub и Bitbucket → постановка билда |
| `watch.py` | Опрос одного репозитория |
| `api.py` | HTTP |
| `db.py` | SQLite, очередь, запрет второго `running` на ту же версию, SHA только у успеха |
| `jobs.py` | Один билд от источника до каталога |
| `worker.py` | Цикл очереди |
| `source.py` | Allowlist, отпечаток, checkout, выгрузка файлов Bitbucket |
| `settings.py` | Переменные окружения |
| `cli.py` | `build`, `serve`, `worker`, `watch` |

Шаблоны попадают в колесо через `package-data` в `pyproject.toml`.

## Проверки

| Файл | Что держит |
| --- | --- |
| `tests/test_smoke_imports.py` | пакет импортируется |
| `tests/test_python_ast.py` | повторный Markdown, класс `Client`, `__init__`, без импорта пакета |
| `tests/test_weave.py` | порядок разделов и битый OpenAPI |
| `tests/test_publisher.py` | главная ссылается на символ, префикс `assets/` у index, индекс не пуст |
| `tests/test_api_build.py` | очередь, демо-книга, webhook, локальный git |
| `tests/test_regression.py` | пустой `src/` вместе с битой спецификацией |
| `tests/test_bitbucket.py` | разбор `/scm/`, webhook Server, опрос локального git, книга без `docloom.yml` |
| `tests/test_docs.py` | бейджи README и относительные ссылки документации ведут на файлы |

Новая страница справочника должна быть стабильной между двумя прогонами на одном дереве. Новый маршрут API покрывается через `TestClient`, без сети. Относительная ссылка в `docs/` или README должна указывать на существующий файл: это проверяет `tests/test_docs.py`.

## Образ

`Dockerfile` имеет цель `runtime` (то, что запускают api, worker и watch) и цель `test`. В runtime ставятся `git` и `curl`. Зависимости приложения — из `pyproject.toml`, без фиксации вторичного лока в репозитории: версии снизу ограничены, верх не запирается, кроме того, что требует интерпретатор `>=3.11`.

Рендерер GitBook в образ не копируется. Исполнение пользовательского кода в worker не добавляется. Произвольный `build` из yaml остаётся за пределами этой версии.

Секреты, `.env` и тома `data` / `publish` / `sources` в коммит не входят.
