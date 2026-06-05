---
name: meta-flow
description: Use this workflow for vague, multi-step, high-reliability tasks that need questioning, proposal, review, adjudication, planning, task-level execution, verification, direction evaluation, and user confirmation before completion.
---

# Meta-Flow

Meta-flow turns a vague request into a controlled Codex workflow with proposal review, user gates, milestone planning, concrete-task execution, verification, and direction checks.

Use it when reliability matters more than speed. Do not use it for small direct edits, one-off answers, simple code explanations, or tasks without observable acceptance criteria.

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

## Proposal Phase Procedure

1. Create a task directory:

   ```bash
   python3 .meta-flow/scripts/new_task.py "<raw request>"
   ```

2. Save the raw request in `raw-request.md`.
3. Invoke `questioner`.
4. If blocking questions exist, ask the user before continuing.
5. Generate `goal-contract.json`.
6. Validate it:

   ```bash
   python3 .meta-flow/scripts/validate_goal_contract.py <task-dir>/goal-contract.json
   ```

7. Invoke `researcher_proposer` to create `proposal.md`.
8. Invoke `product_reviewer`, `technical_reviewer`, `risk_reviewer`, and `verification_reviewer`, preferably in parallel.
9. Run the mechanical aggregator:

   ```bash
   python3 .meta-flow/scripts/aggregate_reviews.py --reviews-dir <task-dir>/reviews --output <task-dir>/review-aggregate.json
   ```

10. Invoke `adjudicator`.
11. Validate `adjudication-report.json`.
12. If the decision is `revise_proposal`, return to `researcher_proposer`.
13. If the decision is `ask_user`, ask the user.
14. If the decision is `accept`, invoke `proposal_summarizer`.
15. Show `proposal-summary.md` to the user and require confirmation.

## Execution Phase Procedure

1. Invoke `planner` to create `milestone-plan.json`.
2. Validate it and ask the user to confirm the plan.
3. Select one current milestone.
4. Invoke `task_decomposer` to create `task-list.json`.
5. Validate the task list.
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
11. Show `final-report.md` and require final user confirmation.
12. Mark `state.json.status = done` and `phase = DONE`.

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

Task directories should use the templates in `.meta-flow/templates/` and keep state in `state.json`. Scripts in `.meta-flow/scripts/` provide initialization, validation, aggregation, and status reporting.
