import { access, readFile } from "node:fs/promises";
import { constants } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = resolve(root, "out");

const html = await readFile(resolve(outDir, "index.html"), "utf8");
const quizHtml = await readFile(resolve(outDir, "quiz/index.html"), "utf8");
await readFile(resolve(outDir, "assets/one-plus-i.png"));
const assets = [...html.matchAll(/(?:src|href)="(\/awesome-ai-agents\/assets\/[^"?]+)"/g)].map(([, path]) => path);
if (!assets.length) throw new Error("No hashed Pages assets found");
for (const asset of assets) await access(resolve(outDir, asset.replace(/^\/awesome-ai-agents\//, "")), constants.R_OK);
const javascript = await Promise.all(assets.filter((asset) => asset.endsWith(".js")).map((asset) => readFile(resolve(outDir, asset.replace(/^\/awesome-ai-agents\//, "")), "utf8")));
const bundle = javascript.join("\n");
if (!bundle.includes("AI Agents") || !bundle.includes("Advanced") || !bundle.includes("Beginner")) throw new Error("Pages bundle is missing current curriculum content");
if (!bundle.includes("A ONE+i OPEN LEARNING PROJECT") || !bundle.includes("ONE+i OPEN LEARNING") || !bundle.includes("https://oneplusi.io")) throw new Error("Pages bundle is missing current One+i branding");
const hubLogo = bundle.match(/\/awesome-ai-agents\/assets\/one-plus-i-[A-Za-z0-9_-]+\.png/)?.[0];
if (!hubLogo) throw new Error("Pages bundle is missing the bundled One+i logo reference");
await access(resolve(outDir, hubLogo.replace(/^\/awesome-ai-agents\//, "")), constants.R_OK);
if (!quizHtml.includes("AI Agents Knowledge Check") || !quizHtml.includes("question-list")) throw new Error("Quiz page artifact is missing the knowledge check shell");
console.log(`Pages smoke check passed (${assets.length} assets, curriculum bundle, quiz page, and One+i branding present).`);
