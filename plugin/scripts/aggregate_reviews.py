#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from _common import fail, load_json, write_json


VALID_DECISIONS = {"pass", "revise", "block"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mechanically aggregate meta-flow reviewer reports.")
    parser.add_argument("--reviews-dir", type=Path, default=Path("reviews"), help="Directory containing reviewer *.json files.")
    parser.add_argument("--output", type=Path, default=Path("review-aggregate.json"), help="Output aggregate JSON path.")
    parser.add_argument("--task-id", help="Task id. If omitted, inferred from first reviewer report when possible.")
    return parser.parse_args()


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def main() -> int:
    args = parse_args()
    paths = sorted(args.reviews_dir.glob("*.json"))
    if not paths:
        fail([f"No reviewer JSON files found in {args.reviews_dir}"])

    errors: list[str] = []
    reviewers: list[dict[str, object]] = []
    blocking: list[str] = []
    suggested: list[str] = []
    missing: list[str] = []
    task_id = args.task_id
    decisions: list[str] = []

    for path in paths:
        report = load_json(path)
        if not isinstance(report, dict):
            errors.append(f"{path} must contain an object")
            continue
        reviewer = report.get("reviewer")
        decision = report.get("decision")
        confidence = report.get("confidence")
        if not isinstance(reviewer, str) or not reviewer.strip():
            errors.append(f"{path}: reviewer must be a non-empty string")
        if decision not in VALID_DECISIONS:
            errors.append(f"{path}: decision must be one of {sorted(VALID_DECISIONS)}")
        else:
            decisions.append(decision)
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            errors.append(f"{path}: confidence must be a number between 0 and 1")
        for key, sink in (
            ("blocking_issues", blocking),
            ("suggested_changes", suggested),
            ("missing_information", missing),
        ):
            value = report.get(key, [])
            if not isinstance(value, list):
                errors.append(f"{path}: {key} must be a list")
            else:
                sink.extend(str(item) for item in value)
        if not task_id and isinstance(report.get("task_id"), str):
            task_id = str(report["task_id"])
        reviewers.append({"reviewer": reviewer, "decision": decision, "confidence": confidence})

    if errors:
        fail(errors)

    if "block" in decisions:
        result = "block"
    elif "revise" in decisions:
        result = "revise"
    else:
        result = "pass"

    aggregate = {
        "task_id": task_id or "unknown",
        "overall_mechanical_result": result,
        "reviewers": reviewers,
        "all_blocking_issues": unique(blocking),
        "all_suggested_changes": unique(suggested),
        "all_missing_information": unique(missing),
    }
    write_json(args.output, aggregate)
    print(f"OK: wrote {args.output} with mechanical_result={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
