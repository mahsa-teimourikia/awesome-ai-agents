import { readFile, readdir } from "node:fs/promises";
for (const file of await readdir("labs/notebooks")) {
  if (!file.endsWith(".ipynb")) continue;
  const notebook = JSON.parse(await readFile(`labs/notebooks/${file}`, "utf8"));
  if (notebook.nbformat !== 4 || !Array.isArray(notebook.cells)) throw new Error(`Invalid notebook: ${file}`);
}
console.log("Validated notebook JSON and nbformat metadata.");
