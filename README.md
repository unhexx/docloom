# Docloom

Самостоятельная платформа документации: GitBook-подобный читатель и конвейер сборки в духе Read the Docs.

Инженер кладёт в репозиторий код и `docloom.yml`. Docloom забирает ревизию, собирает гайды из Markdown, справочник Python из AST и страницы методов из OpenAPI, публикует версию и отдаёт сайт.

- Продуктовое имя: **Docloom**
- Слоган: *Documentation that weaves itself from source*
- Репозиторий: `unhexx/docloom`
- Конфиг проекта-источника: `docloom.yml`

Человек пишет только нарратив. Справочник перезаписывается целиком при каждой сборке. Пользовательский Python не импортируется и не исполняется. Команды сборки из yaml не запускаются.

## Быстрый старт

Нужны Docker и Docker Compose. Порты: nginx `8080`, API внутри сети compose `8000`.

```bash
docker compose up -d --build --wait
curl -fsS http://127.0.0.1:8080/health
bash scripts/compose-smoke.sh
```

Демо-книга: [http://127.0.0.1:8080/sites/demo-lib/latest/](http://127.0.0.1:8080/sites/demo-lib/latest/)

Повторный `docker compose up -d --wait` ничего не пересоздаёт, пока файлы и образ те же. Каталоги данных — тома `data`, `publish`, `sources`. Не удаляйте их командой `down -v`, пока явно не решили стереть сборки.

Остановка без удаления томов: `docker compose stop`.

## Как подключить свой репозиторий

Рядом с кодом лежит `docloom.yml`:

```yaml
project: demo-lib
version: "0.1.0"
language: ru
theme: gitbook
sources:
  guides: docs
  python: [src]
  openapi: [openapi.yaml]
exclude:
  - "**/tests/**"
publish:
  versions_from: [tags, default_branch]
search: true
llms: true
```

`SUMMARY.md` задаёт порядок гайдов. Блок справочника платформа дописывает сама.

Локальный каталог должен лежать внутри `DOCLOOM_SOURCE_ROOTS` (в compose это `/opt/docloom/samples` и `/sources`).

```bash
curl -fsS -X POST http://127.0.0.1:8080/api/projects \
  -H 'content-type: application/json' \
  -d '{"name":"demo-lib","local_path":"/opt/docloom/samples/demo-lib"}'

curl -fsS -X POST http://127.0.0.1:8080/api/projects/1/builds \
  -H 'content-type: application/json' \
  -d '{"ref":"latest"}'
```

Для Git укажите `git_url` вместо `local_path`. Имя версии — ветка или тег (`main`, `v0.1.0`). `refs/heads/main` из push-события превращается в версию `main`.

Webhook `POST /hooks/git` принимает payload push в формате GitHub. Если задан `DOCLOOM_WEBHOOK_SECRET`, нужен заголовок `X-Hub-Signature-256`. Секрет не пишется в репозиторий: его место в окружении, см. `.env.example`.

Сайт версии: `/sites/{проект}/{версия}/`. Рядом лежат `llms.txt`, `llms-full.txt`, `search-index.json` и `build.json`.

## Локально без Docker

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest -q
docloom build --root samples/demo-lib --out /tmp/demo-lib
```

Тесты в образе: `docker compose --profile test run --rm test`.

## Ограничения MVP

- Нет редактора, совместного курсора и двустороннего Git Sync.
- Нет PDF, EPUB, SSO и переводов.
- Нет произвольных генераторов (Docusaurus, VitePress, Sphinx) и команд `custom.build`.
- Поиск клиентский, по файлу индекса, без отдельной поисковой службы.
- Очередь билдов — SQLite на томе `data`, не Redis.
- Битый OpenAPI и пустой `src/` не роняют книгу: статус `success_with_warnings` и страница диагностики.
- Символ без docstring остаётся в справочнике и попадает в предупреждения.
- Одна пара (проект, версия) собирается по очереди.
- Тема своя. Рендерер `GitbookIO/gitbook` не используется.

Дальше, отдельно от этого выпуска: сборка в соседнем контейнере, превью различий, PDF, Postgres, проверка имени Docloom перед публичным продвижением.

## Документы

| Файл | Назначение |
| --- | --- |
| `RESEARCH.md` | Сравнение Read the Docs и локального GitBook |
| `DESIGN.md` | Архитектура и контракты |
| `PLAN.md` | Волны 0–6 и границы MVP |
| `samples/demo-lib` | Витрина автогенерации |
