.PHONY: help setup-learner setup-intermediate setup-advanced setup-contributor \
	test test-quiz test-ui content-check notebook-check test-mock-notebooks validate clean

UV_RUN ?= uv run
TARGET_DIR ?= curriculum
EXCLUDE_DIR ?=

help:
	@echo "setup-learner       Install the locked beginner environment"
	@echo "setup-intermediate  Install the locked intermediate environment"
	@echo "setup-advanced      Install the locked advanced environment"
	@echo "setup-contributor   Install all validation dependencies and Hub packages"
	@echo "validate            Run content, quiz, Python, and Learning Hub checks"

setup-learner:
	uv sync --locked --extra beginner

setup-intermediate:
	uv sync --locked --extra intermediate

setup-advanced:
	uv sync --locked --extra advanced

setup-contributor:
	uv sync --locked --all-extras
	npm ci --prefix app

test:
	PYTHONPATH=. $(UV_RUN) pytest -q

test-quiz:
	npm test --prefix quiz

test-ui:
	npm run test:pages --prefix app

content-check:
	node scripts/validate-content.mjs

notebook-check:
	PYTHONPATH=. $(UV_RUN) python scripts/execute-notebooks.py --timeout 90

test-mock-notebooks:
	@echo "Testing notebooks in $(TARGET_DIR) using MockOpenAI (OPENAI_API_KEY unset)..."
	unset OPENAI_API_KEY && PYTHONPATH=. $(UV_RUN) python scripts/execute-notebooks.py --timeout 90 $(TARGET_DIR) $(if $(EXCLUDE_DIR),--exclude $(EXCLUDE_DIR))
	@echo "All notebooks in $(TARGET_DIR) executed successfully on mock data!"

validate: content-check test-quiz test test-ui
	uv lock --check
	npm audit --prefix app --audit-level=high

clean:
	rm -rf .venv app/node_modules build dist out *.egg-info .pytest_cache .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
