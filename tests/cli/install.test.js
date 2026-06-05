import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { runInstall } from "../../src/cli/commands/install.js";

test("repo install creates plugin, marketplace, agents, and config", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-install-test-"));
  await runInstall(["--scope", "repo", "--target", target, "--yes"]);

  assert.equal(await exists(path.join(target, "plugins", "meta-flow", ".codex-plugin", "plugin.json")), true);
  assert.equal(await exists(path.join(target, ".codex", "agents", "questioner.toml")), true);
  assert.equal(await exists(path.join(target, ".codex", "config.toml")), true);

  const marketplace = JSON.parse(await fs.readFile(path.join(target, ".agents", "plugins", "marketplace.json"), "utf8"));
  assert.equal(marketplace.plugins.filter((plugin) => plugin.name === "meta-flow").length, 1);
});

test("repo install is idempotent for marketplace entry", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-install-test-"));
  await runInstall(["--scope", "repo", "--target", target, "--yes"]);
  await runInstall(["--scope", "repo", "--target", target, "--yes"]);
  const marketplace = JSON.parse(await fs.readFile(path.join(target, ".agents", "plugins", "marketplace.json"), "utf8"));
  assert.equal(marketplace.plugins.filter((plugin) => plugin.name === "meta-flow").length, 1);
});

test("dry-run does not write files", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-dry-test-"));
  await runInstall(["--scope", "repo", "--target", target, "--dry-run"]);
  assert.deepEqual(await fs.readdir(target), []);
});

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}
