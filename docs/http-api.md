# HTTP API

Базовый URL в compose: `http://127.0.0.1:8080`. Тело запросов — JSON. Секрет webhook в ответах не появляется.

Коды ошибок FastAPI: `detail` — строка.

## `GET /health`

`200` и `{"status":"ok"}`.

## `GET /api/projects`

Список проектов. У элемента есть `id`, `name`, `git_url`, `local_path`, `created_at`.

## `POST /api/projects`

`201`

```json
{"name": "demo-lib", "local_path": "/opt/docloom/samples/demo-lib"}
```

Нужен `local_path` или `git_url`. Имя: `^[A-Za-z0-9._-]{1,80}$`.

| Код | Причина |
| --- | --- |
| 400 | Пустое имя, нет источника, `local_path` вне allowlist |
| 409 | Проект с таким именем уже есть |

`webhook_secret` необязателен, до 200 символов, в ответ не входит.

## `POST /api/projects/{id}/builds`

`202`. Тело: `{"ref":"latest"}`. Пока worker не забрал задачу, `status` равен `queued`. При `DOCLOOM_SYNC_BUILDS=1` ответ уже содержит итог сборки.

Поля билда: `id`, `project_id`, `ref`, `version`, `sha`, `status`, `started_at`, `finished_at`, `log_path`, `artifact_path`, `warnings`.

`warnings` — список объектов, когда сборка закончилась, и пустой список в очереди.

Статусы: `queued`, `running`, `success`, `success_with_warnings`, `failed`.

| Код | Причина |
| --- | --- |
| 404 | Нет проекта |
| 400 | `ref` нельзя превратить в имя версии |

## `GET /api/projects/{id}/builds/{build_id}`

Тот же объект билда. `404`, если билда нет или он принадлежит другому проекту.

## `POST /hooks/git`

Тело — push payload в форме GitHub.

Проект ищется по `repository.clone_url` (сравнение с `git_url`), иначе по `repository.name`.

| Событие | Ответ |
| --- | --- |
| ping (`zen` и `hook_id`) | `{"ok": true, "ignored": "ping"}` |
| удаление ветки или `after` из сорока нулей | `{"ok": true, "ignored": "delete"}` |
| push | `202` и `{"ok": true, "build": {…}}` |

`ref` вида `refs/heads/main` становится версией `main`.

Если задан секрет, заголовок `X-Hub-Signature-256` должен быть равен `sha256=` и HMAC-SHA256 тела на этом секрете. Иначе `401`. Нет проекта — `404`. Не JSON — `400`.

Подпись считается по сырым байтам тела, до разбора JSON.

## Сайт

| URL | Что отдаёт |
| --- | --- |
| `/sites/{проект}/{версия}/` | `index.html` |
| `/sites/{проект}/{версия}/llms.txt` | оглавление |
| `/sites/{проект}/{версия}/build.json` | манифест |
| любой другой отсутствующий путь внутри версии | `404.html`, статус 404 |

Демо после smoke: `/sites/demo-lib/latest/`.
