#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from controller import ROOT, render_payload, resolve_task_dir, status_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print current meta-flow task status.")
    parser.add_argument("task", type=Path, nargs="?", help="Task directory path, task id, or omitted for the active task.")
    parser.add_argument("--format", choices=["text", "json", "codex"], default="text")
    parser.add_argument("--json", action="store_true", help="Alias for --format json.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_format = "json" if args.json else args.format
    task_value = str(args.task) if args.task else None
    render_payload(status_payload(resolve_task_dir(ROOT, task_value)), output_format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
