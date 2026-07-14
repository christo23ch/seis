.PHONY: up down logs test seed shell
up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f backend worker
test:
	cd backend && python -m pytest -q
seed:
	docker compose exec backend python -m scripts.init_db
shell:
	docker compose exec backend python
