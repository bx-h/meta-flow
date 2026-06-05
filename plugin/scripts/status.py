#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from _common import load_json


ROOT = Path(os.environ.get("META_FLOW_ROOT", Path.cwd() / ".meta-flow"))


NEXT_ACTION_BY_PHASE = {
    "INTAKE": "Run questioner and create questioning-report.json.",
    "QUESTIONING": "Resolve blocking questions or record assumptions.",
    "GOAL_CONTRACT_DRAFTED": "Validate goal-contract.json, then run researcher_proposer.",
    "RESEARCH_AND_PROPOSAL": "Produce proposal.md and send it to reviewers.",
    "PROPOSAL_REVIEW": "Run aggregate_reviews.py, then invoke adjudicator.",
    "ADJUDICATION": "Route according to adjudication-report.json.",
    "PROPOSAL_REWORK": "Rework proposal, respecting proposal_review_round limit.",
    "PROPOSAL_SUMMARY": "Summarize proposal for user confirmation.",
    "USER_PROPOSAL_CONFIRMATION": "Ask user to accept or reject the proposal.",
    "PROPOSAL_ACCEPTED": "Run planner.",
    "PLANNING": "Create milestone-plan.json.",
    "USER_PLAN_CONFIRMATION": "Ask user to confirm milestone-plan.json.",
    "MILESTONE_SELECTED": "Run task_decomposer for current milestone.",
    "TASK_DECOMPOSITION": "Validate task-list.json and select the next concrete task.",
    "TASK_EXECUTION": "Run executor for current concrete task.",
    "TASK_VERIFICATION": "Run result_verifier for current concrete task.",
    "TASK_REPAIR": "Return to executor with minimal repair instructions.",
    "MILESTONE_COMPLETED": "Run direction_evaluator.",
    "DIRECTION_EVALUATION": "Route based on direction-evaluation.json.",
    "CONTINUE_NEXT_MILESTONE": "Select the next milestone.",
    "REPLAN": "Return to planner or task_decomposer.",
    "GOAL_ADJUSTMENT_REQUIRED": "Ask user to confirm contract patch before returning to proposal phase.",
    "FINAL_SUMMARY": "Run final_summarizer.",
    "USER_FINAL_CONFIRMATION": "Ask user to confirm final result.",
    "DONE": "No next action.",
    "BLOCKED": "Ask user for a decision or unblock input.",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print current meta-flow task status.")
    parser.add_argument("task", type=Path, help="Task directory path, or task id under .meta-flow/tasks.")
    return parser.parse_args()


def resolve_task_dir(value: Path) -> Path:
    if value.exists():
        return value
    candidate = ROOT / "tasks" / str(value)
    if candidate.exists():
        return candidate
    raise SystemExit(f"Task directory not found: {value}")


def collect_blocked_issues(task_dir: Path) -> list[str]:
    issues: list[str] = []
    for path in task_dir.rglob("*.json"):
        data = load_json(path)
        if isinstance(data, dict):
            if data.get("status") == "blocked" and isinstance(data.get("summary"), str):
                issues.append(f"{path.name}: {data['summary']}")
            if data.get("decision") == "block":
                reason = data.get("minimal_repair_instructions") or data.get("block_reason") or data.get("rationale")
                if reason:
                    issues.append(f"{path.name}: {reason}")
    return issues


def main() -> int:
    task_dir = resolve_task_dir(parse_args().task)
    state = load_json(task_dir / "state.json")
    phase = state.get("phase", "UNKNOWN")
    print(f"task: {state.get('task_id', task_dir.name)}")
    print(f"status: {state.get('status', 'unknown')}")
    print(f"current phase: {phase}")
    print(f"current milestone: {state.get('current_milestone_id')}")
    print(f"current task: {state.get('current_task_id')}")
    print(f"last route decision: {state.get('last_route_decision', '')}")
    blocked = collect_blocked_issues(task_dir)
    print("blocked issues:")
    if blocked:
        for issue in blocked:
            print(f"- {issue}")
    else:
        print("- none")
    print(f"next recommended action: {NEXT_ACTION_BY_PHASE.get(phase, 'Inspect state.json and route manually.')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
