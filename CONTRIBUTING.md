# Contributing

Thank you for improving Awesome AI Agents & Agentic Workflows. Read the
[installation guide](INSTALLATION.md) before making changes.

## Add or update a lesson

Keep each lesson self-contained and use one implementation as its source of
truth:

1. Create or update the lesson `README.md` in the appropriate curriculum track.
2. Maintain exactly one canonical notebook in the lesson directory. The
   notebook should import a reusable co-located module when the lesson has
   substantial implementation logic.
3. Add focused tests for the lesson's important contracts, failure modes, and
   safety boundaries.
4. Register the lesson in `app/page-data.tsx`, including its canonical notebook
   and README paths.
5. Add cross-course quiz questions to `quiz/questions.js`. Each question must
   cite an existing repository file and, when used, a valid heading anchor.
6. Update `README.md` and `COURSE_MAP.md` so the public navigation remains
   complete.

Do not duplicate notebooks, fabricate execution outputs, or copy a lesson's
implementation into a second untested source file. Credential-free fixtures
should be deterministic; provider-backed extensions must be clearly labeled.

## Validate the change

Run the focused lesson tests and notebook first, then the repository checks:

```bash
make content-check
make test-quiz
make test
make notebook-check
make test-ui
```

When dependency declarations change, update and commit `uv.lock` or
`app/package-lock.json` as appropriate. CI installs from those lockfiles.

## Pull request scope

Keep pull requests focused. Separate broad formatting changes from conceptual
revisions. Support technical claims with primary research, standards, or
official documentation and record the exact validation performed.

By contributing, you agree that your contribution will be licensed under the
repository's MIT License.
