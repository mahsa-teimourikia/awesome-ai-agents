# Installation and local development

The repository uses `uv.lock` as the reproducible Python environment and
`app/package-lock.json` as the reproducible Learning Hub environment. Prefer
the locked commands below over installing individual libraries by hand.

## Prerequisites

- Git
- Python 3.11 or newer (CI validates Python 3.11)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 22 for the Learning Hub and quiz checks

## Clone

```bash
git clone https://github.com/mahsa-teimourikia/awesome-ai-agents.git
cd awesome-ai-agents
```

## Choose a Python environment

`uv sync` creates `.venv` automatically and installs the exact versions in
`uv.lock`.

```bash
# Beginner notebooks
uv sync --locked --extra beginner

# Intermediate notebooks
uv sync --locked --extra intermediate

# Advanced and enterprise-agent notebooks
uv sync --locked --extra advanced

# Optional framework adapters
uv sync --locked --extra beginner --extra frameworks

# Computer-use/browser lesson
uv sync --locked --extra beginner --extra browser
uv run playwright install chromium

# Contributors and the full validation matrix
uv sync --locked --all-extras
```

The framework-neutral course designs do not depend on one SDK release. A few
optional adapters are deliberately pinned to the versions tested by the
course: AutoGen AgentChat 0.7.5, CrewAI 1.15.20, OpenAI Agents SDK 0.20.x, and
MCP Python SDK 1.28.1. Upgrade those adapter pins only with their focused tests
and notebooks; unpinned transitive dependencies are refreshed through
`uv.lock`.

## Run notebooks and tests

```bash
uv run jupyter notebook curriculum/
make test
make notebook-check
```

Credential-free deterministic fixtures are the default. Optional provider
examples are marked and should use scoped environment variables; never commit
credentials or `.env` files.

## Learning Hub and quiz

```bash
npm ci --prefix app
npm run dev --prefix app
```

Vite prints the local URL, normally `http://localhost:5173/awesome-ai-agents/`.
The standalone full quiz is copied into the production build at
`/awesome-ai-agents/quiz/`.

Run the frontend checks with:

```bash
make content-check
make test-quiz
make test-ui
```

## Full contributor validation

```bash
make setup-contributor
make validate
make notebook-check
```

`make validate` checks curriculum/Hub coverage, local links and quiz sources,
the quiz grader, the Python suite, the production Hub build, the lockfile, and
high-severity npm advisories.

## Dependency maintenance

Inspect available compatible Python updates without changing the lockfile:

```bash
uv lock --upgrade --dry-run
```

After intentionally accepting compatible updates, run `uv lock --upgrade` and
the full validation matrix. For frontend updates, change `app/package.json`, run
`npm install --prefix app`, and require `npm audit --prefix app` plus the
production build before merging.
