# Волна 0 — контур

Дата: 2026-09-24.

## Команды

```bash
bash Agent-Init.sh
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m memory.proxy health
pytest -q
```

## Результат

- `AGENT_INIT_OK version=3.13.0`, симлинк `agentic_loop_template` → `/home/unhex/_PROJECT/agentic_loop_template`
- В `.venv/bin/activate` прописаны `GROK_CLI_CHAT_PROXY_BASE_URL=http://127.0.0.1:8110/v1` и `AGENTIX_PXPIPE_URL=http://127.0.0.1:8100`
- `memory.proxy health`: `pxpipe_ok=true`, `gateway_ok=true`, `dial_ok=true`, режим `required`
- `pytest -q`: `1 passed`
- Python 3.14.7, Docker доступен
- Дерево `samples/demo-lib`: два гайда, пакет `demo_lib`, `openapi.yaml`, `docloom.yml`

Чекпоинт C0 пройден.
