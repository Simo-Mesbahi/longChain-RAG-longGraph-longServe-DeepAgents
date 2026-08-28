"""Evaluation helpers for advanced RAG generation quality."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Protocol, TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field, model_validator

from ai_course.rag_basics import RagAnswer, RetrievedChunk, format_context

ModelT = TypeVar("ModelT", bound=BaseModel)


class GenerationEvaluationExample(BaseModel):
    """One labelled question used to evaluate the generation step."""

    id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    question: str = Field(min_length=3)
    expected_sources: list[str] = Field(default_factory=list)
    answerable: bool
    reference_answer: str | None = None

    @model_validator(mode="after")
    def validate_ground_truth(self) -> GenerationEvaluationExample:
        if self.answerable:
            if not self.expected_sources:
                raise ValueError("An answerable example requires at least one expected source")
            if not self.reference_answer or not self.reference_answer.strip():
                raise ValueError("An answerable example requires a reference answer")
        elif self.expected_sources:
            raise ValueError("An unanswerable example cannot declare expected sources")
        return self


class GenerationPrediction(BaseModel):
    """Saved output of a RAG system for one evaluation question."""

    id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    answer: str = Field(min_length=1)
    answered: bool
    cited_sources: list[str] = Field(default_factory=list)
    cited_chunk_ids: list[str] = Field(default_factory=list)
    evidence_sources: list[str] = Field(default_factory=list)
    evidence: str | None = None

    @classmethod
    def from_rag_answer(
        cls,
        *,
        example_id: str,
        answer: RagAnswer,
        retrieved_chunks: list[RetrievedChunk] | None = None,
    ) -> GenerationPrediction:
        chunks = retrieved_chunks or []
        return cls(
            id=example_id,
            answer=answer.answer,
            answered=answer.answered,
            cited_sources=[citation.source for citation in answer.citations],
            cited_chunk_ids=[citation.chunk_id for citation in answer.citations],
            evidence_sources=[chunk.source for chunk in chunks],
            evidence=format_context(chunks) if chunks else None,
        )

    @model_validator(mode="after")
    def deduplicate_provenance(self) -> GenerationPrediction:
        self.cited_sources = list(dict.fromkeys(self.cited_sources))
        self.cited_chunk_ids = list(dict.fromkeys(self.cited_chunk_ids))
        self.evidence_sources = list(dict.fromkeys(self.evidence_sources))
        return self


class RagJudgeFeedback(BaseModel):
    """Structured feedback returned by an optional LLM-as-judge evaluator."""

    correctness: float = Field(ge=0.0, le=1.0)
    groundedness: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    failure_modes: list[str] = Field(default_factory=list)


class RagJudge(Protocol):
    """Minimal synchronous interface required from a generation judge."""

    def invoke(self, input: dict[str, str]) -> RagJudgeFeedback:
        """Evaluate one saved RAG answer."""
        ...


class GenerationCaseResult(BaseModel):
    """Per-question diagnostics for generation quality."""

    id: str
    answerable: bool
    answered: bool
    answerability_correct: bool
    citation_precision: float | None = Field(default=None, ge=0.0, le=1.0)
    citation_recall: float | None = Field(default=None, ge=0.0, le=1.0)
    lexical_f1: float | None = Field(default=None, ge=0.0, le=1.0)
    cited_sources: list[str] = Field(default_factory=list)
    expected_sources: list[str] = Field(default_factory=list)
    error_tags: list[str] = Field(default_factory=list)
    judge_feedback: RagJudgeFeedback | None = None


class GenerationEvaluationSummary(BaseModel):
    """Aggregate generation metrics kept separate from retrieval metrics."""

    examples: int = Field(ge=1)
    answerable_examples: int = Field(ge=0)
    unanswerable_examples: int = Field(ge=0)
    answerability_accuracy: float = Field(ge=0.0, le=1.0)
    citation_precision: float = Field(ge=0.0, le=1.0)
    citation_recall: float = Field(ge=0.0, le=1.0)
    lexical_f1: float = Field(ge=0.0, le=1.0)
    judged_examples: int = Field(default=0, ge=0)
    judge_correctness: float | None = Field(default=None, ge=0.0, le=1.0)
    judge_groundedness: float | None = Field(default=None, ge=0.0, le=1.0)
    judge_completeness: float | None = Field(default=None, ge=0.0, le=1.0)
    cases: list[GenerationCaseResult]


def load_generation_evaluation_dataset(path: Path) -> list[GenerationEvaluationExample]:
    """Load reference answers for generation evaluation from JSONL."""
    return _load_jsonl(path, GenerationEvaluationExample, "generation evaluation example")


def load_generation_predictions(path: Path) -> list[GenerationPrediction]:
    """Load saved RAG predictions from JSONL and reject duplicate identifiers."""
    return _load_jsonl(path, GenerationPrediction, "generation prediction")


def evaluate_generation(
    examples: list[GenerationEvaluationExample],
    predictions: list[GenerationPrediction],
    *,
    judge: RagJudge | None = None,
    lexical_warning_threshold: float = 0.35,
) -> GenerationEvaluationSummary:
    """Evaluate saved RAG answers against references and optional judge feedback."""
    if not examples:
        raise ValueError("At least one generation evaluation example is required")
    if not 0.0 <= lexical_warning_threshold <= 1.0:
        raise ValueError("lexical_warning_threshold must be between 0 and 1")

    predictions_by_id = _index_predictions(predictions) if predictions else {}
    expected_ids = {example.id for example in examples}
    missing = sorted(expected_ids - predictions_by_id.keys())
    extra = sorted(predictions_by_id.keys() - expected_ids)
    if missing:
        raise ValueError(f"Missing predictions for examples: {missing}")
    if extra:
        raise ValueError(f"Predictions reference unknown examples: {extra}")

    cases = [
        _evaluate_case(
            example,
            predictions_by_id[example.id],
            judge=judge,
            lexical_warning_threshold=lexical_warning_threshold,
        )
        for example in examples
    ]
    answerable_cases = [case for case in cases if case.answerable]
    unanswerable_cases = [case for case in cases if not case.answerable]
    judged_cases = [case for case in cases if case.judge_feedback is not None]

    return GenerationEvaluationSummary(
        examples=len(cases),
        answerable_examples=len(answerable_cases),
        unanswerable_examples=len(unanswerable_cases),
        answerability_accuracy=_mean(
            [float(case.answerability_correct) for case in cases],
        ),
        citation_precision=_mean(
            [
                case.citation_precision
                for case in answerable_cases
                if case.citation_precision is not None
            ],
        ),
        citation_recall=_mean(
            [case.citation_recall for case in answerable_cases if case.citation_recall is not None],
        ),
        lexical_f1=_mean(
            [case.lexical_f1 for case in answerable_cases if case.lexical_f1 is not None],
        ),
        judged_examples=len(judged_cases),
        judge_correctness=(
            _mean([case.judge_feedback.correctness for case in judged_cases])
            if judged_cases
            else None
        ),
        judge_groundedness=(
            _mean([case.judge_feedback.groundedness for case in judged_cases])
            if judged_cases
            else None
        ),
        judge_completeness=(
            _mean([case.judge_feedback.completeness for case in judged_cases])
            if judged_cases
            else None
        ),
        cases=cases,
    )


def build_rag_judge(model: BaseChatModel) -> Runnable:
    """Build a structured LLM-as-judge for RAG answer quality."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Tu es un evaluateur RAG strict. "
                "Tu notes uniquement la reponse fournie, sans utiliser tes connaissances externes. "
                "correctness mesure l'accord avec la reponse de reference. "
                "groundedness mesure si la reponse est soutenue par les preuves. "
                "completeness mesure si la reponse couvre les elements importants. "
                "Chaque score est compris entre 0 et 1.",
            ),
            (
                "human",
                "Question:\n{question}\n\n"
                "Question repondable:\n{answerable}\n\n"
                "Reponse de reference:\n{reference_answer}\n\n"
                "Sources attendues:\n{expected_sources}\n\n"
                "Reponse du systeme:\n{answer}\n\n"
                "Sources citees:\n{cited_sources}\n\n"
                "Preuves fournies au modele:\n{evidence}",
            ),
        ]
    )
    return prompt | model.with_structured_output(RagJudgeFeedback)


def build_judge_input(
    example: GenerationEvaluationExample,
    prediction: GenerationPrediction,
) -> dict[str, str]:
    """Format one case for a judge prompt without leaking hidden state."""
    return {
        "question": example.question,
        "answerable": str(example.answerable),
        "reference_answer": example.reference_answer or "Question hors corpus.",
        "expected_sources": json.dumps(example.expected_sources, ensure_ascii=False),
        "answer": prediction.answer,
        "cited_sources": json.dumps(_prediction_sources(prediction), ensure_ascii=False),
        "evidence": prediction.evidence or "Aucune preuve fournie.",
    }


def lexical_token_f1(candidate: str, reference: str) -> float:
    """Compute a deterministic token F1 score against a reference answer."""
    candidate_tokens = _tokens(candidate)
    reference_tokens = _tokens(reference)
    if not candidate_tokens and not reference_tokens:
        return 1.0
    if not candidate_tokens or not reference_tokens:
        return 0.0

    candidate_counts = Counter(candidate_tokens)
    reference_counts = Counter(reference_tokens)
    overlap = sum((candidate_counts & reference_counts).values())
    if overlap == 0:
        return 0.0

    precision = overlap / len(candidate_tokens)
    recall = overlap / len(reference_tokens)
    return 2 * precision * recall / (precision + recall)


def _evaluate_case(
    example: GenerationEvaluationExample,
    prediction: GenerationPrediction,
    *,
    judge: RagJudge | None,
    lexical_warning_threshold: float,
) -> GenerationCaseResult:
    cited_sources = _prediction_sources(prediction)
    expected_sources = list(dict.fromkeys(example.expected_sources))
    answerability_correct = prediction.answered == example.answerable
    citation_precision = _citation_precision(cited_sources, expected_sources, example.answerable)
    citation_recall = _citation_recall(cited_sources, expected_sources, example.answerable)
    lexical_f1 = (
        lexical_token_f1(prediction.answer, example.reference_answer or "")
        if example.answerable
        else None
    )

    error_tags = _error_tags(
        example=example,
        prediction=prediction,
        cited_sources=cited_sources,
        expected_sources=expected_sources,
        lexical_f1=lexical_f1,
        lexical_warning_threshold=lexical_warning_threshold,
    )
    feedback = _call_judge(judge, example, prediction) if judge is not None else None

    return GenerationCaseResult(
        id=example.id,
        answerable=example.answerable,
        answered=prediction.answered,
        answerability_correct=answerability_correct,
        citation_precision=citation_precision,
        citation_recall=citation_recall,
        lexical_f1=lexical_f1,
        cited_sources=cited_sources,
        expected_sources=expected_sources,
        error_tags=error_tags,
        judge_feedback=feedback,
    )


def _prediction_sources(prediction: GenerationPrediction) -> list[str]:
    sources = prediction.cited_sources
    if not sources:
        sources = [_source_from_chunk_id(chunk_id) for chunk_id in prediction.cited_chunk_ids]
    return list(dict.fromkeys(source for source in sources if source))


def _citation_precision(
    cited_sources: list[str],
    expected_sources: list[str],
    answerable: bool,
) -> float | None:
    if not answerable:
        return None
    if not cited_sources:
        return 0.0
    expected = set(expected_sources)
    return len(expected.intersection(cited_sources)) / len(cited_sources)


def _citation_recall(
    cited_sources: list[str],
    expected_sources: list[str],
    answerable: bool,
) -> float | None:
    if not answerable:
        return None
    expected = set(expected_sources)
    if not expected:
        return 0.0
    return len(expected.intersection(cited_sources)) / len(expected)


def _error_tags(
    *,
    example: GenerationEvaluationExample,
    prediction: GenerationPrediction,
    cited_sources: list[str],
    expected_sources: list[str],
    lexical_f1: float | None,
    lexical_warning_threshold: float,
) -> list[str]:
    tags: list[str] = []
    if example.answerable and not prediction.answered:
        tags.append("false_refusal")
    if not example.answerable and prediction.answered:
        tags.append("answered_unanswerable")
    if prediction.answered and not cited_sources:
        tags.append("answer_without_citation")
    if example.answerable:
        cited = set(cited_sources)
        expected = set(expected_sources)
        if cited - expected:
            tags.append("citation_outside_expected_sources")
        if expected - cited:
            tags.append("missing_expected_source")
        if lexical_f1 is not None and lexical_f1 < lexical_warning_threshold:
            tags.append("low_reference_overlap")
    return tags


def _call_judge(
    judge: RagJudge,
    example: GenerationEvaluationExample,
    prediction: GenerationPrediction,
) -> RagJudgeFeedback:
    raw_feedback = judge.invoke(build_judge_input(example, prediction))
    if isinstance(raw_feedback, RagJudgeFeedback):
        return raw_feedback
    try:
        return RagJudgeFeedback.model_validate(raw_feedback)
    except ValueError as error:
        raise TypeError("Judge must return RagJudgeFeedback-compatible data") from error


def _load_jsonl(path: Path, model: type[ModelT], kind: str) -> list[ModelT]:
    if not path.is_file():
        raise ValueError(f"JSONL file not found: {path}")

    items: list[ModelT] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = model.model_validate_json(line)
        except ValueError as error:
            raise ValueError(f"Invalid {kind} on line {line_number}") from error
        item_id = str(item.model_dump()["id"])
        if item_id in seen_ids:
            raise ValueError(f"Duplicate {kind} id: {item_id}")
        seen_ids.add(item_id)
        items.append(item)

    if not items:
        raise ValueError(f"{kind.title()} file cannot be empty")
    return items


def _index_predictions(
    predictions: list[GenerationPrediction],
) -> dict[str, GenerationPrediction]:
    if not predictions:
        raise ValueError("At least one generation prediction is required")

    indexed: dict[str, GenerationPrediction] = {}
    for prediction in predictions:
        if prediction.id in indexed:
            raise ValueError(f"Duplicate prediction id: {prediction.id}")
        indexed[prediction.id] = prediction
    return indexed


def _source_from_chunk_id(chunk_id: str) -> str:
    return chunk_id.split("#", maxsplit=1)[0]


def _tokens(value: str) -> list[str]:
    return re.findall(r"\w+", value.casefold())


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
