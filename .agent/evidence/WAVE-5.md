# Волна 5 — Docker Compose

Дата: 2026-09-24.

## Команды

```bash
docker compose up -d --build --wait
docker compose ps
bash scripts/compose-smoke.sh
docker compose up -d --wait
docker compose top
docker compose logs --tail 40 --no-color
```

## Результат

- Образ `docloom:0.1.0`, сервисы `api`, `worker`, `nginx` в статусе healthy
- Повторный `docker compose up -d --wait` не пересоздаёт контейнеры
- `GET http://127.0.0.1:8080/health` → `{"status":"ok"}`
- Сборка `samples/demo-lib` через API: `success_with_warnings`
- `GET /sites/demo-lib/latest/` содержит `demo-lib` и ссылку на `Client`
- Открываются страница класса, `GET /widgets`, `llms.txt`, `search-index.json`
- Процесс `docloom` работает от uid 10001. `runuser` только сбрасывает права при старте
- В логах api и worker нет ERROR. Единственная строка nginx error — проба несуществующей страницы, ответ 404

Чекпоинт C5 пройден. Redis не входит в compose: очередь в SQLite на volume `data`.
