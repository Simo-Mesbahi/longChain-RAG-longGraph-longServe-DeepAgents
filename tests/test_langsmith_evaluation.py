from pathlib import Path

import pytest

from ai_course.langsmith_evaluation import (
    ExpectedInvestigationOutput,
    LangSmithEvaluationExample,
    LocalExperiment,
    evaluate_local_experiment,
    load_langsmith_dataset,
    run_local_experiment,
    sync_examples_to_langsmith,
    to_langsmith_examples,
    trace_steps_from_audit,
    write_langsmith_dataset_export,
)


def make_examples() -> list[LangSmithEvaluationExample]:
    return [
        LangSmithEvaluationExample(
            id="coverage-water",
            inputs={"question": "Quelle est la franchise degat des eaux ?"},
            outputs=ExpectedInvestigationOutput(
                answered=True,
                needs_human_review=False,
                topic="coverage",
                expected_sources=["home.md"],
                expected_evidence_sources=["home.md"],
                reference_answer="La franchise est de 180 euros par sinistre.",
                min_evidence_count=1,
            ),
            metadata={"risk": "standard"},
        ),
        LangSmithEvaluationExample(
            id="dental-out-of-corpus",
            inputs={"question": "Quelle garantie existe pour une couronne dentaire ?"},
            outputs=ExpectedInvestigationOutput(
                answered=False,
                needs_human_review=True,
                topic="unknown",
                min_evidence_count=0,
            ),
        ),
    ]


def test_expected_output_requires_sources_for_answered_examples() -> None:
    with pytest.raises(ValueError, match="expected_sources"):
        ExpectedInvestigationOutput(
            answered=True,
            needs_human_review=False,
            topic="coverage",
            reference_answer="Reference.",
        )

    with pytest.raises(ValueError, match="reference_answer"):
        ExpectedInvestigationOutput(
            answered=True,
            needs_human_review=False,
            topic="coverage",
            expected_sources=["policy.md"],
        )


def test_dataset_loader_rejects_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    line = (
        '{"id":"case","inputs":{"question":"Question ?"},'
        '"outputs":{"answered":false,"needs_human_review":true,"topic":"unknown"}}\n'
    )
    path.write_text(line + line, encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate"):
        load_langsmith_dataset(path)


def test_trace_steps_are_derived_from_audit_events() -> None:
    steps = trace_steps_from_audit(
        ["analyze_question", "retrieve_evidence:1", "verify_evidence:sufficient"]
    )

    assert [step.name for step in steps] == [
        "analyze_question",
        "retrieve_evidence",
        "verify_evidence",
    ]
    assert steps[1].event == "retrieve_evidence:1"
    assert steps[1].sequence == 1


def test_run_local_experiment_captures_success_and_summary() -> None:
    examples = make_examples()

    def target(inputs: dict[str, str]) -> dict[str, object]:
        if "franchise" in inputs["question"]:
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

    experiment = run_local_experiment(examples, target, experiment_name="unit-test")
    summary = evaluate_local_experiment(examples, experiment)

    assert isinstance(experiment, LocalExperiment)
    assert len(experiment.runs) == 2
    assert experiment.runs[0].trace[0].name == "analyze_question"
    assert summary.case_count == 2
    assert summary.pass_rate == pytest.approx(1.0)
    assert summary.metrics["route_accuracy"] == pytest.approx(1.0)
    assert summary.metrics["audit_contract"] == pytest.approx(1.0)


def test_evaluate_local_experiment_flags_regressions() -> None:
    examples = make_examples()
    experiment = run_local_experiment(
        examples,
        lambda _inputs: {
            "answer": "Reponse inventee.",
            "answered": True,
            "needs_human_review": False,
            "topic": "claim",
            "evidence_count": 0,
            "citations": [],
            "audit_trail": ["analyze_question"],
        },
        experiment_name="bad-run",
    )

    summary = evaluate_local_experiment(examples, experiment)

    assert summary.pass_rate == pytest.approx(0.0)
    assert summary.metrics["route_accuracy"] == pytest.approx(0.5)
    assert "citation_recall" in summary.cases[0].failure_tags
    assert "answer_contract" in summary.cases[0].failure_tags


def test_local_experiment_captures_target_errors() -> None:
    examples = make_examples()

    def target(_inputs: dict[str, str]) -> dict[str, object]:
        raise RuntimeError("boom")

    experiment = run_local_experiment(examples, target, experiment_name="error-run")
    summary = evaluate_local_experiment(examples, experiment)

    assert experiment.runs[0].status == "error"
    assert experiment.runs[0].trace[0].status == "error"
    assert summary.metrics["target_success"] == pytest.approx(0.0)


def test_langsmith_export_payload_and_file(tmp_path: Path) -> None:
    examples = make_examples()

    rows = to_langsmith_examples(examples)
    assert rows[0]["inputs"] == {"question": "Quelle est la franchise degat des eaux ?"}
    assert rows[0]["outputs"]["answered"] is True
    assert rows[0]["metadata"]["example_id"] == "coverage-water"

    export_path = write_langsmith_dataset_export(examples, tmp_path / "export.jsonl")
    loaded_lines = export_path.read_text(encoding="utf-8").splitlines()
    assert len(loaded_lines) == 2
    assert '"example_id": "coverage-water"' in loaded_lines[0]


def test_sync_examples_to_langsmith_uses_client_bulk_api() -> None:
    class Dataset:
        id = "dataset-123"

    class FakeClient:
        def __init__(self) -> None:
            self.created: dict[str, str] = {}
            self.uploaded: dict[str, object] = {}

        def create_dataset(self, *, dataset_name: str, description: str) -> Dataset:
            self.created = {"dataset_name": dataset_name, "description": description}
            return Dataset()

        def create_examples(self, *, dataset_id: str, examples: list[dict[str, object]]) -> None:
            self.uploaded = {"dataset_id": dataset_id, "examples": examples}

    client = FakeClient()
    result = sync_examples_to_langsmith(
        make_examples(),
        dataset_name="Investigation Quality",
        description="Dataset de test.",
        client=client,
    )

    assert result == {
        "dataset_name": "Investigation Quality",
        "dataset_id": "dataset-123",
        "examples": 2,
    }
    assert client.created["dataset_name"] == "Investigation Quality"
    assert client.uploaded["dataset_id"] == "dataset-123"
