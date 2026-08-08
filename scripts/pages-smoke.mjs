import { access, readFile } from "node:fs/promises";
import { constants } from "node:fs";

await access("hub/index.html", constants.R_OK);
await access("quiz/index.html", constants.R_OK);
const html = await readFile("hub/index.html", "utf8");
const app = await readFile("hub/app.js", "utf8");
for (const asset of ["styles.css", "app.js"]) {
  const match = html.match(new RegExp(`(?:href|src)=\\"${asset}\\"`));
  if (!match) throw new Error(`Hub asset is not referenced: ${asset}`);
  await access(`hub/${asset}`, constants.R_OK);
}
if (html.includes("../quiz/") || app.includes("../quiz/")) {
  throw new Error("Hub quiz links must use quiz/index.html because quiz is deployed under the Pages site root.");
}
if (!html.includes("quiz/index.html") || !app.includes("quiz/index.html")) {
  throw new Error("Hub must link to the deployed quiz entry point at quiz/index.html.");
}
console.log("Pages smoke check passed for Hub and quiz entry points.");
