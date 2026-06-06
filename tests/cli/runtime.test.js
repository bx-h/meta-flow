import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const CLI = path.resolve("bin", "meta-flow.js");
const CONTROLLER = path.resolve("plugin", "scripts", "controller.py");

test("runtime CLI defaults task state to the user meta-flow root", async () => {
  const home = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-home-test-"));
  const cwd = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-cwd-test-"));
  const env = { ...process.env, HOME: home };

  const start = spawnSync("node", [CLI, "start", "Use home runtime", "--task-id", "T-home", "--format", "json"], {
    cwd,
    env,
    encoding: "utf8"
  });
  assert.equal(start.status, 0, start.stderr);
  const payload = JSON.parse(start.stdout);
  assert.equal(payload.task_id, "T-home");
  assert.match(payload.task_dir, new RegExp(escapeRegex(path.join(home, ".meta-flow", "tasks", "T-home"))));
  assert.equal(await exists(path.join(home, ".meta-flow", "tasks", "T-home", "state.json")), true);
  assert.equal(await exists(path.join(home, ".meta-flow", "tasks", "T-home", "artifacts", "by-node", "01-INTAKE", "done", "raw-request.md")), true);
  assert.equal(await exists(path.join(cwd, ".meta-flow")), false);

  const status = spawnSync("node", [CLI, "status", "--format", "json"], { cwd, env, encoding: "utf8" });
  assert.equal(status.status, 0, status.stderr);
  assert.equal(JSON.parse(status.stdout).task_id, "T-home");

  const validation = spawnSync("node", [CLI, "artifacts", "validate", "T-home", "--format", "json"], { cwd, env, encoding: "utf8" });
  assert.equal(validation.status, 0, validation.stderr);
  assert.equal(JSON.parse(validation.stdout).ok, true);
});

test("runtime CLI supports explicit root and package bin alias", async () => {
  const packageJson = JSON.parse(await fs.readFile(path.resolve("package.json"), "utf8"));
  assert.equal(packageJson.bin.metaflow, "bin/meta-flow.js");

  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-explicit-root-test-")), "runtime");
  const start = spawnSync("node", [CLI, "start", "Use explicit runtime", "--task-id", "T-root", "--root", root, "--format", "json"], {
    encoding: "utf8"
  });
  assert.equal(start.status, 0, start.stderr);
  assert.equal(await exists(path.join(root, "tasks", "T-root", "state.json")), true);
});

test("direct python helpers do not create __pycache__", async () => {
  const pycache = path.resolve("plugin", "scripts", "__pycache__");
  await fs.rm(pycache, { recursive: true, force: true });

  const result = spawnSync("python3", [CONTROLLER, "--help"], {
    encoding: "utf8"
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(await exists(pycache), false);
});

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
