# TASK_SPECIFICATION.md — Docloom

**Проект:** Docloom
**Целевая версия:** 0.1.0
**Цель:** самодостаточная платформа документации, которая из Git-ревизии и `docloom.yml` собирает GitBook-подобную книгу и публикует её через Docker Compose.

## Задачи продукта

- Справочник Python из AST, без импорта пользовательского кода
- Страницы операций из OpenAPI 3 и гайды из Markdown
- Статический сайт: навигация, поиск, `llms.txt`, манифест `build.json`
- HTTP API, очередь билдов, worker, webhook push
- Первый публичный релиз `v0.1.0`

## В объёме

Волны 0–6 из `PLAN.md`. Образец — `samples/demo-lib`.

## Вне объёма

WYSIWYG, Git Sync в обе стороны, PDF, SSO, произвольные команды сборки, Meilisearch, форк GitBook.

## Критерий готовности

- Пункты `.agent/TODO.md` закрыты, `pytest -q` зелёный
- `docker compose` поднимает api, worker и nginx, `/health` отвечает, демо-книга открывается
- На GitHub опубликован релиз `v0.1.0`
