"""LangGraph workflow primitives for a documentary investigation assistant."""

from __future__ import annotations

import operator
import re
from typing import Annotated, Literal, Protocol, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field, model_validator

from ai_course.rag_basics import Citation, RetrievedChunk

Topic = Literal["coverage", "claim", "fraud", "unknown"]
EvidenceStatus = Literal["sufficient", "insufficient", "needs_human_review"]
NextAction = Literal["draft_answer", "draft_refusal", "request_human_review"]
STOPWORDS = frozenset(
    {
        "a",
        "au",
        "aux",
        "ce",
        "dans",
        "de",
        "des",
        "du",
        "elle",
        "en",
        "est",
        "et",
        "existe",
        "il",
        "la",
        "le",
        "les",
        "pour",
        "que",
        "quel",
        "quelle",
        "quelles",
        "quels",
        "qui",
        "sur",
        "t",
        "un",
        "une",
    }
)
FOCUS_TERMS = frozenset(
    {
        "caracteristiques",
        "delai",
        "franchise",
        "indemnisation",
        "pieces",
        "plafond",
        "preuve",
        "preuves",
        "remboursement",
        "score",
    }
)


class EvidenceChunk(BaseModel):
    """Evidence passed through the graph state."""

    chunk_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    content: str = Field(min_length=1)
    score: float = Field(default=0.0, ge=0.0, le=1.0)

    @classmethod
    def from_retrieved_chunk(cls, chunk: RetrievedChunk) -> EvidenceChunk:
        return cls(
            chunk_id=chunk.chunk_id,
            source=chunk.source,
            content=chunk.content,
            score=chunk.score,
        )


class QuestionAnalysis(BaseModel):
    """Deterministic analysis used to route an investigation."""

    normalized_question: str = Field(min_length=1)
    topic: Topic
    risk_signals: list[str] = Field(default_factory=list)
    requires_human_review: bool = False


class HumanReviewDecision(BaseModel):
    """Human decision used to resume or simulate a review step."""

    approved: bool
    notes: str = ""
    replacement_answer: str | None = None

    @model_validator(mode="after")
    def validate_replacement_answer(self) -> HumanReviewDecision:
        if self.replacement_answer is not None and not self.replacement_answer.strip():
            raise ValueError("replacement_answer cannot be empty")
        return self


class InvestigationPolicy(BaseModel):
    """Thresholds controlling deterministic graph routing."""

    k: int = Field(default=4, ge=1)
    min_score: float = Field(default=0.2, ge=0.0, le=1.0)
    review_score: float = Field(default=0.55, ge=0.0, le=1.0)
    min_evidence: int = Field(default=1, ge=1)
    review_on_insufficient_evidence: bool = True


class InvestigationReport(BaseModel):
    """Stable response shape exposed by the LangGraph workflow."""

    question: str
    answer: str
    answered: bool
    needs_human_review: bool
    topic: Topic
    evidence_status: EvidenceStatus | None = None
    evidence_count: int = Field(ge=0)
    citations: list[Citation] = Field(default_factory=list)
    audit_trail: list[str] = Field(default_factory=list)
    human_notes: str | None = None


class InvestigationState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes."""

    question: str
    normalized_question: str
    topic: Topic
    risk_signals: list[str]
    requires_human_review: bool
    evidence: list[dict[str, object]]
    evidence_status: EvidenceStatus
    next_action: NextAction
    answer: str
    answered: bool
    needs_human_review: bool
    citations: list[dict[str, str]]
    human_decision: dict[str, object]
    human_notes: str
    audit_trail: Annotated[list[str], operator.add]


class EvidenceStore(Protocol):
    """Search capability required by the graph's retrieval node."""

    def search(self, query: str, *, k: int, min_score: float) -> list[EvidenceChunk]:
        """Return candidate evidence chunks."""
        ...


class StaticEvidenceStore:
    """Small deterministic lexical evidence store for examples and tests."""

    def __init__(self, chunks: list[EvidenceChunk]) -> None:
        if not chunks:
            raise ValueError("At least one evidence chunk is required")
        self._chunks = chunks

    def search(self, query: str, *, k: int, min_score: float) -> list[EvidenceChunk]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if k < 1:
            raise ValueError("k must be at least 1")
        if not 0.0 <= min_score <= 1.0:
            raise ValueError("min_score must be between 0 and 1")

        query_tokens = set(_tokens(query))
        scored: list[EvidenceChunk] = []
        for chunk in self._chunks:
            chunk_tokens = set(_tokens(f"{chunk.source} {chunk.content}"))
            lexical_score = (
                len(query_tokens.intersection(chunk_tokens)) / len(query_tokens)
                if query_tokens
                else 0.0
            )
            if lexical_score >= min_score:
                scored.append(chunk.model_copy(update={"score": lexical_score}))

        return sorted(scored, key=lambda item: (-item.score, item.source, item.chunk_id))[:k]


def analyze_question(state: InvestigationState) -> dict[str, object]:
    """Classify a question before retrieval."""
    question = state.get("question", "").strip()
    if not question:
        raise ValueError("question is required")

    analysis = _analyze_question(question)
    return {
        "normalized_question": analysis.normalized_question,
        "topic": analysis.topic,
        "risk_signals": analysis.risk_signals,
        "requires_human_review": analysis.requires_human_review,
        "audit_trail": ["analyze_question"],
    }


def verify_evidence(state: InvestigationState, policy: InvestigationPolicy) -> dict[str, object]:
    """Decide whether the graph can answer or must ask for review."""
    evidence = _state_evidence(state)
    if len(evidence) < policy.min_evidence:
        status: EvidenceStatus = "insufficient"
        next_action: NextAction = (
            "request_human_review" if policy.review_on_insufficient_evidence else "draft_refusal"
        )
    elif (
        state.get("requires_human_review")
        and max(chunk.score for chunk in evidence) < policy.review_score
    ):
        status = "needs_human_review"
        next_action = "request_human_review"
    else:
        status = "sufficient"
        next_action = "draft_answer"

    return {
        "evidence_status": status,
        "next_action": next_action,
        "audit_trail": [f"verify_evidence:{status}"],
    }


def route_after_verification(state: InvestigationState) -> NextAction:
    """Return the next node selected by deterministic verification."""
    action = state.get("next_action")
    if action not in {"draft_answer", "draft_refusal", "request_human_review"}:
        raise ValueError(f"Unknown next_action: {action}")
    return action


def draft_answer(state: InvestigationState) -> dict[str, object]:
    """Create a deterministic answer from verified evidence."""
    evidence = _state_evidence(state)
    if not evidence:
        raise ValueError("draft_answer requires evidence")
    return {
        "answer": _compose_answer(evidence, question=state.get("normalized_question")),
        "answered": True,
        "needs_human_review": False,
        "citations": _citations_from_evidence(evidence),
        "audit_trail": ["draft_answer"],
    }


def draft_refusal(state: InvestigationState) -> dict[str, object]:
    """Return a controlled refusal when the graph should not answer."""
    return {
        "answer": "Je ne dispose pas de preuves suffisantes dans les documents indexes.",
        "answered": False,
        "needs_human_review": False,
        "citations": [],
        "audit_trail": ["draft_refusal"],
    }


def request_human_review(
    state: InvestigationState,
    *,
    interactive: bool = False,
) -> dict[str, object]:
    """Pause for human review or mark the run as awaiting validation."""
    raw_decision: object | None = state.get("human_decision")
    if interactive:
        raw_decision = interrupt(_review_payload(state))

    if raw_decision is None:
        return {
            "answer": "Validation humaine requise avant de repondre.",
            "answered": False,
            "needs_human_review": True,
            "citations": [],
            "audit_trail": ["request_human_review:pending"],
        }

    decision = HumanReviewDecision.model_validate(raw_decision)
    evidence = _state_evidence(state)
    if decision.approved and evidence:
        answer = decision.replacement_answer or _compose_answer(
            evidence,
            question=state.get("normalized_question"),
        )
        return {
            "answer": answer,
            "answered": True,
            "needs_human_review": False,
            "citations": _citations_from_evidence(evidence),
            "human_notes": decision.notes,
            "audit_trail": ["request_human_review:approved"],
        }

    return {
        "answer": "La revue humaine n'a pas valide de reponse fondee sur les preuves.",
        "answered": False,
        "needs_human_review": False,
        "citations": [],
        "human_notes": decision.notes,
        "audit_trail": ["request_human_review:rejected"],
    }


def build_investigation_graph(
    evidence_store: EvidenceStore,
    *,
    policy: InvestigationPolicy | None = None,
    interactive_review: bool = False,
    checkpointer: object | None = None,
):
    """Build a LangGraph workflow for documentary investigation."""
    policy = policy or InvestigationPolicy()

    def retrieve_node(state: InvestigationState) -> dict[str, object]:
        chunks = evidence_store.search(
            state["normalized_question"],
            k=policy.k,
            min_score=policy.min_score,
        )
        return {
            "evidence": [chunk.model_dump() for chunk in chunks],
            "audit_trail": [f"retrieve_evidence:{len(chunks)}"],
        }

    def verify_node(state: InvestigationState) -> dict[str, object]:
        return verify_evidence(state, policy)

    def review_node(state: InvestigationState) -> dict[str, object]:
        return request_human_review(state, interactive=interactive_review)

    builder = StateGraph(InvestigationState)
    builder.add_node("analyze_question", analyze_question)
    builder.add_node("retrieve_evidence", retrieve_node)
    builder.add_node("verify_evidence", verify_node)
    builder.add_node("draft_answer", draft_answer)
    builder.add_node("draft_refusal", draft_refusal)
    builder.add_node("request_human_review", review_node)

    builder.add_edge(START, "analyze_question")
    builder.add_edge("analyze_question", "retrieve_evidence")
    builder.add_edge("retrieve_evidence", "verify_evidence")
    builder.add_conditional_edges("verify_evidence", route_after_verification)
    builder.add_edge("draft_answer", END)
    builder.add_edge("draft_refusal", END)
    builder.add_edge("request_human_review", END)

    if interactive_review and checkpointer is None:
        checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)


def state_to_report(state: InvestigationState) -> InvestigationReport:
    """Convert a graph state dictionary into a stable public report."""
    return InvestigationReport(
        question=str(state.get("question", "")),
        answer=str(state.get("answer", "Execution en attente de validation humaine.")),
        answered=bool(state.get("answered", False)),
        needs_human_review=bool(state.get("needs_human_review", "__interrupt__" in state)),
        topic=state.get("topic", "unknown"),
        evidence_status=state.get("evidence_status"),
        evidence_count=len(state.get("evidence", [])),
        citations=[Citation.model_validate(citation) for citation in state.get("citations", [])],
        audit_trail=list(state.get("audit_trail", [])),
        human_notes=state.get("human_notes"),
    )


def _analyze_question(question: str) -> QuestionAnalysis:
    tokens = set(_tokens(question))
    topic_scores = {
        "coverage": len(tokens.intersection({"garantie", "couvre", "franchise", "plafond"})),
        "claim": len(
            tokens.intersection({"declarer", "delai", "sinistre", "vol", "pieces", "justificatifs"})
        ),
        "fraud": len(tokens.intersection({"fraude", "score", "risque", "modele", "sensible"})),
    }
    topic: Topic = "unknown"
    if any(topic_scores.values()):
        topic = max(topic_scores, key=topic_scores.get)  # type: ignore[assignment]

    risk_signals = sorted(
        tokens.intersection(
            {
                "exclusion",
                "exclues",
                "fraude",
                "refus",
                "risque",
                "score",
                "sensible",
                "sensibles",
            }
        )
    )
    return QuestionAnalysis(
        normalized_question=" ".join(question.split()),
        topic=topic,
        risk_signals=risk_signals,
        requires_human_review=topic == "fraud" or bool(risk_signals),
    )


def _state_evidence(state: InvestigationState) -> list[EvidenceChunk]:
    return [EvidenceChunk.model_validate(chunk) for chunk in state.get("evidence", [])]


def _citations_from_evidence(evidence: list[EvidenceChunk]) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    seen: set[str] = set()
    for chunk in evidence:
        if chunk.chunk_id in seen:
            continue
        seen.add(chunk.chunk_id)
        citations.append({"chunk_id": chunk.chunk_id, "source": chunk.source})
    return citations


def _compose_answer(evidence: list[EvidenceChunk], *, question: str | None = None) -> str:
    primary = evidence[0]
    excerpt = _best_sentence(primary.content, question=question)
    if len(evidence) == 1:
        return f"Les preuves retrouvees indiquent : {excerpt}"
    sources = ", ".join(dict.fromkeys(chunk.source for chunk in evidence[1:]))
    return (
        f"Les preuves retrouvees indiquent : {excerpt} "
        f"Sources complementaires consultees : {sources}."
    )


def _best_sentence(content: str, *, question: str | None = None) -> str:
    sentences = _useful_sentences(content)
    if not sentences:
        compact = " ".join(content.split())
        return compact[:220].rstrip(".") + "."
    question_tokens = set(_tokens(question or ""))
    if not question_tokens:
        return sentences[0]
    return max(
        sentences,
        key=lambda sentence: (
            len(question_tokens.intersection(FOCUS_TERMS).intersection(_tokens(sentence))),
            len(question_tokens.intersection(_tokens(sentence))) / len(_tokens(sentence) or [""]),
            -sentences.index(sentence),
        ),
    )


def _useful_sentences(content: str) -> list[str]:
    useful_lines: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(">"):
            continue
        useful_lines.append(stripped)
    compact = " ".join(useful_lines)
    return [
        sentence.rstrip(".") + "."
        for sentence in re.split(r"(?<=[.!?])\s+", compact)
        if sentence.strip()
    ]


def _review_payload(state: InvestigationState) -> dict[str, object]:
    evidence = _state_evidence(state)
    return {
        "question": state.get("question", ""),
        "topic": state.get("topic", "unknown"),
        "evidence_status": state.get("evidence_status"),
        "risk_signals": state.get("risk_signals", []),
        "evidence_sources": [chunk.source for chunk in evidence],
        "suggested_answer": (
            _compose_answer(evidence, question=state.get("normalized_question"))
            if evidence
            else None
        ),
    }


def _tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"\w+", value.casefold()) if token not in STOPWORDS]
