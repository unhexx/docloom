# TODO

Источник объёма: `PLAN.md`. Один открытый спринт за раз.

## Спринт 0 — контур

- [x] C0: pyproject, venv, `samples/demo-lib`, `pytest -q` на импорте
- [x] Agentix: симлинк на SSOT, шлюз `:8110` → pxpipe `:8100`
- [x] Evidence: `.agent/evidence/WAVE-0.md`

## Спринт 1 — Python autodoc

- [x] C1: `ProjectConfig`, IR, обход AST, Markdown символа
- [x] Повторный прогон байт-в-байт, страница класса `Client`, предупреждение без docstring

## Спринт 2 — книга

- [x] C2: OpenAPI 3, гайды, склейка SUMMARY
- [x] Битый spec → `success_with_warnings` и страница Diagnostics

## Спринт 3 — издатель

- [x] C3: HTML-тема, поиск, `llms.txt`, `llms-full.txt`, `build.json`

## Спринт 4 — control plane

- [x] C4: SQLite, API, worker, логи, публикация `samples/demo-lib`
- [x] Параллельные билды одной пары (проект, версия) сериализуются

## Спринт 5 — compose

- [x] C5: Dockerfile, nginx, healthcheck, smoke `/sites/demo-lib/latest/`

## Спринт 6 — релиз

- [ ] C6: регрессия, webhook-фикстура, README
- [ ] Релиз `v0.1.0` на GitHub
