from pathlib import Path

import pytest

from ai_course.rag_basics import Citation, RagAnswer, RetrievedChunk
from ai_course.rag_evaluation import (
    GenerationEvaluationExample,
    GenerationPrediction,
    RagJudgeFeedback,
    build_judge_input,
    evaluate_generation,
    lexical_token_f1,
    load_generation_evaluation_dataset,
    load_generation_predictions,
)


class StubJudge:
    def __init__(self) -> None:
        self.inputs: list[dict[str, str]] = []

    def invoke(self, input: dict[str, str]) -> RagJudgeFeedback:
        self.inputs.append(input)
        return RagJudgeFeedback(
            correctness=0.75,
            groundedness=0.5,
            completeness=0.25,
            rationale="Synthetic judge feedback.",
            failure_modes=["partial"],
        )


def test_generation_dataset_validation_requires_reference_for_answerable() -> None:
    with pytest.raises(ValueError, match="reference answer"):
        GenerationEvaluationExample(
            id="missing-reference",
            question="What is covered?",
            expected_sources=["policy.md"],
            answerable=True,
        )

    with pytest.raises(ValueError, match="cannot declare expected sources"):
        GenerationEvaluationExample(
            id="bad-negative",
            question="What is covered?",
            expected_sources=["policy.md"],
            answerable=False,
            reference_answer=None,
        )


def test_prediction_can_be_created_from_rag_answer_and_chunks() -> None:
    answer = RagAnswer(
        answer="La franchise est de 180 euros.",
        answered=True,
        citations=[Citation(chunk_id="policy.md#chunk-000", source="policy.md")],
        retrieved_chunks=1,
    )
    chunks = [
        RetrievedChunk(
            chunk_id="policy.md#chunk-000",
            source="policy.md",
            content="Franchise de 180 euros.",
            score=0.91,
        )
    ]

    prediction = GenerationPrediction.from_rag_answer(
        example_id="water",
        answer=answer,
        retrieved_chunks=chunks,
    )

    assert prediction.cited_sources == ["policy.md"]
    assert prediction.cited_chunk_ids == ["policy.md#chunk-000"]
    assert "[policy.md#chunk-000]" in (prediction.evidence or "")


def test_lexical_token_f1_handles_overlap_and_empty_inputs() -> None:
    assert lexical_token_f1("", "") == pytest.approx(1.0)
    assert lexical_token_f1("franchise 180 euros", "") == pytest.approx(0.0)
    assert lexical_token_f1(
        "La franchise est de 180 euros.",
        "Franchise de 180 euros par sinistre.",
    ) == pytest.approx(0.6666667)


def test_evaluate_generation_computes_deterministic_metrics() -> None:
    examples = [
        GenerationEvaluationExample(
            id="good",
            question="Quelle est la franchise ?",
            expected_sources=["policy.md"],
            answerable=True,
            reference_answer="La franchise est de 180 euros par sinistre.",
        ),
        GenerationEvaluationExample(
            id="false-refusal",
            question="Quelles pieces sont demandees ?",
            expected_sources=["procedure.md"],
            answerable=True,
            reference_answer="Le depot de plainte et les preuves de possession sont demandes.",
        ),
        GenerationEvaluationExample(
            id="bad-negative",
            question="Quelle est la franchise auto ?",
            answerable=False,
            reference_answer=None,
        ),
    ]
    predictions = [
        GenerationPrediction(
            id="good",
            answer="La franchise est de 180 euros.",
            answered=True,
            cited_sources=["policy.md"],
        ),
        GenerationPrediction(
            id="false-refusal",
            answer="Je ne dispose pas de preuves suffisantes.",
            answered=False,
        ),
        GenerationPrediction(
            id="bad-negative",
            answer="La franchise auto est de 400 euros.",
            answered=True,
            cited_chunk_ids=["invented.md#chunk-000"],
        ),
    ]

    summary = evaluate_generation(examples, predictions)

    assert summary.examples == 3
    assert summary.answerability_accuracy == pytest.approx(1 / 3)
    assert summary.citation_precision == pytest.approx(0.5)
    assert summary.citation_recall == pytest.approx(0.5)
    assert summary.cases[1].error_tags == [
        "false_refusal",
        "missing_expected_source",
        "low_reference_overlap",
    ]
    assert summary.cases[2].error_tags == ["answered_unanswerable"]


def test_evaluate_generation_rejects_missing_or_extra_predictions() -> None:
    examples = [
        GenerationEvaluationExample(
            id="known",
            question="Question valide ?",
            expected_sources=["source.md"],
            answerable=True,
            reference_answer="Reponse de reference.",
        )
    ]

    with pytest.raises(ValueError, match="Missing predictions"):
        evaluate_generation(examples, [])

    with pytest.raises(ValueError, match="unknown examples"):
        evaluate_generation(
            examples,
            [
                GenerationPrediction(
                    id="known",
                    answer="Reponse.",
                    answered=True,
                    cited_sources=["source.md"],
                ),
                GenerationPrediction(id="extra", answer="Reponse.", answered=False),
            ],
        )


def test_evaluate_generation_uses_optional_judge() -> None:
    example = GenerationEvaluationExample(
        id="judged",
        question="Quelle est la regle ?",
        expected_sources=["policy.md"],
        answerable=True,
        reference_answer="La validation humaine est obligatoire.",
    )
    prediction = GenerationPrediction(
        id="judged",
        answer="La validation humaine est obligatoire.",
        answered=True,
        cited_sources=["policy.md"],
        evidence="La validation humaine est obligatoire avant decision.",
    )
    judge = StubJudge()

    summary = evaluate_generation([example], [prediction], judge=judge)

    assert summary.judged_examples == 1
    assert summary.judge_correctness == pytest.approx(0.75)
    assert summary.judge_groundedness == pytest.approx(0.5)
    assert summary.judge_completeness == pytest.approx(0.25)
    assert judge.inputs[0]["question"] == "Quelle est la regle ?"


def test_build_judge_input_formats_json_fields() -> None:
    example = GenerationEvaluationExample(
        id="case",
        question="Une question ?",
        expected_sources=["policy.md"],
        answerable=True,
        reference_answer="Une reference.",
    )
    prediction = GenerationPrediction(
        id="case",
        answer="Une reponse.",
        answered=True,
        cited_sources=["policy.md"],
    )

    formatted = build_judge_input(example, prediction)

    assert formatted["expected_sources"] == '["policy.md"]'
    assert formatted["cited_sources"] == '["policy.md"]'
    assert formatted["evidence"] == "Aucune preuve fournie."


def test_generation_jsonl_loaders_reject_duplicates(tmp_path: Path) -> None:
    dataset = tmp_path / "questions.jsonl"
    dataset.write_text(
        '{"id":"one","question":"Question valide ?","expected_sources":["a.md"],'
        '"answerable":true,"reference_answer":"Reponse."}\n',
        encoding="utf-8",
    )
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(
        '{"id":"one","answer":"Reponse.","answered":true,"cited_sources":["a.md"]}\n',
        encoding="utf-8",
    )

    assert load_generation_evaluation_dataset(dataset)[0].id == "one"
    assert load_generation_predictions(predictions)[0].id == "one"

    dataset.write_text(dataset.read_text(encoding="utf-8") * 2, encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        load_generation_evaluation_dataset(dataset)
