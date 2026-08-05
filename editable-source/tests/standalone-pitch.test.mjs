import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { inlineLocalAssets } from "../tools/build-standalone-pitch.mjs";

test("inlines local image assets while preserving the HTML content", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "standalone-pitch-"));
  await mkdir(path.join(root, "assets"));
  await writeFile(path.join(root, "assets", "sample.png"), Buffer.from([0x89, 0x50, 0x4e, 0x47]));

  const source = '<!doctype html><title>Original</title><img src="./assets/sample.png" alt="proof">';
  const output = await inlineLocalAssets(source, root);

  assert.ok(output.includes("<title>Original</title>"));
  assert.ok(output.includes('alt="proof"'));
  assert.match(output, /src="data:image\/png;base64,/);
  assert.doesNotMatch(output, /src="\.\/assets\//);
});
