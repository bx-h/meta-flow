#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _common import fail, load_json, write_json


ROOT = Path(os.environ.get("META_FLOW_ROOT", Path.cwd() / ".meta-flow"))
WORKFLOW_VERSION = "1"


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
        "instruction": "Resolve blocking questions or record assumptions, then produce goal-contract.json.",
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
        "instruction": "Validate task-list.json and select the next concrete task.",
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
        "role": "executor",
        "instruction": "Run the minimal repair requested by the verifier.",
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

REQUIRED_ARTIFACTS_BY_EVENT = {
    "goal_contract_drafted": ["goal-contract.json"],
    "proposal_created": ["proposal.md"],
    "reviews_aggregated": ["review-aggregate.json"],
    "adjudication_accept": ["adjudication-report.json"],
    "adjudication_revise": ["adjudication-report.json"],
    "proposal_summarized": ["proposal-summary.md"],
    "milestone_plan_created": ["milestone-plan.json"],
    "tasks_decomposed": ["task-list.json"],
    "task_executed": ["task-execution-report.json"],
    "verification_passed": ["task-verification-report.json"],
    "verification_revise": ["task-verification-report.json"],
    "milestone_completed": ["direction-evaluation.json"],
    "direction_continue": ["direction-evaluation.json"],
    "direction_replan": ["direction-evaluation.json"],
    "direction_adjust_goal": ["direction-evaluation.json"],
    "direction_final": ["direction-evaluation.json"],
    "final_summarized": ["final-report.md"],
}

REQUIRED_DECIDED_GATE_BY_EVENT = {
    "proposal_accepted": {"types": ["proposal_confirmation"], "decisions": ["accept"]},
    "plan_accepted": {"types": ["plan_confirmation"], "decisions": ["accept"]},
    "goal_adjustment_confirmed": {"types": ["goal_adjustment"], "decisions": ["accept"]},
    "final_accepted": {"types": ["final_confirmation"], "decisions": ["accept"]},
}


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


def write_event(task_dir: Path, event: dict[str, Any]) -> None:
    events_path = task_dir / "events.ndjson"
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


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
        "max_proposal_rework_rounds": 3,
        "max_task_repair_rounds": 2,
        "max_direction_adjustment_rounds": 2,
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
    (task_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (task_dir / "gates").mkdir(parents=True, exist_ok=True)
    (task_dir / "runs").mkdir(parents=True, exist_ok=True)

    state = initial_state(resolved_task_id, timestamp)
    write_json(task_dir / "state.json", state)
    text = raw_request.rstrip() + "\n"
    (task_dir / "raw-request.md").write_text(text, encoding="utf-8")
    (task_dir / "artifacts" / "raw-request.md").write_text(text, encoding="utf-8")
    write_event(
        task_dir,
        {
            "at": timestamp,
            "actor": "controller",
            "event": "task_started",
            "from_phase": "NONE",
            "to_phase": "INTAKE",
            "reason": "Raw request captured.",
            "artifact_refs": ["raw-request.md", "artifacts/raw-request.md"],
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
    candidates = [
        task_dir / name,
        task_dir / "artifacts" / name,
    ]
    if "/" in name:
        candidates.append(task_dir / name)
    return any(path.exists() for path in candidates)


def missing_required_artifacts(task_dir: Path, event: str) -> list[str]:
    return [name for name in REQUIRED_ARTIFACTS_BY_EVENT.get(event, []) if not artifact_exists(task_dir, name)]


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
    refs = []
    for name in (
        "raw-request.md",
        "goal-contract.json",
        "proposal.md",
        "review-aggregate.json",
        "adjudication-report.json",
        "proposal-summary.md",
        "milestone-plan.json",
        "final-report.md",
    ):
        if artifact_exists(task_dir, name):
            refs.append(name)
    return refs


def status_payload(task_dir: Path) -> dict[str, Any]:
    state = load_state(task_dir)
    phase = state.get("phase", "UNKNOWN")
    gate = open_gate(task_dir)
    return {
        "task_id": state.get("task_id", task_dir.name),
        "task_dir": str(task_dir),
        "status": state.get("status", "unknown"),
        "phase": phase,
        "phase_label": PHASE_LABELS.get(phase, phase),
        "current_milestone_id": state.get("current_milestone_id"),
        "current_task_id": state.get("current_task_id"),
        "last_route_decision": state.get("last_route_decision", ""),
        "open_gate": gate,
        "next_action": NEXT_ACTION_BY_PHASE.get(phase, {
            "kind": "inspect",
            "role": "main_agent",
            "instruction": "Inspect state.json and route manually.",
            "completion_event": "",
        }),
        "allowed_user_actions": allowed_user_actions(phase, gate),
        "blocked_issues": collect_blocked_issues(task_dir),
        "artifact_refs": artifact_refs(task_dir),
    }


def allowed_user_actions(phase: str, gate: dict[str, Any] | None) -> list[str]:
    if gate:
        return ["接受", "拒绝", "修改目标", "暂停"]
    if phase in {"DONE"}:
        return ["开始新任务", "查看最终报告"]
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
    print("blocked issues:")
    if payload["blocked_issues"]:
        for issue in payload["blocked_issues"]:
            print(f"- {issue}")
    else:
        print("- none")
    print(f"next recommended action: {payload['next_action']['instruction']}")


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
    print(f"Next action role: {payload['next_action']['role']}")
    print(f"Next action: {payload['next_action']['instruction']}")
    print(f"Completion event after the bounded step: {payload['next_action']['completion_event']}")
    if gate:
        print(f"Open gate: {gate.get('gate_id')} ({gate.get('type')})")
        print(f"Gate prompt: {gate.get('prompt', '')}")
    print("Instructions for Codex:")
    print("- Tell the user the current user-facing stage before doing work.")
    print("- Do only the next bounded action described above.")
    print("- Do not directly edit state.phase; call controller.py advance after producing required artifacts.")
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
        task_id = state.get("current_task_id") or "__unassigned__"
        attempts = state.setdefault("task_repair_attempts", {})
        current = int(attempts.get(task_id, 0)) + 1
        if current > int(state.get("max_task_repair_rounds", 2)):
            raise SystemExit("Task repair limit exceeded; route to block or ask_user.")
        attempts[task_id] = current


def advance_task(root: Path, task_dir: Path, event: str, reason: str, target: str | None = None, artifact_refs_arg: list[str] | None = None) -> dict[str, Any]:
    state = load_state(task_dir)
    event = resolve_event_for_target(state, event, target)
    next_phase = transition_for(state, event, target)
    missing = missing_required_artifacts(task_dir, event)
    if missing:
        raise SystemExit(f"Cannot advance with {event}; missing required artifacts: {', '.join(missing)}")
    enforce_gate_requirements(task_dir, event)
    previous = state.get("phase")
    enforce_loop_limits(state, event)
    timestamp = now()
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
    refs = artifact_refs_arg or REQUIRED_ARTIFACTS_BY_EVENT.get(event, [])
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
    write_event(task_dir, {
        "at": timestamp,
        "actor": "controller",
        "event": "gate_opened",
        "from_phase": state.get("phase"),
        "to_phase": state.get("phase"),
        "reason": prompt,
        "artifact_refs": [f"gates/{gate['gate_id']}.json"],
    })
    return gate


def decide_gate_command(task_dir: Path, gate_id: str, decision: str, comment: str) -> dict[str, Any]:
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
    write_event(task_dir, {
        "at": timestamp,
        "actor": "user",
        "event": "gate_decided",
        "from_phase": state.get("phase"),
        "to_phase": state.get("phase"),
        "reason": f"{decision}: {comment}".strip(),
        "artifact_refs": [f"gates/{gate_id}.json"],
    })
    return gate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the meta-flow controller.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Meta-flow root directory. Defaults to .meta-flow or META_FLOW_ROOT.")
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

    deactivate = subparsers.add_parser("deactivate", help="Deactivate the active task.")
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
            result = decide_gate_command(task_dir, args.gate, args.decision, args.comment)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["gate_id"])
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
