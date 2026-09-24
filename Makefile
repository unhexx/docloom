.PHONY: test compose-up compose-ps compose-smoke

test:
	pytest -q

compose-up:
	docker compose up -d --build --wait

compose-ps:
	docker compose ps

compose-smoke:
	bash scripts/compose-smoke.sh
