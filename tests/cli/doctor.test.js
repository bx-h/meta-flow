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

test("doctor fails stale marketplace, plugin version, and missing support scripts", async () => {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-doctor-strict-test-"));
  await runInstall(["--scope", "repo", "--target", target, "--yes"]);

  const marketplacePath = path.join(target, ".agents", "plugins", "marketplace.json");
  const marketplace = JSON.parse(await fs.readFile(marketplacePath, "utf8"));
  marketplace.plugins[0].version = "0.0.0";
  await fs.writeFile(marketplacePath, `${JSON.stringify(marketplace, null, 2)}\n`);
  assert.equal(await runDoctor(["--scope", "repo", "--target", target]), 1);

  marketplace.plugins[0].version = "0.1.2";
  await fs.writeFile(marketplacePath, `${JSON.stringify(marketplace, null, 2)}\n`);
  const manifestPath = path.join(target, "plugins", "meta-flow", ".codex-plugin", "plugin.json");
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  manifest.version = "0.0.0";
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  assert.equal(await runDoctor(["--scope", "repo", "--target", target]), 1);

  manifest.version = "0.1.2";
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  await fs.rm(path.join(target, ".meta-flow", "scripts", "aggregate_reviews.py"));
  assert.equal(await runDoctor(["--scope", "repo", "--target", target]), 1);
});
