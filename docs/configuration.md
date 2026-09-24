# Конфигурация

## Книга без `docloom.yml`

Если в корне ревизии нет `docloom.yml`, Docloom собирает книгу по дереву:

| Что нашлось | Как попадает в книгу |
| --- | --- |
| имя каталога | поле `project` |
| `docs/` | гайды |
| `src/` | корни Python |
| `openapi.yaml` или `openapi.yml` | спецификация |
| `README.md` | первая страница руководств |
| `SUMMARY.md` | порядок гайдов, если файл есть |

Язык такой книги — `ru`, поиск и `llms.txt` включены, маска исключений — `**/tests/**`. Свой `docloom.yml` перекрывает этот набор целиком: обнаружение каталогов рядом с файлом не дописывает пропущенные поля.

`docloom build` и worker вызывают один и тот же разбор. Отсутствие `docloom.yml` сборку не роняет.

## `docloom.yml`

Файл лежит в корне источника. Поле `project` обязательно. Язык по умолчанию, если ключ опущен, — `en`.

```yaml
project: demo-lib
version: "0.1.0"          # подпись в книге для docloom build
language: ru              # ru — русские заголовки разделов
theme: gitbook            # имя темы; в 0.1.0 собирается одна встроенная тема
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

`python` и `openapi` принимают строку или список. `guides` — один каталог. Нет каталога Python — предупреждение `missing_python_root`, книга собирается дальше. Нет файла OpenAPI — `missing_openapi`.

`SUMMARY.md` в корне источника задаёт порядок гайдов списком ссылок:

```markdown
# Summary

* [Введение](docs/intro.md)
* [Понятия](docs/concepts.md)
```

Заголовок ссылки перекрывается полем `title` во front matter страницы. Если заголовок страницы совпал с именем файла, берётся первая строка `# `. Файл гайда, который не упомянут в `SUMMARY.md`, попадает в конец раздела и даёт предупреждение `unlisted_guide`. Внешние `http`-ссылки в summary страницами не становятся (`external_summary_link`).

`exclude` понимает `*`, `?` и `**`. Маска `**/tests/**` отсекает и `tests/test_client.py`, и `src/pkg/tests/test_client.py`.

Поле `version` из yaml использует команда `docloom build`, если не передан `--version`. Билд через API называет версию по `ref`. Поле `publish.versions_from` сохраняется в конфиге и само по себе сборки тегов не запускает: версию выбирает `ref` билда или опрос `watch`.

## Переменные окружения

Их читает и API, и worker, и watch. Секреты в образ не зашиваются. Образец — [`.env.example`](../.env.example). Файл `.env` compose подхватывает сам и в git не входит.

| Переменная | По умолчанию | Смысл |
| --- | --- | --- |
| `DOCLOOM_DATA` | `data` | SQLite и логи |
| `DOCLOOM_PUBLISH` | `publish` | Каталог сайтов |
| `DOCLOOM_SOURCES` | `$DOCLOOM_DATA/sources` | Клоны git и один из корней allowlist |
| `DOCLOOM_SOURCE_ROOTS` | пусто | Дополнительные корни через `:`. Пустое значение добавляет ещё и текущий каталог процесса |
| `DOCLOOM_SYNC_BUILDS` | `0` | `1` — сборка внутри запроса API или внутри `watch`, без отдельного worker |
| `DOCLOOM_HOST` | `127.0.0.1` | Адрес `docloom serve` |
| `DOCLOOM_PORT` | `8000` | Порт API |
| `DOCLOOM_WEBHOOK_SECRET` | пусто | Если задан, `POST /hooks/git` требует подпись |
| `DOCLOOM_WATCH_URL` | пусто | Clone URL, который опрашивает `watch`. Пусто — наблюдение спит |
| `DOCLOOM_WATCH_REF` | `master` | Ветка или тег |
| `DOCLOOM_WATCH_INTERVAL` | `60` | Секунды между опросами, не меньше 15 |
| `DOCLOOM_GIT_TOKEN` | пусто | HTTP access token. Уходит заголовком `Authorization: Bearer` |
| `DOCLOOM_GIT_SSL_VERIFY` | `1` | `0` — не проверять сертификат Git и REST |
| `DOCLOOM_EXTRA_HOST` | `localhost:127.0.0.1` | Запись `имя:адрес` в `/etc/hosts` контейнеров `worker` и `watch` |

В compose `DOCLOOM_SYNC_BUILDS=0`: запрос только ставит билд в очередь, книгу пишет worker. Для отладки одного процесса можно поднять `serve` с `DOCLOOM_SYNC_BUILDS=1`.

Секрет webhook можно задать и на проекте (`webhook_secret` в `POST /api/projects`). Он в ответах API не возвращается. Если секрет есть и у проекта, и в окружении, проверяется секрет проекта.

Токен в URL клона не подставляется и из текста ошибок вырезается. В compose его получают `api`, `worker` и `watch`, потому что webhook и ручной билд тоже ходят в Git из worker.
