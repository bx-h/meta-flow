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
  assert.equal(await exists(path.join(target, ".agents", "skills", "meta-flow", "SKILL.md")), true);
  assert.equal(await exists(path.join(target, ".agents", "skills", "meta-flow", ".meta-flow-managed.json")), true);
  assert.equal(await exists(path.join(target, ".meta-flow", "scripts", "controller.py")), true);
  assert.equal(await exists(path.join(target, ".meta-flow", "scripts", "new_task.py")), true);
  assert.equal(await exists(path.join(target, ".meta-flow", "scripts", ".meta-flow-managed.json")), true);
  assert.equal(await exists(path.join(target, ".meta-flow", "templates", "state.json")), true);
  assert.equal(await exists(path.join(target, ".meta-flow", "templates", ".meta-flow-managed.json")), true);
  assert.equal(await exists(path.join(target, ".codex", "agents", "questioner.toml")), true);
  assert.equal(await exists(path.join(target, ".codex", "config.toml")), true);
  assert.equal(await exists(path.join(target, "AGENTS.md")), false);

  const marketplace = JSON.parse(await fs.readFile(path.join(target, ".agents", "plugins", "marketplace.json"), "utf8"));
  assert.equal(marketplace.plugins.filter((plugin) => plugin.name === "meta-flow").length, 1);
});

test("repo install with persistent adds an idempotent AGENTS managed block", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-persistent-install-test-"));
  await fs.writeFile(path.join(target, "AGENTS.md"), "# Existing Instructions\n\nKeep this line.\n", "utf8");

  await runInstall(["--scope", "repo", "--target", target, "--persistent", "--yes"]);
  await runInstall(["--scope", "repo", "--target", target, "--persistent", "--yes"]);

  const agents = await fs.readFile(path.join(target, "AGENTS.md"), "utf8");
  assert.match(agents, /# Existing Instructions/);
  assert.match(agents, /Keep this line\./);
  assert.equal(agents.match(/meta-flow:persistent:start/g).length, 1);
  assert.equal(agents.match(/meta-flow:persistent:end/g).length, 1);
  assert.match(agents, /python3 \.meta-flow\/scripts\/controller\.py resume --format codex/);
  assert.match(agents, /META-FLOW RESUME PACK/);
});

test("repo install refuses unmanaged skill and support conflicts", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-conflict-test-"));
  await fs.mkdir(path.join(target, ".agents", "skills", "meta-flow"), { recursive: true });
  await fs.writeFile(path.join(target, ".agents", "skills", "meta-flow", "SKILL.md"), "custom\n");
  await fs.mkdir(path.join(target, ".meta-flow", "scripts"), { recursive: true });
  await fs.writeFile(path.join(target, ".meta-flow", "scripts", "new_task.py"), "custom\n");

  await runInstall(["--scope", "repo", "--target", target, "--yes"]);

  assert.equal(await fs.readFile(path.join(target, ".agents", "skills", "meta-flow", "SKILL.md"), "utf8"), "custom\n");
  assert.equal(await fs.readFile(path.join(target, ".meta-flow", "scripts", "new_task.py"), "utf8"), "custom\n");
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
