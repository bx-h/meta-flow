import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { runInstall } from "../../src/cli/commands/install.js";
import { runUninstall } from "../../src/cli/commands/uninstall.js";

test("uninstall removes managed plugin and agents but keeps task data", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-uninstall-test-"));
  await runInstall(["--scope", "repo", "--target", target, "--yes"]);
  await fs.mkdir(path.join(target, ".meta-flow", "tasks", "T"), { recursive: true });
  await fs.writeFile(path.join(target, ".meta-flow", "tasks", "T", "state.json"), "{}\n");

  await runUninstall(["--scope", "repo", "--target", target, "--yes"]);

  assert.equal(await exists(path.join(target, "plugins", "meta-flow")), false);
  assert.equal(await exists(path.join(target, ".codex", "agents", "questioner.toml")), false);
  assert.equal(await exists(path.join(target, ".meta-flow", "tasks", "T", "state.json")), true);
});

test("uninstall refuses deletion without yes or dry-run", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-uninstall-test-"));
  await runInstall(["--scope", "repo", "--target", target, "--yes"]);
  await assert.rejects(() => runUninstall(["--scope", "repo", "--target", target]), /--yes/);
});

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}
