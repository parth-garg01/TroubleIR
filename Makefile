PYTHON := py
SRC := src
TESTS := tests

.PHONY: install dev test test-unit test-api lint serve clean

install:
	$(PYTHON) -m pip install -r requirements.txt

dev:
	$(PYTHON) -m pip install -r requirements.txt -r requirements-dev.txt

serve:
	set PYTHONPATH=$(SRC) && $(PYTHON) -m uvicorn troubleir.api.main:app --host 0.0.0.0 --port 8000 --reload

test-unit:
	PYTHONPATH=$(SRC) $(PYTHON) -m pytest $(TESTS)/test_schema.py $(TESTS)/test_cache.py $(TESTS)/test_lint.py $(TESTS)/test_grounding.py -v

test-api:
	$(PYTHON) -m pytest $(TESTS)/test_api.py -v

test: test-unit

lint:
	$(PYTHON) -m ruff check $(SRC) $(TESTS)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
