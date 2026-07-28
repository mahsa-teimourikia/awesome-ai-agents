import { access, readFile } from "node:fs/promises";
import { constants } from "node:fs";

await access("hub/index.html", constants.R_OK);
await access("quiz/index.html", constants.R_OK);
const html = await readFile("hub/index.html", "utf8");
for (const asset of ["styles.css", "app.js"]) {
  const match = html.match(new RegExp(`(?:href|src)=\\"${asset}\\"`));
  if (!match) throw new Error(`Hub asset is not referenced: ${asset}`);
  await access(`hub/${asset}`, constants.R_OK);
}
console.log("Pages smoke check passed for Hub and quiz entry points.");
