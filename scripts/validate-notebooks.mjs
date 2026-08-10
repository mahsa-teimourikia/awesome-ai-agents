import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";

async function findNotebooks(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(entries.map((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return findNotebooks(path);
    return entry.name.endsWith(".ipynb") ? [path] : [];
  }));
  return files.flat();
}

const notebooks = await findNotebooks("curriculum");
if (!notebooks.length) throw new Error("No curriculum notebooks found.");
for (const file of notebooks) {
  const notebook = JSON.parse(await readFile(file, "utf8"));
  if (notebook.nbformat !== 4 || !Array.isArray(notebook.cells)) throw new Error(`Invalid notebook: ${file}`);
}
console.log(`Validated ${notebooks.length} curriculum notebooks as JSON with nbformat metadata.`);
