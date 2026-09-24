# Разработка

Python 3.11 и новее. Пакет живёт в `src/docloom` и ставится editable.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest -q
docloom build --root samples/demo-lib --out /tmp/demo-lib
```

`--root` может быть относительным: перед чтением файлов путь приводится к абсолютному.

Тесты в образе, с тем же `git`, что у runtime:

```bash
docker compose --profile test run --rm --build test
```

Команда внутри образа: `pytest -q -p no:cacheprovider`. Кэш pytest в каталог приложения не пишется: пользователь образа не владеет исходниками.

## Карта кода

| Путь | Ответственность |
| --- | --- |
| `config.py` | Разбор `docloom.yml` |
| `generators/python_ast.py` | Справочник из AST |
| `generators/openapi.py` | Страницы операций |
| `generators/guides.py` | Гайды и `SUMMARY.md` |
| `book.py` | Склейка книги и статус |
| `publisher/html.py` | HTML, индекс, llms, манифест |
| `publisher/templates/` | Вёрстка, стили, поиск |
| `hooks.py` | GitHub и Bitbucket → постановка билда |
| `watch.py` | Опрос одного репозитория |
| `api.py` | HTTP |
| `db.py` | SQLite, очередь, запрет второго `running` на ту же версию |
| `jobs.py` | Один билд от источника до каталога |
| `worker.py` | Цикл очереди |
| `source.py` | Allowlist, отпечаток, checkout |
| `cli.py` | `build`, `serve`, `worker` |

Шаблоны попадают в колесо через `package-data` в `pyproject.toml`.

## Проверки, которые уже есть

| Файл | Что держит |
| --- | --- |
| `tests/test_python_ast.py` | Повторный Markdown, класс `Client`, `__init__`, без импорта пакета |
| `tests/test_weave.py` | Порядок разделов и битый OpenAPI |
| `tests/test_publisher.py` | Главная ссылается на символ, префикс `assets/` у index, индекс не пуст |
| `tests/test_api_build.py` | Очередь, демо-книга, webhook, локальный git |
| `tests/test_regression.py` | Пустой `src/` вместе с битой спецификацией |
| `tests/test_docs.py` | Ссылки из оглавления документации ведут на существующие файлы |

Новая страница справочника должна быть стабильной между двумя прогонами на одном дереве. Новый маршрут API покрывается через `TestClient`, без сети.

## Образ

`Dockerfile` имеет цель `runtime` (то, что запускают api и worker) и цель `test`. В runtime ставятся `git` и `curl`. Зависимости приложения — из `pyproject.toml`, без фиксации вторичного лока в репозитории: версии снизу ограничены, верх не запирается, кроме того, что требует интерпретатор `>=3.11`.

Не копировать рендерер GitBook и не добавлять исполнение пользовательского кода в worker. Произвольный `build` из yaml остаётся за пределами этой версии.
