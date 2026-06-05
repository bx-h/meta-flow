#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from _common import fail, load_json, ok, require_dict, require_list, require_non_empty_string, warn


VALID_RISKS = {"low", "medium", "high"}
VALID_STATUSES = {"pending", "in_progress", "passed", "failed", "blocked"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a meta-flow task-list.json file.")
    parser.add_argument("path", type=Path, nargs="?", default=Path("task-list.json"))
    return parser.parse_args()


def main() -> int:
    data = require_dict(load_json(parse_args().path), "task list", errors := [])
    require_non_empty_string(data, "task_id", errors)
    require_non_empty_string(data, "milestone_id", errors)
    tasks = require_list(data.get("tasks"), "tasks", errors)
    if not tasks:
        errors.append("tasks must not be empty")
    warnings: list[str] = []
    for idx, task in enumerate(tasks, start=1):
        item = require_dict(task, f"tasks[{idx}]", errors)
        for key in ("id", "objective"):
            require_non_empty_string(item, key, errors)
        for key in ("expected_outputs", "acceptance_checks", "dependencies"):
            value = require_list(item.get(key), f"tasks[{idx}].{key}", errors)
            if key in {"expected_outputs", "acceptance_checks"} and not value:
                errors.append(f"tasks[{idx}].{key} must not be empty")
        allowed_files = require_list(item.get("allowed_files"), f"tasks[{idx}].allowed_files", errors)
        require_list(item.get("forbidden_files"), f"tasks[{idx}].forbidden_files", errors)
        if not allowed_files:
            warnings.append(f"task {item.get('id', idx)} has empty allowed_files")
        if len(allowed_files) > 10:
            warnings.append(f"task {item.get('id', idx)} may be too broad: more than 10 allowed files")
        if len(item.get("expected_outputs", [])) > 6:
            warnings.append(f"task {item.get('id', idx)} may be too broad: more than 6 expected outputs")
        if item.get("risk") not in VALID_RISKS:
            errors.append(f"tasks[{idx}].risk must be one of {sorted(VALID_RISKS)}")
        if item.get("status") not in VALID_STATUSES:
            errors.append(f"tasks[{idx}].status must be one of {sorted(VALID_STATUSES)}")
        if not isinstance(item.get("repair_attempts", 0), int):
            errors.append(f"tasks[{idx}].repair_attempts must be an integer")
    if warnings:
        warn(warnings)
    if errors:
        fail(errors)
    ok(f"OK: task list valid ({len(tasks)} concrete tasks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
