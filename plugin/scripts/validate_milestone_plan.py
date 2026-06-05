#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from _common import fail, load_json, ok, require_dict, require_list, require_non_empty_string, warn


VALID_RISKS = {"low", "medium", "high"}
VALID_STATUSES = {"pending", "in_progress", "done", "blocked"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a meta-flow milestone-plan.json file.")
    parser.add_argument("path", type=Path, nargs="?", default=Path("milestone-plan.json"))
    return parser.parse_args()


def main() -> int:
    data = require_dict(load_json(parse_args().path), "milestone plan", errors := [])
    milestones = require_list(data.get("milestones"), "milestones", errors)
    if not milestones:
        errors.append("milestones must not be empty")
    warnings: list[str] = []
    for idx, milestone in enumerate(milestones, start=1):
        item = require_dict(milestone, f"milestones[{idx}]", errors)
        for key in ("id", "objective"):
            require_non_empty_string(item, key, errors)
        for key in ("scope", "acceptance_checks"):
            value = require_list(item.get(key), f"milestones[{idx}].{key}", errors)
            if key == "acceptance_checks" and not value:
                errors.append(f"milestones[{idx}].acceptance_checks must not be empty")
            if key == "scope" and len(value) > 7:
                warnings.append(f"milestone {item.get('id', idx)} has scope larger than 7 items")
        if item.get("risk") not in VALID_RISKS:
            errors.append(f"milestones[{idx}].risk must be one of {sorted(VALID_RISKS)}")
        if item.get("status") not in VALID_STATUSES:
            errors.append(f"milestones[{idx}].status must be one of {sorted(VALID_STATUSES)}")
    if warnings:
        warn(warnings)
    if errors:
        fail(errors)
    ok(f"OK: milestone plan valid ({len(milestones)} milestones).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
