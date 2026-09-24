# Автосборка из Bitbucket

Пользователь ничего не нажимает. Есть два входа, оба ставят тот же билд.

## Опрос

Сервис `watch` в compose раз в минуту спрашивает удалённую ветку. Если SHA отличается от последнего билда этой версии, задача попадает в очередь, и worker её собирает. Повторный опрос того же коммита ничего не ставит. Неудачный билд тоже запоминает SHA, чтобы не крутить одну и ту же ошибку каждую минуту: новый коммит запускает сборку снова, старый можно пересобрать через `POST /api/projects/{id}/builds`.

В `.env` (файл не коммитится):

```env
DOCLOOM_WATCH_URL=https://git.example.com/scm/PROJ/repo.git
DOCLOOM_WATCH_REF=master
DOCLOOM_WATCH_INTERVAL=60
DOCLOOM_GIT_TOKEN=
DOCLOOM_GIT_SSL_VERIFY=1
```

`DOCLOOM_GIT_TOKEN` — HTTP access token Bitbucket. Он уходит заголовком `Authorization`, не попадает в URL и вырезается из текста ошибок. `DOCLOOM_GIT_SSL_VERIFY=0` нужен, только если сертификат сервера выписан на другое имя.

Адрес вида `https://сервер/scm/ПРОЕКТ/репозиторий.git` Docloom не клонирует целиком: с такого сервера pack часто не доезжает. Берутся SHA ветки и файлы книги (`README.md`, `docs/**/*.md`, `docloom.yml`, `openapi.yaml`, `src/**/*.py`). Остальные git-адреса по-прежнему клонируются.

Один проход без демона: `docloom watch --once`.

Если в репозитории нет `docloom.yml`, книга всё равно собирается: `README.md`, каталог `docs/` и `openapi.yaml`, когда они есть. Свой `docloom.yml` по-прежнему перекрывает этот набор.

## Webhook

Bitbucket Server / Data Center, репозиторий → Webhooks → Add webhook.

| Поле | Значение |
| --- | --- |
| URL | `http://<хост-docloom>:8080/hooks/git` |
| События | `repo:refs_changed` |
| Secret | тот же, что `DOCLOOM_WEBHOOK_SECRET` |

Docloom принимает и облачный payload Bitbucket (`push.changes`), и серверный (`eventKey: repo:refs_changed`). Проект ищется по clone URL без учёта пользователя в адресе и суффикса `.git`, затем по slug. Удаление ветки сборку не ставит. Подпись сверяется по `X-Hub-Signature` или `X-Hub-Signature-256`, оба в виде `sha256=<hmac>`.

Webhook сработает, только если Bitbucket открывает этот URL. Если Docloom стоит во внутренней сети, а Bitbucket снаружи, рабочий путь — опрос: соединение исходит от Docloom.
