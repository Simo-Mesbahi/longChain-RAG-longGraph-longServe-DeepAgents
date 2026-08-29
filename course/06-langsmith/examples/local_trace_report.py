"""Run a tiny LangSmith-style evaluation fully offline."""

from __future__ import annotations

from ai_course.langsmith_evaluation import (
    ExpectedInvestigationOutput,
    LangSmithEvaluationExample,
    evaluate_local_experiment,
    run_local_experiment,
)


def target(inputs: dict[str, str]) -> dict[str, object]:
    question = inputs["question"]
    if "franchise" in question:
        return {
            "answer": "La franchise est de 180 euros.",
            "answered": True,
            "needs_human_review": False,
            "topic": "coverage",
            "evidence_count": 1,
            "evidence_sources": ["home.md"],
            "citations": [{"source": "home.md", "chunk_id": "home.md#chunk-000"}],
            "audit_trail": [
                "analyze_question",
                "retrieve_evidence:1",
                "verify_evidence:sufficient",
                "draft_answer",
            ],
        }
    return {
        "answer": "Validation humaine requise avant de repondre.",
        "answered": False,
        "needs_human_review": True,
        "topic": "unknown",
        "evidence_count": 0,
        "evidence_sources": [],
        "citations": [],
        "audit_trail": [
            "analyze_question",
            "retrieve_evidence:0",
            "verify_evidence:insufficient",
            "request_human_review:pending",
        ],
    }


def main() -> int:
    examples = [
        LangSmithEvaluationExample(
            id="coverage-water",
            inputs={"question": "Quelle est la franchise degat des eaux ?"},
            outputs=ExpectedInvestigationOutput(
                answered=True,
                needs_human_review=False,
                topic="coverage",
                expected_sources=["home.md"],
                expected_evidence_sources=["home.md"],
                reference_answer="La franchise est de 180 euros.",
                min_evidence_count=1,
            ),
        ),
        LangSmithEvaluationExample(
            id="missing-dental",
            inputs={"question": "Quel remboursement existe pour une couronne dentaire ?"},
            outputs=ExpectedInvestigationOutput(
                answered=False,
                needs_human_review=True,
                topic="unknown",
            ),
        ),
    ]
    experiment = run_local_experiment(
        examples,
        target,
        experiment_name="offline-langsmith-demo",
    )
    summary = evaluate_local_experiment(examples, experiment)
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
