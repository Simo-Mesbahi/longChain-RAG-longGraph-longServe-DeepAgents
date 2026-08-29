"""Dry-run template for moving the local dataset into LangSmith."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_course.langsmith_evaluation import load_langsmith_dataset, sync_examples_to_langsmith

ROOT_DIR = Path(__file__).resolve().parents[3]
DATASET_PATH = (
    ROOT_DIR
    / "projects"
    / "04-langsmith-quality-monitoring"
    / "evaluation"
    / "langsmith_cases.jsonl"
)
DATASET_NAME = "Asteria Investigation Workflow Quality"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare or run a LangSmith dataset sync.")
    parser.add_argument("--run-sync", action="store_true")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--dataset-name", default=DATASET_NAME)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    examples = load_langsmith_dataset(args.dataset)
    if not args.run_sync:
        print(
            json.dumps(
                {
                    "mode": "dry-run",
                    "dataset_name": args.dataset_name,
                    "examples": len(examples),
                    "next_step": "Run with --run-sync after configuring LangSmith credentials.",
                },
                indent=2,
            )
        )
        return 0

    result = sync_examples_to_langsmith(
        examples,
        dataset_name=args.dataset_name,
        description="Evaluation cases for the course LangGraph investigation workflow.",
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
