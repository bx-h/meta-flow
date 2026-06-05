import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const CLI = path.resolve("bin", "meta-flow.js");

test("CLI propagates doctor failure exit code", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-cli-exit-test-"));
  const result = spawnSync("node", [CLI, "doctor", "--scope", "repo", "--target", target], {
    encoding: "utf8"
  });
  assert.equal(result.status, 1);
  assert.match(`${result.stdout}\n${result.stderr}`, /FAIL:/);
});

test("CLI propagates verify success exit code", () => {
  const result = spawnSync("node", [CLI, "verify", "--lint-only"], {
    encoding: "utf8"
  });
  assert.equal(result.status, 0);
  assert.match(result.stdout, /PASS: package\.json/);
});
