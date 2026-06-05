#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from _common import fail, load_json, ok, require_dict, require_non_empty_string


ALLOWED_NEXT_PHASES = {
    "accept": {"PROPOSAL_SUMMARY", "USER_PROPOSAL_CONFIRMATION", "PROPOSAL_ACCEPTED"},
    "revise_proposal": {"PROPOSAL_REWORK", "RESEARCH_AND_PROPOSAL", "PROPOSAL_REVIEW"},
    "ask_user": {"QUESTIONING", "USER_PROPOSAL_CONFIRMATION", "USER_PLAN_CONFIRMATION", "USER_FINAL_CONFIRMATION", "GOAL_ADJUSTMENT_REQUIRED"},
    "adjust_goal": {"GOAL_ADJUSTMENT_REQUIRED", "QUESTIONING", "RESEARCH_AND_PROPOSAL"},
    "replan": {"REPLAN", "PLANNING", "TASK_DECOMPOSITION"},
    "block": {"BLOCKED", "ADJUDICATION"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a meta-flow adjudication-report.json file.")
    parser.add_argument("path", type=Path, nargs="?", default=Path("adjudication-report.json"))
    return parser.parse_args()


def main() -> int:
    data = require_dict(load_json(parse_args().path), "adjudication report", errors := [])
    require_non_empty_string(data, "task_id", errors)
    require_non_empty_string(data, "source", errors)
    require_non_empty_string(data, "rationale", errors)
    require_non_empty_string(data, "instructions_for_next_agent", errors)
    decision = data.get("decision")
    next_phase = data.get("next_phase")
    if decision not in ALLOWED_NEXT_PHASES:
        errors.append(f"decision must be one of {sorted(ALLOWED_NEXT_PHASES)}")
    elif next_phase not in ALLOWED_NEXT_PHASES[decision]:
        errors.append(f"next_phase {next_phase!r} is not consistent with decision {decision!r}")
    if not isinstance(data.get("requires_user_confirmation"), bool):
        errors.append("requires_user_confirmation must be a boolean")
    if errors:
        fail(errors)
    ok(f"OK: adjudication valid ({decision} -> {next_phase}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
