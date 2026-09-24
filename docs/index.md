# Документация Docloom

[![Версия](https://img.shields.io/github/v/release/unhexx/docloom?style=flat-square&label=release)](https://github.com/unhexx/docloom/releases/tag/v0.1.0)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Лицензия MIT](https://img.shields.io/github/license/unhexx/docloom?style=flat-square)](../LICENSE)
[![Compose](https://img.shields.io/badge/run-docker%20compose-2496ED?style=flat-square&logo=docker&logoColor=white)](../docker-compose.yml)
[![API](https://img.shields.io/badge/API-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](http-api.md)
[![Очередь](https://img.shields.io/badge/queue-SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)](architecture.md)

Docloom собирает сайт документации из Git-ревизии. Гайды пишет человек. Справочник Python и страницы HTTP платформа строит сама и публикует каталог версии. Читатель открывает `/sites/{проект}/{версия}/`.

Сборка одного источника идёт так: прочитать `docloom.yml` или обнаружить `README`, `docs/` и OpenAPI, склеить книгу, записать HTML, `search-index.json`, `llms.txt` и `build.json`. Очередь билдов — SQLite. Снаружи compose слушает порт `8080`.

## Порядок чтения

1. [Архитектура](architecture.md) — кто принимает билд и куда пишет сайт.
2. [Конфигурация](configuration.md) — `docloom.yml`, режим без файла и переменные окружения.
3. [Генерация](generation.md) — AST, OpenAPI, гайды и коды предупреждений.
4. [Публикация](publishing.md) — тема, поиск, манифест.
5. [HTTP API](http-api.md) — проекты, билды, webhook.
6. [Bitbucket](bitbucket.md) — опрос одной ветки без участия людей.
7. [Эксплуатация](operations.md) — стенд, свой репозиторий, разбор сбоев.
8. [Разработка](development.md) — команды, тесты, карта каталогов.

| Документ | О чём |
| --- | --- |
| [Архитектура](architecture.md) | Сервисы, тома, пара проект/версия |
| [Конфигурация](configuration.md) | `docloom.yml` и переменные окружения |
| [Генерация](generation.md) | AST, OpenAPI, гайды, диагностика |
| [Публикация](publishing.md) | HTML, поиск, `llms.txt`, `build.json` |
| [HTTP API](http-api.md) | Проекты, билды, webhook |
| [Bitbucket](bitbucket.md) | Автосборка одного репозитория |
| [Эксплуатация](operations.md) | Compose, свой репозиторий, секреты |
| [Разработка](development.md) | Команды, тесты, карта каталогов |

Исследование рынка и исходный дизайн лежат в корне репозитория: [RESEARCH.md](../RESEARCH.md), [DESIGN.md](../DESIGN.md), [PLAN.md](../PLAN.md). Пример источника — [samples/demo-lib](../samples/demo-lib/docloom.yml). Краткая витрина с теми же бейджами — [README](../README.md).
