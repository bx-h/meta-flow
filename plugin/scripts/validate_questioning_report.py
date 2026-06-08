#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from _common import fail, load_json, ok, require_dict, require_list, require_non_empty_string


VALID_ANSWER_SOURCES = {"user_required", "codebase_checked", "safe_default"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a meta-flow questioning-report.json file.")
    parser.add_argument("path", type=Path, nargs="?", default=Path("questioning-report.json"))
    return parser.parse_args()


def main() -> int:
    data = require_dict(load_json(parse_args().path), "questioning report", errors := [])

    producer = require_dict(data.get("producer"), "producer", errors)
    if producer.get("agent_name") != "questioner":
        errors.append("producer.agent_name must be questioner")
    if producer.get("execution_mode") != "spawned_agent":
        errors.append("producer.execution_mode must be spawned_agent")

    require_non_empty_string(data, "task_id", errors)
    require_non_empty_string(data, "raw_user_request", errors)
    require_list(data.get("known_information"), "known_information", errors)
    missing_information = require_list(data.get("missing_information"), "missing_information", errors)
    assumptions = require_list(data.get("assumptions_if_user_does_not_answer"), "assumptions_if_user_does_not_answer", errors)
    if not isinstance(data.get("can_continue_without_user_answer"), bool):
        errors.append("can_continue_without_user_answer must be a boolean")

    questions = require_list(data.get("clarifying_questions"), "clarifying_questions", errors)
    question_ids: set[str] = set()
    for idx, question in enumerate(questions, start=1):
        item = require_dict(question, f"clarifying_questions[{idx}]", errors)
        for key in ("question", "why_it_matters"):
            require_non_empty_string(item, key, errors)
        question_id = item.get("id")
        if isinstance(question_id, str) and question_id.strip():
            if question_id in question_ids:
                errors.append(f"clarifying_questions[{idx}].id must be unique")
            question_ids.add(question_id)
        if not isinstance(item.get("blocking"), bool):
            errors.append(f"clarifying_questions[{idx}].blocking must be a boolean")

        optional_string_keys = ("decision_axis", "recommended_answer", "answer_source")
        has_rich_metadata = any(key in item for key in ("id", "depends_on", *optional_string_keys))
        if has_rich_metadata:
            if not isinstance(question_id, str) or not question_id.strip():
                errors.append(f"clarifying_questions[{idx}].id must be a non-empty string when rich metadata is present")
            for key in optional_string_keys:
                require_non_empty_string(item, key, errors)
            depends_on = require_list(item.get("depends_on"), f"clarifying_questions[{idx}].depends_on", errors)
            for ref in depends_on:
                if not isinstance(ref, str) or not ref.strip():
                    errors.append(f"clarifying_questions[{idx}].depends_on entries must be non-empty strings")
            if item.get("answer_source") not in VALID_ANSWER_SOURCES:
                errors.append(f"clarifying_questions[{idx}].answer_source must be one of {sorted(VALID_ANSWER_SOURCES)}")

    for idx, question in enumerate(questions, start=1):
        item = question if isinstance(question, dict) else {}
        for ref in item.get("depends_on", []) if isinstance(item.get("depends_on"), list) else []:
            if isinstance(ref, str) and ref not in question_ids:
                errors.append(f"clarifying_questions[{idx}].depends_on references unknown question id {ref}")

    decision_tree_raw = data.get("decision_tree", [])
    decision_tree = require_list(decision_tree_raw, "decision_tree", errors)
    for idx, decision in enumerate(decision_tree, start=1):
        item = require_dict(decision, f"decision_tree[{idx}]", errors)
        for key in ("axis", "known", "open_decision", "recommended_default"):
            require_non_empty_string(item, key, errors)
        question_refs = require_list(item.get("question_refs"), f"decision_tree[{idx}].question_refs", errors)
        downstream = require_list(item.get("downstream_effect"), f"decision_tree[{idx}].downstream_effect", errors)
        if not question_refs:
            errors.append(f"decision_tree[{idx}].question_refs must not be empty")
        if not downstream:
            errors.append(f"decision_tree[{idx}].downstream_effect must not be empty")
        for ref in question_refs:
            if not isinstance(ref, str) or not ref.strip():
                errors.append(f"decision_tree[{idx}].question_refs entries must be non-empty strings")
            elif ref not in question_ids:
                errors.append(f"decision_tree[{idx}].question_refs references unknown question id {ref}")
        for effect in downstream:
            if not isinstance(effect, str) or not effect.strip():
                errors.append(f"decision_tree[{idx}].downstream_effect entries must be non-empty strings")

    if questions and data.get("can_continue_without_user_answer") is True and not assumptions:
        errors.append("assumptions_if_user_does_not_answer must explain the default path when questions remain but can_continue_without_user_answer is true")
    if missing_information and data.get("can_continue_without_user_answer") is True and not assumptions:
        errors.append("assumptions_if_user_does_not_answer must explain the default path when missing_information remains but can_continue_without_user_answer is true")

    if errors:
        fail(errors)
    ok(f"OK: questioning report valid ({len(questions)} questions, {len(decision_tree)} decision-tree entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
