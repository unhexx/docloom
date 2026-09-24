# RESEARCH: Read the Docs vs локальный GitBook

Дата среза: 2026-09-24. Источники: about.readthedocs.com, docs.readthedocs.com, gitbook.com, GitbookIO/gitbook.

## 1. Что такое каждый продукт на самом деле

### Read the Docs

Инфраструктурный слой **docs-as-code**, а не редактор. Команда пишет в Sphinx / MkDocs / Docusaurus / VitePress / Markdoc / Jupyter Book (или любом генераторе HTML). RTD по webhook/push клонирует Git, собирает в облаке, публикует версии с веток и тегов, отдаёт поиск, CDN, превью PR, PDF/EPUB, llms.txt, agent skills.

Ключевые свойства автосборки:

- конфиг в репозитории (`.readthedocs.yaml`): ОС, toolchain, команда сборки, зависимости;
- сборка на каждое изменение источника;
- несколько версий с одного проекта;
- previews на PR с visual diff;
- tool-agnostic: любой процесс, который выдаёт HTML;
- Community бесплатен для OSS; private repos, auth, audit, teams — платные планы ($50–$250/мес, Enterprise от $10k/год).

Платформа существует с 2010, >100k OSS-проектов, код readthedocs.org открыт, но self-host полного RTD — отдельная операционная задача, которую сама компания не позиционирует как основной путь.

### GitBook (2026)

Проприетарная SaaS-платформа: блоковый WYSIWYG, двусторонний Git Sync (GitHub/GitLab), change requests, realtime collaboration, OpenAPI playground, AI Agent / Assistant, MCP-сервер из документации, llms.txt, варианты сайта, аналитика.

«Локальное развёртывание GitBook» сегодня — это **не** полноценная платформа.

| Что открыто | Что закрыто |
| --- | --- |
| Репозиторий `GitbookIO/gitbook` — **рендерер** опубликованных сайтов (Next.js + Bun), GPLv3 | Редактор, Git Sync backend, хостинг, auth, биллинг, агент, MCP generation |
| Legacy `gitbook-cli` / `gitbook serve` — заброшен, официально не использовать | Рекомендация self-host современного рендерера: «только если уверены»; вы сами держите uptime и merge upstream |

Следствие: «поднять GitBook в Docker у себя» даёт либо мёртвый legacy-генератор книг из Markdown+SUMMARY.md, либо чужой фронт, который умеет показывать уже опубликованный GitBook.com. Автосборки из кода, версий, превью PR и пайплайна генерации там нет.

## 2. Сравнение по осям, важным для аналога

| Возможность | Read the Docs | GitBook SaaS | Self-host GitBook (реально) |
| --- | --- | --- | --- |
| Docs-as-code в Git | Да, нативный | Да, Git Sync | Только файлы Markdown вручную |
| Автосборка по push | Да, ядро продукта | Публикация после sync | Нет |
| Генерация API из кода (autodoc) | Через Sphinx autodoc / mkdocstrings / OpenAPI-тулы в билде | OpenAPI import + playground, не AST/docstrings | Нет |
| Мультиверсионность (ветка/тег) | Да | Variants (часто платно) | Нет |
| PR preview + visual diff | Да | Change requests / preview deploys | Нет |
| Редактор для не-инженеров | Нет (текст в IDE) | Да, сильная сторона | Нет |
| Realtime collab | Нет | Да | Нет |
| Поиск | Встроенный, кросс-версии | Да | Статика в лучшем случае |
| PDF / EPUB | Да (Sphinx-экосистема) | PDF на платных планах | Нет |
| Auth / private docs | Платно | Платно | DIY |
| AI / MCP / llms.txt | llms.txt, content negotiation, skills | Agent, Assistant, MCP из доков | Нет |
| Vendor lock-in | Низкий (открытые генераторы) | Высокий (редактор + формат блоков) | Высокий или мёртвый стек |
| Self-host целиком | Формально OSS, тяжело | Не рекомендуется | Рендерер ≠ продукт |
| Per-seat / per-site цена | Нет per-seat; планы за приватность | Free + ~$65/site и выше | Операционные затраты |

## 3. Чего не хватает рынку (и зачем свой продукт)

Дыра между двумя полюсами:

1. RTD закрывает **сборку и хостинг**, но не даёт GitBook-опыта чтения/навигации «книга + боковая ось + мгновенный поиск» из коробки для произвольного стека и не делает **унифицированную** автогенерацию (Python + OpenAPI + гайды) своим продуктом — это плагины генераторов.
2. GitBook закрывает **редактор и коллаборацию**, но локально его нет; автогенерация из исходников слабее, чем Sphinx autodoc; self-host не является продуктом.
3. MkDocs / Docusaurus / Sphinx локально дают генератор, но **не платформу**: нет очереди билдов, версий, webhook, манифеста проекта, изоляции сборок, каталога сайтов.
4. Fern / Mintlify / ReadMe закрывают API-порталы, чаще SaaS; self-host — enterprise.

Целевой продукт занимает щель:

> Self-hosted конвейер, который **сам извлекает** справочник из кода и спецификаций, склеивает его с Markdown-книгой в стиле GitBook и публикует версии так, как это делает Read the Docs.

Самое важное — не тема и не WYSIWYG, а **детерминированная автогенерация + воспроизводимый Docker-билд**.

## 4. Вывод для имени и позиционирования

Имена вроде Buildbook / Docsmith / Bookforge заняты соседними рынками (стройка, AI-книги, генераторы Markdown).

Рабочее имя: **Docloom** — «документация ткётся из исходников». Коротко, пригодно для `docloom.yml`, CLI `docloom build`, домена `docloom.dev` / `docs.docloom`. Альтернативы на случай коллизии при проверке товарного знака: **Srcpress**, **Gitledge**, **Codocline**, **Refbook**, **Autobook** (слабее: booking-коллизии).
