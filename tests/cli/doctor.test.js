import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { runDoctor } from "../../src/cli/commands/doctor.js";
import { runInstall } from "../../src/cli/commands/install.js";

test("doctor passes installed repo target", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-doctor-test-"));
  await runInstall(["--scope", "repo", "--target", target, "--yes"]);
  const code = await runDoctor(["--scope", "repo", "--target", target]);
  assert.equal(code, 0);
});
