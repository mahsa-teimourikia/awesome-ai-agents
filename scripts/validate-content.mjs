#!/usr/bin/env node

import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, extname, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const ignoredDirectories = new Set([
  ".git",
  ".venv",
  "node_modules",
  "out",
  "dist",
  ".pytest_cache",
  ".ruff_cache",
]);

function walk(directory, predicate) {
  const results = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) continue;
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) results.push(...walk(path, predicate));
    else if (predicate(path)) results.push(path);
  }
  return results;
}

function repoPath(path) {
  return relative(root, path).split("\\").join("/");
}

const tracks = ["beginner", "intermediate", "advanced"];
const courseDirectories = tracks.flatMap((track) =>
  readdirSync(resolve(root, "curriculum", track), { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => resolve(root, "curriculum", track, entry.name)),
);

assert.equal(courseDirectories.length, 47, "expected 47 published course directories");

const courseReadmes = new Set();
const canonicalNotebooks = new Set();
for (const course of courseDirectories) {
  const readme = resolve(course, "README.md");
  assert.ok(existsSync(readme), `${repoPath(course)} is missing README.md`);
  courseReadmes.add(repoPath(readme));

  const notebooks = readdirSync(course)
    .filter((name) => extname(name) === ".ipynb")
    .map((name) => resolve(course, name));
  assert.equal(
    notebooks.length,
    1,
    `${repoPath(course)} must contain exactly one canonical notebook; found ${notebooks.length}`,
  );
  const notebook = JSON.parse(readFileSync(notebooks[0], "utf8"));
  assert.equal(notebook.nbformat, 4, `${repoPath(notebooks[0])} must use nbformat 4`);
  assert.ok(notebook.cells.length > 0, `${repoPath(notebooks[0])} has no cells`);
  const cellIds = notebook.cells.map((cell) => cell.id);
  assert.ok(cellIds.every(Boolean), `${repoPath(notebooks[0])} has cells without IDs`);
  assert.equal(
    new Set(cellIds).size,
    cellIds.length,
    `${repoPath(notebooks[0])} has duplicate cell IDs`,
  );
  canonicalNotebooks.add(repoPath(notebooks[0]));
}

const pageDataPath = resolve(root, "app/page-data.tsx");
const pageData = readFileSync(pageDataPath, "utf8");
const guideBlock = pageData.match(
  /export const guidePaths:[\s\S]*?=\s*\{([\s\S]*?)\n\};/,
);
assert.ok(guideBlock, "could not parse guidePaths from app/page-data.tsx");
const guidePaths = new Map(
  [...guideBlock[1].matchAll(/"([^"]+)":\s*"([^"]+)"/g)].map((match) => [
    match[1],
    match[2],
  ]),
);

const subjectPattern =
  /"id":\s*"([^"]+)",\s*"level":\s*"([^"]+)",\s*"step":\s*"([^"]+)",[\s\S]*?"notebook":\s*"([^"]+)"/g;
const subjects = [...pageData.matchAll(subjectPattern)].map((match) => ({
  id: match[1],
  level: match[2],
  step: match[3],
  notebook: match[4],
}));

assert.equal(subjects.length, 47, "Hub must register all 47 lessons");
assert.equal(new Set(subjects.map(({ id }) => id)).size, subjects.length, "Hub IDs must be unique");
assert.deepEqual(
  new Set(guidePaths.keys()),
  new Set(subjects.map(({ id }) => id)),
  "Hub guide IDs and subject IDs differ",
);
assert.deepEqual(
  new Set(guidePaths.values()),
  courseReadmes,
  "Hub guide paths must cover every course README exactly once",
);
assert.deepEqual(
  new Set(subjects.map(({ notebook }) => notebook)),
  canonicalNotebooks,
  "Hub notebook paths must cover every canonical notebook exactly once",
);

const expectedLevelCounts = {
  Beginner: 7,
  Intermediate: 9,
  Advanced: 14,
  "Enterprise Agent": 17,
};
for (const [level, expected] of Object.entries(expectedLevelCounts)) {
  assert.equal(
    subjects.filter((subject) => subject.level === level).length,
    expected,
    `Hub ${level} count is out of date`,
  );
}

for (const navigationPath of ["README.md", "COURSE_MAP.md"]) {
  const navigation = readFileSync(resolve(root, navigationPath), "utf8");
  for (const readme of courseReadmes) {
    assert.ok(navigation.includes(readme), `${navigationPath} does not link ${readme}`);
  }
}

function githubSlug(heading) {
  return heading
    .trim()
    .toLowerCase()
    .replace(/<[^>]*>/g, "")
    .replace(/[\p{P}\p{S}]/gu, (character) =>
      character === "-" || character === "_" ? character : "",
    )
    .replace(/\s/g, "-");
}

const markdownFiles = walk(root, (path) => extname(path).toLowerCase() === ".md");
const anchorCache = new Map();

function anchorsFor(path) {
  if (anchorCache.has(path)) return anchorCache.get(path);
  const text = readFileSync(path, "utf8");
  const anchors = new Set();
  const occurrences = new Map();
  for (const line of text.split("\n")) {
    const heading = line.match(/^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$/);
    if (heading) {
      const baseSlug = githubSlug(heading[1]);
      const count = occurrences.get(baseSlug) ?? 0;
      occurrences.set(baseSlug, count + 1);
      anchors.add(count === 0 ? baseSlug : `${baseSlug}-${count}`);
    }
    for (const match of line.matchAll(/\b(?:id|name)=["']([^"']+)["']/g)) {
      anchors.add(match[1]);
    }
  }
  anchorCache.set(path, anchors);
  return anchors;
}

let markdownLinkCount = 0;
for (const markdownPath of markdownFiles) {
  const markdown = readFileSync(markdownPath, "utf8");
  const links = markdown.matchAll(/!?\[[^\]]*\]\((<[^>]+>|[^)\s]+)(?:\s+["'][^"']*["'])?\)/g);
  for (const match of links) {
    let destination = match[1].replace(/^<|>$/g, "");
    if (
      !destination ||
      /^(?:https?:|mailto:|tel:|data:|javascript:)/i.test(destination)
    ) {
      continue;
    }
    markdownLinkCount += 1;

    const [rawPath, rawFragment] = destination.split("#", 2);
    let target;
    try {
      target = rawPath
        ? resolve(dirname(markdownPath), decodeURIComponent(rawPath))
        : markdownPath;
    } catch {
      assert.fail(`${repoPath(markdownPath)} has malformed link ${destination}`);
    }
    assert.ok(
      existsSync(target),
      `${repoPath(markdownPath)} links missing path ${destination}`,
    );
    if (rawFragment && statSync(target).isFile() && extname(target).toLowerCase() === ".md") {
      const fragment = decodeURIComponent(rawFragment);
      assert.ok(
        anchorsFor(target).has(fragment),
        `${repoPath(markdownPath)} links missing heading ${destination}`,
      );
    }
  }
}

const { questions } = await import(
  pathToFileURL(resolve(root, "quiz/questions.js")).href
);
const questionIds = new Set();
for (const question of questions) {
  assert.ok(!questionIds.has(question.id), `duplicate quiz ID ${question.id}`);
  questionIds.add(question.id);
  assert.ok(question.options.length >= 2, `${question.id} needs answer options`);
  assert.ok(question.correct.length >= 1, `${question.id} needs a correct answer`);
  assert.ok(
    question.correct.every((index) => Number.isInteger(index) && index >= 0 && index < question.options.length),
    `${question.id} has an invalid correct-answer index`,
  );

  const [sourcePath, fragment] = question.source.url.split("#", 2);
  const source = resolve(root, sourcePath);
  assert.ok(existsSync(source), `${question.id} cites missing source ${sourcePath}`);
  if (fragment && extname(source).toLowerCase() === ".md") {
    assert.ok(
      anchorsFor(source).has(decodeURIComponent(fragment)),
      `${question.id} cites missing heading ${question.source.url}`,
    );
  }
}

console.log(
  `Validated ${courseDirectories.length} courses, ${canonicalNotebooks.size} canonical notebooks, ` +
    `${markdownLinkCount} local Markdown links, ${questions.length} quiz sources, and Hub coverage.`,
);
