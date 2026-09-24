# DESIGN: Docloom

## 1. Ценность

Инженер пушит код и `docloom.yml`. Платформа без участия человека:

1. клонирует ревизию;
2. извлекает справочник из исходников и OpenAPI;
3. собирает GitBook-подобную книгу (гайды + generated);
4. публикует версию и индекс поиска;
5. отдаёт сайт, `llms.txt` и манифест сборки.

Человек пишет только нарратив (tutorials, concepts). Справочник не редактируется руками.

## 2. Принципы

- Источник истины — Git-ревизия, не БД редактора.
- Генерация идемпотентна: один commit SHA → один артефакт.
- Изоляция сборки в контейнере; хост не ставит toolchain проекта.
- Формат книги совместим с GitBook Classic по файлам: `SUMMARY.md`, Markdown-главы, `assets/`.
- Generated-страницы живут в `generated/` и перезаписываются целиком.
- Никакого копирования проприетарного редактора GitBook и никакого форка GPLv3-рендерера `GitbookIO/gitbook` в закрытый продукт.

## 3. Область MVP (волны 1–6)

Входит:

- проект + версии (`latest` + git tag/branch);
- генераторы: Python autodoc (AST + docstrings + type hints), OpenAPI 3 → страницы методов, Markdown-гайды;
- сборка статического сайта с навигацией GitBook-типа;
- клиентский поиск по индексу;
- webhook `/hooks/git` и ручной `POST /api/projects/{id}/builds`;
- очередь билдов, логи, статус;
- `llms.txt` / `llms-full.txt`;
- весь runtime через `docker-compose`.

Не входит в MVP (бэклог v1.1+):

- WYSIWYG и realtime;
- двусторонний Git Sync;
- visual diff PR;
- PDF/EPUB;
- SSO / SAML;
- переводы;
- произвольные билдеры Docusaurus/VitePress (достаточно hook `custom.build` позже);
- облачный multi-tenant.

## 4. Логическая архитектура

```
Git remote / local bind-mount
        │
        ▼
   Control API (FastAPI)
        │  enqueue job
        ▼
   Worker
        │  docker run builder  ИЛИ  in-process generators (dev)
        ▼
   Generators ──► Book IR (pages, nav, assets, search docs)
        │
        ▼
   Publisher ──► /publish/{project}/{version}/
        │
        ▼
   Nginx ──► читатель + /llms.txt
```

Сервисы Compose:

| Сервис | Роль |
| --- | --- |
| `api` | проекты, вебхуки, статус билдов, раздача манифестов |
| `worker` | забирает job, запускает генерацию, пишет артефакт |
| `nginx` | статика опубликованных книг, health reverse-proxy |
| `redis` | очередь + lock на (project, version) |
| volume `sources` | клоны репозиториев |
| volume `publish` | готовый HTML |
| volume `data` | SQLite или Postgres (на старте SQLite) |

Postgres не обязателен в MVP: один файл БД на volume упрощает on-prem.

## 5. Контракт `docloom.yml`

```yaml
project: demo-lib
version: "0.1.0"          # override; иначе имя ветки/тега
language: ru
theme: gitbook
sources:
  guides: docs            # Markdown + SUMMARY.md
  python: [src]
  openapi: [openapi.yaml]
exclude:
  - "**/tests/**"
publish:
  versions_from: [tags, default_branch]
search: true
llms: true
```

`SUMMARY.md` задаёт порядок гайдов. Блок «Справочник API» платформа дописывает сама после генерации и не требует ручного списка каждого символа.

## 6. Автогенерация — главный модуль

Пайплайн одного билда (строго в этом порядке):

1. **Resolve source** — clone/fetch SHA, checkout, записать `source_sha`.
2. **Discover** — найти пакеты Python, spec OpenAPI, дерево `docs/`.
3. **Extract**
   - Python: `ast` + модульный обход; класс/функция/метод; сигнатура, аннотации, docstring, декораторы, `__all__`, публичность по соглашению `_`.
   - OpenAPI: paths × methods, parameters, requestBody, responses, examples, security.
   - Guides: front matter + Markdown.
4. **Normalize** — внутренняя IR-страница:

   ```json
   {
     "id": "python:demo_lib.Client.connect",
     "kind": "python.function",
     "title": "Client.connect",
     "path": "generated/python/demo_lib/Client/connect.md",
     "anchors": ["parameters", "returns"],
     "source": {"file": "src/demo_lib/client.py", "line": 41},
     "text": "..."
   }
   ```

5. **Render Markdown** — стабильные шаблоны Jinja, без LLM в MVP (LLM — отдельный опциональный слой «проза вокруг сигнатуры», выключен по умолчанию).
6. **Weave book** — склеить SUMMARY: Intro из гайдов, затем Generated.
7. **Publish HTML** — тема GitBook-like (сайдбар, crumb, prev/next, search, переключатель версий).
8. **Index** — `search-index.json` (title, headings, body, path).
9. **Manifest** — `build.json`: sha, время, список страниц, ошибки extract (невалидный spec ≠ падение всего билда, а warning + страница Diagnostics).

Требования к генератору:

- не исполнять пользовательский Python (никакого `import` целевого пакета в MVP — только AST). Это снимает зависимость от runtime и атаки на worker.
- предупреждать о символах без docstring (coverage в `build.json`).
- одинаковый вывод на Linux в контейнере и в unit-тестах.

## 7. Читатель (GitBook-like, своя тема)

Не форкать `GitbookIO/gitbook`. Своя статическая тема:

- левая навигация по SUMMARY;
- контент с подсветкой кода;
- правый TOC страницы;
- поиск по индексу (клиентский, без Meilisearch в MVP);
- селектор версии;
- тёмная тема;
- страница 404 проекта.

Этого достаточно, чтобы продукт воспринимался как «локальный GitBook», не таща GPLv3-рендерер.

## 8. API control plane (минимум)

- `GET /health`
- `POST /api/projects` `{name, git_url?, local_path?}`
- `POST /api/projects/{id}/builds` `{ref}`
- `GET /api/projects/{id}/builds/{build_id}`
- `POST /hooks/git` (GitHub-compatible push payload)
- `GET /sites/{project}/{version}/` → nginx
- `GET /sites/{project}/{version}/llms.txt`

Секреты webhook и git credentials только из env / mounted secret, не в образе.

## 9. Модель данных

- `Project(id, name, git_url, local_path, webhook_secret, created_at)`
- `Build(id, project_id, ref, sha, status, started_at, finished_at, log_path, artifact_path, warnings)`
- `Version(project_id, name, build_id, is_default)`

Статусы: `queued | running | success | success_with_warnings | failed`.

## 10. Безопасность on-prem

- builder без privileged и без docker.sock внутри job (на MVP генерация in-process в worker; на v1.1 — sibling container из предсобранного образа `docloom-builder`);
- allowlist путей для `local_path`;
- таймаут билда и лимит размера артефакта;
- никакого исполнения произвольных `build` команд из yaml в MVP (закрывает RCE). `custom.build` появится только за policy-флагом.

## 11. Качество и наблюдаемость

Каждый билд пишет:

- `logs/build.log`
- `publish/.../build.json`
- coverage docstring
- список пропущенных файлов

Smoke после Compose: `/health` = 200, сборка `samples/demo-lib` = HTML с непустым справочником, поиск находит имя функции из демо.

## 12. Как это закрывает пробелы RTD и GitBook

| Пробел | Решение Docloom |
| --- | --- |
| GitBook нельзя честно self-host как платформу | Свой control plane + своя тема |
| RTD не генерирует справочник сам — только запускает чужой tool | Встроенные генераторы Python/OpenAPI как продукт |
| SSG не является платформой версий и очереди | API + worker + publish versions |
| SaaS lock-in и per-site цена | Compose на контуре заказчика |
| Legacy GitBook мёртв | Новый конвейер, старый файловый DX (SUMMARY.md) |
