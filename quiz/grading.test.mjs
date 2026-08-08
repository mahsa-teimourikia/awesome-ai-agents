import assert from "node:assert/strict";
import test from "node:test";

import { gradeQuiz, isExactMatch, normalizeSelection } from "./grading.js";
import { questions } from "./questions.js";

test("the quiz contains 22 questions across 6 categories", () => {
  assert.equal(questions.length, 22);

  const categories = questions.reduce((counts, question) => {
    counts[question.category] = (counts[question.category] ?? 0) + 1;
    return counts;
  }, {});

  assert.equal(Object.keys(categories).length, 6);
  assert.ok(Object.values(categories).every((count) => count >= 3));
  assert.equal(categories["Agent Loop"], 5);
  assert.equal(categories.Workflows, 5);
});

test("every question is a valid multiple-answer question", () => {
  for (const question of questions) {
    assert.ok(question.id);
    assert.ok(question.prompt);
    assert.ok(question.options.length >= 4);
    assert.ok(question.correct.length >= 2);
    assert.equal(new Set(question.correct).size, question.correct.length);
    assert.ok(question.correct.every((index) => index >= 0 && index < question.options.length));
    assert.ok(question.explanation.length >= 40);
    assert.ok(question.source.url);
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

  assert.equal(result.answeredCount, 22);
  assert.equal(result.correctCount, 22);
  assert.equal(result.percent, 100);
  assert.ok(Object.values(result.categories).every((score) => score.correct === score.total));
});

test("unanswered questions count as incorrect", () => {
  const result = gradeQuiz(questions, {});

  assert.equal(result.answeredCount, 0);
  assert.equal(result.correctCount, 0);
  assert.equal(result.percent, 0);
});
