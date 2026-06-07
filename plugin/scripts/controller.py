#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from _common import fail, load_json, write_json


ROOT = Path(os.environ.get("META_FLOW_ROOT", Path.home() / ".meta-flow"))
WORKFLOW_VERSION = "1"
ARTIFACT_INDEX_LAYOUT = "by-node-v2"
LEGACY_ARTIFACT_INDEX_LAYOUTS = {"by-node-v1"}

PHASE_SEQUENCE = [
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
    "ABANDONED",
]

PHASE_ORDER = {phase: index + 1 for index, phase in enumerate(PHASE_SEQUENCE)}


PHASE_LABELS = {
    "INTAKE": "任务已创建",
    "QUESTIONING": "目标澄清",
    "GOAL_CONTRACT_DRAFTED": "目标契约已起草",
    "RESEARCH_AND_PROPOSAL": "方案调研与起草",
    "PROPOSAL_REVIEW": "方案评审",
    "ADJUDICATION": "评审裁决",
    "PROPOSAL_REWORK": "方案返工",
    "PROPOSAL_SUMMARY": "方案确认摘要",
    "USER_PROPOSAL_CONFIRMATION": "等待方案确认",
    "PROPOSAL_ACCEPTED": "方案已确认",
    "PLANNING": "里程碑规划",
    "USER_PLAN_CONFIRMATION": "等待计划确认",
    "MILESTONE_SELECTED": "里程碑已选择",
    "TASK_DECOMPOSITION": "具体任务拆解",
    "TASK_EXECUTION": "具体任务执行",
    "TASK_VERIFICATION": "具体任务验收",
    "TASK_REPAIR": "具体任务修复",
    "MILESTONE_COMPLETED": "里程碑完成",
    "DIRECTION_EVALUATION": "方向复盘",
    "CONTINUE_NEXT_MILESTONE": "准备进入下一个里程碑",
    "REPLAN": "重新规划",
    "GOAL_ADJUSTMENT_REQUIRED": "等待目标调整确认",
    "FINAL_SUMMARY": "最终总结",
    "USER_FINAL_CONFIRMATION": "等待最终确认",
    "DONE": "已完成",
    "BLOCKED": "已阻塞",
    "ABANDONED": "已放弃",
}

NEXT_ACTION_BY_PHASE = {
    "INTAKE": {
        "kind": "role",
        "role": "questioner",
        "instruction": "Enter goal clarification before drafting the goal contract.",
        "completion_event": "start_questioning",
    },
    "QUESTIONING": {
        "kind": "role",
        "role": "questioner",
        "instruction": "Bias toward asking the user. If meaningful clarifying questions remain, open a clarifying_questions gate; only continue without a gate when questioning-report.json has no clarifying_questions and explicitly records safe assumptions.",
        "completion_event": "goal_contract_drafted",
    },
    "GOAL_CONTRACT_DRAFTED": {
        "kind": "role",
        "role": "researcher_proposer",
        "instruction": "Validate goal-contract.json, then enter proposal research and drafting.",
        "completion_event": "proposal_started",
    },
    "RESEARCH_AND_PROPOSAL": {
        "kind": "role",
        "role": "researcher_proposer",
        "instruction": "Produce proposal.md and prepare it for reviewer reports.",
        "completion_event": "proposal_created",
    },
    "PROPOSAL_REVIEW": {
        "kind": "role",
        "role": "reviewers",
        "instruction": "Run product, technical, risk, and verification review; aggregate reports.",
        "completion_event": "reviews_aggregated",
    },
    "ADJUDICATION": {
        "kind": "role",
        "role": "adjudicator",
        "instruction": "Read review aggregate and decide accept, revise, ask user, adjust goal, replan, or block.",
        "completion_event": "adjudication_accept|adjudication_revise|adjudication_ask_user|block",
    },
    "PROPOSAL_REWORK": {
        "kind": "role",
        "role": "researcher_proposer",
        "instruction": "Rework proposal.md according to adjudication-report.json.",
        "completion_event": "proposal_created",
    },
    "PROPOSAL_SUMMARY": {
        "kind": "role",
        "role": "proposal_summarizer",
        "instruction": "Write proposal-summary.md for user confirmation.",
        "completion_event": "proposal_summarized",
    },
    "USER_PROPOSAL_CONFIRMATION": {
        "kind": "gate",
        "role": "user",
        "instruction": "Ask the user to accept, reject, or request changes to the proposal.",
        "completion_event": "proposal_accepted|adjudication_ask_user",
    },
    "PROPOSAL_ACCEPTED": {
        "kind": "role",
        "role": "planner",
        "instruction": "Start milestone planning.",
        "completion_event": "planning_started",
    },
    "PLANNING": {
        "kind": "role",
        "role": "planner",
        "instruction": "Create milestone-plan.json.",
        "completion_event": "milestone_plan_created",
    },
    "USER_PLAN_CONFIRMATION": {
        "kind": "gate",
        "role": "user",
        "instruction": "Ask the user to accept or change the milestone plan.",
        "completion_event": "plan_accepted|replan_to_planning",
    },
    "MILESTONE_SELECTED": {
        "kind": "role",
        "role": "task_decomposer",
        "instruction": "Select the current milestone and decompose it into concrete tasks.",
        "completion_event": "tasks_decomposed",
    },
    "TASK_DECOMPOSITION": {
        "kind": "role",
        "role": "task_decomposer",
        "instruction": "Validate task-list.json, select the next concrete task, and write task-spec.json.",
        "completion_event": "task_selected",
    },
    "TASK_EXECUTION": {
        "kind": "role",
        "role": "executor",
        "instruction": "Execute exactly one concrete task and write task-execution-report.json.",
        "completion_event": "task_executed",
    },
    "TASK_VERIFICATION": {
        "kind": "role",
        "role": "result_verifier",
        "instruction": "Verify exactly one concrete task and write task-verification-report.json.",
        "completion_event": "verification_passed|verification_revise|block",
    },
    "TASK_REPAIR": {
        "kind": "role",
        "role": "task_decomposer",
        "instruction": "Use the verifier's minimal repair instructions to update or reselect exactly one concrete task spec.",
        "completion_event": "task_selected",
    },
    "MILESTONE_COMPLETED": {
        "kind": "role",
        "role": "direction_evaluator",
        "instruction": "Run direction evaluation for the completed milestone.",
        "completion_event": "milestone_completed",
    },
    "DIRECTION_EVALUATION": {
        "kind": "role",
        "role": "direction_evaluator",
        "instruction": "Route to continue, replan, adjust goal, ask user, abort, or final summary.",
        "completion_event": "direction_continue|direction_replan|direction_adjust_goal|direction_final|block",
    },
    "CONTINUE_NEXT_MILESTONE": {
        "kind": "role",
        "role": "planner",
        "instruction": "Select the next milestone.",
        "completion_event": "milestone_selected",
    },
    "REPLAN": {
        "kind": "role",
        "role": "planner",
        "instruction": "Replan milestones or concrete task decomposition.",
        "completion_event": "replan_to_planning|replan_to_decomposition",
    },
    "GOAL_ADJUSTMENT_REQUIRED": {
        "kind": "gate",
        "role": "user",
        "instruction": "Ask the user to confirm a goal contract patch.",
        "completion_event": "goal_adjustment_confirmed",
    },
    "FINAL_SUMMARY": {
        "kind": "role",
        "role": "final_summarizer",
        "instruction": "Write final-report.md.",
        "completion_event": "final_summarized",
    },
    "USER_FINAL_CONFIRMATION": {
        "kind": "gate",
        "role": "user",
        "instruction": "Ask the user to confirm the final result.",
        "completion_event": "final_accepted",
    },
    "DONE": {
        "kind": "done",
        "role": "none",
        "instruction": "No next action.",
        "completion_event": "",
    },
    "BLOCKED": {
        "kind": "blocked",
        "role": "user",
        "instruction": "Ask the user for an unblock decision.",
        "completion_event": "",
    },
    "ABANDONED": {
        "kind": "done",
        "role": "none",
        "instruction": "The user abandoned this task. Do not continue it unless the user explicitly starts or selects another task.",
        "completion_event": "",
    },
}

ROLE_AGENT_NAMES = {
    "questioner": ["questioner"],
    "researcher_proposer": ["researcher_proposer"],
    "reviewers": ["product_reviewer", "technical_reviewer", "risk_reviewer", "verification_reviewer"],
    "adjudicator": ["adjudicator"],
    "proposal_summarizer": ["proposal_summarizer"],
    "planner": ["planner"],
    "task_decomposer": ["task_decomposer"],
    "executor": ["executor"],
    "result_verifier": ["result_verifier"],
    "direction_evaluator": ["direction_evaluator"],
    "final_summarizer": ["final_summarizer"],
}
REVIEWER_AGENT_NAMES = ["product_reviewer", "technical_reviewer", "risk_reviewer", "verification_reviewer"]
JSON_PRODUCER_BY_EVENT = {
    "goal_contract_drafted": {
        "questioning-report.json": "questioner",
        "goal-contract.json": "questioner",
    },
    "adjudication_accept": {"adjudication-report.json": "adjudicator"},
    "adjudication_revise": {"adjudication-report.json": "adjudicator"},
    "adjudication_ask_user": {"adjudication-report.json": "adjudicator"},
    "milestone_plan_created": {"milestone-plan.json": "planner"},
    "tasks_decomposed": {"task-list.json": "task_decomposer"},
    "task_selected": {"task-spec.json": "task_decomposer"},
    "task_executed": {"task-execution-report.json": "executor"},
    "verification_passed": {"task-verification-report.json": "result_verifier"},
    "verification_revise": {"task-verification-report.json": "result_verifier"},
    "milestone_completed": {"direction-evaluation.json": "direction_evaluator"},
    "direction_continue": {"direction-evaluation.json": "direction_evaluator"},
    "direction_replan": {"direction-evaluation.json": "direction_evaluator"},
    "direction_adjust_goal": {"direction-evaluation.json": "direction_evaluator"},
    "direction_final": {"direction-evaluation.json": "direction_evaluator"},
}
MARKDOWN_PRODUCER_BY_EVENT = {
    "proposal_created": {"proposal.md": "researcher_proposer"},
    "proposal_summarized": {"proposal-summary.md": "proposal_summarizer"},
    "final_summarized": {"final-report.md": "final_summarizer"},
}

TRANSITIONS = {
    "start_questioning": {"INTAKE": "QUESTIONING"},
    "goal_contract_drafted": {"QUESTIONING": "GOAL_CONTRACT_DRAFTED"},
    "proposal_started": {"GOAL_CONTRACT_DRAFTED": "RESEARCH_AND_PROPOSAL"},
    "proposal_created": {"RESEARCH_AND_PROPOSAL": "PROPOSAL_REVIEW", "PROPOSAL_REWORK": "PROPOSAL_REVIEW"},
    "reviews_aggregated": {"PROPOSAL_REVIEW": "ADJUDICATION"},
    "adjudication_accept": {"ADJUDICATION": "PROPOSAL_SUMMARY"},
    "adjudication_revise": {"ADJUDICATION": "PROPOSAL_REWORK"},
    "adjudication_ask_user": {"ADJUDICATION": "QUESTIONING", "USER_PROPOSAL_CONFIRMATION": "ADJUDICATION"},
    "proposal_summarized": {"PROPOSAL_SUMMARY": "USER_PROPOSAL_CONFIRMATION"},
    "proposal_accepted": {"USER_PROPOSAL_CONFIRMATION": "PROPOSAL_ACCEPTED"},
    "planning_started": {"PROPOSAL_ACCEPTED": "PLANNING"},
    "milestone_plan_created": {"PLANNING": "USER_PLAN_CONFIRMATION"},
    "plan_accepted": {"USER_PLAN_CONFIRMATION": "MILESTONE_SELECTED"},
    "milestone_selected": {"CONTINUE_NEXT_MILESTONE": "MILESTONE_SELECTED"},
    "tasks_decomposed": {"MILESTONE_SELECTED": "TASK_DECOMPOSITION"},
    "task_selected": {"TASK_DECOMPOSITION": "TASK_EXECUTION", "TASK_REPAIR": "TASK_EXECUTION"},
    "task_executed": {"TASK_EXECUTION": "TASK_VERIFICATION"},
    "verification_passed": {"TASK_VERIFICATION": "MILESTONE_COMPLETED"},
    "verification_revise": {"TASK_VERIFICATION": "TASK_REPAIR"},
    "milestone_completed": {"MILESTONE_COMPLETED": "DIRECTION_EVALUATION"},
    "direction_continue": {"DIRECTION_EVALUATION": "CONTINUE_NEXT_MILESTONE"},
    "direction_replan": {"DIRECTION_EVALUATION": "REPLAN"},
    "direction_adjust_goal": {"DIRECTION_EVALUATION": "GOAL_ADJUSTMENT_REQUIRED"},
    "direction_final": {"DIRECTION_EVALUATION": "FINAL_SUMMARY"},
    "replan_to_planning": {"REPLAN": "PLANNING"},
    "replan_to_decomposition": {"REPLAN": "TASK_DECOMPOSITION"},
    "goal_adjustment_confirmed": {"GOAL_ADJUSTMENT_REQUIRED": "QUESTIONING"},
    "final_summarized": {"FINAL_SUMMARY": "USER_FINAL_CONFIRMATION"},
    "final_accepted": {"USER_FINAL_CONFIRMATION": "DONE"},
}

ARTIFACT_SPECS_BY_EVENT = {
    "task_started": [{"name": "raw-request.md", "phase": "INTAKE"}],
    "goal_contract_drafted": [
        {"name": "questioning-report.json", "phase": "QUESTIONING"},
        {"name": "goal-contract.json", "phase": "QUESTIONING"},
    ],
    "proposal_created": [{"name": "proposal.md"}],
    "reviews_aggregated": [{"name": "review-aggregate.json", "phase": "PROPOSAL_REVIEW"}],
    "adjudication_accept": [{"name": "adjudication-report.json", "phase": "ADJUDICATION"}],
    "adjudication_revise": [{"name": "adjudication-report.json", "phase": "ADJUDICATION"}],
    "adjudication_ask_user": [{"name": "adjudication-report.json", "phase": "ADJUDICATION", "from_phase": "ADJUDICATION"}],
    "proposal_summarized": [{"name": "proposal-summary.md", "phase": "PROPOSAL_SUMMARY"}],
    "milestone_plan_created": [{"name": "milestone-plan.json", "phase": "PLANNING"}],
    "tasks_decomposed": [{"name": "task-list.json", "phase": "MILESTONE_SELECTED"}],
    "task_selected": [{"name": "task-spec.json"}],
    "task_executed": [{"name": "task-execution-report.json", "phase": "TASK_EXECUTION"}],
    "verification_passed": [{"name": "task-verification-report.json", "phase": "TASK_VERIFICATION"}],
    "verification_revise": [{"name": "task-verification-report.json", "phase": "TASK_VERIFICATION"}],
    "milestone_completed": [{"name": "direction-evaluation.json", "phase": "MILESTONE_COMPLETED"}],
    "direction_continue": [{"name": "direction-evaluation.json", "phase": "DIRECTION_EVALUATION"}],
    "direction_replan": [{"name": "direction-evaluation.json", "phase": "DIRECTION_EVALUATION"}],
    "direction_adjust_goal": [{"name": "direction-evaluation.json", "phase": "DIRECTION_EVALUATION"}],
    "direction_final": [{"name": "direction-evaluation.json", "phase": "DIRECTION_EVALUATION"}],
    "final_summarized": [{"name": "final-report.md", "phase": "FINAL_SUMMARY"}],
}

BLOCK_ARTIFACT_SPECS_BY_PHASE = {
    "QUESTIONING": [{"name": "questioning-report.json", "phase": "QUESTIONING", "json_producer": "questioner"}],
    "RESEARCH_AND_PROPOSAL": [{"name": "proposal.md", "phase": "RESEARCH_AND_PROPOSAL", "markdown_producer": "researcher_proposer"}],
    "PROPOSAL_REVIEW": [{"name": "review-aggregate.json", "phase": "PROPOSAL_REVIEW"}],
    "ADJUDICATION": [{"name": "adjudication-report.json", "phase": "ADJUDICATION", "json_producer": "adjudicator"}],
    "PROPOSAL_REWORK": [{"name": "proposal.md", "phase": "PROPOSAL_REWORK", "markdown_producer": "researcher_proposer"}],
    "PROPOSAL_SUMMARY": [{"name": "proposal-summary.md", "phase": "PROPOSAL_SUMMARY", "markdown_producer": "proposal_summarizer"}],
    "PLANNING": [{"name": "milestone-plan.json", "phase": "PLANNING", "json_producer": "planner"}],
    "MILESTONE_SELECTED": [{"name": "task-list.json", "phase": "MILESTONE_SELECTED", "json_producer": "task_decomposer"}],
    "TASK_DECOMPOSITION": [{"name": "task-spec.json", "phase": "TASK_DECOMPOSITION", "json_producer": "task_decomposer"}],
    "TASK_EXECUTION": [{"name": "task-execution-report.json", "phase": "TASK_EXECUTION", "json_producer": "executor"}],
    "TASK_VERIFICATION": [{"name": "task-verification-report.json", "phase": "TASK_VERIFICATION", "json_producer": "result_verifier"}],
    "TASK_REPAIR": [{"name": "task-spec.json", "phase": "TASK_REPAIR", "json_producer": "task_decomposer"}],
    "MILESTONE_COMPLETED": [{"name": "direction-evaluation.json", "phase": "MILESTONE_COMPLETED", "json_producer": "direction_evaluator"}],
    "DIRECTION_EVALUATION": [{"name": "direction-evaluation.json", "phase": "DIRECTION_EVALUATION", "json_producer": "direction_evaluator"}],
    "FINAL_SUMMARY": [{"name": "final-report.md", "phase": "FINAL_SUMMARY", "markdown_producer": "final_summarizer"}],
}

REQUIRED_DECIDED_GATE_BY_EVENT = {
    "proposal_accepted": {"types": ["proposal_confirmation"], "decisions": ["accept"]},
    "plan_accepted": {"types": ["plan_confirmation"], "decisions": ["accept"]},
    "goal_adjustment_confirmed": {"types": ["goal_adjustment"], "decisions": ["accept"]},
    "final_accepted": {"types": ["final_confirmation"], "decisions": ["accept"]},
}
CLARIFICATION_GATE_TYPE = "clarifying_questions"
CLARIFICATION_GATE_DECISIONS = {"accept", "revise"}
DELEGATION_GATE_TYPE = "delegation_authorization"
DELEGATION_GATE_ACCEPT_DECISIONS = {"accept"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:48] or "task"


def root_from(value: Path | None = None) -> Path:
    return value or ROOT


def tasks_root(root: Path) -> Path:
    return root / "tasks"


def active_task_path(root: Path) -> Path:
    return root / "active-task.json"


def task_index_path(root: Path) -> Path:
    return root / "task-index.json"


def artifact_index_path(task_dir: Path) -> Path:
    return task_dir / "artifact-index.json"


def artifacts_dir(task_dir: Path) -> Path:
    return task_dir / "artifacts"


def task_dir_for(root: Path, task_id: str) -> Path:
    return tasks_root(root) / task_id


def ensure_root(root: Path) -> None:
    tasks_root(root).mkdir(parents=True, exist_ok=True)


def read_raw_request(args: argparse.Namespace) -> str:
    if getattr(args, "raw_request", None) and getattr(args, "raw_request_file", None):
        raise SystemExit("Use either raw_request or --raw-request-file, not both.")
    if getattr(args, "raw_request_file", None):
        return args.raw_request_file.read_text(encoding="utf-8")
    if getattr(args, "raw_request", None):
        return args.raw_request
    raise SystemExit("A raw request is required.")


def relative_to_root(root: Path, value: Path) -> str:
    try:
        return str(value.relative_to(root))
    except ValueError:
        return str(value)


def relative_to_task(task_dir: Path, value: Path) -> str:
    try:
        return str(value.relative_to(task_dir))
    except ValueError:
        return str(value)


def node_order(phase: str) -> int:
    return PHASE_ORDER.get(phase, 99)


def node_key(phase: str) -> str:
    return f"{node_order(phase):02d}-{phase}"


def spec_applies_to_phase(spec: dict[str, Any], from_phase: str | None) -> bool:
    expected_from_phase = spec.get("from_phase")
    return not expected_from_phase or expected_from_phase == from_phase


def artifact_specs_for_event(event: str, from_phase: str | None) -> list[dict[str, Any]]:
    if event == "block" and from_phase:
        return BLOCK_ARTIFACT_SPECS_BY_PHASE.get(from_phase, [])
    return [
        spec
        for spec in ARTIFACT_SPECS_BY_EVENT.get(event, [])
        if spec_applies_to_phase(spec, from_phase)
    ]


def artifact_phase_for_spec(spec: dict[str, Any], from_phase: str | None) -> str:
    phase = spec.get("phase") or from_phase
    return phase if isinstance(phase, str) and phase else "UNKNOWN"


def required_artifact_names_for_event(event: str, from_phase: str | None) -> list[str]:
    if event == "task_started":
        return []
    return [spec["name"] for spec in artifact_specs_for_event(event, from_phase)]


def write_event(task_dir: Path, event: dict[str, Any]) -> None:
    events_path = task_dir / "events.ndjson"
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def read_events(task_dir: Path) -> list[dict[str, Any]]:
    path = task_dir / "events.ndjson"
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            events.append(data)
    return events


def empty_artifact_index() -> dict[str, Any]:
    return {
        "version": WORKFLOW_VERSION,
        "layout": ARTIFACT_INDEX_LAYOUT,
        "adopted_at": None,
        "updated_at": None,
        "artifacts": [],
    }


def load_artifact_index(task_dir: Path) -> dict[str, Any]:
    path = artifact_index_path(task_dir)
    if not path.exists():
        return empty_artifact_index()
    data = load_json(path)
    if not isinstance(data, dict):
        fail([f"{path} must be an object"])
    data.setdefault("version", WORKFLOW_VERSION)
    data.setdefault("layout", ARTIFACT_INDEX_LAYOUT)
    data.setdefault("adopted_at", None)
    data.setdefault("artifacts", [])
    return data


def write_artifact_index(task_dir: Path, index: dict[str, Any], timestamp: str) -> None:
    if not index.get("adopted_at"):
        index["adopted_at"] = timestamp
    index["updated_at"] = timestamp
    write_json(artifact_index_path(task_dir), index)


def index_artifact_paths(task_dir: Path, name: str) -> list[Path]:
    index = load_artifact_index(task_dir)
    artifacts = index.get("artifacts", [])
    if not isinstance(artifacts, list):
        return []
    paths: list[Path] = []
    for entry in reversed(artifacts):
        if not isinstance(entry, dict) or entry.get("name") != name:
            continue
        for field in ("display_path", "canonical_path"):
            value = entry.get(field)
            if isinstance(value, str) and value:
                paths.append(task_dir / value)
    return paths


def legacy_artifact_candidates(task_dir: Path, name: str) -> list[Path]:
    if name.startswith("gates/"):
        return [task_dir / name]
    return [task_dir / name, artifacts_dir(task_dir) / name]


def artifact_candidates(task_dir: Path, name: str) -> list[Path]:
    if name.startswith("gates/"):
        return [task_dir / name]
    return [*index_artifact_paths(task_dir, name), *legacy_artifact_candidates(task_dir, name)]


def recorded_artifact_path(task_dir: Path, name: str, *, event: str | None = None, node: str | None = None, status: str = "done") -> Path | None:
    index = load_artifact_index(task_dir)
    artifacts = index.get("artifacts", [])
    if not isinstance(artifacts, list):
        return None
    for entry in reversed(artifacts):
        if not isinstance(entry, dict):
            continue
        if entry.get("name") != name or entry.get("status") != status:
            continue
        if event is not None and entry.get("event") != event:
            continue
        if node is not None and entry.get("node") != node:
            continue
        for field in ("display_path", "canonical_path"):
            value = entry.get(field)
            if isinstance(value, str) and value:
                path = task_dir / value
                if path.exists():
                    return path
    return None


def latest_existing_path(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime_ns)


def safe_path_segment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "artifact"


def content_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_artifact_path(task_dir: Path, phase: str, status: str, name: str, occurrence: int = 1, event: str = "") -> Path:
    safe_name = name.replace("/", "__")
    base = artifacts_dir(task_dir) / "by-node" / node_key(phase) / status
    if occurrence <= 1:
        return base / safe_name
    event_segment = safe_path_segment(event)
    return base / f"{occurrence:02d}-{event_segment}" / safe_name


def copy_if_needed(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == destination.resolve():
        return
    shutil.copyfile(source, destination)


def artifact_occurrence(index: dict[str, Any], phase: str, status: str, name: str) -> int:
    artifacts = index.get("artifacts", [])
    if not isinstance(artifacts, list):
        return 1
    return 1 + sum(
        1
        for entry in artifacts
        if isinstance(entry, dict)
        and entry.get("node") == phase
        and entry.get("status") == status
        and entry.get("name") == name
    )


def ensure_artifact_layout(task_dir: Path, name: str, phase: str, status: str, occurrence: int, event: str) -> tuple[Path, Path, Path]:
    display = display_artifact_path(task_dir, phase, status, name, occurrence, event)
    source = latest_existing_path([display, *legacy_artifact_candidates(task_dir, name)])
    if not source:
        raise SystemExit(f"Cannot record artifact {name}; file not found.")
    display.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != display.resolve():
        shutil.move(str(source), str(display))
    return display, display, display


def append_artifact_entry(
    task_dir: Path,
    index: dict[str, Any],
    *,
    event: str,
    phase: str,
    status: str,
    name: str,
    source: Path,
    canonical: Path,
    display: Path,
    timestamp: str,
    occurrence: int,
    artifact_type: str = "file",
) -> None:
    artifacts = index.setdefault("artifacts", [])
    artifacts.append({
        "sequence": len(artifacts) + 1,
        "event": event,
        "artifact_type": artifact_type,
        "node_order": node_order(phase),
        "node": phase,
        "node_key": node_key(phase),
        "status": status,
        "occurrence": occurrence,
        "name": name,
        "source_path": relative_to_task(task_dir, source),
        "canonical_path": relative_to_task(task_dir, canonical),
        "display_path": relative_to_task(task_dir, display),
        "content_sha256": content_sha256(display),
        "recorded_at": timestamp,
    })


def record_artifacts_for_event(task_dir: Path, event: str, phase: str, status: str, timestamp: str) -> list[str]:
    specs = artifact_specs_for_event(event, phase)
    if not specs:
        return []
    index = load_artifact_index(task_dir)
    refs = []
    for spec in specs:
        artifact_phase = artifact_phase_for_spec(spec, phase)
        name = spec["name"]
        occurrence = artifact_occurrence(index, artifact_phase, status, name)
        source, canonical, display = ensure_artifact_layout(task_dir, name, artifact_phase, status, occurrence, event)
        append_artifact_entry(
            task_dir,
            index,
            event=event,
            phase=artifact_phase,
            status=status,
            name=name,
            source=source,
            canonical=canonical,
            display=display,
            timestamp=timestamp,
            occurrence=occurrence,
        )
        refs.append(relative_to_task(task_dir, canonical))
    write_artifact_index(task_dir, index, timestamp)
    return refs


def record_gate_artifact(task_dir: Path, gate: dict[str, Any], status: str, event: str, timestamp: str) -> str:
    gate_id = gate["gate_id"]
    phase = gate.get("phase") or "UNKNOWN"
    name = f"{gate_id}.json"
    source = task_dir / "gates" / name
    index = load_artifact_index(task_dir)
    occurrence = artifact_occurrence(index, phase, status, name)
    display = display_artifact_path(task_dir, phase, status, name, occurrence, event)
    copy_if_needed(source, display)
    append_artifact_entry(
        task_dir,
        index,
        event=event,
        phase=phase,
        status=status,
        name=name,
        source=source,
        canonical=source,
        display=display,
        timestamp=timestamp,
        occurrence=occurrence,
        artifact_type="gate",
    )
    write_artifact_index(task_dir, index, timestamp)
    return relative_to_task(task_dir, source)


def update_index(root: Path, state: dict[str, Any], task_dir: Path) -> None:
    path = task_index_path(root)
    if path.exists():
        index = load_json(path)
    else:
        index = {"version": WORKFLOW_VERSION, "tasks": []}
    tasks = index.setdefault("tasks", [])
    item = {
        "task_id": state["task_id"],
        "task_dir": relative_to_root(root, task_dir),
        "status": state.get("status", "active"),
        "phase": state.get("phase", "INTAKE"),
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
    }
    for idx, existing in enumerate(tasks):
        if existing.get("task_id") == state["task_id"]:
            tasks[idx] = item
            break
    else:
        tasks.append(item)
    write_json(path, index)


def set_active_task(root: Path, state: dict[str, Any], task_dir: Path) -> None:
    write_json(
        active_task_path(root),
        {
            "version": WORKFLOW_VERSION,
            "task_id": state["task_id"],
            "task_dir": relative_to_root(root, task_dir),
            "status": state.get("status", "active"),
            "phase": state.get("phase", "INTAKE"),
            "updated_at": state.get("updated_at"),
        },
    )


def deactivate_task(root: Path, task_id: str) -> None:
    path = active_task_path(root)
    if not path.exists():
        return
    active = load_json(path)
    if active.get("task_id") == task_id:
        path.unlink()


def close_open_gates_for_abandon(task_dir: Path, reason: str, timestamp: str) -> list[str]:
    gates_dir = task_dir / "gates"
    if not gates_dir.exists():
        return []
    refs = []
    for path in sorted(gates_dir.glob("*.json")):
        gate = load_json(path)
        if not isinstance(gate, dict) or gate.get("status") != "open":
            continue
        gate["status"] = "decided"
        gate["decision"] = "abort"
        gate["comment"] = reason
        gate["decided_at"] = timestamp
        write_json(path, gate)
        ref = record_gate_artifact(task_dir, gate, "decided", "gate_decided", timestamp)
        refs.append(ref)
        phase = gate.get("phase") if isinstance(gate.get("phase"), str) else "UNKNOWN"
        write_event(
            task_dir,
            {
                "at": timestamp,
                "actor": "controller",
                "event": "gate_decided",
                "from_phase": phase,
                "to_phase": phase,
                "reason": reason,
                "artifact_refs": [ref],
            },
        )
    return refs


def abandon_task(root: Path, task_dir: Path, reason: str) -> dict[str, Any]:
    state = load_state(task_dir)
    task_id = state.get("task_id", task_dir.name)
    if state.get("status") == "abandoned" or state.get("phase") == "ABANDONED":
        deactivate_task(root, task_id)
        update_index(root, state, task_dir)
        return status_payload(task_dir)

    timestamp = now()
    previous = state.get("phase", "UNKNOWN")
    resolved_reason = reason or "Task abandoned by user."
    gate_refs = close_open_gates_for_abandon(task_dir, resolved_reason, timestamp)

    state["phase"] = "ABANDONED"
    state["updated_at"] = timestamp
    state["status"] = "abandoned"
    state["last_route_decision"] = resolved_reason
    state.setdefault("history", []).append({
        "at": timestamp,
        "from_phase": previous,
        "to_phase": "ABANDONED",
        "reason": resolved_reason,
    })
    write_json(task_dir / "state.json", state)
    write_event(
        task_dir,
        {
            "at": timestamp,
            "actor": "controller",
            "event": "task_abandoned",
            "from_phase": previous,
            "to_phase": "ABANDONED",
            "reason": resolved_reason,
            "artifact_refs": gate_refs,
        },
    )
    update_index(root, state, task_dir)
    deactivate_task(root, task_id)
    return status_payload(task_dir)


def initial_state(task_id: str, timestamp: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "workflow_version": WORKFLOW_VERSION,
        "phase": "QUESTIONING",
        "created_at": timestamp,
        "updated_at": timestamp,
        "proposal_review_round": 0,
        "direction_adjustment_round": 0,
        "task_repair_attempts": {},
        "current_milestone_id": None,
        "current_task_id": None,
        "current_repair_root_task_id": None,
        "max_proposal_rework_rounds": 3,
        "max_task_repair_rounds": 2,
        "max_direction_adjustment_rounds": 2,
        "delegation_authorization": default_delegation_authorization(),
        "status": "active",
        "last_route_decision": "Raw request captured; goal clarification started.",
        "history": [
            {
                "at": timestamp,
                "from_phase": "NONE",
                "to_phase": "INTAKE",
                "reason": "Raw request captured.",
            },
            {
                "at": timestamp,
                "from_phase": "INTAKE",
                "to_phase": "QUESTIONING",
                "reason": "Goal clarification started.",
            }
        ],
    }


def start_task(root: Path, raw_request: str, task_id: str | None = None) -> Path:
    ensure_root(root)
    timestamp = now()
    resolved_task_id = task_id or f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{slugify(raw_request)}"
    task_dir = task_dir_for(root, resolved_task_id)
    task_dir.mkdir(parents=True, exist_ok=False)
    artifacts_dir(task_dir).mkdir(parents=True, exist_ok=True)
    (task_dir / "gates").mkdir(parents=True, exist_ok=True)
    (task_dir / "runs").mkdir(parents=True, exist_ok=True)

    state = initial_state(resolved_task_id, timestamp)
    write_json(task_dir / "state.json", state)
    text = raw_request.rstrip() + "\n"
    raw_request_path = display_artifact_path(task_dir, "INTAKE", "done", "raw-request.md", 1, "task_started")
    raw_request_path.parent.mkdir(parents=True, exist_ok=True)
    raw_request_path.write_text(text, encoding="utf-8")
    artifact_refs = record_artifacts_for_event(task_dir, "task_started", "INTAKE", "done", timestamp)
    write_event(
        task_dir,
        {
            "at": timestamp,
            "actor": "controller",
            "event": "task_started",
            "from_phase": "NONE",
            "to_phase": "INTAKE",
            "reason": "Raw request captured.",
            "artifact_refs": artifact_refs,
        },
    )
    write_event(
        task_dir,
        {
            "at": timestamp,
            "actor": "controller",
            "event": "start_questioning",
            "from_phase": "INTAKE",
            "to_phase": "QUESTIONING",
            "reason": "Goal clarification started.",
            "artifact_refs": [],
        },
    )
    set_active_task(root, state, task_dir)
    update_index(root, state, task_dir)
    return task_dir


def resolve_task_dir(root: Path, value: str | None = None) -> Path:
    if value:
        candidate = Path(value)
        if candidate.exists():
            return candidate
        by_id = task_dir_for(root, value)
        if by_id.exists():
            return by_id
        raise SystemExit(f"Task directory not found: {value}")
    active_path = active_task_path(root)
    if not active_path.exists():
        raise SystemExit("No active meta-flow task. Start one with: controller.py start \"<request>\"")
    active = load_json(active_path)
    task_ref = active.get("task_dir")
    if not isinstance(task_ref, str):
        raise SystemExit("active-task.json is invalid: missing task_dir")
    task_dir = root / task_ref
    if not task_dir.exists():
        raise SystemExit(f"Active task directory not found: {task_dir}")
    return task_dir


def load_state(task_dir: Path) -> dict[str, Any]:
    data = load_json(task_dir / "state.json")
    if not isinstance(data, dict):
        fail([f"{task_dir / 'state.json'} must be an object"])
    return data


def artifact_exists(task_dir: Path, name: str) -> bool:
    return latest_existing_path(artifact_candidates(task_dir, name)) is not None


def artifact_exists_for_spec(task_dir: Path, event: str, from_phase: str | None, spec: dict[str, Any]) -> bool:
    return artifact_path_for_spec(task_dir, event, from_phase, spec) is not None


def artifact_path_for_spec(task_dir: Path, event: str, from_phase: str | None, spec: dict[str, Any]) -> Path | None:
    artifact_phase = artifact_phase_for_spec(spec, from_phase)
    name = spec["name"]
    index = load_artifact_index(task_dir)
    occurrence = artifact_occurrence(index, artifact_phase, "done", name)
    expected_path = display_artifact_path(task_dir, artifact_phase, "done", name, occurrence, event)
    return latest_existing_path([expected_path, *legacy_artifact_candidates(task_dir, name)])


def task_started_before_artifact_adoption(task_dir: Path) -> bool:
    events = read_events(task_dir)
    started_at = next(
        (event.get("at") for event in events if event.get("event") == "task_started" and isinstance(event.get("at"), str)),
        None,
    )
    if not artifact_index_path(task_dir).exists():
        return started_at is not None
    index = load_artifact_index(task_dir)
    adopted_at = index.get("adopted_at")
    if not isinstance(started_at, str) or not isinstance(adopted_at, str):
        return False
    return started_at < adopted_at


def ensure_legacy_questioning_report(task_dir: Path, timestamp: str) -> None:
    if artifact_exists(task_dir, "questioning-report.json") or not artifact_exists(task_dir, "goal-contract.json"):
        return
    if not task_started_before_artifact_adoption(task_dir):
        return
    raw_request = ""
    raw_path = latest_existing_path(artifact_candidates(task_dir, "raw-request.md"))
    if raw_path:
        raw_request = raw_path.read_text(encoding="utf-8").strip()
    report = {
        "task_id": load_state(task_dir).get("task_id", task_dir.name),
        "raw_user_request": raw_request or "Recovered from a legacy task without questioning-report.json.",
        "known_information": [],
        "missing_information": [],
        "clarifying_questions": [],
        "assumptions_if_user_does_not_answer": [
            "Legacy task created before questioning-report.json became a required controller artifact."
        ],
        "can_continue_without_user_answer": True,
        "compatibility_generated_at": timestamp,
    }
    index = load_artifact_index(task_dir)
    phase = "QUESTIONING"
    event = "goal_contract_drafted"
    occurrence = artifact_occurrence(index, phase, "done", "questioning-report.json")
    target = display_artifact_path(task_dir, phase, "done", "questioning-report.json", occurrence, event)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json(target, report)


def missing_required_artifacts(task_dir: Path, event: str, from_phase: str | None) -> list[str]:
    missing = []
    for spec in artifact_specs_for_event(event, from_phase):
        name = spec["name"]
        if not artifact_exists_for_spec(task_dir, event, from_phase, spec):
            missing.append(name)
    return missing


def enforce_role_artifact_producers(task_dir: Path, event: str, from_phase: str | None) -> None:
    if not artifact_index_path(task_dir).exists():
        return
    if task_started_before_artifact_adoption(task_dir):
        return
    errors: list[str] = []
    for spec in artifact_specs_for_event(event, from_phase):
        name = spec["name"]
        path = artifact_path_for_spec(task_dir, event, from_phase, spec)
        if path is None:
            continue
        expected_json_agent = spec.get("json_producer") or JSON_PRODUCER_BY_EVENT.get(event, {}).get(name)
        if expected_json_agent:
            errors.extend(validate_json_producer(path, expected_json_agent))
        expected_markdown_agent = spec.get("markdown_producer") or MARKDOWN_PRODUCER_BY_EVENT.get(event, {}).get(name)
        if expected_markdown_agent:
            errors.extend(validate_markdown_producer(path, expected_markdown_agent))
        if name == "review-aggregate.json":
            errors.extend(validate_review_aggregate(path))
    if errors:
        raise SystemExit(f"Cannot advance with {event}; invalid role producer metadata: {'; '.join(errors)}")


def validate_json_producer(path: Path, expected_agent: str) -> list[str]:
    try:
        data = load_json(path)
    except Exception as exc:
        return [f"{path.name} must be valid JSON before producer validation ({exc})"]
    if not isinstance(data, dict):
        return [f"{path.name} must be a JSON object"]
    producer = data.get("producer")
    if not isinstance(producer, dict):
        return [f"{path.name}.producer must be an object"]
    errors = []
    if producer.get("agent_name") != expected_agent:
        errors.append(f"{path.name}.producer.agent_name must be {expected_agent}")
    if producer.get("execution_mode") != "spawned_agent":
        errors.append(f"{path.name}.producer.execution_mode must be spawned_agent")
    return errors


def validate_markdown_producer(path: Path, expected_agent: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return [f"{path.name} must start with producer frontmatter"]
    end = text.find("\n---\n", 4)
    if end == -1:
        return [f"{path.name} producer frontmatter must be closed"]
    fields = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    errors = []
    if fields.get("producer_agent") != expected_agent:
        errors.append(f"{path.name} producer_agent must be {expected_agent}")
    if fields.get("execution_mode") != "spawned_agent":
        errors.append(f"{path.name} execution_mode must be spawned_agent")
    return errors


def validate_review_aggregate(path: Path) -> list[str]:
    try:
        data = load_json(path)
    except Exception as exc:
        return [f"review-aggregate.json must be valid JSON ({exc})"]
    if not isinstance(data, dict):
        return ["review-aggregate.json must be a JSON object"]
    reviewers = data.get("reviewers")
    if not isinstance(reviewers, list):
        return ["review-aggregate.json.reviewers must be a list"]
    errors: list[str] = []
    seen: list[str] = []
    for index, item in enumerate(reviewers, start=1):
        if not isinstance(item, dict):
            errors.append(f"reviewers[{index}] must be an object")
            continue
        reviewer = item.get("reviewer")
        if not isinstance(reviewer, str) or not reviewer:
            errors.append(f"reviewers[{index}].reviewer must be a non-empty string")
            continue
        seen.append(reviewer)
        producer = item.get("producer")
        if not isinstance(producer, dict):
            errors.append(f"reviewers[{index}].producer must be an object")
            continue
        if producer.get("agent_name") != reviewer:
            errors.append(f"reviewers[{index}].producer.agent_name must match reviewer")
        if producer.get("execution_mode") != "spawned_agent":
            errors.append(f"reviewers[{index}].producer.execution_mode must be spawned_agent")
    expected = set(REVIEWER_AGENT_NAMES)
    actual = set(seen)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    duplicates = sorted({name for name in seen if seen.count(name) > 1})
    if missing:
        errors.append(f"review-aggregate.json missing reviewers: {', '.join(missing)}")
    if unexpected:
        errors.append(f"review-aggregate.json has unexpected reviewers: {', '.join(unexpected)}")
    if duplicates:
        errors.append(f"review-aggregate.json has duplicate reviewers: {', '.join(duplicates)}")
    return errors


def expected_json_producer_for_entry(event_name: str, node: str, name: str) -> str | None:
    if event_name == "block":
        return block_spec_producer(node, name, "json_producer")
    return JSON_PRODUCER_BY_EVENT.get(event_name, {}).get(name)


def expected_markdown_producer_for_entry(event_name: str, node: str, name: str) -> str | None:
    if event_name == "block":
        return block_spec_producer(node, name, "markdown_producer")
    return MARKDOWN_PRODUCER_BY_EVENT.get(event_name, {}).get(name)


def block_spec_producer(node: str, name: str, key: str) -> str | None:
    for spec in BLOCK_ARTIFACT_SPECS_BY_PHASE.get(node, []):
        if spec.get("name") == name and isinstance(spec.get(key), str):
            return str(spec[key])
    return None


def open_gate(task_dir: Path) -> dict[str, Any] | None:
    gates_dir = task_dir / "gates"
    if not gates_dir.exists():
        return None
    for path in sorted(gates_dir.glob("*.json")):
        gate = load_json(path)
        if isinstance(gate, dict) and gate.get("status") == "open":
            gate["path"] = str(path)
            return gate
    return None


def decided_gate_for_event(task_dir: Path, event: str) -> dict[str, Any] | None:
    requirement = REQUIRED_DECIDED_GATE_BY_EVENT.get(event)
    if not requirement:
        return None
    gates_dir = task_dir / "gates"
    if not gates_dir.exists():
        return None
    for path in sorted(gates_dir.glob("*.json"), reverse=True):
        gate = load_json(path)
        if not isinstance(gate, dict):
            continue
        if gate.get("status") != "decided":
            continue
        if gate.get("type") not in requirement["types"]:
            continue
        if gate.get("decision") not in requirement["decisions"]:
            continue
        gate["path"] = str(path)
        return gate
    return None


def default_delegation_authorization() -> dict[str, Any]:
    return {
        "status": "pending",
        "gate_id": None,
        "decision": None,
        "comment": "",
        "authorized_at": None,
        "denied_at": None,
    }


def delegation_authorization(state: dict[str, Any]) -> dict[str, Any]:
    authorization = state.get("delegation_authorization")
    if isinstance(authorization, dict):
        result = default_delegation_authorization()
        result.update(authorization)
        return result
    return default_delegation_authorization()


def delegation_authorized(state: dict[str, Any]) -> bool:
    return delegation_authorization(state).get("status") == "approved"


def action_requires_delegation(action: dict[str, Any]) -> bool:
    return bool(action.get("kind") == "role" and ROLE_AGENT_NAMES.get(action.get("role")))


def phase_requires_delegation(phase: str | None) -> bool:
    if not isinstance(phase, str):
        return False
    return action_requires_delegation(NEXT_ACTION_BY_PHASE.get(phase, {}))


def event_requires_delegation(event: str, from_phase: str | None) -> bool:
    if event == "start_questioning":
        return False
    if not phase_requires_delegation(from_phase):
        return False
    return event in completion_events_for_phase(str(from_phase)) or event == "block"


def delegation_authorization_prompt(action: dict[str, Any]) -> str:
    agents = ROLE_AGENT_NAMES.get(action.get("role"), [])
    listed_agents = ", ".join(agents) if agents else "required role agents"
    return (
        "This meta-flow task requires explicit user authorization to use sub-agents/delegation/parallel agent work "
        f"for workflow roles. Accept to authorize spawning these required role agent(s) for this task: {listed_agents}. "
        "Reject or abort to block the task; the main agent must not perform these roles locally."
    )


def latest_decided_gate(task_dir: Path, gate_type: str, decisions: set[str] | None = None) -> dict[str, Any] | None:
    gates_dir = task_dir / "gates"
    if not gates_dir.exists():
        return None
    for path in sorted(gates_dir.glob("*.json"), reverse=True):
        gate = load_json(path)
        if not isinstance(gate, dict):
            continue
        if gate.get("status") != "decided":
            continue
        if gate.get("type") != gate_type:
            continue
        if decisions is not None and gate.get("decision") not in decisions:
            continue
        gate["path"] = str(path)
        return gate
    return None


def questioning_report_for_advance(task_dir: Path) -> tuple[dict[str, Any], Path]:
    index = load_artifact_index(task_dir)
    occurrence = artifact_occurrence(index, "QUESTIONING", "done", "questioning-report.json")
    expected_path = display_artifact_path(
        task_dir,
        "QUESTIONING",
        "done",
        "questioning-report.json",
        occurrence,
        "goal_contract_drafted",
    )
    path = latest_existing_path([expected_path, *artifact_candidates(task_dir, "questioning-report.json")])
    if not path:
        raise SystemExit("Cannot advance with goal_contract_drafted; missing required artifact: questioning-report.json")
    data = load_json(path)
    if not isinstance(data, dict):
        raise SystemExit("Cannot advance with goal_contract_drafted; questioning-report.json must be an object")
    return data, path


def non_empty_items(value: Any) -> bool:
    return isinstance(value, list) and any(item for item in value)


def questioning_report_gate_reasons(report: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    reasons: list[str] = []
    clarifying_questions = report.get("clarifying_questions")
    missing_information = report.get("missing_information")
    assumptions = report.get("assumptions_if_user_does_not_answer")
    can_continue = report.get("can_continue_without_user_answer")

    if not isinstance(clarifying_questions, list):
        errors.append("clarifying_questions must be a list")
    elif non_empty_items(clarifying_questions):
        reasons.append("clarifying_questions is not empty")

    if not isinstance(missing_information, list):
        errors.append("missing_information must be a list")
    if not isinstance(assumptions, list):
        errors.append("assumptions_if_user_does_not_answer must be a list")

    if not isinstance(can_continue, bool):
        errors.append("can_continue_without_user_answer must be a boolean")
    elif can_continue is False:
        reasons.append("can_continue_without_user_answer is false")

    if (
        isinstance(missing_information, list)
        and non_empty_items(missing_information)
        and can_continue is True
        and isinstance(assumptions, list)
        and not non_empty_items(assumptions)
    ):
        reasons.append("missing_information exists without assumptions_if_user_does_not_answer")

    return errors, reasons


def enforce_questioning_clarification_gate(task_dir: Path, event: str) -> None:
    if event != "goal_contract_drafted":
        return
    report, path = questioning_report_for_advance(task_dir)
    errors, reasons = questioning_report_gate_reasons(report)
    if errors:
        raise SystemExit(f"Cannot advance with {event}; invalid {relative_to_task(task_dir, path)}: {', '.join(errors)}")
    if not reasons:
        return
    if latest_decided_gate(task_dir, CLARIFICATION_GATE_TYPE, CLARIFICATION_GATE_DECISIONS):
        return
    reason_text = "; ".join(reasons)
    raise SystemExit(
        f"Cannot advance with {event}; questioning requires user clarification ({reason_text}). "
        f"Open a {CLARIFICATION_GATE_TYPE} gate, ask the user, record the decision, then update artifacts or advance."
    )


def enforce_delegation_authorization(task_dir: Path, event: str, from_phase: str | None) -> None:
    if not event_requires_delegation(event, from_phase):
        return
    state = load_state(task_dir)
    if delegation_authorized(state):
        return
    authorization = delegation_authorization(state)
    gate_id = authorization.get("gate_id")
    gate_hint = f" gate {gate_id}" if isinstance(gate_id, str) and gate_id else f" {DELEGATION_GATE_TYPE} gate"
    raise SystemExit(
        f"Cannot advance with {event}; explicit user authorization for sub-agents/delegation is required first. "
        f"Ask the user to accept{gate_hint}; do not perform this role locally."
    )


def enforce_gate_requirements(task_dir: Path, event: str) -> None:
    gate = open_gate(task_dir)
    if gate and event != "block":
        raise SystemExit(f"Cannot advance with {event}; gate {gate.get('gate_id')} is still open.")
    requirement = REQUIRED_DECIDED_GATE_BY_EVENT.get(event)
    if not requirement:
        return
    if decided_gate_for_event(task_dir, event):
        return
    types = ", ".join(requirement["types"])
    decisions = ", ".join(requirement["decisions"])
    raise SystemExit(f"Cannot advance with {event}; requires decided gate type [{types}] with decision [{decisions}].")


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


def artifact_refs(task_dir: Path) -> list[str]:
    index = load_artifact_index(task_dir)
    artifacts = index.get("artifacts", [])
    if isinstance(artifacts, list):
        refs = [
            entry.get("display_path")
            for entry in artifacts
            if isinstance(entry, dict)
            and entry.get("artifact_type") == "file"
            and isinstance(entry.get("display_path"), str)
        ]
        return list(dict.fromkeys(refs))
    return []


def artifact_summary(task_dir: Path) -> dict[str, Any]:
    index = load_artifact_index(task_dir)
    artifacts = index.get("artifacts", [])
    latest = artifacts[-5:] if isinstance(artifacts, list) else []
    return {
        "index_path": str(artifact_index_path(task_dir)),
        "layout": index.get("layout", ARTIFACT_INDEX_LAYOUT),
        "count": len(artifacts) if isinstance(artifacts, list) else 0,
        "latest": latest,
    }


def completion_events_for_phase(phase: str) -> list[str]:
    action = NEXT_ACTION_BY_PHASE.get(phase, {})
    completion_event = action.get("completion_event", "")
    if not completion_event:
        return []
    return [event for event in completion_event.split("|") if event]


def expected_artifacts_by_event_for_phase(phase: str) -> dict[str, list[str]]:
    expected = {}
    for event in completion_events_for_phase(phase):
        names = required_artifact_names_for_event(event, phase)
        if names:
            expected[event] = names
    return expected


def expected_artifact_paths_by_event_for_phase(task_dir: Path, phase: str) -> dict[str, list[dict[str, Any]]]:
    index = load_artifact_index(task_dir)
    expected: dict[str, list[dict[str, Any]]] = {}
    for event in completion_events_for_phase(phase):
        items = []
        for spec in artifact_specs_for_event(event, phase):
            artifact_phase = artifact_phase_for_spec(spec, phase)
            name = spec["name"]
            occurrence = artifact_occurrence(index, artifact_phase, "done", name)
            path = display_artifact_path(task_dir, artifact_phase, "done", name, occurrence, event)
            items.append({
                "name": name,
                "node": artifact_phase,
                "node_key": node_key(artifact_phase),
                "status": "done",
                "path": relative_to_task(task_dir, path),
            })
        if items:
            expected[event] = items
    return expected


def expected_artifacts_for_next_action(phase: str) -> list[str]:
    names = []
    for artifacts in expected_artifacts_by_event_for_phase(phase).values():
        names.extend(artifacts)
    return list(dict.fromkeys(names))


def ensure_delegation_authorization_gate(task_dir: Path, state: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    existing = open_gate(task_dir)
    if existing:
        return existing
    gate = open_gate_command(task_dir, DELEGATION_GATE_TYPE, delegation_authorization_prompt(action))
    state = load_state(task_dir)
    authorization = delegation_authorization(state)
    authorization.update({
        "status": "pending",
        "gate_id": gate["gate_id"],
        "decision": None,
        "comment": "",
        "authorized_at": None,
        "denied_at": None,
    })
    state["delegation_authorization"] = authorization
    state["updated_at"] = gate["opened_at"]
    write_json(task_dir / "state.json", state)
    return gate


def status_payload(task_dir: Path) -> dict[str, Any]:
    state = load_state(task_dir)
    phase = state.get("phase", "UNKNOWN")
    gate = open_gate(task_dir)
    if gate:
        next_action = enrich_next_action({
            "kind": "gate",
            "role": "user",
            "instruction": "Ask the user to decide the open gate before spawning any role agent or advancing the workflow.",
            "completion_event": "gate_decided",
        })
    else:
        base_next_action = NEXT_ACTION_BY_PHASE.get(phase, {
            "kind": "inspect",
            "role": "main_agent",
            "instruction": "Inspect state.json and route manually.",
            "completion_event": "",
        })
        if action_requires_delegation(base_next_action) and not delegation_authorized(state):
            gate = ensure_delegation_authorization_gate(task_dir, state, base_next_action)
            next_action = enrich_next_action({
                "kind": "gate",
                "role": "user",
                "instruction": "Ask the user to explicitly authorize sub-agents/delegation/parallel agent work for this meta-flow task before spawning any role agent.",
                "completion_event": "gate_decided",
            })
        else:
            next_action = enrich_next_action(base_next_action)
    state = load_state(task_dir)
    return {
        "task_id": state.get("task_id", task_dir.name),
        "task_dir": str(task_dir),
        "status": state.get("status", "unknown"),
        "phase": phase,
        "phase_label": PHASE_LABELS.get(phase, phase),
        "current_milestone_id": state.get("current_milestone_id"),
        "current_task_id": state.get("current_task_id"),
        "current_repair_root_task_id": state.get("current_repair_root_task_id"),
        "last_route_decision": state.get("last_route_decision", ""),
        "delegation_authorization": delegation_authorization(state),
        "open_gate": gate,
        "next_action": next_action,
        "allowed_user_actions": allowed_user_actions(phase, gate),
        "blocked_issues": collect_blocked_issues(task_dir),
        "artifact_refs": artifact_refs(task_dir),
        "artifact_index": artifact_summary(task_dir),
        "expected_artifacts_for_next_action": expected_artifacts_for_next_action(phase),
        "expected_artifacts_by_event": expected_artifacts_by_event_for_phase(phase),
        "expected_artifact_paths_by_event": expected_artifact_paths_by_event_for_phase(task_dir, phase),
    }


def enrich_next_action(action: dict[str, Any]) -> dict[str, Any]:
    result = dict(action)
    role = result.get("role")
    agents = ROLE_AGENT_NAMES.get(role, [])
    if result.get("kind") == "role" and agents:
        result["execution_mode"] = "spawn_agent_required"
        result["required_agents"] = agents
        result["parallel_allowed"] = len(agents) > 1
        result["main_agent_may_execute"] = False
        result["fallback_if_spawn_unavailable"] = (
            "Stop and ask the user; do not perform this role locally or write its artifacts from the main agent."
        )
    elif result.get("kind") == "gate":
        result["execution_mode"] = "user_gate"
        result["required_agents"] = []
        result["parallel_allowed"] = False
        result["main_agent_may_execute"] = False
        result["fallback_if_spawn_unavailable"] = ""
    else:
        result["execution_mode"] = "controller_or_none"
        result["required_agents"] = []
        result["parallel_allowed"] = False
        result["main_agent_may_execute"] = True
        result["fallback_if_spawn_unavailable"] = ""
    return result


def allowed_user_actions(phase: str, gate: dict[str, Any] | None) -> list[str]:
    if gate:
        if gate.get("type") == DELEGATION_GATE_TYPE:
            return ["授权 sub-agent/delegation", "拒绝并阻塞任务", "暂停"]
        return ["接受", "拒绝", "修改目标", "暂停"]
    if phase in {"DONE"}:
        return ["开始新任务", "查看最终报告"]
    if phase in {"ABANDONED"}:
        return ["开始新任务", "查看保留产物"]
    if phase in {"BLOCKED"}:
        return ["提供解除阻塞信息", "调整目标", "暂停"]
    return ["继续", "查看状态", "暂停"]


def print_text(payload: dict[str, Any]) -> None:
    print(f"task: {payload['task_id']}")
    print(f"status: {payload['status']}")
    print(f"current phase: {payload['phase']} ({payload['phase_label']})")
    print(f"current milestone: {payload['current_milestone_id']}")
    print(f"current task: {payload['current_task_id']}")
    print(f"last route decision: {payload['last_route_decision']}")
    print(f"delegation authorization: {payload['delegation_authorization'].get('status')}")
    print(f"next action execution mode: {payload['next_action'].get('execution_mode')}")
    if payload["next_action"].get("required_agents"):
        print(f"required spawned agents: {', '.join(payload['next_action']['required_agents'])}")
    print("blocked issues:")
    if payload["blocked_issues"]:
        for issue in payload["blocked_issues"]:
            print(f"- {issue}")
    else:
        print("- none")
    print(f"next recommended action: {payload['next_action']['instruction']}")
    print(f"artifact index: {payload['artifact_index']['index_path']}")
    if payload.get("expected_artifacts_by_event"):
        for event, artifacts in payload["expected_artifacts_by_event"].items():
            print(f"expected artifacts for {event}: {', '.join(artifacts)}")
            for item in payload.get("expected_artifact_paths_by_event", {}).get(event, []):
                print(f"  - {item['name']}: {item['path']}")
    elif payload["expected_artifacts_for_next_action"]:
        print(f"next expected artifacts: {', '.join(payload['expected_artifacts_for_next_action'])}")


def print_codex(payload: dict[str, Any]) -> None:
    gate = payload.get("open_gate")
    print("META-FLOW RESUME PACK")
    print(f"Task: {payload['task_id']}")
    print(f"Status: {payload['status']}")
    print(f"Internal phase: {payload['phase']}")
    print(f"User-facing stage: {payload['phase_label']}")
    print(f"Current milestone: {payload['current_milestone_id']}")
    print(f"Current task: {payload['current_task_id']}")
    print(f"Last route decision: {payload['last_route_decision']}")
    print(f"Delegation authorization: {payload['delegation_authorization'].get('status')}")
    print(f"Next action role: {payload['next_action']['role']}")
    print(f"Next action: {payload['next_action']['instruction']}")
    print(f"Completion event after the bounded step: {payload['next_action']['completion_event']}")
    print(f"Role execution mode: {payload['next_action'].get('execution_mode')}")
    if payload["next_action"].get("required_agents"):
        print(f"Required spawned agent(s): {', '.join(payload['next_action']['required_agents'])}")
        print("Main-agent boundary: do not perform this role locally and do not write this role's artifacts yourself.")
        if payload["next_action"].get("parallel_allowed"):
            print("Parallel delegation: spawn each listed agent separately; run them in parallel when the tool supports it.")
    if payload["next_action"].get("fallback_if_spawn_unavailable"):
        print(f"If spawning is unavailable: {payload['next_action']['fallback_if_spawn_unavailable']}")
    print(f"Artifact index: {payload['artifact_index']['index_path']} ({payload['artifact_index']['count']} entries)")
    if payload.get("expected_artifacts_by_event"):
        print("Expected artifacts by completion event:")
        for event, artifacts in payload["expected_artifacts_by_event"].items():
            print(f"- {event}: {', '.join(artifacts)}")
            for item in payload.get("expected_artifact_paths_by_event", {}).get(event, []):
                print(f"  - write {item['name']} to {item['path']}")
    elif payload["expected_artifacts_for_next_action"]:
        print(f"Expected artifacts for next action: {', '.join(payload['expected_artifacts_for_next_action'])}")
    if gate:
        print(f"Open gate: {gate.get('gate_id')} ({gate.get('type')})")
        print(f"Gate prompt: {gate.get('prompt', '')}")
    print("Instructions for Codex:")
    print("- Tell the user the current user-facing stage before doing work.")
    print("- Do only the next bounded action described above.")
    print("- If a delegation_authorization gate is open, ask the user to explicitly authorize sub-agents/delegation/parallel agent work for this task before spawning role agents.")
    print("- For spawn_agent_required actions, spawn the required custom agent(s); the main agent is only the orchestrator.")
    print("- Do not locally emulate meta-flow roles such as questioner, reviewers, adjudicator, planner, executor, verifier, or summarizers.")
    print("- If the spawn/subagent tool is unavailable or rejects delegation, stop and report the blocker instead of continuing locally.")
    print("- The main agent may run controller, validation, and review aggregation scripts after role agents write their artifacts.")
    print("- Write required artifacts to the listed by-node paths, then call meta-flow advance.")
    print("- Do not directly edit state.phase; call meta-flow advance after producing required artifacts.")
    print("- If a gate is open, ask for the user's decision and do not continue until it is decided.")
    print("- If an artifact is missing or invalid, explain the blocker and do not skip phases.")
    print(f"Allowed user actions: {', '.join(payload['allowed_user_actions'])}")


def render_payload(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif output_format == "codex":
        print_codex(payload)
    else:
        print_text(payload)


def resolve_event_for_target(state: dict[str, Any], event: str, target: str | None = None) -> str:
    if event != "manual" or not target:
        return event
    phase = state.get("phase")
    if target == "BLOCKED":
        return "block"
    matches = [name for name, mapping in TRANSITIONS.items() if mapping.get(phase) == target]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit(f"Transition from {phase} to {target} is not allowed.")
    raise SystemExit(f"Transition from {phase} to {target} is ambiguous; use --event explicitly.")


def transition_for(state: dict[str, Any], event: str, target: str | None = None) -> str:
    phase = state.get("phase")
    if event == "block":
        next_phase = "BLOCKED"
    else:
        mapping = TRANSITIONS.get(event)
        if not mapping:
            raise SystemExit(f"Unknown transition event: {event}")
        if phase not in mapping:
            raise SystemExit(f"Event {event} is not allowed from phase {phase}.")
        next_phase = mapping[phase]
    if target and next_phase != target:
        raise SystemExit(f"Event {event} routes from {phase} to {next_phase}, not {target}.")
    return next_phase


def enforce_loop_limits(state: dict[str, Any], event: str) -> None:
    if event == "adjudication_revise":
        current = int(state.get("proposal_review_round", 0)) + 1
        if current > int(state.get("max_proposal_rework_rounds", 3)):
            raise SystemExit("Proposal rework limit exceeded; route to block or ask_user.")
        state["proposal_review_round"] = current
    if event == "direction_adjust_goal":
        current = int(state.get("direction_adjustment_round", 0)) + 1
        if current > int(state.get("max_direction_adjustment_rounds", 2)):
            raise SystemExit("Direction adjustment limit exceeded; route to block or ask_user.")
        state["direction_adjustment_round"] = current
    if event == "verification_revise":
        task_id = state.get("current_repair_root_task_id") or state.get("current_task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise SystemExit("Cannot count task repair attempt; current_task_id is missing. Advance task_selected with a concrete_task_id first.")
        attempts = state.setdefault("task_repair_attempts", {})
        current = int(attempts.get(task_id, 0)) + 1
        if current > int(state.get("max_task_repair_rounds", 2)):
            raise SystemExit("Task repair limit exceeded; route to block or ask_user.")
        attempts[task_id] = current


def apply_context_from_task_payload(
    state: dict[str, Any],
    payload: Any,
    *,
    source_name: str = "task payload",
    require_task_selection: bool = False,
) -> None:
    if not isinstance(payload, dict):
        if require_task_selection:
            raise SystemExit(f"{source_name} must be a JSON object.")
        return
    milestone_id = payload.get("milestone_id")
    current_milestone_id = state.get("current_milestone_id")
    if require_task_selection and (not isinstance(milestone_id, str) or not milestone_id.strip()):
        raise SystemExit(f"{source_name}.milestone_id must be a non-empty string.")
    if (
        require_task_selection
        and isinstance(current_milestone_id, str)
        and current_milestone_id
        and isinstance(milestone_id, str)
        and milestone_id
        and milestone_id != current_milestone_id
    ):
        raise SystemExit(f"{source_name}.milestone_id must match current_milestone_id {current_milestone_id}.")
    if isinstance(milestone_id, str) and milestone_id:
        state["current_milestone_id"] = milestone_id
    concrete_task_id = payload.get("concrete_task_id")
    if require_task_selection and (not isinstance(concrete_task_id, str) or not concrete_task_id.strip()):
        raise SystemExit(f"{source_name}.concrete_task_id must be a non-empty string.")
    if isinstance(concrete_task_id, str) and concrete_task_id:
        state["current_task_id"] = concrete_task_id
        repair_root_task_id = payload.get("repairs_concrete_task_id")
        state["current_repair_root_task_id"] = (
            repair_root_task_id
            if isinstance(repair_root_task_id, str) and repair_root_task_id.strip()
            else concrete_task_id
        )


def milestone_ids_from_plan(task_dir: Path) -> list[str]:
    path = recorded_artifact_path(task_dir, "milestone-plan.json", event="milestone_plan_created", node="PLANNING")
    if not path and task_started_before_artifact_adoption(task_dir):
        path = latest_existing_path(legacy_artifact_candidates(task_dir, "milestone-plan.json"))
    if not path:
        return []
    data = load_json(path)
    if not isinstance(data, dict):
        return []
    milestones = data.get("milestones")
    if not isinstance(milestones, list):
        return []
    ids = []
    for milestone in milestones:
        if isinstance(milestone, dict) and isinstance(milestone.get("id"), str) and milestone["id"]:
            ids.append(milestone["id"])
    return ids


def select_first_milestone_from_plan(task_dir: Path, state: dict[str, Any]) -> None:
    ids = milestone_ids_from_plan(task_dir)
    if not ids:
        return
    state["current_milestone_id"] = ids[0]
    state["current_task_id"] = None
    state["current_repair_root_task_id"] = None


def select_next_milestone_from_plan(task_dir: Path, state: dict[str, Any]) -> None:
    ids = milestone_ids_from_plan(task_dir)
    if not ids:
        raise SystemExit("Cannot select next milestone; milestone-plan.json has no milestone ids.")
    current = state.get("current_milestone_id")
    if not isinstance(current, str) or current not in ids:
        raise SystemExit("Cannot select next milestone; current_milestone_id is not in milestone-plan.json.")
    index = ids.index(current)
    if index + 1 >= len(ids):
        raise SystemExit("Cannot select next milestone; current_milestone_id is already the final milestone.")
    state["current_milestone_id"] = ids[index + 1]
    state["current_task_id"] = None
    state["current_repair_root_task_id"] = None


def sync_current_context_from_artifacts(task_dir: Path, state: dict[str, Any], event: str, from_phase: str | None) -> None:
    if event == "plan_accepted":
        select_first_milestone_from_plan(task_dir, state)
        return
    if event == "milestone_selected":
        select_next_milestone_from_plan(task_dir, state)
        return
    if event == "tasks_decomposed":
        for spec in artifact_specs_for_event(event, from_phase):
            if spec.get("name") != "task-list.json":
                continue
            path = artifact_path_for_spec(task_dir, event, from_phase, spec)
            if path:
                apply_context_from_task_payload(state, load_json(path), source_name="task-list.json")
                state["current_task_id"] = None
                state["current_repair_root_task_id"] = None
        return
    if event == "task_selected":
        path = None
        for spec in artifact_specs_for_event(event, from_phase):
            if spec.get("name") == "task-spec.json":
                path = artifact_path_for_spec(task_dir, event, from_phase, spec)
                break
        if path:
            apply_context_from_task_payload(state, load_json(path), source_name="task-spec.json", require_task_selection=True)


def advance_task(root: Path, task_dir: Path, event: str, reason: str, target: str | None = None, artifact_refs_arg: list[str] | None = None) -> dict[str, Any]:
    state = load_state(task_dir)
    event = resolve_event_for_target(state, event, target)
    next_phase = transition_for(state, event, target)
    previous = state.get("phase")
    timestamp = now()
    if event == "goal_contract_drafted":
        ensure_legacy_questioning_report(task_dir, timestamp)
    enforce_delegation_authorization(task_dir, event, previous)
    missing = missing_required_artifacts(task_dir, event, previous)
    if missing:
        raise SystemExit(f"Cannot advance with {event}; missing required artifacts: {', '.join(missing)}")
    enforce_role_artifact_producers(task_dir, event, previous)
    enforce_questioning_clarification_gate(task_dir, event)
    enforce_gate_requirements(task_dir, event)
    sync_current_context_from_artifacts(task_dir, state, event, previous)
    enforce_loop_limits(state, event)
    recorded_refs = record_artifacts_for_event(task_dir, event, previous, "done", timestamp)
    decided_gate = decided_gate_for_event(task_dir, event)
    if decided_gate:
        recorded_refs.append(record_gate_artifact(task_dir, decided_gate, "done", event, timestamp))
    state["phase"] = next_phase
    state["updated_at"] = timestamp
    state["status"] = "done" if next_phase == "DONE" else ("blocked" if next_phase == "BLOCKED" else "active")
    state["last_route_decision"] = reason or f"Advanced by event {event}."
    state.setdefault("history", []).append({
        "at": timestamp,
        "from_phase": previous,
        "to_phase": next_phase,
        "reason": state["last_route_decision"],
    })
    write_json(task_dir / "state.json", state)
    refs = list(dict.fromkeys([*(artifact_refs_arg or []), *recorded_refs]))
    write_event(
        task_dir,
        {
            "at": timestamp,
            "actor": "controller",
            "event": event,
            "from_phase": previous,
            "to_phase": next_phase,
            "reason": state["last_route_decision"],
            "artifact_refs": refs,
        },
    )
    update_index(root, state, task_dir)
    if next_phase == "DONE":
        deactivate_task(root, state["task_id"])
    else:
        set_active_task(root, state, task_dir)
    return status_payload(task_dir)


def gate_id_for(gate_type: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{slugify(gate_type)}"


def open_gate_command(task_dir: Path, gate_type: str, prompt: str) -> dict[str, Any]:
    state = load_state(task_dir)
    timestamp = now()
    gate = {
        "gate_id": gate_id_for(gate_type),
        "type": gate_type,
        "task_id": state.get("task_id", task_dir.name),
        "phase": state.get("phase"),
        "status": "open",
        "prompt": prompt,
        "opened_at": timestamp,
        "decision": None,
        "decided_at": None,
        "comment": "",
    }
    gates_dir = task_dir / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    write_json(gates_dir / f"{gate['gate_id']}.json", gate)
    artifact_ref = record_gate_artifact(task_dir, gate, "open", "gate_opened", timestamp)
    write_event(task_dir, {
        "at": timestamp,
        "actor": "controller",
        "event": "gate_opened",
        "from_phase": state.get("phase"),
        "to_phase": state.get("phase"),
        "reason": prompt,
        "artifact_refs": [artifact_ref],
    })
    return gate


def apply_delegation_gate_decision(root: Path, task_dir: Path, gate: dict[str, Any], decision: str, comment: str, timestamp: str) -> None:
    if gate.get("type") != DELEGATION_GATE_TYPE:
        return
    state = load_state(task_dir)
    previous = state.get("phase", "UNKNOWN")
    authorization = delegation_authorization(state)
    authorization.update({
        "gate_id": gate.get("gate_id"),
        "decision": decision,
        "comment": comment,
    })
    if decision in DELEGATION_GATE_ACCEPT_DECISIONS:
        authorization["status"] = "approved"
        authorization["authorized_at"] = timestamp
        authorization["denied_at"] = None
        state["last_route_decision"] = "User authorized spawned role agents for this meta-flow task."
    else:
        authorization["status"] = "denied"
        authorization["authorized_at"] = None
        authorization["denied_at"] = timestamp
        state["phase"] = "BLOCKED"
        state["status"] = "blocked"
        state["last_route_decision"] = "User did not authorize spawned role agents; workflow blocked."
        state.setdefault("history", []).append({
            "at": timestamp,
            "from_phase": previous,
            "to_phase": "BLOCKED",
            "reason": state["last_route_decision"],
        })
    state["delegation_authorization"] = authorization
    state["updated_at"] = timestamp
    write_json(task_dir / "state.json", state)
    write_event(task_dir, {
        "at": timestamp,
        "actor": "controller",
        "event": "delegation_authorization_updated",
        "from_phase": previous,
        "to_phase": state.get("phase", previous),
        "reason": state["last_route_decision"],
        "artifact_refs": [],
    })
    update_index(root, state, task_dir)
    set_active_task(root, state, task_dir)


def decide_gate_command(root: Path, task_dir: Path, gate_id: str, decision: str, comment: str) -> dict[str, Any]:
    path = task_dir / "gates" / f"{gate_id}.json"
    if not path.exists():
        raise SystemExit(f"Gate not found: {gate_id}")
    gate = load_json(path)
    if gate.get("status") != "open":
        raise SystemExit(f"Gate is not open: {gate_id}")
    timestamp = now()
    gate["status"] = "decided"
    gate["decision"] = decision
    gate["decided_at"] = timestamp
    gate["comment"] = comment
    write_json(path, gate)
    state = load_state(task_dir)
    artifact_ref = record_gate_artifact(task_dir, gate, "decided", "gate_decided", timestamp)
    write_event(task_dir, {
        "at": timestamp,
        "actor": "user",
        "event": "gate_decided",
        "from_phase": state.get("phase"),
        "to_phase": state.get("phase"),
        "reason": f"{decision}: {comment}".strip(),
        "artifact_refs": [artifact_ref],
    })
    apply_delegation_gate_decision(root, task_dir, gate, decision, comment, timestamp)
    return gate


VALID_ARTIFACT_STATUSES = {"done", "open", "decided"}
VALID_ARTIFACT_TYPES = {"file", "gate"}
GATE_STATUS_BY_EVENT = {
    "gate_opened": "open",
    "gate_decided": "decided",
}
GATE_CONSUMING_EVENTS = set(REQUIRED_DECIDED_GATE_BY_EVENT)


def by_node_dir(task_dir: Path) -> Path:
    return artifacts_dir(task_dir) / "by-node"


def task_relative_existing_path(task_dir: Path, raw_path: Any, field: str, errors: list[str]) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path:
        errors.append(f"artifact entry missing {field}")
        return None
    value = Path(raw_path)
    if value.is_absolute():
        errors.append(f"{field} must be task-relative: {raw_path}")
        return None
    task_root = task_dir.resolve()
    path = (task_dir / value).resolve()
    try:
        path.relative_to(task_root)
    except ValueError:
        errors.append(f"{field} escapes task directory: {raw_path}")
        return None
    return path


def event_after_artifact_adoption(event: dict[str, Any], adopted_at: str | None) -> bool:
    if not adopted_at:
        return True
    event_at = event.get("at")
    if not isinstance(event_at, str):
        return True
    return event_at >= adopted_at


def expected_display_path_for_entry(task_dir: Path, entry: dict[str, Any]) -> str | None:
    node = entry.get("node")
    status = entry.get("status")
    name = entry.get("name")
    occurrence = entry.get("occurrence")
    event = entry.get("event")
    if not all(isinstance(value, str) and value for value in (node, status, name, event)):
        return None
    if not isinstance(occurrence, int) or occurrence < 1:
        return None
    display = display_artifact_path(task_dir, node, status, name, occurrence, event)
    return relative_to_task(task_dir, display)


def validate_artifact_index_header(index: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    if index.get("version") != WORKFLOW_VERSION:
        errors.append(f"artifact-index.json version must be {WORKFLOW_VERSION}: {index.get('version')}")
    if index.get("layout") not in {ARTIFACT_INDEX_LAYOUT, *LEGACY_ARTIFACT_INDEX_LAYOUTS}:
        errors.append(f"artifact-index.json layout must be {ARTIFACT_INDEX_LAYOUT}: {index.get('layout')}")
    for field in ("adopted_at", "updated_at"):
        if not isinstance(index.get(field), str) or not index.get(field):
            errors.append(f"artifact-index.json {field} must be a non-empty string")
    artifacts = index.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifact-index.json artifacts must be a list")
        return []
    return artifacts


def gate_status_for_event(event_name: str) -> str | None:
    if event_name in GATE_STATUS_BY_EVENT:
        return GATE_STATUS_BY_EVENT[event_name]
    if event_name in GATE_CONSUMING_EVENTS:
        return "done"
    return None


def gate_name_from_ref(ref: Any) -> str | None:
    if not isinstance(ref, str):
        return None
    path = Path(ref)
    if len(path.parts) != 2 or path.parts[0] != "gates" or path.suffix != ".json":
        return None
    return path.name


def validate_gate_artifact_entry(entry: dict[str, Any], display: Path | None, errors: list[str]) -> None:
    event_name = entry.get("event")
    status = entry.get("status")
    name = entry.get("name")
    if not isinstance(event_name, str):
        return
    expected_status = gate_status_for_event(event_name)
    if not expected_status:
        errors.append(f"gate artifact event is not allowed for {name}: {event_name}")
        return
    if status != expected_status:
        errors.append(f"gate artifact status mismatch for {name}: {event_name} must use {expected_status}, got {status}")
    if not display or not display.exists():
        return
    try:
        display_payload = load_json(display)
    except Exception as exc:
        errors.append(f"gate display artifact is not valid JSON: {entry.get('display_path')} ({exc})")
        return
    if not isinstance(display_payload, dict):
        errors.append(f"gate display artifact must be an object: {entry.get('display_path')}")
        return
    expected_payload_status = "open" if event_name == "gate_opened" else "decided"
    if display_payload.get("status") != expected_payload_status:
        errors.append(
            f"gate display status mismatch for {name}: {event_name} must snapshot {expected_payload_status}, got {display_payload.get('status')}"
        )


def validate_artifacts(task_dir: Path) -> dict[str, Any]:
    index_exists = artifact_index_path(task_dir).exists()
    if not index_exists:
        errors = []
        if by_node_dir(task_dir).exists():
            errors.append("artifact-index.json is missing while artifacts/by-node layout exists")
        if errors:
            return {
                "ok": False,
                "task_dir": str(task_dir),
                "artifact_index": str(artifact_index_path(task_dir)),
                "artifact_count": 0,
                "legacy_without_index": False,
                "warnings": [],
                "errors": errors,
            }
        return {
            "ok": True,
            "task_dir": str(task_dir),
            "artifact_index": str(artifact_index_path(task_dir)),
            "artifact_count": 0,
            "legacy_without_index": True,
            "warnings": [
                "artifact-index.json is missing; treating this as a legacy task created before by-node artifacts."
            ],
            "errors": [],
        }

    errors = []
    warnings = []
    index = load_json(artifact_index_path(task_dir))
    if not isinstance(index, dict):
        index = {}
        errors.append("artifact-index.json must be an object")
    artifacts = validate_artifact_index_header(index, errors)
    layout = index.get("layout")
    by_node_only_layout = layout == ARTIFACT_INDEX_LAYOUT
    legacy_task = task_started_before_artifact_adoption(task_dir)

    seen_sequences = set()
    seen_display_paths = set()
    latest_entry_by_canonical: dict[str, dict[str, Any]] = {}
    for position, entry in enumerate(artifacts, start=1):
        if not isinstance(entry, dict):
            errors.append("artifact entry must be an object")
            continue
        for field in ("event", "node", "node_key", "status", "name", "source_path", "canonical_path", "display_path", "content_sha256"):
            if not entry.get(field):
                errors.append(f"artifact entry missing {field}: {entry}")
        artifact_type = entry.get("artifact_type")
        if artifact_type not in VALID_ARTIFACT_TYPES:
            errors.append(f"invalid artifact type for {entry.get('name')}: {artifact_type}")
        sequence = entry.get("sequence")
        if not isinstance(sequence, int):
            errors.append(f"artifact entry sequence must be an integer: {entry.get('name')}")
        else:
            if sequence in seen_sequences:
                errors.append(f"duplicate artifact sequence: {sequence}")
            seen_sequences.add(sequence)
            if sequence != position:
                errors.append(f"artifact sequence mismatch at position {position}: got {sequence}")
        status = entry.get("status")
        if status not in VALID_ARTIFACT_STATUSES:
            errors.append(f"invalid artifact status for {entry.get('name')}: {status}")
        occurrence = entry.get("occurrence")
        if not isinstance(occurrence, int) or occurrence < 1:
            errors.append(f"artifact occurrence must be a positive integer: {entry.get('name')}")
        source = task_relative_existing_path(task_dir, entry.get("source_path"), "source_path", errors)
        canonical = task_relative_existing_path(task_dir, entry.get("canonical_path"), "canonical_path", errors)
        display = task_relative_existing_path(task_dir, entry.get("display_path"), "display_path", errors)
        if source and not source.exists():
            errors.append(f"source artifact missing: {entry.get('source_path')}")
        if canonical and not canonical.exists():
            errors.append(f"canonical artifact missing: {entry.get('canonical_path')}")
        if by_node_only_layout and entry.get("artifact_type") == "file" and entry.get("canonical_path") != entry.get("display_path"):
            errors.append(f"canonical path must equal display path for by-node machine contract: {entry.get('name')}")
        if display:
            display_key = str(Path(entry.get("display_path", "")))
            if display_key in seen_display_paths:
                errors.append(f"duplicate display artifact path: {display_key}")
            seen_display_paths.add(display_key)
        if display and not display.exists():
            errors.append(f"display artifact missing: {entry.get('display_path')}")
        if display and display.exists():
            expected_hash = entry.get("content_sha256")
            actual_hash = content_sha256(display)
            if isinstance(expected_hash, str) and expected_hash != actual_hash:
                errors.append(f"display artifact hash mismatch: {entry.get('display_path')}")
            if not legacy_task:
                event_name = str(entry.get("event"))
                name = str(entry.get("name"))
                node_name = str(entry.get("node"))
                expected_json_agent = expected_json_producer_for_entry(event_name, node_name, name)
                if expected_json_agent:
                    for error in validate_json_producer(display, expected_json_agent):
                        errors.append(f"{entry.get('display_path')}: {error}")
                expected_markdown_agent = expected_markdown_producer_for_entry(event_name, node_name, name)
                if expected_markdown_agent:
                    for error in validate_markdown_producer(display, expected_markdown_agent):
                        errors.append(f"{entry.get('display_path')}: {error}")
                if name == "review-aggregate.json":
                    for error in validate_review_aggregate(display):
                        errors.append(f"{entry.get('display_path')}: {error}")
        expected_display = expected_display_path_for_entry(task_dir, entry)
        if expected_display and entry.get("display_path") != expected_display:
            errors.append(f"display path mismatch for {entry.get('name')}: {entry.get('display_path')} != {expected_display}")
        if canonical:
            latest_entry_by_canonical[str(Path(entry.get("canonical_path", "")))] = entry
        node = entry.get("node")
        if isinstance(node, str) and entry.get("node_key") != node_key(node):
            errors.append(f"node_key mismatch for {entry.get('name')}: {entry.get('node_key')} != {node_key(node)}")
        if isinstance(node, str) and entry.get("node_order") != node_order(node):
            errors.append(f"node_order mismatch for {entry.get('name')}: {entry.get('node_order')} != {node_order(node)}")
        if artifact_type == "gate":
            validate_gate_artifact_entry(entry, display, errors)

    for canonical_path, entry in latest_entry_by_canonical.items():
        canonical = task_dir / canonical_path
        expected_hash = entry.get("content_sha256")
        if canonical.exists() and isinstance(expected_hash, str) and content_sha256(canonical) != expected_hash:
            warnings.append(f"canonical artifact is newer than historical display for {entry.get('name')}: {canonical_path}")

    events = read_events(task_dir)
    adopted_at = index.get("adopted_at") if isinstance(index.get("adopted_at"), str) else None
    relevant_events = [event for event in events if event_after_artifact_adoption(event, adopted_at)]
    expected_counts: dict[tuple[str, str, str, str], int] = {}
    for event in relevant_events:
        event_name = event.get("event")
        from_phase = event.get("from_phase")
        if not isinstance(event_name, str):
            continue
        if not isinstance(from_phase, str):
            from_phase = None
        for spec in artifact_specs_for_event(event_name, from_phase):
            key = (event_name, spec["name"], artifact_phase_for_spec(spec, from_phase), "done")
            expected_counts[key] = expected_counts.get(key, 0) + 1
    actual_counts: dict[tuple[str, str, str, str], int] = {}
    expected_gate_counts: dict[tuple[str, str, str, str], int] = {}
    for entry in artifacts:
        if not isinstance(entry, dict) or entry.get("artifact_type") != "file":
            continue
        key = (
            str(entry.get("event")),
            str(entry.get("name")),
            str(entry.get("node")),
            str(entry.get("status")),
        )
        actual_counts[key] = actual_counts.get(key, 0) + 1
    actual_gate_counts: dict[tuple[str, str, str, str], int] = {}
    for entry in artifacts:
        if not isinstance(entry, dict) or entry.get("artifact_type") != "gate":
            continue
        key = (
            str(entry.get("event")),
            str(entry.get("name")),
            str(entry.get("node")),
            str(entry.get("status")),
        )
        actual_gate_counts[key] = actual_gate_counts.get(key, 0) + 1
    for event in relevant_events:
        event_name = event.get("event")
        from_phase = event.get("from_phase")
        if not isinstance(event_name, str) or not isinstance(from_phase, str):
            continue
        gate_status = gate_status_for_event(event_name)
        if not gate_status:
            continue
        for ref in event.get("artifact_refs", []):
            gate_name = gate_name_from_ref(ref)
            if not gate_name:
                continue
            key = (event_name, gate_name, from_phase, gate_status)
            expected_gate_counts[key] = expected_gate_counts.get(key, 0) + 1
    for key, expected_count in expected_counts.items():
        actual_count = actual_counts.get(key, 0)
        if actual_count != expected_count:
            event_name, name, phase, status = key
            errors.append(f"artifact index count mismatch {event_name}:{name}:{phase}:{status}; expected {expected_count}, got {actual_count}")
    for key, actual_count in actual_counts.items():
        if key not in expected_counts:
            event_name, name, phase, status = key
            errors.append(f"unexpected artifact index entry {event_name}:{name}:{phase}:{status}; got {actual_count}")
    for key, expected_count in expected_gate_counts.items():
        actual_count = actual_gate_counts.get(key, 0)
        if actual_count != expected_count:
            event_name, name, phase, status = key
            errors.append(f"gate artifact index count mismatch {event_name}:{name}:{phase}:{status}; expected {expected_count}, got {actual_count}")
    for key, actual_count in actual_gate_counts.items():
        if key not in expected_gate_counts:
            event_name, name, phase, status = key
            errors.append(f"unexpected gate artifact index entry {event_name}:{name}:{phase}:{status}; got {actual_count}")

    for event in relevant_events:
        for ref in event.get("artifact_refs", []):
            if not (task_dir / ref).exists():
                errors.append(f"event artifact ref missing: {ref}")

    return {
        "ok": not errors,
        "task_dir": str(task_dir),
        "artifact_index": str(artifact_index_path(task_dir)),
        "artifact_count": len(artifacts),
        "legacy_without_index": False,
        "warnings": warnings,
        "errors": errors,
    }


def render_artifact_validation(result: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"artifact index: {result['artifact_index']}")
    print(f"artifact count: {result['artifact_count']}")
    if result.get("warnings"):
        print("warnings:")
        for warning in result["warnings"]:
            print(f"- {warning}")
    if result["ok"]:
        print("artifact layout: ok")
    else:
        print("artifact layout: failed")
        for error in result["errors"]:
            print(f"- {error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the meta-flow controller.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Meta-flow runtime root. Defaults to META_FLOW_ROOT or ~/.meta-flow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start a new meta-flow task.")
    start.add_argument("raw_request", nargs="?", help="Raw user request text.")
    start.add_argument("--raw-request-file", type=Path, help="File containing raw request text.")
    start.add_argument("--task-id", help="Override generated task id.")
    start.add_argument("--format", choices=["text", "json", "codex"], default="text")

    resume = subparsers.add_parser("resume", help="Resume the active or specified task.")
    resume.add_argument("task", nargs="?", help="Task id or task directory.")
    resume.add_argument("--format", choices=["text", "json", "codex"], default="text")

    status = subparsers.add_parser("status", help="Print task status.")
    status.add_argument("task", nargs="?", help="Task id or task directory.")
    status.add_argument("--format", choices=["text", "json", "codex"], default="text")
    status.add_argument("--json", action="store_true", help="Alias for --format json.")

    advance = subparsers.add_parser("advance", help="Advance a task through an allowed transition.")
    advance.add_argument("task", nargs="?", help="Task id or task directory.")
    advance.add_argument("--event", default="manual", help="Transition event.")
    advance.add_argument("--to", help="Target phase. Must be allowed from the current phase.")
    advance.add_argument("--reason", default="", help="Reason for the transition.")
    advance.add_argument("--artifact-ref", action="append", default=[], help="Artifact reference to record in the event log.")
    advance.add_argument("--format", choices=["text", "json", "codex"], default="text")

    gate = subparsers.add_parser("gate", help="Open or decide a human gate.")
    gate_subparsers = gate.add_subparsers(dest="gate_command", required=True)
    gate_open = gate_subparsers.add_parser("open", help="Open a human gate.")
    gate_open.add_argument("task", nargs="?", help="Task id or task directory.")
    gate_open.add_argument("--type", required=True, help="Gate type.")
    gate_open.add_argument("--prompt", required=True, help="Prompt to show the user.")
    gate_open.add_argument("--format", choices=["text", "json"], default="text")
    gate_decide = gate_subparsers.add_parser("decide", help="Record a human gate decision.")
    gate_decide.add_argument("task", nargs="?", help="Task id or task directory.")
    gate_decide.add_argument("--gate", required=True, help="Gate id.")
    gate_decide.add_argument("--decision", required=True, choices=["accept", "reject", "revise", "pause", "abort"], help="Gate decision.")
    gate_decide.add_argument("--comment", default="", help="Decision comment.")
    gate_decide.add_argument("--format", choices=["text", "json"], default="text")

    artifacts = subparsers.add_parser("artifacts", help="Inspect or validate artifact layout.")
    artifacts_subparsers = artifacts.add_subparsers(dest="artifacts_command", required=True)
    artifacts_validate = artifacts_subparsers.add_parser("validate", help="Validate artifact index and by-node layout.")
    artifacts_validate.add_argument("task", nargs="?", help="Task id or task directory.")
    artifacts_validate.add_argument("--format", choices=["text", "json"], default="text")

    abandon = subparsers.add_parser("abandon", help="Abandon a task and keep its artifacts for audit.")
    abandon.add_argument("task", nargs="?", help="Task id or task directory.")
    abandon.add_argument("--reason", default="", help="Reason for abandoning the task.")
    abandon.add_argument("--format", choices=["text", "json", "codex"], default="text")

    deactivate = subparsers.add_parser("deactivate", help="Deactivate the active task without changing task state.")
    deactivate.add_argument("task", nargs="?", help="Task id or task directory.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = root_from(args.root)
    if args.command == "start":
        task_dir = start_task(root, read_raw_request(args), args.task_id)
        payload = status_payload(task_dir)
        if args.format == "text":
            print(task_dir)
        else:
            render_payload(payload, args.format)
        return 0
    if args.command in {"resume", "status"}:
        output_format = "json" if getattr(args, "json", False) else args.format
        render_payload(status_payload(resolve_task_dir(root, args.task)), output_format)
        return 0
    if args.command == "advance":
        if args.event == "manual" and not args.to:
            raise SystemExit("advance requires --event or --to")
        payload = advance_task(root, resolve_task_dir(root, args.task), args.event, args.reason, args.to, args.artifact_ref)
        render_payload(payload, args.format)
        return 0
    if args.command == "gate":
        task_dir = resolve_task_dir(root, args.task)
        if args.gate_command == "open":
            result = open_gate_command(task_dir, args.type, args.prompt)
        else:
            result = decide_gate_command(root, task_dir, args.gate, args.decision, args.comment)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["gate_id"])
        return 0
    if args.command == "artifacts":
        task_dir = resolve_task_dir(root, args.task)
        if args.artifacts_command == "validate":
            result = validate_artifacts(task_dir)
            render_artifact_validation(result, args.format)
            return 0 if result["ok"] else 1
    if args.command == "abandon":
        payload = abandon_task(root, resolve_task_dir(root, args.task), args.reason)
        if args.format == "text":
            print(f"abandoned: {payload['task_id']}")
        else:
            render_payload(payload, args.format)
        return 0
    if args.command == "deactivate":
        task_dir = resolve_task_dir(root, args.task)
        state = load_state(task_dir)
        deactivate_task(root, state.get("task_id", task_dir.name))
        print(f"deactivated: {state.get('task_id', task_dir.name)}")
        return 0
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
