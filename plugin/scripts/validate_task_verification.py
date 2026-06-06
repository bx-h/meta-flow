#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from _common import fail, load_json, ok, require_dict, require_list, require_non_empty_string


VALID_DECISIONS = {"pass", "revise", "block"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a meta-flow task-verification-report.json file.")
    parser.add_argument("path", type=Path, nargs="?", default=Path("task-verification-report.json"))
    return parser.parse_args()


def main() -> int:
    data = require_dict(load_json(parse_args().path), "task verification report", errors := [])
    for key in ("task_id", "milestone_id", "concrete_task_id"):
        require_non_empty_string(data, key, errors)
    decision = data.get("decision")
    if decision not in VALID_DECISIONS:
        errors.append(f"decision must be one of {sorted(VALID_DECISIONS)}")
    failed = require_list(data.get("failed_checks"), "failed_checks", errors)
    new_findings = require_list(data.get("new_findings"), "new_findings", errors)
    require_list(data.get("checks_run"), "checks_run", errors)
    require_list(data.get("passed_checks"), "passed_checks", errors)
    require_list(data.get("evidence_refs"), "evidence_refs", errors)

    repair = data.get("minimal_repair_instructions", "")
    block_reason = data.get("block_reason", "")
    if decision == "pass" and failed:
        errors.append("failed_checks must be empty when decision is pass")
    if decision in {"revise", "block"} and not str(repair).strip() and not str(block_reason).strip():
        errors.append("revise/block decisions require minimal_repair_instructions or block_reason")
    if data.get("should_trigger_direction_evaluation") is True and not new_findings:
        errors.append("new_findings must not be empty when should_trigger_direction_evaluation is true")
    if not isinstance(data.get("should_trigger_direction_evaluation"), bool):
        errors.append("should_trigger_direction_evaluation must be a boolean")
    if errors:
        fail(errors)
    ok(f"OK: task verification valid ({decision}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
