# HTTP API

Базовый URL в compose: `http://127.0.0.1:8080`. Тело запросов — JSON. Секрет webhook в ответах не появляется.

Коды ошибок FastAPI: `detail` — строка. Успешный webhook со сборкой отвечает `202`. Событие, которое сборку не ставит, отвечает `200`.

## `GET /health`

`200` и `{"status":"ok"}`. Тот же ответ снаружи и с `http://api:8000/health` внутри сети compose.

## `GET /api/projects`

Список проектов. У элемента есть `id`, `name`, `git_url`, `local_path`, `created_at`. Поля `webhook_secret` в объекте нет.

## `POST /api/projects`

`201`

```json
{"name": "demo-lib", "local_path": "/opt/docloom/samples/demo-lib"}
```

Нужен `local_path` или `git_url`. Можно передать оба. Имя: `^[A-Za-z0-9._-]{1,80}$`.

| Код | Причина |
| --- | --- |
| 400 | Пустое или недопустимое имя, нет источника, `local_path` вне allowlist |
| 409 | Проект с таким именем уже есть |

`webhook_secret` необязателен, до 200 символов, в ответ не входит. `local_path` в ответе — уже разрешённый абсолютный путь.

Проект для опроса `watch` создаёт сам, этот запрос для автосборки не нужен. Он нужен для каталога на диске, для git-адреса вне опроса и для секрета webhook на конкретном проекте.

## `POST /api/projects/{id}/builds`

`202`. Тело: `{"ref":"latest"}`. Пока worker не забрал задачу, `status` равен `queued`, `sha` пустой. При `DOCLOOM_SYNC_BUILDS=1` ответ уже содержит итог сборки.

Поля билда: `id`, `project_id`, `ref`, `version`, `sha`, `status`, `started_at`, `finished_at`, `log_path`, `artifact_path`, `warnings`.

`warnings` — список объектов, когда сборка закончилась, и пустой список в очереди и при `failed`.

Статусы: `queued`, `running`, `success`, `success_with_warnings`, `failed`.

| Код | Причина |
| --- | --- |
| 404 | Нет проекта |
| 400 | `ref` нельзя превратить в имя версии |

`ref` `refs/heads/main` становится версией `main`. В версии нет слэша. Пока для той же пары есть `running`, новый билд остаётся `queued`, пока первый не закончится.

## `GET /api/projects/{id}/builds/{build_id}`

Тот же объект билда. `404` и `{"detail":"билд не найден"}`, если билда нет или он принадлежит другому проекту. Этот ответ остаётся JSON: страница `404.html` сайта его не подменяет.

## `POST /hooks/git`

Тело — push GitHub, `repo:refs_changed` Bitbucket Server или `push.changes` Bitbucket Cloud. Разбор описан в [Bitbucket](bitbucket.md).

Проект ищется по clone URL (без пользователя в адресе и без суффикса `.git`), затем по имени или slug.

| Событие | Ответ |
| --- | --- |
| ping (`zen` и `hook_id`) | `200`, `{"ok": true, "ignored": "ping"}` |
| удаление ветки, `after` или `toHash` из сорока нулей | `200`, `{"ok": true, "ignored": "delete"}` либо `no-changes` |
| неизвестный `eventKey` Bitbucket Server | `200`, `{"ok": true, "ignored": "<eventKey>"}` |
| push с новыми ref | `202`, `{"ok": true, "build": {…}, "builds": […]}` |

`build` — первый поставленный билд. `builds` — все ref из события, по одному билду на ref. Несколько веток в одном payload ставят несколько задач.

Если задан секрет, заголовок `X-Hub-Signature-256` или `X-Hub-Signature` должен быть равен `sha256=` и HMAC-SHA256 сырого тела. Иначе `401` и `{"detail":"подпись webhook не сошлась"}`. Нет проекта у события, которое требует сборку, — `404`. Не JSON — `400` «ожидался JSON». Тело не объект — `400` «ожидался объект».

Подпись считается по сырым байтам тела, до разбора JSON. Секрет проекта важнее `DOCLOOM_WEBHOOK_SECRET`. Пустой секрет подпись не требует.

`watch` этот маршрут не вызывает: он пишет в ту же очередь напрямую.

## Сайт

| URL | Что отдаёт |
| --- | --- |
| `/sites/{проект}/{версия}/` | `index.html` |
| `/sites/{проект}/{версия}/llms.txt` | оглавление |
| `/sites/{проект}/{версия}/llms-full.txt` | тексты страниц |
| `/sites/{проект}/{версия}/build.json` | манифест |
| `/sites/{проект}/{версия}/search-index.json` | индекс поиска |
| любой другой отсутствующий путь внутри версии | `404.html`, статус 404 |

Демо после smoke: `/sites/demo-lib/latest/`. Книга, которую собрал `watch`, лежит по последнему сегменту clone URL и по имени ветки: `…/repo.git` и ref `master` дают `/sites/repo/master/`.
