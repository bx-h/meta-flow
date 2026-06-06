import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const CONTROLLER = path.resolve("plugin", "scripts", "controller.py");

test("controller starts active task and emits resume payloads", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-test-")), ".meta-flow");
  const start = runController(root, ["start", "Improve observability", "--task-id", "T-observe"]);
  assert.equal(start.status, 0, start.stderr);
  assert.match(start.stdout, /T-observe/);

  const taskDir = path.join(root, "tasks", "T-observe");
  const active = JSON.parse(await fs.readFile(path.join(root, "active-task.json"), "utf8"));
  assert.equal(active.task_id, "T-observe");
  assert.equal(active.phase, "QUESTIONING");

  const index = JSON.parse(await fs.readFile(path.join(root, "task-index.json"), "utf8"));
  assert.equal(index.tasks.length, 1);
  assert.equal(index.tasks[0].task_id, "T-observe");

  const events = await fs.readFile(path.join(taskDir, "events.ndjson"), "utf8");
  assert.match(events, /task_started/);

  const status = runController(root, ["status", "--format", "json"]);
  assert.equal(status.status, 0, status.stderr);
  const payload = JSON.parse(status.stdout);
  assert.equal(payload.task_id, "T-observe");
  assert.equal(payload.phase, "QUESTIONING");
  assert.equal(payload.next_action.role, "questioner");

  const codex = runController(root, ["resume", "--format", "codex"]);
  assert.equal(codex.status, 0, codex.stderr);
  assert.match(codex.stdout, /META-FLOW RESUME PACK/);
  assert.match(codex.stdout, /Tell the user the current user-facing stage/);
});

test("controller advances only through allowed transitions with required artifacts", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-advance-test-")), ".meta-flow");
  assert.equal(runController(root, ["start", "Improve auth", "--task-id", "T-auth"]).status, 0);

  const invalid = runController(root, ["advance", "--event", "reviews_aggregated"]);
  assert.notEqual(invalid.status, 0);
  assert.match(`${invalid.stdout}\n${invalid.stderr}`, /not allowed from phase QUESTIONING/);

  const missing = runController(root, ["advance", "--event", "goal_contract_drafted"]);
  assert.notEqual(missing.status, 0);
  assert.match(`${missing.stdout}\n${missing.stderr}`, /missing required artifacts: goal-contract\.json/);

  const targetMissing = runController(root, ["advance", "--to", "GOAL_CONTRACT_DRAFTED"]);
  assert.notEqual(targetMissing.status, 0);
  assert.match(`${targetMissing.stdout}\n${targetMissing.stderr}`, /missing required artifacts: goal-contract\.json/);

  const taskDir = path.join(root, "tasks", "T-auth");
  await fs.writeFile(path.join(taskDir, "goal-contract.json"), "{}\n");

  const advance = runController(root, ["advance", "--event", "goal_contract_drafted", "--reason", "Goal contract drafted.", "--format", "json"]);
  assert.equal(advance.status, 0, advance.stderr);
  const payload = JSON.parse(advance.stdout);
  assert.equal(payload.phase, "GOAL_CONTRACT_DRAFTED");

  const state = JSON.parse(await fs.readFile(path.join(taskDir, "state.json"), "utf8"));
  assert.equal(state.phase, "GOAL_CONTRACT_DRAFTED");
  const events = await fs.readFile(path.join(taskDir, "events.ndjson"), "utf8");
  assert.match(events, /goal_contract_drafted/);
});

test("controller records human gates without advancing phase", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-gate-test-")), ".meta-flow");
  assert.equal(runController(root, ["start", "Plan release", "--task-id", "T-release"]).status, 0);

  const open = runController(root, ["gate", "open", "--type", "proposal_confirmation", "--prompt", "Accept proposal?", "--format", "json"]);
  assert.equal(open.status, 0, open.stderr);
  const gate = JSON.parse(open.stdout);
  assert.equal(gate.status, "open");

  const status = JSON.parse(runController(root, ["status", "--format", "json"]).stdout);
  assert.equal(status.open_gate.gate_id, gate.gate_id);
  assert.equal(status.open_gate.type, "proposal_confirmation");

  const decide = runController(root, ["gate", "decide", "--gate", gate.gate_id, "--decision", "accept", "--comment", "Looks good", "--format", "json"]);
  assert.equal(decide.status, 0, decide.stderr);
  const decided = JSON.parse(decide.stdout);
  assert.equal(decided.status, "decided");
  assert.equal(decided.decision, "accept");
});

test("controller requires decided confirmation gates before user acceptance events", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-confirmation-test-")), ".meta-flow");
  assert.equal(runController(root, ["start", "Confirm proposal", "--task-id", "T-confirm"]).status, 0);
  const taskDir = path.join(root, "tasks", "T-confirm");

  await fs.writeFile(path.join(taskDir, "goal-contract.json"), "{}\n");
  assert.equal(runController(root, ["advance", "--event", "goal_contract_drafted"]).status, 0);
  assert.equal(runController(root, ["advance", "--event", "proposal_started"]).status, 0);
  await fs.writeFile(path.join(taskDir, "proposal.md"), "proposal\n");
  assert.equal(runController(root, ["advance", "--event", "proposal_created"]).status, 0);
  await fs.writeFile(path.join(taskDir, "review-aggregate.json"), "{}\n");
  assert.equal(runController(root, ["advance", "--event", "reviews_aggregated"]).status, 0);
  await fs.writeFile(path.join(taskDir, "adjudication-report.json"), "{}\n");
  assert.equal(runController(root, ["advance", "--event", "adjudication_accept"]).status, 0);
  await fs.writeFile(path.join(taskDir, "proposal-summary.md"), "summary\n");
  assert.equal(runController(root, ["advance", "--event", "proposal_summarized"]).status, 0);

  const withoutGate = runController(root, ["advance", "--event", "proposal_accepted"]);
  assert.notEqual(withoutGate.status, 0);
  assert.match(`${withoutGate.stdout}\n${withoutGate.stderr}`, /requires decided gate type \[proposal_confirmation\]/);

  const open = runController(root, ["gate", "open", "--type", "proposal_confirmation", "--prompt", "Accept?", "--format", "json"]);
  const gate = JSON.parse(open.stdout);
  const stillOpen = runController(root, ["advance", "--event", "proposal_accepted"]);
  assert.notEqual(stillOpen.status, 0);
  assert.match(`${stillOpen.stdout}\n${stillOpen.stderr}`, /is still open/);

  assert.equal(runController(root, ["gate", "decide", "--gate", gate.gate_id, "--decision", "accept"]).status, 0);
  const accepted = runController(root, ["advance", "--event", "proposal_accepted", "--format", "json"]);
  assert.equal(accepted.status, 0, accepted.stderr);
  assert.equal(JSON.parse(accepted.stdout).phase, "PROPOSAL_ACCEPTED");
});

function runController(root, args) {
  return spawnSync("python3", [CONTROLLER, "--root", root, ...args], {
    encoding: "utf8",
    env: {
      ...process.env,
      PYTHONDONTWRITEBYTECODE: "1"
    }
  });
}
