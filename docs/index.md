# Документация Docloom

Docloom собирает сайт документации из Git-ревизии: гайды пишет человек, справочник Python и страницы HTTP платформа строит сама.

| Документ | О чём |
| --- | --- |
| [Архитектура](architecture.md) | Сервисы, тома, порядок сборки |
| [Конфигурация](configuration.md) | `docloom.yml` и переменные окружения |
| [Генерация](generation.md) | AST, OpenAPI, гайды, диагностика |
| [Публикация](publishing.md) | HTML, поиск, `llms.txt`, `build.json` |
| [HTTP API](http-api.md) | Проекты, билды, webhook |
| [Bitbucket](bitbucket.md) | Автосборка одного репозитория без участия людей |
| [Эксплуатация](operations.md) | Compose, свой репозиторий, секреты |
| [Разработка](development.md) | Команды, тесты, карта каталогов |

Исследование рынка и исходный дизайн лежат в корне репозитория: `RESEARCH.md`, `DESIGN.md`, `PLAN.md`. Пример источника — `samples/demo-lib`.
