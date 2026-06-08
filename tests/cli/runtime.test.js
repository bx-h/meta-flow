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

test("runtime CLI exposes abandon command", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-abandon-runtime-test-")), "runtime");
  const start = spawnSync("node", [CLI, "start", "Abandon through CLI", "--task-id", "T-cli-abandon", "--root", root], {
    encoding: "utf8"
  });
  assert.equal(start.status, 0, start.stderr);

  const abandon = spawnSync("node", [CLI, "abandon", "--root", root, "--reason", "No longer needed.", "--format", "json"], {
    encoding: "utf8"
  });
  assert.equal(abandon.status, 0, abandon.stderr);
  const payload = JSON.parse(abandon.stdout);
  assert.equal(payload.status, "abandoned");
  assert.equal(payload.phase, "ABANDONED");
  assert.equal(await exists(path.join(root, "active-task.json")), false);
});

test("runtime CLI validates questioning reports with legacy and rich metadata", async () => {
  const work = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-questioning-validate-test-"));
  const legacy = path.join(work, "legacy-questioning-report.json");
  await fs.writeFile(legacy, JSON.stringify({
    producer: { agent_name: "questioner", execution_mode: "spawned_agent" },
    task_id: "T-questioning",
    raw_user_request: "Clarify this task.",
    known_information: [],
    missing_information: [],
    clarifying_questions: [{
      question: "What should success mean?",
      why_it_matters: "Acceptance depends on it.",
      blocking: true
    }],
    assumptions_if_user_does_not_answer: [],
    can_continue_without_user_answer: false
  }));

  const legacyValidation = spawnSync("node", [CLI, "validate", "questioning-report", legacy], {
    encoding: "utf8"
  });
  assert.equal(legacyValidation.status, 0, legacyValidation.stderr);

  const richValidation = spawnSync("node", [CLI, "validate", "questioning-report", path.resolve("plugin", "templates", "questioning-report.json")], {
    encoding: "utf8"
  });
  assert.equal(richValidation.status, 0, richValidation.stderr);

  const blocked = path.join(work, "blocked-questioning-report.json");
  await fs.writeFile(blocked, JSON.stringify({
    producer: { agent_name: "questioner", execution_mode: "spawned_agent" },
    task_id: "T-questioning",
    raw_user_request: "Clarify this task.",
    known_information: [],
    missing_information: ["Acceptance target is still unknown."],
    clarifying_questions: [],
    assumptions_if_user_does_not_answer: [],
    can_continue_without_user_answer: true
  }));
  const blockedValidation = spawnSync("node", [CLI, "validate", "questioning-report", blocked], {
    encoding: "utf8"
  });
  assert.notEqual(blockedValidation.status, 0);
  assert.match(blockedValidation.stderr, /missing_information remains/);
});

test("aggregate-reviews creates nested output directories", async () => {
  const work = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-aggregate-test-"));
  const reviewsDir = path.join(work, "reviews");
  await fs.mkdir(reviewsDir, { recursive: true });

  for (const reviewer of ["product_reviewer", "technical_reviewer", "risk_reviewer", "verification_reviewer"]) {
    const suggestedChanges = ["product_reviewer", "technical_reviewer"].includes(reviewer)
      ? [{ code: "TECH-001", message: "Keep structured review data.", severity: "medium" }]
      : [];
    await fs.writeFile(
      path.join(reviewsDir, `${reviewer}.json`),
      JSON.stringify({
        producer: { agent_name: reviewer, execution_mode: "spawned_agent" },
        task_id: "T-aggregate",
        reviewer,
        decision: "pass",
        confidence: 0.9,
        summary: `${reviewer} passed.`,
        blocking_issues: [],
        suggested_changes: suggestedChanges,
        missing_information: [],
        evidence_refs: []
      })
    );
  }

  const output = path.join(work, "artifacts", "by-node", "05-PROPOSAL_REVIEW", "done", "review-aggregate.json");
  const aggregate = spawnSync("node", [CLI, "aggregate-reviews", "--reviews-dir", reviewsDir, "--output", output], {
    encoding: "utf8"
  });
  assert.equal(aggregate.status, 0, aggregate.stderr);
  assert.equal(await exists(output), true);
  const payload = JSON.parse(await fs.readFile(output, "utf8"));
  assert.equal(payload.task_id, "T-aggregate");
  assert.equal(payload.overall_mechanical_result, "pass");
  assert.equal(payload.reviewers.length, 4);
  assert.deepEqual(payload.all_suggested_changes, [
    { code: "TECH-001", message: "Keep structured review data.", severity: "medium" }
  ]);
  assert.deepEqual(payload.suggested_changes_by_reviewer, [{
    reviewer: "product_reviewer",
    value: { code: "TECH-001", message: "Keep structured review data.", severity: "medium" }
  }, {
    reviewer: "technical_reviewer",
    value: { code: "TECH-001", message: "Keep structured review data.", severity: "medium" }
  }]);
});

test("aggregate-reviews exposes command-specific help", () => {
  const help = spawnSync("node", [CLI, "aggregate-reviews", "--help"], {
    encoding: "utf8"
  });
  assert.equal(help.status, 0, help.stderr);
  assert.match(help.stdout, /--reviews-dir/);
  assert.match(help.stdout, /--output/);
  assert.match(help.stdout, /--task-id/);
});

test("runtime CLI exposes controller command-specific help", () => {
  const gateHelp = spawnSync("node", [CLI, "gate", "--help"], {
    encoding: "utf8"
  });
  assert.equal(gateHelp.status, 0, gateHelp.stderr);
  assert.match(gateHelp.stdout, /Usage:|usage:/);
  assert.match(gateHelp.stdout, /meta-flow gate decide/);
  assert.match(gateHelp.stdout, /--decision accept\|reject\|revise\|pause\|abort/);

  const decideHelp = spawnSync("node", [CLI, "gate", "decide", "--help"], {
    encoding: "utf8"
  });
  assert.equal(decideHelp.status, 0, decideHelp.stderr);
  assert.match(decideHelp.stdout, /usage: meta-flow gate decide/);
  assert.match(decideHelp.stdout, /--gate GATE/);
  assert.match(decideHelp.stdout, /--decision \{accept,reject,revise,pause,abort\}/);
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
