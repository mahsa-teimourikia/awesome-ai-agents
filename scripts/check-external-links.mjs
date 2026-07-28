import { readFile } from "node:fs/promises";
const source = await readFile("hub/lessons.js", "utf8");
const urls = [...new Set([...source.matchAll(/(https?:\/\/[^"']+)/g)].map(([, url]) => url))];
const failures = [];
for (const url of urls) {
  try { const response = await fetch(url, { method: "HEAD", signal: AbortSignal.timeout(10000) }); if (response.status >= 500) failures.push(`${response.status} ${url}`); }
  catch (error) { failures.push(`${error.message} ${url}`); }
}
if (failures.length) { console.error(failures.join("\n")); process.exitCode = 1; }
else console.log(`Validated ${urls.length} external Hub links.`);
