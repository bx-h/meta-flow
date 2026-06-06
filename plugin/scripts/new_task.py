#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from controller import ROOT, read_raw_request, start_task, tasks_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a new meta-flow task directory.")
    parser.add_argument("raw_request", nargs="?", help="Raw user request text.")
    parser.add_argument("--raw-request-file", type=Path, help="File containing raw request text.")
    parser.add_argument("--task-id", help="Override generated task id.")
    parser.add_argument("--tasks-root", type=Path, default=tasks_root(ROOT), help="Task root directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.tasks_root.parent
    task_dir = start_task(root, read_raw_request(args), args.task_id)
    print(task_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
