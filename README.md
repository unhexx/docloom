# Docloom

Самостоятельная платформа документации: GitBook-подобный читатель + конвейер автоматической генерации в духе Read the Docs.

Сборка идёт по `PLAN.md` и `.agent/WORKFLOW.yaml`. Каркас пакета лежит в `src/docloom/`, витрина автогенерации — в `samples/demo-lib`. Контур разработки подключает соседний `agentic_loop_template` (симлинк, не копия) и сжимает контекст через pxpipe.

- Продуктовое имя: **Docloom**
- Слоган: *Documentation that weaves itself from source*
- Репозиторий (целевой): `unhexx/docloom`
- Конфиг проекта-источника: `docloom.yml`

## Документы

| Файл | Назначение |
| --- | --- |
| `RESEARCH.md` | Сравнение Read the Docs и локального GitBook, пробелы рынка |
| `DESIGN.md` | Целевая архитектура, контракты, приоритет автогенерации |
| `PLAN.md` | Пошаговый план для локальных агентов (INVEST, чекпоинты, Definition of Done) |
| `.agent/WORKFLOW.yaml` | Детерминированный workflow с resume |

## Чего ещё нет

Генераторов, HTTP API и `docker-compose.yml` — волны 1–6 плана. Пустой пакет и демо-дерево сами по себе книгой не являются.
