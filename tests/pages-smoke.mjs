import { access, readFile } from "node:fs/promises";
import { constants } from "node:fs";

const html = await readFile("out/index.html", "utf8");
const quizHtml = await readFile("out/quiz/index.html", "utf8");
await readFile("out/assets/one-plus-i.png");
const assets = [...html.matchAll(/(?:src|href)="(\/awsome-ai-agents\/assets\/[^"?]+)"/g)].map(([, path]) => path);
if (!assets.length) throw new Error("No hashed Pages assets found");
for (const asset of assets) await access(`out/${asset.replace(/^\/awsome-ai-agents\//, "")}`, constants.R_OK);
const javascript = await Promise.all(assets.filter((asset) => asset.endsWith(".js")).map((asset) => readFile(`out/${asset.replace(/^\/awsome-ai-agents\//, "")}`, "utf8")));
const bundle = javascript.join("\n");
if (!bundle.includes("AI Agents") || !bundle.includes("Advanced") || !bundle.includes("Beginner")) throw new Error("Pages bundle is missing current curriculum content");
if (!quizHtml.includes("AI Agents Knowledge Check") || !quizHtml.includes("question-list")) throw new Error("Quiz page artifact is missing the knowledge check shell");
console.log(`Pages smoke check passed (${assets.length} assets, curriculum bundle, quiz page, and One+i branding present).`);
