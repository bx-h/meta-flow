#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from _common import write_json


ROOT = Path(os.environ.get("META_FLOW_ROOT", Path.cwd() / ".meta-flow"))
DEFAULT_TASKS_ROOT = ROOT / "tasks"


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:48] or "task"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a new meta-flow task directory.")
    parser.add_argument("raw_request", nargs="?", help="Raw user request text.")
    parser.add_argument("--raw-request-file", type=Path, help="File containing raw request text.")
    parser.add_argument("--task-id", help="Override generated task id.")
    parser.add_argument("--tasks-root", type=Path, default=DEFAULT_TASKS_ROOT, help="Task root directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.raw_request and args.raw_request_file:
        raise SystemExit("Use either raw_request or --raw-request-file, not both.")
    if args.raw_request_file:
        raw_request = args.raw_request_file.read_text(encoding="utf-8")
    elif args.raw_request:
        raw_request = args.raw_request
    else:
        raise SystemExit("A raw request is required.")

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    task_id = args.task_id or f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{slugify(raw_request)}"
    task_dir = args.tasks_root / task_id
    task_dir.mkdir(parents=True, exist_ok=False)

    state = {
        "task_id": task_id,
        "phase": "INTAKE",
        "created_at": now,
        "updated_at": now,
        "proposal_review_round": 0,
        "direction_adjustment_round": 0,
        "current_milestone_id": None,
        "current_task_id": None,
        "max_proposal_rework_rounds": 3,
        "max_task_repair_rounds": 2,
        "max_direction_adjustment_rounds": 2,
        "status": "active",
        "last_route_decision": "Task initialized from raw request.",
        "history": [
            {
                "at": now,
                "from_phase": "NONE",
                "to_phase": "INTAKE",
                "reason": "Raw request captured.",
            }
        ],
    }

    write_json(task_dir / "state.json", state)
    (task_dir / "raw-request.md").write_text(raw_request.rstrip() + "\n", encoding="utf-8")
    print(task_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
