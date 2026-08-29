"""Export the project dataset to a LangSmith bulk-create JSONL shape."""

from __future__ import annotations

import json
from pathlib import Path

from ai_course.langsmith_evaluation import (
    load_langsmith_dataset,
    write_langsmith_dataset_export,
)

ROOT_DIR = Path(__file__).resolve().parents[3]
DATASET_PATH = (
    ROOT_DIR
    / "projects"
    / "04-langsmith-quality-monitoring"
    / "evaluation"
    / "langsmith_cases.jsonl"
)
OUTPUT_PATH = ROOT_DIR / ".local" / "langsmith_dataset_export.jsonl"


def main() -> int:
    examples = load_langsmith_dataset(DATASET_PATH)
    path = write_langsmith_dataset_export(examples, OUTPUT_PATH)
    print(json.dumps({"path": str(path), "examples": len(examples)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
