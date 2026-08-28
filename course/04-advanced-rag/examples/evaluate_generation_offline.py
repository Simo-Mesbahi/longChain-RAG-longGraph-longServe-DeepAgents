"""Evaluate saved RAG predictions without calling an LLM."""

from pathlib import Path

from ai_course.rag_evaluation import (
    evaluate_generation,
    load_generation_evaluation_dataset,
    load_generation_predictions,
)

ROOT_DIR = Path(__file__).resolve().parents[3]
PROJECT_DIR = ROOT_DIR / "projects" / "02-documentary-rag-assistant"


def main() -> int:
    examples = load_generation_evaluation_dataset(PROJECT_DIR / "evaluation" / "questions.jsonl")
    predictions = load_generation_predictions(
        PROJECT_DIR / "evaluation" / "sample_predictions.jsonl"
    )
    summary = evaluate_generation(examples, predictions)
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
