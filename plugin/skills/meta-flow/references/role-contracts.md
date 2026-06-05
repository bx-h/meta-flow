# Meta-Flow Role Contracts

Each role has a narrow contract. Do not merge roles even when a task looks small.

## Proposal Roles

- `questioner`: turns ambiguity into a small set of high-value questions and a draft goal contract. It does not propose an implementation.
- `researcher_proposer`: researches and writes `proposal.md`. It does not change the goal contract.
- `product_reviewer`: checks whether the proposal solves the user's real goal.
- `technical_reviewer`: checks feasibility, complexity, dependencies, and maintainability.
- `risk_reviewer`: checks safety, data, permission, destructive, rollback, and operational risks.
- `verification_reviewer`: checks whether acceptance criteria are observable and repeatable.
- `adjudicator`: resolves reviewer conflicts and routes the workflow. It does not write code or edit the proposal directly.
- `proposal_summarizer`: compresses accepted proposal material for user confirmation without adding new claims.
- `user_confirmation`: a human gate, not an agent.

## Execution Roles

- `planner`: creates milestone-level plan only.
- `task_decomposer`: decomposes the current milestone into concrete tasks.
- `executor`: executes exactly one concrete task.
- `result_verifier`: verifies exactly one concrete task.
- `direction_evaluator`: checks whether the plan and goal remain valid after a milestone or major new finding.
- `final_summarizer`: reports completion, evidence, gaps, and residual risk.
- `user_final_confirmation`: a human gate, not an agent.

## Grain Rule

Milestones are stage checkpoints. Concrete tasks are the executor/verifier unit. Never ask executor or verifier to handle an entire milestone.
