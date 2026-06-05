# Adjudication Policy

Adjudication is not mechanical aggregation. `aggregate_reviews.py` only computes a mechanical result. The adjudicator decides the route.

## Inputs

- reviewer reports
- review aggregate
- user feedback
- direction evaluator output
- current state and round counters

## Decisions

- `accept`: proposal can move to user-facing summary.
- `revise_proposal`: proposal needs specific rework.
- `ask_user`: user input is required.
- `adjust_goal`: goal contract needs a user-confirmed patch.
- `replan`: execution plan or task decomposition needs changes.
- `block`: the workflow cannot continue safely or meaningfully.

## Conflict Handling

A reviewer `block` does not automatically stop the workflow. The adjudicator must decide whether the block is valid, whether it can be mitigated, and whether the next route is user input, goal adjustment, proposal rework, or blocked state.

## Round Limits

- Proposal rework over 3 rounds: block and ask user.
- Direction adjustment over 2 rounds: block and ask user.
- Task repair over 2 rounds: block the concrete task and escalate.
