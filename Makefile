.PHONY: setup-learner setup-contributor test test-ui notebook-check test-mock-notebooks clean

setup-learner:
	uv venv .venv
	uv sync --extra beginner

setup-contributor: setup-learner
	uv sync --extra contributor --extra beginner --extra frameworks --extra browser
	npm ci

test:
	PYTHONPATH=. pytest -q

test-ui:
	npm run test:pages

notebook-check:
	PYTHONPATH=. .venv/bin/python scripts/execute-notebooks.py --timeout 90

TARGET_DIR ?= curriculum

test-mock-notebooks:
	@echo "Testing notebooks in $(TARGET_DIR) using MockOpenAI (OPENAI_API_KEY unset)..."
	unset OPENAI_API_KEY && find $(TARGET_DIR) -name "*.ipynb" -exec python3 -m jupyter nbconvert --to notebook --execute --inplace {} +
	@echo "All notebooks in $(TARGET_DIR) executed successfully on mock data!"

clean:
	rm -rf .venv node_modules build dist *.egg-info .pytest_cache .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
