import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { runInstall } from "../../src/cli/commands/install.js";
import { runUninstall } from "../../src/cli/commands/uninstall.js";

test("uninstall removes managed plugin and agents but keeps task data", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-uninstall-test-"));
  await fs.writeFile(path.join(target, "AGENTS.md"), "# Existing Instructions\n\nKeep this line.\n", "utf8");
  await runInstall(["--scope", "repo", "--target", target, "--persistent", "--yes"]);
  await fs.mkdir(path.join(target, ".meta-flow", "tasks", "T"), { recursive: true });
  await fs.writeFile(path.join(target, ".meta-flow", "tasks", "T", "state.json"), "{}\n");

  await runUninstall(["--scope", "repo", "--target", target, "--yes"]);

  assert.equal(await exists(path.join(target, "plugins", "meta-flow")), false);
  assert.equal(await exists(path.join(target, ".agents", "skills", "meta-flow")), false);
  assert.equal(await exists(path.join(target, ".meta-flow", "scripts")), false);
  assert.equal(await exists(path.join(target, ".meta-flow", "templates")), false);
  assert.equal(await exists(path.join(target, ".codex", "agents", "questioner.toml")), false);
  assert.equal(await exists(path.join(target, ".meta-flow", "tasks", "T", "state.json")), true);
  const agents = await fs.readFile(path.join(target, "AGENTS.md"), "utf8");
  assert.match(agents, /# Existing Instructions/);
  assert.match(agents, /Keep this line\./);
  assert.doesNotMatch(agents, /meta-flow:persistent:start/);
});

test("uninstall refuses deletion without yes or dry-run", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-uninstall-test-"));
  await runInstall(["--scope", "repo", "--target", target, "--yes"]);
  await assert.rejects(() => runUninstall(["--scope", "repo", "--target", target]), /--yes/);
});

test("uninstall on empty target does not create marketplace", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-empty-uninstall-test-"));
  await runUninstall(["--scope", "repo", "--target", target, "--yes"]);
  assert.equal(await exists(path.join(target, ".agents", "plugins", "marketplace.json")), false);
});

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}
