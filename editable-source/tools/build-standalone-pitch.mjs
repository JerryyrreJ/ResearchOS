import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const MIME_BY_EXTENSION = {
  ".gif": "image/gif",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
};

export async function inlineLocalAssets(html, htmlDirectory) {
  const references = [...html.matchAll(/src="(\.\/assets\/[^"?#]+)"/g)];
  const replacements = new Map();

  for (const [, reference] of references) {
    if (replacements.has(reference)) continue;

    const assetPath = path.resolve(htmlDirectory, reference);
    const extension = path.extname(assetPath).toLowerCase();
    const mimeType = MIME_BY_EXTENSION[extension];
    if (!mimeType) throw new Error(`Unsupported asset type: ${extension}`);

    const bytes = await readFile(assetPath);
    replacements.set(reference, `data:${mimeType};base64,${bytes.toString("base64")}`);
  }

  let output = html;
  for (const [reference, dataUrl] of replacements) {
    output = output.replaceAll(`src="${reference}"`, `src="${dataUrl}"`);
  }
  return output;
}

async function main() {
  const [, , inputPath, outputPath] = process.argv;
  if (!inputPath || !outputPath) {
    throw new Error("Usage: node tools/build-standalone-pitch.mjs <input.html> <output.html>");
  }

  const absoluteInput = path.resolve(inputPath);
  const source = await readFile(absoluteInput, "utf8");
  const standalone = await inlineLocalAssets(source, path.dirname(absoluteInput));
  await writeFile(path.resolve(outputPath), standalone);
}

if (fileURLToPath(import.meta.url) === path.resolve(process.argv[1] ?? "")) {
  await main();
}
