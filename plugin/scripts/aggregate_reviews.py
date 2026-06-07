#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from _common import fail, load_json, write_json


VALID_DECISIONS = {"pass", "revise", "block"}
EXPECTED_REVIEWERS = {"product_reviewer", "technical_reviewer", "risk_reviewer", "verification_reviewer"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mechanically aggregate meta-flow reviewer reports.")
    parser.add_argument("--reviews-dir", type=Path, default=Path("reviews"), help="Directory containing reviewer *.json files.")
    parser.add_argument("--output", type=Path, default=Path("review-aggregate.json"), help="Output aggregate JSON path.")
    parser.add_argument("--task-id", help="Task id. If omitted, inferred from first reviewer report when possible.")
    return parser.parse_args()


def stable_json_key(item: Any) -> str:
    try:
        return json.dumps(item, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return repr(item)


def unique(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for item in items:
        key = stable_json_key(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def collect_review_items(
    report: dict[str, Any],
    key: str,
    reviewer: str | None,
    values_sink: list[Any],
    sourced_sink: list[dict[str, Any]],
    errors: list[str],
    path: Path,
) -> None:
    value = report.get(key, [])
    if not isinstance(value, list):
        errors.append(f"{path}: {key} must be a list")
        return
    for item in value:
        values_sink.append(item)
        sourced_sink.append({
            "reviewer": reviewer or "unknown",
            "value": item,
        })


def main() -> int:
    args = parse_args()
    paths = sorted(args.reviews_dir.glob("*.json"))
    if not paths:
        fail([f"No reviewer JSON files found in {args.reviews_dir}"])

    errors: list[str] = []
    reviewers: list[dict[str, Any]] = []
    blocking: list[Any] = []
    suggested: list[Any] = []
    missing: list[Any] = []
    blocking_by_reviewer: list[dict[str, Any]] = []
    suggested_by_reviewer: list[dict[str, Any]] = []
    missing_by_reviewer: list[dict[str, Any]] = []
    task_id = args.task_id
    decisions: list[str] = []
    seen_reviewers: list[str] = []

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
            reviewer_name = None
        else:
            reviewer_name = reviewer
            seen_reviewers.append(reviewer)
            if reviewer not in EXPECTED_REVIEWERS:
                errors.append(f"{path}: reviewer must be one of {sorted(EXPECTED_REVIEWERS)}")
        if decision not in VALID_DECISIONS:
            errors.append(f"{path}: decision must be one of {sorted(VALID_DECISIONS)}")
        else:
            decisions.append(decision)
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            errors.append(f"{path}: confidence must be a number between 0 and 1")
        producer = report.get("producer")
        if not isinstance(producer, dict):
            errors.append(f"{path}: producer must be an object")
        else:
            if producer.get("agent_name") != reviewer:
                errors.append(f"{path}: producer.agent_name must match reviewer")
            if producer.get("execution_mode") != "spawned_agent":
                errors.append(f"{path}: producer.execution_mode must be spawned_agent")
        for key, values_sink, sourced_sink in (
            ("blocking_issues", blocking, blocking_by_reviewer),
            ("suggested_changes", suggested, suggested_by_reviewer),
            ("missing_information", missing, missing_by_reviewer),
        ):
            collect_review_items(report, key, reviewer_name, values_sink, sourced_sink, errors, path)
        if not task_id and isinstance(report.get("task_id"), str):
            task_id = str(report["task_id"])
        reviewers.append({"reviewer": reviewer, "decision": decision, "confidence": confidence, "producer": producer})

    missing_reviewers = sorted(EXPECTED_REVIEWERS - set(seen_reviewers))
    unexpected_duplicates = sorted({name for name in seen_reviewers if seen_reviewers.count(name) > 1})
    if missing_reviewers:
        errors.append(f"missing reviewer reports: {', '.join(missing_reviewers)}")
    if unexpected_duplicates:
        errors.append(f"duplicate reviewer reports: {', '.join(unexpected_duplicates)}")

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
        "blocking_issues_by_reviewer": unique(blocking_by_reviewer),
        "suggested_changes_by_reviewer": unique(suggested_by_reviewer),
        "missing_information_by_reviewer": unique(missing_by_reviewer),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, aggregate)
    print(f"OK: wrote {args.output} with mechanical_result={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
