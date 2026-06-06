---
name: meta-flow
description: Use this workflow for vague, multi-step, high-reliability tasks that need questioning, proposal, review, adjudication, planning, task-level execution, verification, direction evaluation, and user confirmation before completion.
---

# Meta-Flow

Meta-flow turns a vague request into a controlled Codex workflow with proposal review, user gates, milestone planning, concrete-task execution, verification, and direction checks.

Use it when reliability matters more than speed. Do not use it for small direct edits, one-off answers, simple code explanations, or tasks without observable acceptance criteria.

## Runtime Control

Meta-flow is a long-running workflow. Do not rely on chat memory to know where the workflow is. The runtime controller is the source of truth for the current task, phase, next action, open gate, and allowed transition.

Before acting on an existing meta-flow task, run:

```bash
meta-flow resume --format codex || python3 .meta-flow/scripts/controller.py --root ~/.meta-flow resume --format codex
```

If no active task exists and the user is starting a new meta-flow task, run:

```bash
meta-flow start "<raw request>" --format codex || python3 .meta-flow/scripts/controller.py --root ~/.meta-flow start "<raw request>" --format codex
```

`metaflow` is an equivalent bin alias. Runtime task state defaults to `~/.meta-flow`; use `--root <path>` only for explicit migration, testing, or user-requested alternate roots. If the npm CLI is not installed globally, use local Python fallbacks; installed Skills materialize `.meta-flow/scripts/` to the managed support directory.

Fallback command forms:

- Controller commands: `python3 .meta-flow/scripts/controller.py --root ~/.meta-flow <command> ...`
- `validate goal-contract`: `python3 .meta-flow/scripts/validate_goal_contract.py <path>`
- `validate adjudication`: `python3 .meta-flow/scripts/validate_adjudication.py <path>`
- `validate milestone-plan`: `python3 .meta-flow/scripts/validate_milestone_plan.py <path>`
- `validate task-list`: `python3 .meta-flow/scripts/validate_task_list.py <path>`
- `validate task-verification`: `python3 .meta-flow/scripts/validate_task_verification.py <path>`
- `aggregate-reviews`: `python3 .meta-flow/scripts/aggregate_reviews.py ...`

To stop working on a task without deleting audit artifacts, run:

```bash
meta-flow abandon [task-id] --reason "<why>" || python3 .meta-flow/scripts/controller.py --root ~/.meta-flow abandon [task-id] --reason "<why>"
```

Use `deactivate` only to clear the active-task pointer without changing the task state, for example when switching context. Use `abandon` when the user explicitly does not want to continue the task.

The controller output must drive the next response:

- Tell the user the current user-facing stage.
- Do only the next bounded action.
- Do not directly edit `state.phase`.
- Write required artifacts to the by-node paths returned by the controller, validate them, then call `meta-flow advance`.
- During `QUESTIONING`, bias toward asking the user: if `questioning-report.json` contains any `clarifying_questions`, or says `can_continue_without_user_answer=false`, open a `clarifying_questions` gate and wait for the user before `goal_contract_drafted`.
- If a gate is open, ask for the user's decision and do not continue until the gate is decided.
- If the controller rejects a transition, explain the blocker instead of skipping phases.

## Trigger Conditions

- The request is vague or has unclear boundaries.
- The task crosses files, modules, stages, or external systems.
- The user asks for a proposal before implementation.
- The task needs high-reliability execution and review.
- New findings during execution may change the goal.
- The work needs milestones, concrete tasks, and verification loops.

## Non-Triggers

- The user wants a direct answer.
- The user wants code explained.
- The user specified a small, low-risk edit.
- The task has no executable result.
- The task has no observable verification path.

## State Machine

Proposal phase:

```text
INTAKE
-> QUESTIONING
-> GOAL_CONTRACT_DRAFTED
-> RESEARCH_AND_PROPOSAL
-> PROPOSAL_REVIEW
-> ADJUDICATION
-> PROPOSAL_REWORK
-> PROPOSAL_SUMMARY
-> USER_PROPOSAL_CONFIRMATION
-> PROPOSAL_ACCEPTED
```

Execution phase:

```text
PLANNING
-> USER_PLAN_CONFIRMATION
-> MILESTONE_SELECTED
-> TASK_DECOMPOSITION
-> TASK_EXECUTION
-> TASK_VERIFICATION
-> TASK_REPAIR
-> MILESTONE_COMPLETED
-> DIRECTION_EVALUATION
-> CONTINUE_NEXT_MILESTONE
-> REPLAN
-> GOAL_ADJUSTMENT_REQUIRED
-> FINAL_SUMMARY
-> USER_FINAL_CONFIRMATION
-> DONE
```

Allowed loops:

- `PROPOSAL_REVIEW -> ADJUDICATION -> PROPOSAL_REWORK -> PROPOSAL_REVIEW`
- `USER_PROPOSAL_CONFIRMATION -> ADJUDICATION -> QUESTIONING | RESEARCH_AND_PROPOSAL`
- `TASK_VERIFICATION -> TASK_REPAIR -> TASK_EXECUTION -> TASK_VERIFICATION`
- `DIRECTION_EVALUATION -> GOAL_ADJUSTMENT_REQUIRED -> QUESTIONING | RESEARCH_AND_PROPOSAL`
- `DIRECTION_EVALUATION -> REPLAN -> PLANNING | TASK_DECOMPOSITION`

Stop conditions:

- Proposal review/rework: max 3 rounds.
- Concrete task repair: max 2 rounds per task.
- Direction adjustment: max 2 rounds.
- When a limit is exceeded, generate a blocked report and ask the user for a decision.
- If the user abandons the task, call `meta-flow abandon` so the task state becomes `abandoned`, active resume stops, and artifacts remain available for audit.

## Proposal Phase Procedure

1. Create a task directory:

   ```bash
   meta-flow start "<raw request>" --format codex || python3 .meta-flow/scripts/controller.py --root ~/.meta-flow start "<raw request>" --format codex
   ```

2. Follow the controller `next_action`.
3. Invoke `questioner`.
4. If any meaningful user-answerable uncertainty could change scope, acceptance criteria, risk, UI/UX, dependencies, or implementation direction, put it in `clarifying_questions`, open a `clarifying_questions` gate, and ask the user before continuing. Do this even if the question is not strictly blocking.
5. Only skip the clarification gate when `clarifying_questions` is empty, `can_continue_without_user_answer=true`, and `assumptions_if_user_does_not_answer` covers any remaining low-impact gaps.
6. Generate `questioning-report.json` and `goal-contract.json`.
7. Validate it:

   ```bash
   meta-flow validate goal-contract <path-from-controller> || python3 .meta-flow/scripts/validate_goal_contract.py <path-from-controller>
   ```

8. Advance only through the controller:

   ```bash
   meta-flow advance <task-id> --event goal_contract_drafted --reason "Goal contract drafted." || python3 .meta-flow/scripts/controller.py --root ~/.meta-flow advance <task-id> --event goal_contract_drafted --reason "Goal contract drafted."
   ```

9. Enter the proposal drafting node before writing `proposal.md`:

   ```bash
   meta-flow advance <task-id> --event proposal_started --reason "Proposal research started." || python3 .meta-flow/scripts/controller.py --root ~/.meta-flow advance <task-id> --event proposal_started --reason "Proposal research started."
   ```

10. Invoke `researcher_proposer` to create `proposal.md`.
11. Invoke `product_reviewer`, `technical_reviewer`, `risk_reviewer`, and `verification_reviewer`; parallel review is allowed when the environment supports it.
12. Run the mechanical aggregator:

   ```bash
   meta-flow aggregate-reviews --reviews-dir <task-dir>/reviews --output <path-from-controller> || python3 .meta-flow/scripts/aggregate_reviews.py --reviews-dir <task-dir>/reviews --output <path-from-controller>
   ```

13. Invoke `adjudicator`.
14. Validate `adjudication-report.json`.
15. Route through controller events such as `adjudication_accept`, `adjudication_revise`, or `adjudication_ask_user`.
16. If the decision is `accept`, invoke `proposal_summarizer`.
17. Show `proposal-summary.md` to the user, open a `proposal_confirmation` gate, and only after an `accept` gate decision call `proposal_accepted`.

## Execution Phase Procedure

1. Invoke `planner` to create `milestone-plan.json`.
2. Validate it, open a `plan_confirmation` gate, and only after an `accept` gate decision call `plan_accepted`.
3. Select one current milestone.
4. Invoke `task_decomposer` to create `task-list.json`.
5. Validate the task list, then create `task-spec.json` for the selected concrete task before `task_selected`.
6. Process concrete tasks by dependency order.
7. For each concrete task:
   - Invoke `executor` for exactly one concrete task.
   - Invoke `result_verifier` for exactly that concrete task.
   - On `revise`, return to executor for repair, max 2 attempts.
   - On `block`, stop the milestone and route to adjudicator or user.
8. After all concrete tasks in a milestone pass, invoke `direction_evaluator`.
9. Route from `direction-evaluation.json`:
   - `continue`: select next milestone.
   - `replan`: return to `planner` or `task_decomposer`.
   - `adjust_goal`: ask user to confirm a contract patch, then return to proposal phase.
   - `ask_user`: ask user before continuing.
   - `abort`: generate blocked/final report as appropriate.
10. After all milestones complete, invoke `final_summarizer`.
11. Show `final-report.md`, open a `final_confirmation` gate, and require final user confirmation.
12. Mark completion through the controller with `final_accepted` only after an `accept` gate decision; do not edit `state.json` directly.

## Role Boundaries

- User confirmation gates are not agents.
- Reviewers review; they do not decide the route.
- Adjudicator decides the route; it does not write code or edit proposals.
- Planner creates milestones; it does not create concrete task specs.
- Task decomposer creates concrete tasks; it does not execute or verify.
- Executor changes only files allowed by the current task spec.
- Result verifier verifies one concrete task and does not fix code.
- Direction evaluator checks whether the goal, proposal, or plan is still valid.

## Reference Files

- `references/role-contracts.md`
- `references/review-rubric.md`
- `references/adjudication-policy.md`
- `references/execution-policy.md`
- `references/direction-evaluation-policy.md`

## Required Artifacts

Task runtime state defaults to `~/.meta-flow/active-task.json`, `~/.meta-flow/task-index.json`, and `~/.meta-flow/tasks/<task-id>/`. Per-task state keeps `state.json`, `events.ndjson`, `artifact-index.json`, business artifacts under `artifacts/by-node/<order>-<phase>/<status>/`, and optional `gates/*.json`. The by-node path is both the human-readable location and the machine contract path. When a node/status emits the same artifact more than once, the first artifact keeps the direct by-node filename and later attempts are stored in numbered subdirectories under that node/status.

After a phase advance, run artifact validation when the change is non-trivial:

```bash
meta-flow artifacts validate <task-id> || python3 .meta-flow/scripts/controller.py --root ~/.meta-flow artifacts validate <task-id>
```
