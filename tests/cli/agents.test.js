import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { installAgents, uninstallAgents, validateAgentTemplates } from "../../src/cli/lib/agents.js";
import { resolveTargets } from "../../src/cli/lib/paths.js";

test("agent templates have required fields", async () => {
  const results = await validateAgentTemplates();
  assert.equal(results.every((result) => result.missing.length === 0), true);
});

test("installAgents refuses unmanaged conflicts and uninstall removes marked files", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-agent-test-"));
  const targets = resolveTargets({ scope: "repo", target });
  await fs.mkdir(targets.agentsTarget, { recursive: true });
  await fs.writeFile(path.join(targets.agentsTarget, "questioner.toml"), "name = \"local\"\n");

  const installResult = await installAgents(targets);
  assert.equal(installResult.conflicts.length, 1);
  assert.equal(installResult.installed.length, 13);

  const uninstallResult = await uninstallAgents(targets);
  assert.equal(uninstallResult.removed.length, 13);
  assert.equal(uninstallResult.skipped.length, 1);
});
