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
  assert.match(events, /start_questioning/);

  const artifactIndex = JSON.parse(await fs.readFile(path.join(taskDir, "artifact-index.json"), "utf8"));
  assert.equal(artifactIndex.layout, "by-node-v2");
  assert.equal(artifactIndex.artifacts[0].node_key, "01-INTAKE");
  assert.equal(artifactIndex.artifacts[0].status, "done");
  assert.equal(artifactIndex.artifacts[0].canonical_path, artifactIndex.artifacts[0].display_path);
  assert.equal(await exists(path.join(taskDir, "raw-request.md")), false);
  assert.equal(await exists(path.join(taskDir, "artifacts", "raw-request.md")), false);
  assert.equal(await exists(path.join(taskDir, "artifacts", "by-node", "01-INTAKE", "done", "raw-request.md")), true);

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

test("controller distinguishes abandon from deactivate", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-abandon-test-")), ".meta-flow");
  assert.equal(runController(root, ["start", "Stop this work", "--task-id", "T-abandon"]).status, 0);

  const open = runController(root, ["gate", "open", "--type", "clarifying_questions", "--prompt", "Continue?", "--format", "json"]);
  assert.equal(open.status, 0, open.stderr);
  const gate = JSON.parse(open.stdout);

  const abandoned = runController(root, ["abandon", "--reason", "User cancelled.", "--format", "json"]);
  assert.equal(abandoned.status, 0, abandoned.stderr);
  const payload = JSON.parse(abandoned.stdout);
  assert.equal(payload.task_id, "T-abandon");
  assert.equal(payload.status, "abandoned");
  assert.equal(payload.phase, "ABANDONED");
  assert.equal(payload.open_gate, null);
  assert.equal(payload.next_action.role, "none");
  assert.equal(await exists(path.join(root, "active-task.json")), false);

  const taskDir = path.join(root, "tasks", "T-abandon");
  const state = await readJson(path.join(taskDir, "state.json"));
  assert.equal(state.status, "abandoned");
  assert.equal(state.phase, "ABANDONED");
  assert.equal(state.last_route_decision, "User cancelled.");

  const gateState = await readJson(path.join(taskDir, "gates", `${gate.gate_id}.json`));
  assert.equal(gateState.status, "decided");
  assert.equal(gateState.decision, "abort");

  const index = await readJson(path.join(root, "task-index.json"));
  assert.equal(index.tasks.find((entry) => entry.task_id === "T-abandon").status, "abandoned");
  assert.equal(index.tasks.find((entry) => entry.task_id === "T-abandon").phase, "ABANDONED");

  const events = await fs.readFile(path.join(taskDir, "events.ndjson"), "utf8");
  assert.match(events, /gate_decided/);
  assert.match(events, /task_abandoned/);

  const validation = runController(root, ["artifacts", "validate", "T-abandon", "--format", "json"]);
  assert.equal(validation.status, 0, validation.stderr);
  assert.equal(JSON.parse(validation.stdout).ok, true);

  const noActive = runController(root, ["resume", "--format", "json"]);
  assert.notEqual(noActive.status, 0);
  assert.match(`${noActive.stdout}\n${noActive.stderr}`, /No active meta-flow task/);

  assert.equal(runController(root, ["start", "Deactivate only", "--task-id", "T-deactivate"]).status, 0);
  const deactivated = runController(root, ["deactivate"]);
  assert.equal(deactivated.status, 0, deactivated.stderr);
  assert.equal(await exists(path.join(root, "active-task.json")), false);

  const deactivatedState = await readJson(path.join(root, "tasks", "T-deactivate", "state.json"));
  assert.equal(deactivatedState.status, "active");
  assert.equal(deactivatedState.phase, "QUESTIONING");
  const updatedIndex = await readJson(path.join(root, "task-index.json"));
  const deactivatedIndex = updatedIndex.tasks.find((entry) => entry.task_id === "T-deactivate");
  assert.equal(deactivatedIndex.status, "active");
  assert.equal(deactivatedIndex.phase, "QUESTIONING");
});

test("controller advances only through allowed transitions with required artifacts", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-advance-test-")), ".meta-flow");
  assert.equal(runController(root, ["start", "Improve auth", "--task-id", "T-auth"]).status, 0);

  const invalid = runController(root, ["advance", "--event", "reviews_aggregated"]);
  assert.notEqual(invalid.status, 0);
  assert.match(`${invalid.stdout}\n${invalid.stderr}`, /not allowed from phase QUESTIONING/);

  const missing = runController(root, ["advance", "--event", "goal_contract_drafted"]);
  assert.notEqual(missing.status, 0);
  assert.match(`${missing.stdout}\n${missing.stderr}`, /missing required artifacts: questioning-report\.json, goal-contract\.json/);

  const targetMissing = runController(root, ["advance", "--to", "GOAL_CONTRACT_DRAFTED"]);
  assert.notEqual(targetMissing.status, 0);
  assert.match(`${targetMissing.stdout}\n${targetMissing.stderr}`, /missing required artifacts: questioning-report\.json, goal-contract\.json/);

  const taskDir = path.join(root, "tasks", "T-auth");
  await writeQuestioningReport(taskDir);
  await fs.writeFile(path.join(taskDir, "goal-contract.json"), "{}\n");

  const advance = runController(root, ["advance", "--event", "goal_contract_drafted", "--reason", "Goal contract drafted.", "--format", "json"]);
  assert.equal(advance.status, 0, advance.stderr);
  const payload = JSON.parse(advance.stdout);
  assert.equal(payload.phase, "GOAL_CONTRACT_DRAFTED");

  const state = JSON.parse(await fs.readFile(path.join(taskDir, "state.json"), "utf8"));
  assert.equal(state.phase, "GOAL_CONTRACT_DRAFTED");
  const artifactIndex = JSON.parse(await fs.readFile(path.join(taskDir, "artifact-index.json"), "utf8"));
  assert.equal(artifactIndex.artifacts.some((entry) => entry.node_key === "02-QUESTIONING" && entry.name === "goal-contract.json"), true);
  assert.equal(artifactIndex.artifacts.some((entry) => entry.node_key === "02-QUESTIONING" && entry.name === "questioning-report.json"), true);
  assert.equal(await exists(path.join(taskDir, "artifacts", "goal-contract.json")), false);
  assert.equal(await exists(path.join(taskDir, "artifacts", "by-node", "02-QUESTIONING", "done", "goal-contract.json")), true);
  assert.equal(await exists(path.join(taskDir, "artifacts", "by-node", "02-QUESTIONING", "done", "questioning-report.json")), true);
  const artifactValidation = runController(root, ["artifacts", "validate", "--format", "json"]);
  assert.equal(artifactValidation.status, 0, artifactValidation.stderr);
  assert.equal(JSON.parse(artifactValidation.stdout).ok, true);
  const events = await fs.readFile(path.join(taskDir, "events.ndjson"), "utf8");
  assert.match(events, /goal_contract_drafted/);
});

test("controller requires a clarification gate when questioning report still has questions", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-questioning-gate-test-")), ".meta-flow");
  assert.equal(runController(root, ["start", "Clarify realtime CLI", "--task-id", "T-clarify"]).status, 0);
  const taskDir = path.join(root, "tasks", "T-clarify");

  await writeQuestioningReport(taskDir, {
    clarifying_questions: [{
      question: "Should the first version include a TUI or only a watch command?",
      why_it_matters: "This changes scope and dependencies.",
      blocking: false
    }],
    assumptions_if_user_does_not_answer: ["Assume a watch command is enough."],
    can_continue_without_user_answer: true
  });
  await writeJson(path.join(taskDir, "goal-contract.json"), {});

  const withoutGate = runController(root, ["advance", "--event", "goal_contract_drafted"]);
  assert.notEqual(withoutGate.status, 0);
  assert.match(`${withoutGate.stdout}\n${withoutGate.stderr}`, /questioning requires user clarification/);
  assert.match(`${withoutGate.stdout}\n${withoutGate.stderr}`, /clarifying_questions/);

  const gate = runController(root, ["gate", "open", "--type", "clarifying_questions", "--prompt", "Should first version include TUI?", "--format", "json"]);
  assert.equal(gate.status, 0, gate.stderr);
  const openAdvance = runController(root, ["advance", "--event", "goal_contract_drafted"]);
  assert.notEqual(openAdvance.status, 0);
  assert.match(`${openAdvance.stdout}\n${openAdvance.stderr}`, /questioning requires user clarification/);

  const gatePayload = JSON.parse(gate.stdout);
  const decide = runController(root, ["gate", "decide", "--gate", gatePayload.gate_id, "--decision", "accept", "--comment", "Use watch command first.", "--format", "json"]);
  assert.equal(decide.status, 0, decide.stderr);
  const advance = runController(root, ["advance", "--event", "goal_contract_drafted", "--format", "json"]);
  assert.equal(advance.status, 0, advance.stderr);
  assert.equal(JSON.parse(advance.stdout).phase, "GOAL_CONTRACT_DRAFTED");
});

test("controller validates and migrates legacy tasks without artifact index", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-legacy-test-")), ".meta-flow");
  const taskDir = path.join(root, "tasks", "T-legacy");
  await fs.mkdir(path.join(taskDir, "gates"), { recursive: true });
  await fs.mkdir(path.join(taskDir, "runs"), { recursive: true });
  const createdAt = "2026-01-01T00:00:00Z";
  await writeJson(path.join(taskDir, "state.json"), {
    task_id: "T-legacy",
    workflow_version: "1",
    phase: "QUESTIONING",
    created_at: createdAt,
    updated_at: createdAt,
    status: "active",
    last_route_decision: "Legacy task.",
    history: []
  });
  await writeJson(path.join(root, "active-task.json"), {
    version: "1",
    task_id: "T-legacy",
    task_dir: "tasks/T-legacy",
    status: "active",
    phase: "QUESTIONING",
    updated_at: createdAt
  });
  await writeJson(path.join(root, "task-index.json"), {
    version: "1",
    tasks: [{
      task_id: "T-legacy",
      task_dir: "tasks/T-legacy",
      status: "active",
      phase: "QUESTIONING",
      created_at: createdAt,
      updated_at: createdAt
    }]
  });
  await fs.writeFile(path.join(taskDir, "events.ndjson"), [
    JSON.stringify({ at: createdAt, actor: "controller", event: "task_started", from_phase: "NONE", to_phase: "INTAKE", artifact_refs: ["raw-request.md", "artifacts/raw-request.md"] }),
    JSON.stringify({ at: createdAt, actor: "controller", event: "start_questioning", from_phase: "INTAKE", to_phase: "QUESTIONING", artifact_refs: [] }),
    ""
  ].join("\n"));
  await fs.writeFile(path.join(taskDir, "raw-request.md"), "legacy request\n");
  await fs.writeFile(path.join(taskDir, "goal-contract.json"), "{}\n");

  const legacyValidation = runController(root, ["artifacts", "validate", "T-legacy", "--format", "json"]);
  assert.equal(legacyValidation.status, 0, legacyValidation.stderr);
  const legacyPayload = JSON.parse(legacyValidation.stdout);
  assert.equal(legacyPayload.legacy_without_index, true);
  assert.equal(legacyPayload.warnings.length, 1);

  const legacyGateOpen = runController(root, ["gate", "open", "--type", "clarifying_questions", "--prompt", "Need one answer?", "--format", "json"]);
  assert.equal(legacyGateOpen.status, 0, legacyGateOpen.stderr);
  const legacyGate = JSON.parse(legacyGateOpen.stdout);
  assert.equal(runController(root, ["gate", "decide", "--gate", legacyGate.gate_id, "--decision", "accept"]).status, 0);

  const advance = runController(root, ["advance", "--event", "goal_contract_drafted", "--format", "json"]);
  assert.equal(advance.status, 0, advance.stderr);
  assert.equal(JSON.parse(advance.stdout).phase, "GOAL_CONTRACT_DRAFTED");
  assert.equal(await exists(path.join(taskDir, "questioning-report.json")), false);
  assert.equal(await exists(path.join(taskDir, "artifacts", "by-node", "02-QUESTIONING", "done", "questioning-report.json")), true);
  assert.equal(await exists(path.join(taskDir, "artifacts", "by-node", "02-QUESTIONING", "done", "goal-contract.json")), true);

  const validation = runController(root, ["artifacts", "validate", "T-legacy", "--format", "json"]);
  assert.equal(validation.status, 0, validation.stderr);
  assert.equal(JSON.parse(validation.stdout).ok, true);
});

test("controller rejects corrupted artifact manifests", async () => {
  {
    const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-missing-index-test-")), ".meta-flow");
    assert.equal(runController(root, ["start", "Missing index", "--task-id", "T-missing-index"]).status, 0);
    const taskDir = path.join(root, "tasks", "T-missing-index");
    await fs.unlink(path.join(taskDir, "artifact-index.json"));

    const validation = runController(root, ["artifacts", "validate", "T-missing-index", "--format", "json"]);
    assert.notEqual(validation.status, 0);
    assert.match(validation.stdout, /artifact-index\.json is missing while artifacts\/by-node layout exists/);
  }

  {
    const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-bad-layout-test-")), ".meta-flow");
    assert.equal(runController(root, ["start", "Bad layout", "--task-id", "T-bad-layout"]).status, 0);
    const taskDir = path.join(root, "tasks", "T-bad-layout");
    const artifactIndexPath = path.join(taskDir, "artifact-index.json");
    const artifactIndex = await readJson(artifactIndexPath);
    artifactIndex.layout = "not-by-node";
    await writeJson(artifactIndexPath, artifactIndex);

    const validation = runController(root, ["artifacts", "validate", "T-bad-layout", "--format", "json"]);
    assert.notEqual(validation.status, 0);
    assert.match(validation.stdout, /artifact-index\.json layout must be by-node-v2/);
  }
});

test("controller requires adjudication report for adjudicator ask-user route", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-adjudication-ask-test-")), ".meta-flow");
  assert.equal(runController(root, ["start", "Ask user from adjudication", "--task-id", "T-adjudication-ask"]).status, 0);
  const taskDir = path.join(root, "tasks", "T-adjudication-ask");

  await writeQuestioningReport(taskDir);
  await writeArtifact(taskDir, "goal-contract.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "goal_contract_drafted"]).status, 0);
  assert.equal(runController(root, ["advance", "--event", "proposal_started"]).status, 0);
  await writeArtifact(taskDir, "proposal.md", "proposal\n");
  assert.equal(runController(root, ["advance", "--event", "proposal_created"]).status, 0);
  await writeArtifact(taskDir, "review-aggregate.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "reviews_aggregated"]).status, 0);

  const status = JSON.parse(runController(root, ["status", "--format", "json"]).stdout);
  assert.deepEqual(status.expected_artifacts_by_event.adjudication_ask_user, ["adjudication-report.json"]);
  const missing = runController(root, ["advance", "--event", "adjudication_ask_user"]);
  assert.notEqual(missing.status, 0);
  assert.match(`${missing.stdout}\n${missing.stderr}`, /missing required artifacts: adjudication-report\.json/);

  await writeArtifact(taskDir, "adjudication-report.json", "{}\n");
  const advance = runController(root, ["advance", "--event", "adjudication_ask_user", "--format", "json"]);
  assert.equal(advance.status, 0, advance.stderr);
  assert.equal(JSON.parse(advance.stdout).phase, "QUESTIONING");
  assert.equal(await exists(path.join(taskDir, "artifacts", "by-node", "06-ADJUDICATION", "done", "adjudication-report.json")), true);
  const validation = runController(root, ["artifacts", "validate", "T-adjudication-ask", "--format", "json"]);
  assert.equal(validation.status, 0, validation.stderr);
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
  assert.equal(await exists(path.join(root, "tasks", "T-release", "artifacts", "by-node", "02-QUESTIONING", "open", `${gate.gate_id}.json`)), true);
  assert.equal(await exists(path.join(root, "tasks", "T-release", "artifacts", "by-node", "02-QUESTIONING", "decided", `${gate.gate_id}.json`)), true);

  const taskDir = path.join(root, "tasks", "T-release");
  const artifactIndexPath = path.join(taskDir, "artifact-index.json");
  const artifactIndex = await readJson(artifactIndexPath);
  const openedEntry = artifactIndex.artifacts.find((entry) => entry.event === "gate_opened" && entry.name === `${gate.gate_id}.json`);
  openedEntry.status = "decided";
  await writeJson(artifactIndexPath, artifactIndex);
  const corruptedValidation = runController(root, ["artifacts", "validate", "T-release", "--format", "json"]);
  assert.notEqual(corruptedValidation.status, 0);
  assert.match(corruptedValidation.stdout, /gate artifact status mismatch/);
});

test("controller requires decided confirmation gates before user acceptance events", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-confirmation-test-")), ".meta-flow");
  assert.equal(runController(root, ["start", "Confirm proposal", "--task-id", "T-confirm"]).status, 0);
  const taskDir = path.join(root, "tasks", "T-confirm");

  await writeQuestioningReport(taskDir);
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
  assert.equal(await exists(path.join(taskDir, "artifacts", "by-node", "09-USER_PROPOSAL_CONFIRMATION", "done", `${gate.gate_id}.json`)), true);
  const artifactValidation = runController(root, ["artifacts", "validate", "--format", "json"]);
  assert.equal(artifactValidation.status, 0, artifactValidation.stderr);
  assert.equal(JSON.parse(artifactValidation.stdout).ok, true);
});

test("controller maintains artifact layout for main execution nodes", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-artifacts-test-")), ".meta-flow");
  assert.equal(runController(root, ["start", "Run full artifact layout", "--task-id", "T-artifacts"]).status, 0);
  const taskDir = path.join(root, "tasks", "T-artifacts");

  await writeQuestioningReport(taskDir);
  await writeArtifact(taskDir, "goal-contract.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "goal_contract_drafted"]).status, 0);
  assert.equal(runController(root, ["advance", "--event", "proposal_started"]).status, 0);
  await writeArtifact(taskDir, "proposal.md", "proposal\n");
  assert.equal(runController(root, ["advance", "--event", "proposal_created"]).status, 0);
  await writeArtifact(taskDir, "review-aggregate.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "reviews_aggregated"]).status, 0);
  const adjudicationStatus = JSON.parse(runController(root, ["status", "--format", "json"]).stdout);
  assert.deepEqual(adjudicationStatus.expected_artifacts_by_event.adjudication_accept, ["adjudication-report.json"]);
  assert.deepEqual(adjudicationStatus.expected_artifacts_by_event.adjudication_revise, ["adjudication-report.json"]);
  await writeArtifact(taskDir, "adjudication-report.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "adjudication_accept"]).status, 0);
  await writeArtifact(taskDir, "proposal-summary.md", "summary\n");
  assert.equal(runController(root, ["advance", "--event", "proposal_summarized"]).status, 0);
  await decideAcceptGate(root, "proposal_confirmation", "Accept proposal?");
  assert.equal(runController(root, ["advance", "--event", "proposal_accepted"]).status, 0);
  assert.equal(runController(root, ["advance", "--event", "planning_started"]).status, 0);
  await writeArtifact(taskDir, "milestone-plan.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "milestone_plan_created"]).status, 0);
  await decideAcceptGate(root, "plan_confirmation", "Accept plan?");
  assert.equal(runController(root, ["advance", "--event", "plan_accepted"]).status, 0);
  await writeArtifact(taskDir, "task-list.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "tasks_decomposed"]).status, 0);
  await writeArtifact(taskDir, "task-spec.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "task_selected"]).status, 0);
  await writeArtifact(taskDir, "task-execution-report.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "task_executed"]).status, 0);
  await writeArtifact(taskDir, "task-verification-report.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "verification_passed"]).status, 0);
  await writeArtifact(taskDir, "direction-evaluation.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "milestone_completed"]).status, 0);
  await writeArtifact(taskDir, "direction-evaluation.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "direction_final"]).status, 0);
  await writeArtifact(taskDir, "final-report.md", "final\n");
  assert.equal(runController(root, ["advance", "--event", "final_summarized"]).status, 0);
  const finalGate = await decideAcceptGate(root, "final_confirmation", "Accept final?");
  assert.equal(runController(root, ["advance", "--event", "final_accepted"]).status, 0);

  const validation = runController(root, ["artifacts", "validate", "T-artifacts", "--format", "json"]);
  assert.equal(validation.status, 0, validation.stderr);
  assert.equal(JSON.parse(validation.stdout).ok, true);

  const expectedPaths = [
    ["13-MILESTONE_SELECTED", "done", "task-list.json"],
    ["14-TASK_DECOMPOSITION", "done", "task-spec.json"],
    ["15-TASK_EXECUTION", "done", "task-execution-report.json"],
    ["16-TASK_VERIFICATION", "done", "task-verification-report.json"],
    ["18-MILESTONE_COMPLETED", "done", "direction-evaluation.json"],
    ["19-DIRECTION_EVALUATION", "done", "direction-evaluation.json"],
    ["23-FINAL_SUMMARY", "done", "final-report.md"],
    ["24-USER_FINAL_CONFIRMATION", "done", `${finalGate.gate_id}.json`],
  ];
  for (const [node, status, fileName] of expectedPaths) {
    assert.equal(await exists(path.join(taskDir, "artifacts", "by-node", node, status, fileName)), true, `${node}/${status}/${fileName}`);
  }

  await fs.unlink(path.join(taskDir, "artifacts", "by-node", "14-TASK_DECOMPOSITION", "done", "task-spec.json"));
  const brokenValidation = runController(root, ["artifacts", "validate", "T-artifacts", "--format", "json"]);
  assert.notEqual(brokenValidation.status, 0);
  assert.match(brokenValidation.stdout, /display artifact missing: artifacts\/by-node\/14-TASK_DECOMPOSITION\/done\/task-spec\.json/);
});

test("controller keeps repeated loop artifacts distinct and records repair node artifacts", async () => {
  const root = path.join(await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-controller-loop-artifacts-test-")), ".meta-flow");
  assert.equal(runController(root, ["start", "Repair loop artifacts", "--task-id", "T-loop"]).status, 0);
  const taskDir = path.join(root, "tasks", "T-loop");

  await writeQuestioningReport(taskDir);
  await writeArtifact(taskDir, "goal-contract.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "goal_contract_drafted"]).status, 0);
  assert.equal(runController(root, ["advance", "--event", "proposal_started"]).status, 0);
  await writeArtifact(taskDir, "proposal.md", "proposal\n");
  assert.equal(runController(root, ["advance", "--event", "proposal_created"]).status, 0);
  await writeArtifact(taskDir, "review-aggregate.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "reviews_aggregated"]).status, 0);
  await writeArtifact(taskDir, "adjudication-report.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "adjudication_accept"]).status, 0);
  await writeArtifact(taskDir, "proposal-summary.md", "summary\n");
  assert.equal(runController(root, ["advance", "--event", "proposal_summarized"]).status, 0);
  await decideAcceptGate(root, "proposal_confirmation", "Accept proposal?");
  assert.equal(runController(root, ["advance", "--event", "proposal_accepted"]).status, 0);
  assert.equal(runController(root, ["advance", "--event", "planning_started"]).status, 0);
  await writeArtifact(taskDir, "milestone-plan.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "milestone_plan_created"]).status, 0);
  await decideAcceptGate(root, "plan_confirmation", "Accept plan?");
  assert.equal(runController(root, ["advance", "--event", "plan_accepted"]).status, 0);
  await writeArtifact(taskDir, "task-list.json", "{}\n");
  assert.equal(runController(root, ["advance", "--event", "tasks_decomposed"]).status, 0);
  await writeArtifact(taskDir, "task-spec.json", "{\"attempt\":0}\n");
  assert.equal(runController(root, ["advance", "--event", "task_selected"]).status, 0);
  await writeArtifact(taskDir, "task-execution-report.json", "{\"attempt\":0}\n");
  assert.equal(runController(root, ["advance", "--event", "task_executed"]).status, 0);

  const verificationStatus = JSON.parse(runController(root, ["status", "--format", "json"]).stdout);
  assert.deepEqual(verificationStatus.expected_artifacts_by_event.verification_passed, ["task-verification-report.json"]);
  assert.deepEqual(verificationStatus.expected_artifacts_by_event.verification_revise, ["task-verification-report.json"]);

  await writeArtifact(taskDir, "task-verification-report.json", "{\"decision\":\"revise\",\"attempt\":1}\n");
  assert.equal(runController(root, ["advance", "--event", "verification_revise"]).status, 0);
  await writeArtifact(taskDir, "task-spec.json", "{\"attempt\":1}\n");
  assert.equal(runController(root, ["advance", "--event", "task_selected"]).status, 0);
  await writeArtifact(taskDir, "task-execution-report.json", "{\"attempt\":1}\n");
  assert.equal(runController(root, ["advance", "--event", "task_executed"]).status, 0);
  await writeArtifact(taskDir, "task-verification-report.json", "{\"decision\":\"revise\",\"attempt\":2}\n");
  assert.equal(runController(root, ["advance", "--event", "verification_revise"]).status, 0);

  const validation = runController(root, ["artifacts", "validate", "T-loop", "--format", "json"]);
  assert.equal(validation.status, 0, validation.stderr);
  assert.equal(JSON.parse(validation.stdout).ok, true);
  const artifactIndex = JSON.parse(await fs.readFile(path.join(taskDir, "artifact-index.json"), "utf8"));
  const verificationEntries = artifactIndex.artifacts.filter((entry) => entry.event === "verification_revise" && entry.name === "task-verification-report.json");
  assert.deepEqual(verificationEntries.map((entry) => entry.display_path), [
    "artifacts/by-node/16-TASK_VERIFICATION/done/task-verification-report.json",
    "artifacts/by-node/16-TASK_VERIFICATION/done/02-verification_revise/task-verification-report.json"
  ]);
  assert.notEqual(
    await fs.readFile(path.join(taskDir, verificationEntries[0].display_path), "utf8"),
    await fs.readFile(path.join(taskDir, verificationEntries[1].display_path), "utf8")
  );
  const repairTaskSpec = artifactIndex.artifacts.find((entry) => entry.event === "task_selected" && entry.node_key === "17-TASK_REPAIR");
  assert.equal(repairTaskSpec?.display_path, "artifacts/by-node/17-TASK_REPAIR/done/task-spec.json");

  const corruptedIndex = JSON.parse(JSON.stringify(artifactIndex));
  const corruptedRepairTaskSpec = corruptedIndex.artifacts.find((entry) => entry.event === "task_selected" && entry.node_key === "17-TASK_REPAIR");
  corruptedRepairTaskSpec.node = "TASK_DECOMPOSITION";
  corruptedRepairTaskSpec.node_key = "14-TASK_DECOMPOSITION";
  corruptedRepairTaskSpec.node_order = 14;
  await writeJson(path.join(taskDir, "artifact-index.json"), corruptedIndex);
  const corruptedValidation = runController(root, ["artifacts", "validate", "T-loop", "--format", "json"]);
  assert.notEqual(corruptedValidation.status, 0);
  assert.match(corruptedValidation.stdout, /TASK_REPAIR/);
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

async function writeArtifact(taskDir, name, content) {
  await fs.writeFile(path.join(taskDir, name), content);
}

async function writeQuestioningReport(taskDir, overrides = {}) {
  await writeJson(path.join(taskDir, "questioning-report.json"), {
    task_id: path.basename(taskDir),
    raw_user_request: "test request",
    known_information: [],
    missing_information: [],
    clarifying_questions: [],
    assumptions_if_user_does_not_answer: [],
    can_continue_without_user_answer: true,
    ...overrides
  });
}

async function writeJson(filePath, data) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(data, null, 2)}\n`);
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, "utf8"));
}

async function decideAcceptGate(root, type, prompt) {
  const open = runController(root, ["gate", "open", "--type", type, "--prompt", prompt, "--format", "json"]);
  assert.equal(open.status, 0, open.stderr);
  const gate = JSON.parse(open.stdout);
  const decide = runController(root, ["gate", "decide", "--gate", gate.gate_id, "--decision", "accept", "--format", "json"]);
  assert.equal(decide.status, 0, decide.stderr);
  return gate;
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}
