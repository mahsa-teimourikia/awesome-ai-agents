# Learning Guide

This repository is a notebook-first path from bounded agents to governed,
production-scale agentic systems. Start with the [installation guide](INSTALLATION.md),
then use the [Learning Hub](https://mahsa-teimourikia.github.io/awesome-ai-agents/)
or the [course map](COURSE_MAP.md) to choose a lesson.

## The study loop

1. Read the lesson `README.md` for the concepts, constraints, and prerequisites.
2. Read any co-located deep dives that support the lesson.
3. Run the lesson's canonical notebook from top to bottom.
4. Change one variable and inspect the resulting behavior.
5. Exercise the documented failure modes and boundaries.
6. Turn a meaningful fix or invariant into a repeatable test.

The objective is not merely to produce a successful output. It is to understand
why the system succeeds, how it fails, and which application-owned controls make
that behavior reproducible.

## Four learning levels

| Level | Published lessons | Goal |
| --- | ---: | --- |
| Beginner | 7 | Build one bounded, trustworthy agent and understand its runtime. |
| Intermediate | 9 | Engineer tools, context, approvals, evaluation, planning, retrieval, and durable state. Course number 07 is reserved. |
| Advanced | 14 | Design teams, memory, model routing, asynchronous execution, evaluation, protocols, and governed skills. |
| Enterprise Agent | 17 | Synthesize architecture, operations, security, governance, economics, and human oversight. |

Enterprise Agent lessons are stored in `curriculum/advanced/15-31` for
repository compatibility, but the Hub presents them as a separate 17-step
track.

## Run the Learning Hub locally

The Hub is a React and Vite application in `app/`:

```bash
npm ci --prefix app
npm run dev --prefix app
```

Vite prints the local address when it starts. With the repository base path it
is normally `http://localhost:5173/awesome-ai-agents/`.

## Check your understanding

Each Hub lesson includes a checkpoint when embedded questions are available.
Lessons without an embedded checkpoint link to the full cross-course knowledge
check and the source lesson instead of displaying an empty quiz.

Use the hosted [full Knowledge Check](https://mahsa-teimourikia.github.io/awesome-ai-agents/quiz/)
for a broader assessment. Every answer links back to its supporting repository
source.
