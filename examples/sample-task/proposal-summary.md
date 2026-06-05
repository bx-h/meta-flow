# Proposal Summary

## What Will Be Done

Add `GET /healthz` as a shallow backend liveness endpoint, with a route test and documentation.

## What Will Not Be Done

No database, cache, queue, or external service readiness checks. No deployment or monitoring configuration changes.

## Why This Approach

A shallow liveness endpoint is deterministic, low-risk, and enough to satisfy the initial user request.

## Main Risks

The repo may already prefer a different health endpoint path. Documentation must prevent operators from assuming this is a deep readiness check.

## User Confirmation Needed

Confirm that a shallow `GET /healthz` endpoint is the intended first version.
