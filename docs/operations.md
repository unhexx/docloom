# Эксплуатация

## Поднять стенд

Нужны Docker и Compose. Порт `8080` должен быть свободен.

```bash
docker compose up -d --build --wait
curl -fsS http://127.0.0.1:8080/health
bash scripts/compose-smoke.sh
```

Smoke создаёт проект `demo-lib` на `/opt/docloom/samples/demo-lib`, если его ещё нет, ставит билд `latest` и ждёт статус, который начинается с `success`. Затем открывает главную и проверяет, что в ней есть имя проекта и ссылка на класс `Client`.

Повторный `docker compose up -d --wait` не пересобирает контейнеры, пока образ и файлы те же. Остановка без удаления томов: `docker compose stop`. `docker compose down -v` стирает базу, логи и опубликованные сайты. Так делать, когда именно это и нужно.

Четыре сервиса обычного стенда: `api`, `worker`, `watch`, `nginx`. Пустой `DOCLOOM_WATCH_URL` оставляет `watch` здоровым и очередь не трогает. Образец переменных — [`.env.example`](../.env.example).

## Свой каталог на той же машине

Каталог должен оказаться внутри allowlist. Проще всего положить дерево в том `sources` или расширить `DOCLOOM_SOURCE_ROOTS` и пересоздать `api` и `worker`.

```bash
curl -fsS -X POST http://127.0.0.1:8080/api/projects \
  -H 'content-type: application/json' \
  -d '{"name":"demo-lib","local_path":"/opt/docloom/samples/demo-lib"}'

curl -fsS -X POST http://127.0.0.1:8080/api/projects/1/builds \
  -H 'content-type: application/json' \
  -d '{"ref":"latest"}'
```

Дальше опрашивать `GET /api/projects/1/builds/1`, пока статус не начнётся с `success` или не станет `failed`. Лог — поле `log_path`, книга — `artifact_path`. Снаружи книга доступна по `/sites/demo-lib/latest/`.

`docloom.yml` в каталоге необязателен: хватает `README.md` и `docs/`.

## Git

```json
{"name": "demo-lib", "git_url": "https://example.com/demo-lib.git"}
```

Билд с `ref` `main` клонирует ветку `main` в `/sources/demo-lib/main`. Повторный билд делает `fetch` той же ветки. Образ содержит `git`. Таймаут clone и fetch — 300 секунд. Запросы идут по HTTP/1.1.

Адрес `https://сервер/scm/ПРОЕКТ/репозиторий.git` при заданном `DOCLOOM_GIT_TOKEN` клоном не качается: worker забирает файлы книги через REST Bitbucket. Как включить опрос без ручного билда — в [Bitbucket](bitbucket.md).

Webhook GitHub или Bitbucket указывает на `http://<хост>:8080/hooks/git`. Секрет хука задаётся `DOCLOOM_WEBHOOK_SECRET` или полем `webhook_secret` при создании проекта. Пустой секрет принимает хук на замкнутом стенде. На доступном адресе секрет стоит задать.

## Что смотреть, если книга не появилась

| Симптом | Куда глядеть |
| --- | --- |
| `queued` долго висит | `docker compose ps`, heartbeat `/data/worker-heartbeat`, лог сервиса `worker` |
| `failed` | файл из `log_path` внутри тома `data` (`/data/logs/{id}.log`) |
| `watch: …` в логе watch | имя не резолвится (`DOCLOOM_EXTRA_HOST`), сертификат (`DOCLOOM_GIT_SSL_VERIFY`), токен или пустая книга |
| 400 на `local_path` | путь вне `DOCLOOM_SOURCE_ROOTS` |
| 502 на `/health` сразу после пересоздания API | подождать, пока контейнер станет healthy; nginx сам берёт новый адрес |
| страница без стилей | открывать URL со слэшем на конце или `index.html`; ссылки версии относительные |
| `success_with_warnings` | книга опубликована; список в `warnings` и на странице «Диагностика» |
| один и тот же коммит собирается каждую минуту | предыдущий билд завершился `failed` и SHA не записан; смотреть лог, а не интервал |

Токен в логе заменён на `***`. В аргументах процесса его тоже лучше не печатать.

## Чего стенд не делает

Редактора, SSO, PDF и поиска отдельной службой нет. Произвольная команда сборки из yaml не запускается, код проекта не исполняется. Один процесс worker разбирает очередь по одной задаче за раз. Разные версии друг друга не блокируют. Один `watch` следит за одним URL.
