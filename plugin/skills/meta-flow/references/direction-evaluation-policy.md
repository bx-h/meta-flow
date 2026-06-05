# Direction Evaluation Policy

Direction evaluation runs after every completed milestone and whenever a verifier reports a major new finding.

## Questions

- Does the original goal still hold?
- Did execution disprove a proposal assumption?
- Did the milestone expose a new boundary?
- Are the acceptance criteria still valid?
- Is user input now required?
- Would continuing create wrong results or wasted effort?

## Decisions

- `continue`: proceed to the next milestone.
- `replan`: plan or task decomposition needs changes, but the goal is still valid.
- `adjust_goal`: goal contract needs a user-confirmed patch.
- `ask_user`: user decision is required before routing.
- `abort`: continuing is unsafe or meaningless.

## Contract Patch Rule

The direction evaluator may propose a contract patch. It must not modify `goal-contract.json` directly. User confirmation is required before goal changes take effect.
