.PHONY: install install-api quality test docs capstone capstone-evaluate capstone-ready

install:
	python -m pip install -e ".[dev,docs]"

install-api:
	python -m pip install -e ".[dev,docs,api]"

quality:
	python -m ruff check .
	python -m ruff format --check .
	python -m pytest
	python -m mkdocs build --strict

test:
	python -m pytest

docs:
	python -m mkdocs serve

capstone:
	python projects/07-asteria-investigation-platform/app.py serve --reload

capstone-evaluate:
	python projects/07-asteria-investigation-platform/app.py evaluate

capstone-ready:
	python projects/07-asteria-investigation-platform/app.py readiness
