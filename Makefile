# .PHONY: install test lint format clean run docker-up docker-down

# install:
# 	poetry install

# test:
# 	poetry run pytest tests/ -v --cov=src

# lint:
# 	poetry run ruff check src/
# 	poetry run mypy src/

# format:
# 	poetry run black src/ examples/ tests/
# 	poetry run ruff check --fix src/

# clean:
# 	find . -type d -name "__pycache__" -exec rm -rf {} +
# 	find . -type f -name "*.pyc" -delete
# 	find . -type f -name "*.pyo" -delete
# 	find . -type d -name "*.egg-info" -exec rm -rf {} +
# 	rm -rf .pytest_cache .coverage htmlcov/

# run:
# 	poetry run python src/server.py

# docker-up:
# 	docker-compose up -d

# docker-down:
# 	docker-compose down

# docker-logs:
# 	docker-compose logs -f

# setup-example:
# 	poetry run python examples/setup_example.py





.PHONY: install test lint format clean run docker-up docker-down

install:
	poetry install

test:
	poetry run pytest tests/ -v --cov=src

lint:
	poetry run ruff check src/
	poetry run mypy src/

format:
	poetry run black src/ examples/ tests/
	poetry run ruff check --fix src/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov/

# Run server correctly (python -m)
run:
	poetry run python -m src.server

run-database:
	poetry run python -m src.database

run-example:
	poetry run python -m examples.setup_example

# For uv users
uv-run:
	uv run -m src.server

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

