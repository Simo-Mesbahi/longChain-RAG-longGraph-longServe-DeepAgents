"""Evaluate saved RAG predictions with an optional LLM-as-judge.

This example calls a chat model and can create provider costs.
"""

from pathlib import Path

from ai_course.langchain_basics import create_chat_model
from ai_course.rag_evaluation import (
    build_rag_judge,
    evaluate_generation,
    load_generation_evaluation_dataset,
    load_generation_predictions,
)
from ai_course.settings import load_settings

ROOT_DIR = Path(__file__).resolve().parents[3]
PROJECT_DIR = ROOT_DIR / "projects" / "02-documentary-rag-assistant"


def main() -> int:
    settings = load_settings()
    examples = load_generation_evaluation_dataset(PROJECT_DIR / "evaluation" / "questions.jsonl")
    predictions = load_generation_predictions(
        PROJECT_DIR / "evaluation" / "sample_predictions.jsonl"
    )
    judge = build_rag_judge(create_chat_model(settings))
    summary = evaluate_generation(examples, predictions, judge=judge)
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
