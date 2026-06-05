from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


VALID_PHASES = {
    "INTAKE",
    "QUESTIONING",
    "GOAL_CONTRACT_DRAFTED",
    "RESEARCH_AND_PROPOSAL",
    "PROPOSAL_REVIEW",
    "ADJUDICATION",
    "PROPOSAL_REWORK",
    "PROPOSAL_SUMMARY",
    "USER_PROPOSAL_CONFIRMATION",
    "PROPOSAL_ACCEPTED",
    "PLANNING",
    "USER_PLAN_CONFIRMATION",
    "MILESTONE_SELECTED",
    "TASK_DECOMPOSITION",
    "TASK_EXECUTION",
    "TASK_VERIFICATION",
    "TASK_REPAIR",
    "MILESTONE_COMPLETED",
    "DIRECTION_EVALUATION",
    "CONTINUE_NEXT_MILESTONE",
    "REPLAN",
    "GOAL_ADJUSTMENT_REQUIRED",
    "FINAL_SUMMARY",
    "USER_FINAL_CONFIRMATION",
    "DONE",
    "BLOCKED",
}


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        fail([f"Missing file: {path}"])
    except json.JSONDecodeError as exc:
        fail([f"Invalid JSON in {path}: {exc}"])


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)


def warn(warnings: list[str]) -> None:
    for item in warnings:
        print(f"WARNING: {item}", file=sys.stderr)


def require_dict(value: Any, name: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return {}
    return value


def require_list(value: Any, name: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{name} must be a list")
        return []
    return value


def require_non_empty_string(obj: dict[str, Any], key: str, errors: list[str]) -> None:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{key} must be a non-empty string")


def require_key(obj: dict[str, Any], key: str, errors: list[str]) -> Any:
    if key not in obj:
        errors.append(f"Missing required key: {key}")
        return None
    return obj[key]


def ok(message: str) -> None:
    print(message)
