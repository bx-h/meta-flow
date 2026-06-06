#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from _common import fail, load_json, ok, require_dict, require_list, require_non_empty_string


VALID_METHODS = {"manual", "test", "lint", "typecheck", "script", "review", "user_confirmation"}
VALID_RISKS = {"low", "medium", "high"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a meta-flow goal-contract.json file.")
    parser.add_argument("path", type=Path, nargs="?", default=Path("goal-contract.json"))
    return parser.parse_args()


def main() -> int:
    data = require_dict(load_json(parse_args().path), "goal contract", errors := [])
    require_non_empty_string(data, "refined_goal", errors)
    require_non_empty_string(data, "problem_boundary", errors)
    require_non_empty_string(data, "success_definition", errors)

    non_goals = require_list(data.get("non_goals"), "non_goals", errors)
    constraints = require_list(data.get("constraints"), "constraints", errors)
    criteria = require_list(data.get("acceptance_criteria"), "acceptance_criteria", errors)
    if not criteria:
        errors.append("acceptance_criteria must not be empty")
    for idx, item in enumerate(criteria, start=1):
        item_obj = require_dict(item, f"acceptance_criteria[{idx}]", errors)
        require_non_empty_string(item_obj, "id", errors)
        require_non_empty_string(item_obj, "criterion", errors)
        require_non_empty_string(item_obj, "evidence_required", errors)
        method = item_obj.get("verification_method")
        if method not in VALID_METHODS:
            errors.append(f"acceptance_criteria[{idx}].verification_method must be one of {sorted(VALID_METHODS)}")

    if data.get("risk_level") not in VALID_RISKS:
        errors.append(f"risk_level must be one of {sorted(VALID_RISKS)}")
    if "non_goals" not in data:
        errors.append("non_goals key must exist")
    if "constraints" not in data:
        errors.append("constraints key must exist")
    if not isinstance(data.get("requires_user_confirmation"), bool):
        errors.append("requires_user_confirmation must be a boolean")

    if errors:
        fail(errors)
    ok(f"OK: goal contract valid ({len(non_goals)} non-goals, {len(constraints)} constraints, {len(criteria)} criteria).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
