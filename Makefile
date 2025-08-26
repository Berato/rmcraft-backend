.PHONY: help install run test lint

help:
	@echo "Commands:"
	@echo "  install: installs dependencies"
	@echo "  run:     runs the web server"
	@echo "  test:    runs the tests"
	@echo "  lint:    runs the linter"

install:
	poetry install --no-root

run:
	poetry run uvicorn main:app --reload --host 127.0.0.1 --port 8000

test:
	poetry run pytest -q

lint:
	poetry run ruff check .
