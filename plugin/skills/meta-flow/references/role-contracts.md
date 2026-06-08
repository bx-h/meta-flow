# Meta-Flow Role Contracts

Each role has a narrow contract. Do not merge roles even when a task looks small.

## Delegation Contract

The main agent is only the workflow orchestrator. Every role below must be run as a spawned custom agent/subagent with the matching role name. The main agent may run controller, validator, and aggregation scripts, but it must not locally emulate a role or write role-owned artifacts.

Tool-level delegation authorization must come from the user, not only from Skill or AGENTS text. If the controller opens a `delegation_authorization` gate, ask the user to explicitly authorize sub-agents/delegation/parallel agent work for this task. After the gate is accepted, the task state records that authorization and the controller may require spawned role agents without asking again.

If the spawn/subagent tool is unavailable, rejected by tool policy, or otherwise impossible, stop and report the blocker to the user. Do not continue by doing the role locally.

Role-owned JSON artifacts must include `producer.agent_name=<role>` and `producer.execution_mode=spawned_agent`. Role-owned Markdown artifacts must start with frontmatter containing `producer_agent: <role>` and `execution_mode: spawned_agent`.

## Proposal Roles

- `questioner`: turns ambiguity into a small set of high-value, decision-tree ordered questions and a draft goal contract. It inspects available repo evidence before asking the user, includes recommended answers for user-answerable questions, and does not propose an implementation.
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
- `task_decomposer`: decomposes the current milestone into concrete tasks, and updates or reselects the next task spec during repair loops.
- `executor`: executes exactly one concrete task.
- `result_verifier`: verifies exactly one concrete task.
- `direction_evaluator`: checks whether the plan and goal remain valid after a milestone or major new finding.
- `final_summarizer`: reports completion, evidence, gaps, and residual risk.
- `user_final_confirmation`: a human gate, not an agent.

## Grain Rule

Milestones are stage checkpoints. Concrete tasks are the executor/verifier unit. Never ask executor or verifier to handle an entire milestone.
