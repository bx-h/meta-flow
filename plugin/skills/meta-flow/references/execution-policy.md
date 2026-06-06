# Execution Policy

Execution is concrete-task scoped.

## Planner

The planner writes milestone-level checkpoints with objective, scope, out-of-scope, acceptance checks, expected outputs, risk, and status. It does not create implementation steps.

## Task Decomposer

The task decomposer writes concrete tasks for one milestone. Each task must be independently executable and independently verifiable.

## Executor

The executor:

- handles one concrete task at a time
- changes only `allowed_files`
- avoids broad refactors
- records changed files, commands, evidence, discovered facts, and risk flags
- marks blocked instead of silently expanding scope

## Result Verifier

The verifier:

- checks one concrete task against `task-spec.json`
- may run tests, lint, typecheck, scripts, or diff review
- outputs pass/revise/block
- gives minimal repair instructions on failure
- does not modify implementation files

## Repair Limit

Each concrete task has at most 2 repair attempts. On verifier `revise`, the task decomposer updates or reselects exactly one task spec from the verifier's minimal repair instructions, then the executor runs that bounded spec. After 2 repair attempts, mark blocked and route to adjudicator or user.
