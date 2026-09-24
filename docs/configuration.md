# Конфигурация

## `docloom.yml`

Файл лежит в корне источника. Поле `project` обязательно.

```yaml
project: demo-lib
version: "0.1.0"          # подпись в книге; API может передать свою через ref
language: ru              # ru — русские заголовки разделов, иначе английские
theme: gitbook            # имя темы; в MVP собирается одна встроенная тема
sources:
  guides: docs            # каталог Markdown-гайдов
  python: [src]           # корни обхода *.py, пути от корня источника
  openapi: [openapi.yaml] # один или несколько файлов OpenAPI 3
exclude:
  - "**/tests/**"         # маски относительно корня источника
publish:
  versions_from: [tags, default_branch]
search: true
llms: true
```

`python` и `openapi` принимают и строку, и список. `guides` — один каталог. Нет каталога Python — предупреждение `missing_python_root`, книга при этом собирается дальше. Нет файла OpenAPI — `missing_openapi`.

`SUMMARY.md` в корне источника задаёт порядок гайдов списком ссылок:

```markdown
# Summary

* [Введение](docs/intro.md)
* [Понятия](docs/concepts.md)
```

Заголовок ссылки можно перекрыть полем `title` во front matter страницы. Файл гайда, который не упомянут в `SUMMARY.md`, попадает в конец раздела и даёт предупреждение `unlisted_guide`. Внешние `http`-ссылки в summary не становятся страницами.

`exclude` понимает `*`, `?` и `**`. Маска `**/tests/**` отсекает и `tests/test_client.py`, и `src/pkg/tests/test_client.py`.

`version` из yaml используется командой `docloom build`, если не передан `--version`. Билд через API называет версию по `ref`, а не по этому полю.

## Переменные окружения

Их читает и API, и worker. Секреты в образ не зашиваются. Образец — `.env.example`.

| Переменная | По умолчанию | Смысл |
| --- | --- | --- |
| `DOCLOOM_DATA` | `data` | SQLite и логи |
| `DOCLOOM_PUBLISH` | `publish` | Каталог сайтов |
| `DOCLOOM_SOURCES` | `$DOCLOOM_DATA/sources` | Клоны git и один из корней allowlist |
| `DOCLOOM_SOURCE_ROOTS` | пусто | Дополнительные корни через `:`. Пустое значение добавляет ещё и текущий каталог процесса |
| `DOCLOOM_SYNC_BUILDS` | `0` | `1` — сборка внутри запроса API, без отдельного worker |
| `DOCLOOM_HOST` | `127.0.0.1` | Адрес `docloom serve` |
| `DOCLOOM_PORT` | `8000` | Порт API |
| `DOCLOOM_WEBHOOK_SECRET` | пусто | Если задан, `POST /hooks/git` требует `X-Hub-Signature-256` |

В compose `DOCLOOM_SYNC_BUILDS=0`: запрос только ставит билд в очередь, книгу пишет worker. Для отладки одного процесса можно поднять `serve` с `DOCLOOM_SYNC_BUILDS=1`.

Секрет webhook можно задать и на проекте (`webhook_secret` в `POST /api/projects`). Он не возвращается в ответах API. Если секрет есть и у проекта, и в окружении, проверяется секрет проекта.
