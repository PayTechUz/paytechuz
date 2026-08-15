.PHONY: help clean install install-dev test lint build publish

help:
	@echo "make install      - install the package in editable mode"
	@echo "make install-dev  - install with django, fastapi and dev extras"
	@echo "make test         - run the test suite"
	@echo "make lint         - run flake8 over the package"
	@echo "make build        - build sdist and wheel into dist/"
	@echo "make publish      - upload dist/* to PyPI with twine"
	@echo "make clean        - remove build artifacts"

clean:
	@rm -rf build dist *.egg-info .pytest_cache
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@echo "Cleaned build artifacts"

install:
	@pip install -e .

install-dev:
	@pip install -e ".[django,fastapi,dev]"

test:
	@pytest

lint:
	@flake8 paytechuz --max-line-length=120

build: clean
	@python -m build
	@echo "Built:"
	@ls -1 dist

publish:
	@twine upload dist/*
