# Эксплуатация

## Поднять стенд

Нужны Docker и Compose. Порт `8080` должен быть свободен.

```bash
docker compose up -d --build --wait
curl -fsS http://127.0.0.1:8080/health
bash scripts/compose-smoke.sh
```

Smoke создаёт проект `demo-lib` на `/opt/docloom/samples/demo-lib`, если его ещё нет, ставит билд `latest` и ждёт статус на `success`. Затем открывает главную и проверяет, что в ней есть имя проекта и ссылка на класс `Client`.

Повторный `docker compose up -d --wait` не пересобирает контейнеры, пока образ и файлы те же. Остановка без удаления томов: `docker compose stop`. `docker compose down -v` стирает базу, логи и опубликованные сайты. Так делать только когда это намерение.

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

## Git

```json
{"name": "demo-lib", "git_url": "https://example.com/demo-lib.git"}
```

Билд с `ref` `main` клонирует ветку `main` в `/sources/demo-lib/main`. В ревизии должен быть `docloom.yml`. Повторный билд делает `fetch` той же ветки. Образ содержит `git`.

Webhook GitHub указывает на `http://<хост>:8080/hooks/git`. Секрет хука задаётся `DOCLOOM_WEBHOOK_SECRET` или полем `webhook_secret` при создании проекта. Без секрета хук принимается: так удобно на замкнутом стенде и опасно на доступном адресе.

## Что смотреть, если книга не появилась

| Симптом | Куда глядеть |
| --- | --- |
| `queued` долго висит | `docker compose ps`, heartbeat worker, лог сервиса `worker` |
| `failed` | файл из `log_path` внутри тома `data` |
| 400 на `local_path` | путь не внутри `DOCLOOM_SOURCE_ROOTS` |
| 502 на `/health` сразу после пересоздания API | подождать, пока контейнер станет healthy; nginx сам берёт новый адрес |
| страница без стилей | открывать URL со слэшем на конце или `index.html`; ссылки версии относительные |
| `success_with_warnings` | это успешная книга; список в `warnings` и на странице «Диагностика» |

## Чего стенд не делает

Нет редактора, SSO, PDF, поиска отдельной службой, произвольной команды сборки и исполнения кода проекта. Один процесс worker разбирает очередь по одной задаче за раз, но разные версии не блокируют друг друга. Таймаут git-клона — 60 секунд.
