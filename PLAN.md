# PLAN: разработка и развёртывание локальными агентами

Оркестрация: детерминированный workflow `.agent/WORKFLOW.yaml`.  
Источник истины по продукту: `DESIGN.md`.  
Не начинать код, пока не пройден чекпоинт C0.

## Правила для агентов

1. Одна волна = один узкий INVEST-срез. Не смешивать генератор, API и тему в одном коммите без нужды.
2. После каждого шага — чекпоинт: файлы + тесты + запись в `.agent/evidence/WAVE-N.md`.
3. Resume только с последнего успешного чекпоинта. При расхождении рабочего дерева с манифестом — остановиться.
4. Секреты не писать в репозиторий. `.env` из `.env.example`.
5. Destructive docker (`down -v`, prune) — только после явного «proceed» человека.
6. Коммиты — от лица разработчика, без упоминания ИИ. Сообщения можно на русском.
7. Не форкать `GitbookIO/gitbook`. Тема — своя.
8. Definition of Done волны: тесты зелёные локально **и** тот же сценарий воспроизводится через `docker compose` начиная с волны 5.
9. Каталог этого пакета (`RESEARCH.md`, `DESIGN.md`, `PLAN.md`) не удалять.

## Целевой скелет репозитория (создаёт волна 1)

```
docloom/
  README.md
  DESIGN.md
  RESEARCH.md
  PLAN.md
  docker-compose.yml
  Dockerfile
  .env.example
  .dockerignore
  pyproject.toml
  nginx/default.conf
  src/docloom/
    __init__.py
    config.py
    ir.py
    api.py
    worker.py
    db.py
    generators/python_ast.py
    generators/openapi.py
    generators/guides.py
    publisher/theme.py
    publisher/search.py
    publisher/llms.py
  samples/demo-lib/
    docloom.yml
    SUMMARY.md
    docs/
    src/demo_lib/
    openapi.yaml
  tests/
  .agent/evidence/
```

Пакет реализации класть в `src/docloom/`, не путать с уже лежащими здесь проектными документами.

---

## Волна 0 — подготовка контура (C0)

**Цель.** Локальный агент может собирать Python-пакет и запускать pytest. Docker доступен на машине агента (в облачной песочнице Grok его может не быть — это не блокер волны 0–4).

Задачи:

- проверить `python3`, `git`, `docker` / `docker compose`;
- создать venv, `pyproject.toml` (fastapi, uvicorn, pyyaml, markdown, jinja2, pygments, httpx, pytest, redis при необходимости);
- завести `samples/demo-lib` с 2–3 модулями, docstring, OpenAPI 3 и двумя гайдами;
- пустой `.agent/evidence/WAVE-0.md`.

DoD: `pytest -q` на пустом `tests/test_smoke_imports.py` зелёный; демо-дерево существует.

Стоп-кран: нет Python 3.11+. Не ставить системный пакет без фиксации версии в `pyproject.toml`.

---

## Волна 1 — IR + Python autodoc (C1)  ★ критический путь

**Цель.** Из каталога исходников без `import` пользовательского кода получается стабильный Markdown-справочник.

Задачи:

- `ProjectConfig.load` из `docloom.yml`;
- IR-модель страницы (см. DESIGN §6);
- обход `*.py`, разбор `ast`, публичные модули/классы/функции/методы;
- шаблон страницы символа: сигнатура, docstring, параметры, returns, source file:line;
- `tests/test_python_ast.py` на `samples/demo-lib`;
- покрытие: символы без docstring попадают в `warnings`.

DoD:

- повторный запуск даёт byte-identical Markdown при том же дереве;
- в выводе есть страница конкретного класса демо;
- тесты не требуют сети и Docker.

Не делать: HTML-тему, API, очередь.

---

## Волна 2 — OpenAPI + гайды + weave (C2)

**Цель.** Одна книга: гайды из `docs/` + generated Python + generated OpenAPI, единый `SUMMARY.md`.

Задачи:

- парсер OpenAPI 3.0/3.1 → страница на операцию (`METHOD path`);
- чтение гайдов и существующего SUMMARY;
- склейка навигации: Guides → Reference / Python → Reference / HTTP;
- диагностика: битый spec → `success_with_warnings`, страница `Diagnostics`.

DoD: `tests/test_weave.py` проверяет порядок секций и наличие операции из `openapi.yaml`.

---

## Волна 3 — Publisher GitBook-like (C3)

**Цель.** Статический HTML, в котором книга читается как GitBook, не являясь GitBook.

Задачи:

- шаблоны: layout, sidebar, article, 404;
- подсветка кода;
- `search-index.json` + минимальный клиентский поиск;
- `llms.txt` и `llms-full.txt`;
- `build.json` манифест;
- `tests/test_publisher.py`: в HTML есть заголовок проекта, ссылка на сгенерированный символ, индекс не пустой.

Не делать: Meilisearch, PDF.

---

## Волна 4 — Control plane и worker без Docker (C4)

**Цель.** HTTP API ставит билд, worker выполняет генерацию в том же коде, артефакт пишется на диск.

Задачи:

- SQLite: Project, Build, Version;
- endpoints из DESIGN §8;
- файловая или Redis-очередь (если Redis нет — список в SQLite + polling);
- логи билда в файл;
- `tests/test_api_build.py` через TestClient: create project на `samples/demo-lib`, build, GET статуса `success`, файлы в `publish/`.

DoD: полный цикл без compose. Параллельные билды одной `(project, version)` сериализуются.

---

## Волна 5 — Docker Compose (C5)

**Цель.** Весь стек поднимается одной командой на машине агента.

Состав минимум:

```yaml
services:
  api:
  worker:
  nginx:
  redis:   # можно отложить, если очередь SQLite; тогда сервис не включать
```

Задачи:

- multi-stage `Dockerfile` (builder + runtime);
- non-root user;
- healthcheck API и nginx;
- volumes: `data`, `publish`, `sources`;
- `.dockerignore`;
- `make compose-up` / документированная команда;
- smoke: `curl /health`, открыть `/sites/demo-lib/latest/`.

DoD:

- `docker compose ps` — все сервисы healthy;
- повторный `compose up` идемпотентен;
- evidence: хвост логов без ERROR, скрин/HTML-фрагмент индексной страницы.

Стоп-кран: нет Docker daemon — волна 5 в статусе `blocked`, волны 1–4 остаются валидным локальным контуром. Не эмулировать Docker «примерно».

---

## Волна 6 — отладка, регрессия, демо-проект (C6)

**Цель.** Закрыть контур качества, после которого человек может отдать репозиторий дальше.

Задачи:

- прогнать pytest в контейнере `api` или отдельном `test` service;
- сломанный OpenAPI и пустой `src/` — ожидаемые warnings, не crash;
- webhook: фикстура GitHub push payload на локальный путь (без реального GitHub);
- README: быстрый старт Compose, как подключить свой репозиторий, ограничения MVP;
- `.agent/evidence/WAVE-6.md` со списком команд и exit codes.

DoD продукта MVP:

- [ ] автогенерация Python + OpenAPI работает;
- [ ] GitBook-подобная навигация;
- [ ] версии как имя ref;
- [ ] compose поднят и проверен;
- [ ] нет секретов в git;
- [ ] исследование и дизайн сохранены.

Gate человека: просмотр демо-страницы и решение, идти ли в v1.1 (PR preview, custom builders, auth).

---

## Бэклог после MVP (не планировать в том же прогоне)

- sibling-container builder + allowlist образов;
- visual diff и preview на «виртуальный PR» (две сборки + html-diff);
- PDF через weasyprint или pandoc-контейнер;
- mkdocstrings/Sphinx как внешний tool за policy-флагом;
- MCP endpoint поверх `llms-full.txt`;
- Postgres + миграции;
- проверка домена и товарного знака Docloom перед публичным продвижением.

---

## Параллельные потоки

| Поток | Волны | Можно параллелить с |
| --- | --- | --- |
| PRODUCT-GEN | 1, 2 | PUB после C1 |
| PRODUCT-PUB | 3 | после C2 (нужна IR) |
| PRODUCT-CTRL | 4 | после C2 |
| OPS | 5, 6 | строго после C4 |
| META | evidence, README | каждая волна |

Синхроточка перед Compose: C3 + C4 зелёные.

---

## Команды, которые агент имеет право считать каноном

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q
# только с волны 5:
docker compose up -d --build
docker compose ps
curl -fsS http://localhost:8080/health
docker compose logs --tail 80 --no-color
```

Порты по умолчанию: nginx `8080`, api `8000` внутренний. Не занимать 80 без нужды.

## Что сдать человеку в конце

1. Репозиторий с зелёными тестами.
2. Работающий `docker-compose.yml`.
3. `samples/demo-lib` как витрина автогенерации.
4. Evidence-файлы волн 0–6.
5. Короткая записка «что не вошло в MVP».
