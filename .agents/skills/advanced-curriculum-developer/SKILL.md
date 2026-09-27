---
name: advanced-curriculum-developer
description: Use this skill when creating or improving technical curriculum, notebooks, labs, and course tests in this repository.
---

# Advanced Curriculum Developer

Use the repository's existing course contracts and validation commands before
introducing a new structure.

## Lesson contract

Each lesson directory has:

- a `README.md` with objectives, prerequisites, architecture, failure modes,
  exercises, and primary references;
- exactly one canonical notebook;
- optional deep dives and assets;
- a reusable co-located implementation and focused tests when the lesson needs
  substantial code.

Prefer one tested implementation imported by the notebook and tests. Do not
replace a working reusable module with notebook-only code.

## Notebook evidence

Execute notebooks in a real kernel. Never fabricate outputs or inject simulated
logs that have not been produced by the displayed code. Credential-free
fixtures should be deterministic and safe; provider-backed examples must be
clearly labeled and opt-in.

A notebook should teach the control boundaries as well as the happy path:
authorization, untrusted content, budgets, cancellation, idempotency, evidence,
terminal states, and observability where relevant.

## Technical depth and sources

Explain meaningful trade-offs and production failure modes without forcing the
same outline onto every topic. Ground current framework claims in official
documentation and pin adapter versions when reproducibility requires it.
Architecture lessons should distinguish stable, framework-neutral application
controls from version-specific adapters.

Diagrams may use Mermaid in Markdown or a checked-in accessible SVG. Keep source
files with generated diagrams when practical and verify relative image paths.

## Dependency and navigation updates

Use the central `pyproject.toml` and `uv.lock`; do not add per-lesson
`requirements.txt` files. Add a dependency only when executable course code
imports it, and place it in the narrowest optional group.

Register new lessons and paths in:

- `app/page-data.tsx`
- `README.md`
- `COURSE_MAP.md`
- `quiz/questions.js` when adding cross-course assessment

Then run the focused tests and notebook plus:

```bash
make content-check
make test-quiz
make test
make notebook-check
make test-ui
```
