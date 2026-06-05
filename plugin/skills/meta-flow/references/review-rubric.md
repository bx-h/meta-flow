# Review Rubric

Reviewer output must be a `reviewer-report.json` object with:

- `decision`: `pass`, `revise`, or `block`
- `confidence`: number from 0 to 1
- concrete evidence references
- blocking issues, suggested changes, and missing information

## Product Review

Pass only when the proposal directly addresses the refined goal, respects non-goals, and preserves user value. Revise if scope or value is blurry. Block if it solves the wrong problem.

## Technical Review

Pass only when the implementation route is feasible, simple enough, and compatible with the local architecture. Revise if complexity is avoidable. Block if the route is structurally unsafe or impossible under constraints.

## Risk Review

Pass only when safety, data, permission, destructive action, rollback, and operational risks are identified and controlled. Block high-risk work that lacks mitigation.

## Verification Review

Pass only when every acceptance criterion can be observed, repeated, and evidenced. Revise vague checks. Block when success cannot be verified.

## Duplication Rule

Reviewers may read prior reviewer reports to avoid repeating the same issue. They should cite agreement instead of restating generic feedback.
