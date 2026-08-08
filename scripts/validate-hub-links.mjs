import { access, readFile } from "node:fs/promises";
import { constants } from "node:fs";

const source = await readFile("hub/lessons.js", "utf8");
const local = [...source.matchAll(/(?:material|lab|notebook):"([^"]+)"/g)].map(([, path]) => path.split("#")[0]).filter((path) => !path.startsWith("http"));
for (const path of local) await access(path, constants.R_OK);
console.log(`Validated ${local.length} local Hub material links.`);
