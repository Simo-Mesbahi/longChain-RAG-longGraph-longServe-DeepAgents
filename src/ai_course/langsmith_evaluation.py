"""LangSmith-style evaluation helpers for observable graph workflows."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

InvestigationTopic = Literal["coverage", "claim", "fraud", "unknown"]
RunStatus = Literal["success", "error"]


class ExpectedInvestigationOutput(BaseModel):
    """Reference outputs stored in a LangSmith dataset example."""

    answered: bool
    needs_human_review: bool
    topic: InvestigationTopic
    expected_sources: list[str] = Field(default_factory=list)
    expected_evidence_sources: list[str] = Field(default_factory=list)
    reference_answer: str | None = None
    min_evidence_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_reference_contract(self) -> ExpectedInvestigationOutput:
        if self.answered and self.needs_human_review:
            raise ValueError("answered and needs_human_review cannot both be true")
        if self.answered:
            if not self.expected_sources:
                raise ValueError("answered examples require expected_sources")
            if not self.reference_answer or not self.reference_answer.strip():
                raise ValueError("answered examples require a reference_answer")
        elif self.expected_sources:
            raise ValueError("expected_sources only apply to answered examples")
        return self


class LangSmithEvaluationExample(BaseModel):
    """One dataset row using the same inputs/outputs vocabulary as LangSmith."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    inputs: dict[str, str]
    reference_outputs: ExpectedInvestigationOutput = Field(alias="outputs")
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    split: str = Field(default="validation", min_length=1)

    @model_validator(mode="after")
    def validate_inputs(self) -> LangSmithEvaluationExample:
        question = self.inputs.get("question", "").strip()
        if not question:
            raise ValueError("inputs.question is required")
        return self


class TraceStep(BaseModel):
    """Compact local representation of a traced node execution."""

    name: str = Field(min_length=1)
    event: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    status: RunStatus = "success"
    duration_ms: float = Field(default=0.0, ge=0.0)


class LocalExperimentRun(BaseModel):
    """Captured execution of one target function on one dataset example."""

    example_id: str
    inputs: dict[str, str]
    outputs: dict[str, Any] = Field(default_factory=dict)
    trace: list[TraceStep] = Field(default_factory=list)
    status: RunStatus = "success"
    started_at: datetime
    latency_ms: float = Field(ge=0.0)
    error: str | None = None


class LocalExperiment(BaseModel):
    """A local experiment that mirrors the shape of a LangSmith evaluation run."""

    experiment_name: str = Field(min_length=1)
    started_at: datetime
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    runs: list[LocalExperimentRun]


class EvaluatorScore(BaseModel):
    """One evaluator result for one example."""

    key: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    comment: str


class CaseEvaluation(BaseModel):
    """All evaluator results for one dataset example."""

    id: str
    passed: bool
    scores: list[EvaluatorScore]
    failure_tags: list[str] = Field(default_factory=list)


class ExperimentSummary(BaseModel):
    """Aggregate metrics for a local or LangSmith-style experiment."""

    experiment_name: str
    case_count: int = Field(ge=1)
    passed_cases: int = Field(ge=0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    metrics: dict[str, float]
    cases: list[CaseEvaluation]


def load_langsmith_dataset(path: Path) -> list[LangSmithEvaluationExample]:
    """Load LangSmith-compatible dataset examples from JSONL."""
    if not path.is_file():
        raise ValueError(f"Dataset file not found: {path}")

    examples: list[LangSmithEvaluationExample] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            example = LangSmithEvaluationExample.model_validate_json(line)
        except ValueError as error:
            raise ValueError(f"Invalid LangSmith dataset example on line {line_number}") from error
        if example.id in seen_ids:
            raise ValueError(f"Duplicate dataset example id: {example.id}")
        seen_ids.add(example.id)
        examples.append(example)

    if not examples:
        raise ValueError("Dataset file cannot be empty")
    return examples


def to_langsmith_examples(examples: list[LangSmithEvaluationExample]) -> list[dict[str, object]]:
    """Convert local examples to the bulk `Client.create_examples` payload."""
    if not examples:
        raise ValueError("At least one example is required")

    rows: list[dict[str, object]] = []
    for example in examples:
        metadata = dict(example.metadata)
        metadata.setdefault("split", example.split)
        metadata.setdefault("example_id", example.id)
        rows.append(
            {
                "inputs": dict(example.inputs),
                "outputs": example.reference_outputs.model_dump(mode="json"),
                "metadata": metadata,
            }
        )
    return rows


def write_langsmith_dataset_export(
    examples: list[LangSmithEvaluationExample],
    path: Path,
) -> Path:
    """Write a JSONL file that can be imported or synced to LangSmith."""
    rows = to_langsmith_examples(examples)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def sync_examples_to_langsmith(
    examples: list[LangSmithEvaluationExample],
    *,
    dataset_name: str,
    description: str,
    client: object | None = None,
) -> dict[str, object]:
    """Create a LangSmith dataset and upload examples with the official SDK."""
    if client is None:
        try:
            from langsmith import Client
        except ImportError as error:
            raise RuntimeError(
                "Install the observability extra before syncing: pip install -e '.[observability]'"
            ) from error
        client = Client()

    dataset = client.create_dataset(dataset_name=dataset_name, description=description)
    rows = to_langsmith_examples(examples)
    client.create_examples(dataset_id=dataset.id, examples=rows)
    return {
        "dataset_name": dataset_name,
        "dataset_id": str(dataset.id),
        "examples": len(rows),
    }


def run_local_experiment(
    examples: list[LangSmithEvaluationExample],
    target: Callable[[dict[str, str]], Mapping[str, Any]],
    *,
    experiment_name: str,
    metadata: Mapping[str, str | int | float | bool | None] | None = None,
) -> LocalExperiment:
    """Run a target function over a dataset and capture trace-like outputs."""
    if not examples:
        raise ValueError("At least one example is required")

    runs: list[LocalExperimentRun] = []
    started_at = datetime.now(UTC)
    for example in examples:
        run_started_at = datetime.now(UTC)
        timer = perf_counter()
        try:
            outputs = dict(target(dict(example.inputs)))
            latency_ms = (perf_counter() - timer) * 1000
            audit_trail = [str(event) for event in outputs.get("audit_trail", [])]
            runs.append(
                LocalExperimentRun(
                    example_id=example.id,
                    inputs=dict(example.inputs),
                    outputs=outputs,
                    trace=trace_steps_from_audit(audit_trail),
                    status="success",
                    started_at=run_started_at,
                    latency_ms=latency_ms,
                )
            )
        except Exception as error:
            latency_ms = (perf_counter() - timer) * 1000
            message = f"{type(error).__name__}: {error}"
            runs.append(
                LocalExperimentRun(
                    example_id=example.id,
                    inputs=dict(example.inputs),
                    outputs={},
                    trace=[
                        TraceStep(
                            name="target",
                            event="target:error",
                            sequence=0,
                            status="error",
                            duration_ms=latency_ms,
                        )
                    ],
                    status="error",
                    started_at=run_started_at,
                    latency_ms=latency_ms,
                    error=message,
                )
            )

    return LocalExperiment(
        experiment_name=experiment_name,
        started_at=started_at,
        metadata=dict(metadata or {}),
        runs=runs,
    )


def trace_steps_from_audit(audit_trail: list[str]) -> list[TraceStep]:
    """Turn graph audit events into trace steps for local inspection."""
    return [
        TraceStep(
            name=event.split(":", maxsplit=1)[0],
            event=event,
            sequence=index,
        )
        for index, event in enumerate(audit_trail)
    ]


def evaluate_local_experiment(
    examples: list[LangSmithEvaluationExample],
    experiment: LocalExperiment,
) -> ExperimentSummary:
    """Evaluate an experiment with deterministic LangSmith-style evaluators."""
    if not examples:
        raise ValueError("At least one example is required")

    examples_by_id = {example.id: example for example in examples}
    if len(examples_by_id) != len(examples):
        raise ValueError("Duplicate examples are not allowed")

    runs_by_id: dict[str, LocalExperimentRun] = {}
    for run in experiment.runs:
        if run.example_id in runs_by_id:
            raise ValueError(f"Duplicate run for example: {run.example_id}")
        runs_by_id[run.example_id] = run

    missing = sorted(examples_by_id.keys() - runs_by_id.keys())
    extra = sorted(runs_by_id.keys() - examples_by_id.keys())
    if missing:
        raise ValueError(f"Missing runs for examples: {missing}")
    if extra:
        raise ValueError(f"Runs reference unknown examples: {extra}")

    cases = [
        _evaluate_case(examples_by_id[example_id], runs_by_id[example_id])
        for example_id in sorted(examples_by_id)
    ]
    metric_keys = sorted({score.key for case in cases for score in case.scores})
    metrics = {
        key: _mean([score.score for case in cases for score in case.scores if score.key == key])
        for key in metric_keys
    }
    passed_cases = sum(case.passed for case in cases)
    return ExperimentSummary(
        experiment_name=experiment.experiment_name,
        case_count=len(cases),
        passed_cases=passed_cases,
        pass_rate=passed_cases / len(cases),
        metrics=metrics,
        cases=cases,
    )


def _evaluate_case(
    example: LangSmithEvaluationExample,
    run: LocalExperimentRun,
) -> CaseEvaluation:
    reference = example.reference_outputs
    scores = [
        _score(
            "target_success",
            1.0 if run.status == "success" else 0.0,
            "target executed successfully"
            if run.status == "success"
            else (run.error or "target error"),
        ),
        _score_route(reference, run.outputs),
        _score_topic(reference, run.outputs),
        _score_citation_recall(reference, run.outputs),
        _score_evidence_sources(reference, run.outputs),
        _score_min_evidence(reference, run.outputs),
        _score_audit_contract(reference, run.outputs),
        _score_answer_contract(run.outputs),
    ]
    failure_tags = [score.key for score in scores if not score.passed]
    return CaseEvaluation(
        id=example.id,
        passed=not failure_tags,
        scores=scores,
        failure_tags=failure_tags,
    )


def _score_route(
    reference: ExpectedInvestigationOutput,
    outputs: Mapping[str, Any],
) -> EvaluatorScore:
    actual_answered = bool(outputs.get("answered", False))
    actual_review = bool(outputs.get("needs_human_review", False))
    value = float(
        actual_answered == reference.answered and actual_review == reference.needs_human_review
    )
    return _score(
        "route_accuracy",
        value,
        (
            "answered/human-review flags match the reference"
            if value == 1.0
            else (
                "expected answered="
                f"{reference.answered}, review={reference.needs_human_review}; "
                f"got answered={actual_answered}, review={actual_review}"
            )
        ),
    )


def _score_topic(
    reference: ExpectedInvestigationOutput,
    outputs: Mapping[str, Any],
) -> EvaluatorScore:
    actual_topic = str(outputs.get("topic", "unknown"))
    value = float(actual_topic == reference.topic)
    return _score(
        "topic_accuracy",
        value,
        (
            "topic matches the reference"
            if value == 1.0
            else f"expected topic={reference.topic}; got topic={actual_topic}"
        ),
    )


def _score_citation_recall(
    reference: ExpectedInvestigationOutput,
    outputs: Mapping[str, Any],
) -> EvaluatorScore:
    if not reference.expected_sources:
        return _score("citation_recall", 1.0, "no expected citation sources for this case")

    cited_sources = set(_citation_sources(outputs))
    expected = set(reference.expected_sources)
    value = len(expected.intersection(cited_sources)) / len(expected)
    return _score(
        "citation_recall",
        value,
        (
            "all expected citation sources are present"
            if value == 1.0
            else f"missing citation sources: {sorted(expected - cited_sources)}"
        ),
    )


def _score_evidence_sources(
    reference: ExpectedInvestigationOutput,
    outputs: Mapping[str, Any],
) -> EvaluatorScore:
    if not reference.expected_evidence_sources:
        return _score("evidence_source_recall", 1.0, "no expected evidence sources for this case")

    actual = set(_string_list(outputs.get("evidence_sources", [])))
    expected = set(reference.expected_evidence_sources)
    value = len(expected.intersection(actual)) / len(expected)
    return _score(
        "evidence_source_recall",
        value,
        (
            "all expected evidence sources are present"
            if value == 1.0
            else f"missing evidence sources: {sorted(expected - actual)}"
        ),
    )


def _score_min_evidence(
    reference: ExpectedInvestigationOutput,
    outputs: Mapping[str, Any],
) -> EvaluatorScore:
    actual = int(outputs.get("evidence_count", 0) or 0)
    value = float(actual >= reference.min_evidence_count)
    return _score(
        "evidence_count_contract",
        value,
        (
            "minimum evidence count satisfied"
            if value == 1.0
            else f"expected at least {reference.min_evidence_count} evidence chunks; got {actual}"
        ),
    )


def _score_audit_contract(
    reference: ExpectedInvestigationOutput,
    outputs: Mapping[str, Any],
) -> EvaluatorScore:
    audit_trail = [str(event) for event in outputs.get("audit_trail", [])]
    expected_nodes = ["analyze_question", "retrieve_evidence", "verify_evidence"]
    if reference.answered:
        expected_nodes.append("draft_answer")
    elif reference.needs_human_review:
        expected_nodes.append("request_human_review")
    else:
        expected_nodes.append("draft_refusal")

    missing = [node for node in expected_nodes if not _node_present(node, audit_trail)]
    value = 1.0 if not missing else max(0.0, 1.0 - len(missing) / len(expected_nodes))
    return _score(
        "audit_contract",
        value,
        "audit trail contains the expected graph nodes"
        if not missing
        else f"missing audit nodes: {missing}",
    )


def _score_answer_contract(outputs: Mapping[str, Any]) -> EvaluatorScore:
    answer = str(outputs.get("answer", "")).strip()
    citations = _citation_sources(outputs)
    answered = bool(outputs.get("answered", False))
    needs_review = bool(outputs.get("needs_human_review", False))

    if answered:
        ok = bool(answer and citations)
        comment = "answered outputs contain an answer and citations"
    elif needs_review:
        ok = bool(answer and not citations and "validation" in answer.casefold())
        comment = "human-review outputs contain a pending review message without citations"
    else:
        ok = bool(answer and not citations)
        comment = "refusal outputs contain a controlled answer without citations"

    return _score("answer_contract", 1.0 if ok else 0.0, comment)


def _score(key: str, value: float, comment: str) -> EvaluatorScore:
    return EvaluatorScore(
        key=key,
        score=value,
        passed=value >= 0.999,
        comment=comment,
    )


def _citation_sources(outputs: Mapping[str, Any]) -> list[str]:
    raw_citations = outputs.get("citations", [])
    sources: list[str] = []
    if not isinstance(raw_citations, list):
        return sources
    for citation in raw_citations:
        if isinstance(citation, Mapping):
            source = citation.get("source")
            if isinstance(source, str) and source:
                sources.append(source)
    return list(dict.fromkeys(sources))


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _node_present(node: str, audit_trail: list[str]) -> bool:
    return any(event == node or event.startswith(f"{node}:") for event in audit_trail)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
