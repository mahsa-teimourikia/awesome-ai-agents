# AI Agents Curriculum

The curriculum is the hands-on route through this repository. Its 47 lessons
share a notebook-first study loop and progressively add the controls required
for reliable, secure, and governable agentic systems.

## Use a lesson

1. Read the lesson `README.md` for outcomes, prerequisites, and constraints.
2. Run the single canonical notebook in that lesson directory.
3. Inspect the documented failure modes and complete the exercises.
4. Run the co-located focused tests when the lesson includes reusable code.
5. Complete the Hub checkpoint or use the full Knowledge Check.

Open the hosted [Learning Hub](https://mahsa-teimourikia.github.io/awesome-ai-agents/)
for guided navigation, or use the repository [course map](../COURSE_MAP.md) for
direct links to every lesson. The [installation guide](../INSTALLATION.md)
documents supported runtimes and locked dependency groups.

## Learning path

| Level | Lessons | Outcome |
| --- | ---: | --- |
| Beginner | 7 | Build a bounded agent and understand what the runtime owns. |
| Intermediate | 9 | Make tools, context, approvals, evaluation, planning, retrieval, and state dependable. |
| Advanced | 14 | Design teams, memory, routing, asynchronous work, evaluators, protocols, and governed skills. |
| Enterprise Agent | 17 | Synthesize architecture, operations, economics, governance, security, and human oversight. |

The Enterprise Agent lessons are stored in `advanced/15-31` to preserve stable
repository paths. The Learning Hub presents them as their own 01–17 sequence.

## Repository contract

Each lesson directory must contain a `README.md` and exactly one canonical
notebook. Substantial implementations should live in a reusable co-located
module imported by both the notebook and its tests. Hub paths, course maps,
quiz sources, and Markdown links are checked automatically by
`scripts/validate-content.mjs`.
