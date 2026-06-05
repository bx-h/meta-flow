# Proposal

## Goal

Add a shallow backend liveness endpoint with tests and documentation.

## Recommended Approach

Implement `GET /healthz` using the existing route registration pattern. The endpoint returns HTTP 200 and a JSON body such as `{"status":"ok"}`. Add a focused route test and document that this is a shallow liveness check, not a dependency readiness check.

This keeps behavior deterministic and avoids coupling deploy health to external systems.

## Alternatives

- Deep readiness endpoint: useful later, but higher risk because dependency outages may affect rollout behavior.
- Framework middleware/plugin: unnecessary unless the repo already standardizes on one.
- Reuse an existing status endpoint: possible, but only if it already has the same semantics.

## Risks

- Existing route conventions may prefer `/health` over `/healthz`.
- Tests may need framework-specific fixtures.
- Operators may expect dependency checks; documentation must state the shallow scope.

## Verification

- Run the backend route test.
- Review docs for endpoint path, response shape, and non-goals.
- Confirm dependency files are unchanged.
