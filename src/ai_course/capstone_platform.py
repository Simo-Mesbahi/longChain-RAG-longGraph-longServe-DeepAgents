"""Unified, testable application layer for the Asteria capstone platform."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from ai_course.deep_agents import DeepAgentPolicy, run_deep_investigation_agent
from ai_course.documentary_rag import load_corpus_documents
from ai_course.investigation_graph import (
    EvidenceChunk,
    InvestigationPolicy,
    StaticEvidenceStore,
    analyze_question,
    build_investigation_graph,
    draft_answer,
    draft_refusal,
    request_human_review,
    state_to_report,
)
from ai_course.production_readiness import (
    ReadinessReport,
    assert_no_secret_like_values,
    build_default_service,
    build_demo_evidence,
    build_deployment_manifest,
    evaluate_production_readiness,
)
from ai_course.rag_basics import Citation, split_documents

PlatformMode = Literal["auto", "rag", "graph", "deep_agent"]
ResolvedMode = Literal["rag", "graph", "deep_agent"]
RunStatus = Literal["completed", "review_required", "refused"]
CheckStatus = Literal["pass", "fail"]


class CapstoneRequest(BaseModel):
    """Stable input contract shared by the CLI, API, and web cockpit."""

    question: str = Field(min_length=5, max_length=8_000)
    mode: PlatformMode = "auto"
    require_human_review_on_insufficient: bool = True
    enforce_production_gate: bool = True

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 5:
            raise ValueError("question must contain at least five visible characters")
        return normalized


class EvidencePreview(BaseModel):
    """Public, bounded excerpt of evidence retrieved for a run."""

    chunk_id: str
    source: str
    excerpt: str = Field(max_length=360)
    score: float = Field(ge=0.0, le=1.0)


class ExecutionTask(BaseModel):
    """One user-visible step in the platform execution plan."""

    id: str
    title: str
    owner: str
    status: Literal["completed", "blocked"]
    summary: str


class BusinessCheck(BaseModel):
    """Machine-readable business acceptance check."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str
    status: CheckStatus
    detail: str

    @property
    def passed(self) -> bool:
        return self.status == "pass"


class CapstoneResponse(BaseModel):
    """Unified public output for every execution engine."""

    request_id: str
    trace_id: str
    created_at: datetime
    question: str
    requested_mode: PlatformMode
    mode_used: ResolvedMode
    status: RunStatus
    topic: str
    answer: str
    answered: bool
    needs_human_review: bool
    evidence_status: str | None = None
    evidence_count: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[Citation] = Field(default_factory=list)
    evidence: list[EvidencePreview] = Field(default_factory=list)
    tasks: list[ExecutionTask] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    audit_trail: list[str] = Field(default_factory=list)
    quality_gate_passed: bool
    production_status: str
    business_checks: list[BusinessCheck] = Field(default_factory=list)
    latency_ms: float = Field(ge=0.0)


class BusinessScenario(BaseModel):
    """Expected behavior for one end-to-end acceptance scenario."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str
    question: str
    expected_mode: ResolvedMode
    expected_answered: bool
    expected_human_review: bool
    expected_sources: list[str] = Field(default_factory=list)


class ScenarioResult(BaseModel):
    """Observed behavior and assertions for a business scenario."""

    scenario: BusinessScenario
    response: CapstoneResponse
    assertions: dict[str, bool]
    passed: bool


class AcceptanceSummary(BaseModel):
    """Aggregate result used as a deployment quality gate."""

    executed_at: datetime
    scenarios: int = Field(ge=1)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    release_gate_passed: bool
    results: list[ScenarioResult]


def build_capstone_store(corpus_dir: Path) -> StaticEvidenceStore:
    """Load the synthetic corpus into a deterministic local evidence store."""
    documents = load_corpus_documents(corpus_dir)
    chunks = split_documents(documents, chunk_size=780, chunk_overlap=90)
    return StaticEvidenceStore(
        [
            EvidenceChunk(
                chunk_id=str(chunk.metadata["chunk_id"]),
                source=str(chunk.metadata["source"]),
                content=chunk.page_content,
            )
            for chunk in chunks
        ]
    )


def build_capstone_readiness() -> ReadinessReport:
    """Return the production gate used by the capstone demonstration."""
    report = evaluate_production_readiness(
        build_default_service(environment="production"),
        build_demo_evidence(deployment_target="docker"),
    )
    report.manifest = build_deployment_manifest(
        report.service,
        target="docker",
        app_dir="projects/07-asteria-investigation-platform",
    )
    return report


def select_execution_mode(question: str, requested_mode: PlatformMode = "auto") -> ResolvedMode:
    """Choose the smallest engine that safely handles the requested objective."""
    if requested_mode != "auto":
        return requested_mode
    normalized = _ascii_tokens(question)
    sensitive = {"fraude", "modele", "risque", "score", "sensible", "sensibles"}
    deep_work = {"analyse", "analyser", "audit", "compare", "comparer", "investigation", "synthese"}
    workflow = {
        "decision",
        "declarer",
        "dossier",
        "etape",
        "etapes",
        "instruction",
        "justificatifs",
        "pieces",
        "validation",
        "valider",
        "workflow",
    }
    if normalized.intersection(sensitive | deep_work):
        return "deep_agent"
    if normalized.intersection(workflow):
        return "graph"
    return "rag"


def run_capstone_request(
    request: CapstoneRequest,
    evidence_store: StaticEvidenceStore,
    *,
    readiness: ReadinessReport | None = None,
) -> CapstoneResponse:
    """Run one investigation through RAG, LangGraph, or the Deep Agent workflow."""
    started = perf_counter()
    readiness = readiness or build_capstone_readiness()
    mode = select_execution_mode(request.question, request.mode)
    previews = _retrieve_previews(evidence_store, request.question)

    if mode == "rag":
        payload = _run_rag(request, previews)
    elif mode == "graph":
        payload = _run_graph(request, evidence_store)
    else:
        payload = _run_deep_agent(request, evidence_store)

    request_id = f"req_{uuid4().hex[:16]}"
    response = CapstoneResponse(
        request_id=request_id,
        trace_id=f"trace_{uuid4().hex[:16]}",
        created_at=datetime.now(UTC),
        question=request.question,
        requested_mode=request.mode,
        mode_used=mode,
        status=_run_status(payload["answered"], payload["needs_human_review"]),
        topic=str(payload["topic"]),
        answer=str(payload["answer"]),
        answered=bool(payload["answered"]),
        needs_human_review=bool(payload["needs_human_review"]),
        evidence_status=payload.get("evidence_status"),
        evidence_count=len(previews),
        confidence=max((item.score for item in previews), default=0.0),
        citations=payload["citations"],
        evidence=previews,
        tasks=payload["tasks"],
        files=payload["files"],
        audit_trail=payload["audit_trail"],
        quality_gate_passed=bool(payload["quality_gate_passed"]),
        production_status=readiness.status,
        latency_ms=round((perf_counter() - started) * 1_000, 2),
    )
    response.business_checks = evaluate_business_checks(
        response,
        enforce_production_gate=request.enforce_production_gate,
    )
    response.quality_gate_passed = response.quality_gate_passed and all(
        check.passed for check in response.business_checks
    )
    assert_no_secret_like_values(
        {
            "answer": response.answer,
            "citations": [citation.model_dump() for citation in response.citations],
            "audit_trail": response.audit_trail,
        }
    )
    return response


def evaluate_business_checks(
    response: CapstoneResponse,
    *,
    enforce_production_gate: bool = True,
) -> list[BusinessCheck]:
    """Evaluate end-to-end product invariants before a response is released."""
    evidence_ids = {item.chunk_id for item in response.evidence}
    citation_ids = {citation.chunk_id for citation in response.citations}
    checks = [
        _check(
            "answer-contract",
            "Contrat de reponse",
            bool(response.answer.strip()),
            "Une reponse publique non vide a ete produite.",
            "La reponse publique est vide.",
        ),
        _check(
            "grounded-answer",
            "Ancrage documentaire",
            not response.answered or bool(response.citations),
            "Toute reponse factuelle contient au moins une citation.",
            "Une reponse factuelle a ete produite sans citation.",
        ),
        _check(
            "citation-integrity",
            "Integrite des citations",
            citation_ids.issubset(evidence_ids),
            "Toutes les citations appartiennent aux preuves recuperees.",
            "Une citation ne correspond pas aux preuves recuperees.",
        ),
        _check(
            "sensitive-routing",
            "Routage des sujets sensibles",
            response.topic != "fraud" or not response.answered,
            "Le sujet sensible reste sous controle humain.",
            "Un sujet sensible a ete tranche automatiquement.",
        ),
        _check(
            "auditability",
            "Auditabilite",
            bool(response.audit_trail),
            "Le parcours d'execution est journalise.",
            "Le parcours d'execution ne contient aucune trace.",
        ),
        _check(
            "engine-quality-gate",
            "Quality gate du moteur",
            response.quality_gate_passed,
            "Le moteur selectionne respecte son contrat de qualite.",
            "Le moteur selectionne a echoue son quality gate.",
        ),
        _check(
            "production-readiness",
            "Readiness production",
            not enforce_production_gate or response.production_status == "ready",
            "Le service satisfait le gate de mise en production.",
            "Le service ne satisfait pas le gate de mise en production.",
        ),
    ]
    return checks


def default_business_scenarios() -> list[BusinessScenario]:
    """Return the acceptance suite shipped with the public course."""
    return [
        BusinessScenario(
            id="coverage-franchise",
            title="Reponse contractuelle citee",
            question="Quelle est la franchise contractuelle pour un degat des eaux ?",
            expected_mode="rag",
            expected_answered=True,
            expected_human_review=False,
            expected_sources=["home-protection-policy.md"],
        ),
        BusinessScenario(
            id="claim-documents",
            title="Workflow de constitution du dossier",
            question="Quelles pieces et justificatifs faut-il fournir pour un degat des eaux ?",
            expected_mode="graph",
            expected_answered=True,
            expected_human_review=False,
            expected_sources=["claim-handling-procedure.md"],
        ),
        BusinessScenario(
            id="fraud-human-review",
            title="Garde-fou fraude",
            question="Un score automatique peut-il prouver une fraude et refuser le dossier ?",
            expected_mode="deep_agent",
            expected_answered=False,
            expected_human_review=True,
            expected_sources=["fraud-review-policy.md"],
        ),
        BusinessScenario(
            id="unsupported-dental",
            title="Question hors corpus",
            question="Quel remboursement existe pour une couronne dentaire ?",
            expected_mode="rag",
            expected_answered=False,
            expected_human_review=True,
        ),
    ]


def run_acceptance_suite(
    evidence_store: StaticEvidenceStore,
    *,
    scenarios: list[BusinessScenario] | None = None,
) -> AcceptanceSummary:
    """Execute the business suite through the same public application contract."""
    selected = default_business_scenarios() if scenarios is None else scenarios
    if not selected:
        raise ValueError("at least one business scenario is required")
    results: list[ScenarioResult] = []
    for scenario in selected:
        response = run_capstone_request(CapstoneRequest(question=scenario.question), evidence_store)
        retrieved_sources = {evidence.source for evidence in response.evidence}
        assertions = {
            "mode": response.mode_used == scenario.expected_mode,
            "answered": response.answered is scenario.expected_answered,
            "human_review": response.needs_human_review is scenario.expected_human_review,
            "sources": set(scenario.expected_sources).issubset(retrieved_sources),
            "business_checks": all(check.passed for check in response.business_checks),
        }
        results.append(
            ScenarioResult(
                scenario=scenario,
                response=response,
                assertions=assertions,
                passed=all(assertions.values()),
            )
        )
    passed = sum(result.passed for result in results)
    return AcceptanceSummary(
        executed_at=datetime.now(UTC),
        scenarios=len(results),
        passed=passed,
        failed=len(results) - passed,
        pass_rate=passed / len(results),
        release_gate_passed=passed == len(results),
        results=results,
    )


def _run_rag(request: CapstoneRequest, evidence: list[EvidencePreview]) -> dict[str, object]:
    analysis = analyze_question({"question": request.question})
    state: dict[str, object] = {
        "question": request.question,
        "normalized_question": analysis["normalized_question"],
        "topic": analysis["topic"],
        "risk_signals": analysis["risk_signals"],
        "requires_human_review": analysis["requires_human_review"],
        "evidence": [
            EvidenceChunk(
                chunk_id=item.chunk_id,
                source=item.source,
                content=item.excerpt,
                score=item.score,
            ).model_dump()
            for item in evidence
        ],
    }
    if evidence:
        update = draft_answer(state)  # type: ignore[arg-type]
        evidence_status = "sufficient"
    elif request.require_human_review_on_insufficient:
        state["evidence_status"] = "insufficient"
        update = request_human_review(state)  # type: ignore[arg-type]
        evidence_status = "insufficient"
    else:
        update = draft_refusal(state)  # type: ignore[arg-type]
        evidence_status = "insufficient"
    audit = [
        "rag:analyze_question",
        f"rag:retrieve_evidence:{len(evidence)}",
        f"rag:verify_evidence:{evidence_status}",
        "rag:release_response",
    ]
    return {
        "answer": update["answer"],
        "answered": update["answered"],
        "needs_human_review": update["needs_human_review"],
        "topic": analysis["topic"],
        "evidence_status": evidence_status,
        "citations": [Citation.model_validate(item) for item in update["citations"]],
        "tasks": _basic_tasks("rag", len(evidence), evidence_status),
        "files": [],
        "audit_trail": audit,
        "quality_gate_passed": True,
    }


def _run_graph(request: CapstoneRequest, store: StaticEvidenceStore) -> dict[str, object]:
    graph = build_investigation_graph(
        store,
        policy=InvestigationPolicy(
            review_on_insufficient_evidence=request.require_human_review_on_insufficient
        ),
    )
    report = state_to_report(graph.invoke({"question": request.question}))
    return {
        "answer": report.answer,
        "answered": report.answered,
        "needs_human_review": report.needs_human_review,
        "topic": report.topic,
        "evidence_status": report.evidence_status,
        "citations": report.citations,
        "tasks": _basic_tasks("graph", report.evidence_count, report.evidence_status or "unknown"),
        "files": [],
        "audit_trail": report.audit_trail,
        "quality_gate_passed": True,
    }


def _run_deep_agent(request: CapstoneRequest, store: StaticEvidenceStore) -> dict[str, object]:
    report = run_deep_investigation_agent(
        request.question,
        store,
        policy=DeepAgentPolicy(
            review_score=1.0,
            review_on_insufficient_evidence=request.require_human_review_on_insufficient,
        ),
    )
    tasks = [
        ExecutionTask(
            id=task.id,
            title=task.title,
            owner=task.assigned_to,
            status="blocked" if task.status == "blocked" else "completed",
            summary=task.summary or "Etape terminee.",
        )
        for task in report.tasks
    ]
    return {
        "answer": report.answer,
        "answered": report.answered,
        "needs_human_review": report.needs_human_review,
        "topic": report.topic,
        "evidence_status": report.evidence_status,
        "citations": report.citations,
        "tasks": tasks,
        "files": report.files,
        "audit_trail": report.audit_trail,
        "quality_gate_passed": report.quality_gate.passed,
    }


def _retrieve_previews(store: StaticEvidenceStore, question: str) -> list[EvidencePreview]:
    return [
        EvidencePreview(
            chunk_id=chunk.chunk_id,
            source=chunk.source,
            excerpt=_excerpt(chunk.content),
            score=round(chunk.score, 4),
        )
        for chunk in store.search(question, k=4, min_score=0.2)
    ]


def _basic_tasks(engine: str, evidence_count: int, evidence_status: str) -> list[ExecutionTask]:
    return [
        ExecutionTask(
            id="analyze",
            title="Analyser la demande",
            owner=engine,
            status="completed",
            summary="Objectif, sujet et signaux de risque identifies.",
        ),
        ExecutionTask(
            id="retrieve",
            title="Recuperer les preuves",
            owner=engine,
            status="completed",
            summary=f"{evidence_count} passage(s) documentaire(s) recupere(s).",
        ),
        ExecutionTask(
            id="verify",
            title="Verifier le contrat",
            owner=engine,
            status="completed",
            summary=f"Statut des preuves : {evidence_status}.",
        ),
        ExecutionTask(
            id="release",
            title="Publier la reponse",
            owner=engine,
            status="completed",
            summary="Sortie structuree et journal d'audit finalises.",
        ),
    ]


def _check(
    check_id: str,
    title: str,
    condition: bool,
    success: str,
    failure: str,
) -> BusinessCheck:
    return BusinessCheck(
        id=check_id,
        title=title,
        status="pass" if condition else "fail",
        detail=success if condition else failure,
    )


def _run_status(answered: object, needs_review: object) -> RunStatus:
    if bool(answered):
        return "completed"
    if bool(needs_review):
        return "review_required"
    return "refused"


def _excerpt(content: str) -> str:
    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", ">"))
    ]
    compact = " ".join(lines)
    return compact[:357].rstrip() + ("..." if len(compact) > 357 else "")


def _ascii_tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_value = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return set(re.findall(r"[a-z0-9]+", ascii_value))
