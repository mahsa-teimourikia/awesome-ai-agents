import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { gradeQuiz, isExactMatch, normalizeSelection } from "./grading.js";
import { questions } from "./questions.js";

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

test("the quiz contains at least 104 questions across 16 or more categories", () => {
  assert.ok(questions.length >= 104);

  const categories = questions.reduce((counts, question) => {
    counts[question.category] = (counts[question.category] ?? 0) + 1;
    return counts;
  }, {});

  assert.ok(Object.keys(categories).length >= 16);
  assert.ok(Object.values(categories).every((count) => count >= 1));
});

test("every question has a valid answer set", () => {
  for (const question of questions) {
    assert.ok(question.id);
    assert.ok(question.prompt);
    assert.ok(question.options.length >= 4);
    assert.ok(question.correct.length >= 1);
    assert.equal(new Set(question.correct).size, question.correct.length);
    assert.ok(question.correct.every((index) => index >= 0 && index < question.options.length));
    assert.ok(question.explanation.length >= 40);
    assert.ok(question.source.url);
  }
});

test("every question cites an existing repository source", () => {
  for (const question of questions) {
    const [sourcePath] = question.source.url.split("#", 1);
    assert.equal(
      existsSync(resolve(repositoryRoot, sourcePath)),
      true,
      `${question.id} cites missing source ${sourcePath}`,
    );
  }
});

test("selection normalization removes duplicates, converts, and sorts", () => {
  assert.deepEqual(normalizeSelection(["3", 1, 3, 0]), [0, 1, 3]);
});

test("exact-match grading rejects partial and extra selections", () => {
  assert.equal(isExactMatch([0, 2], [2, 0]), true);
  assert.equal(isExactMatch([0], [0, 2]), false);
  assert.equal(isExactMatch([0, 1, 2], [0, 2]), false);
});

test("a complete answer key earns 100 percent", () => {
  const selections = Object.fromEntries(
    questions.map((question) => [question.id, question.correct]),
  );
  const result = gradeQuiz(questions, selections);

  assert.equal(result.answeredCount, questions.length);
  assert.equal(result.correctCount, questions.length);
  assert.equal(result.percent, 100);
  assert.ok(Object.values(result.categories).every((score) => score.correct === score.total));
});

test("unanswered questions count as incorrect", () => {
  const result = gradeQuiz(questions, {});

  assert.equal(result.answeredCount, 0);
  assert.equal(result.correctCount, 0);
  assert.equal(result.percent, 0);
});
