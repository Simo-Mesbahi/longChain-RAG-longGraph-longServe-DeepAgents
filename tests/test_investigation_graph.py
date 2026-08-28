import pytest
from langgraph.types import Command

from ai_course.investigation_graph import (
    EvidenceChunk,
    HumanReviewDecision,
    InvestigationPolicy,
    StaticEvidenceStore,
    analyze_question,
    build_investigation_graph,
    state_to_report,
)


def make_store() -> StaticEvidenceStore:
    return StaticEvidenceStore(
        [
            EvidenceChunk(
                chunk_id="home.md#chunk-000",
                source="home.md",
                content="La franchise degat des eaux est fixee a 180 euros par sinistre.",
            ),
            EvidenceChunk(
                chunk_id="claim.md#chunk-000",
                source="claim.md",
                content="Un vol doit etre declare dans les deux jours ouvres.",
            ),
            EvidenceChunk(
                chunk_id="fraud.md#chunk-000",
                source="fraud.md",
                content="Un score eleve ne prouve pas une fraude et impose une analyse humaine.",
                score=0.4,
            ),
        ]
    )


def test_static_evidence_store_returns_ranked_matches() -> None:
    store = make_store()

    chunks = store.search("franchise degat eaux", k=2, min_score=0.1)

    assert chunks[0].source == "home.md"
    assert chunks[0].score == pytest.approx(1.0)


def test_question_analysis_detects_sensitive_fraud_route() -> None:
    update = analyze_question({"question": "Un score de risque prouve-t-il une fraude ?"})

    assert update["topic"] == "fraud"
    assert update["requires_human_review"] is True
    assert "fraude" in update["risk_signals"]


def test_graph_answers_when_evidence_is_sufficient() -> None:
    graph = build_investigation_graph(make_store())

    state = graph.invoke({"question": "Quelle est la franchise degat des eaux ?"})
    report = state_to_report(state)

    assert report.answered is True
    assert report.needs_human_review is False
    assert report.topic == "coverage"
    assert report.citations[0].source == "home.md"
    assert report.audit_trail == [
        "analyze_question",
        "retrieve_evidence:1",
        "verify_evidence:sufficient",
        "draft_answer",
    ]


def test_graph_marks_human_review_when_evidence_is_missing() -> None:
    graph = build_investigation_graph(make_store())

    state = graph.invoke({"question": "Quelle garantie existe pour une couronne dentaire ?"})
    report = state_to_report(state)

    assert report.answered is False
    assert report.needs_human_review is True
    assert report.evidence_status == "insufficient"
    assert report.audit_trail[-1] == "request_human_review:pending"


def test_graph_can_refuse_without_review_when_policy_disables_it() -> None:
    graph = build_investigation_graph(
        make_store(),
        policy=InvestigationPolicy(review_on_insufficient_evidence=False),
    )

    state = graph.invoke({"question": "Quelle garantie existe pour une couronne dentaire ?"})
    report = state_to_report(state)

    assert report.answered is False
    assert report.needs_human_review is False
    assert report.audit_trail[-1] == "draft_refusal"


def test_sensitive_low_confidence_evidence_goes_to_human_review() -> None:
    graph = build_investigation_graph(
        make_store(),
        policy=InvestigationPolicy(min_score=0.2, review_score=0.9),
    )

    state = graph.invoke({"question": "Un score de risque prouve-t-il une fraude ?"})
    report = state_to_report(state)

    assert report.answered is False
    assert report.needs_human_review is True
    assert report.evidence_status == "needs_human_review"


def test_non_interactive_human_decision_can_approve_answer() -> None:
    graph = build_investigation_graph(
        make_store(),
        policy=InvestigationPolicy(min_score=0.2, review_score=0.9),
    )

    state = graph.invoke(
        {
            "question": "Un score de risque prouve-t-il une fraude ?",
            "human_decision": {
                "approved": True,
                "notes": "Preuve suffisante pour une reponse prudente.",
                "replacement_answer": "Non, le score sert a prioriser et ne prouve pas la fraude.",
            },
        }
    )
    report = state_to_report(state)

    assert report.answered is True
    assert report.needs_human_review is False
    assert report.answer == "Non, le score sert a prioriser et ne prouve pas la fraude."
    assert report.human_notes == "Preuve suffisante pour une reponse prudente."
    assert report.citations[0].source == "fraud.md"


def test_human_review_decision_rejects_empty_replacement() -> None:
    with pytest.raises(ValueError, match="replacement_answer"):
        HumanReviewDecision(approved=True, replacement_answer="   ")


def test_interactive_graph_interrupts_and_resumes() -> None:
    graph = build_investigation_graph(
        make_store(),
        policy=InvestigationPolicy(min_score=0.2, review_score=0.9),
        interactive_review=True,
    )
    config = {"configurable": {"thread_id": "fraud-review-demo"}}

    first_state = graph.invoke(
        {"question": "Un score de risque prouve-t-il une fraude ?"},
        config,
    )

    assert "__interrupt__" in first_state
    payload = first_state["__interrupt__"][0].value
    assert payload["topic"] == "fraud"
    assert payload["evidence_status"] == "needs_human_review"

    final_state = graph.invoke(
        Command(
            resume={
                "approved": True,
                "notes": "Validation humaine OK.",
                "replacement_answer": (
                    "Non, une validation humaine fondee sur des preuves est requise."
                ),
            }
        ),
        config,
    )
    report = state_to_report(final_state)

    assert report.answered is True
    assert report.needs_human_review is False
    assert report.answer == "Non, une validation humaine fondee sur des preuves est requise."
    assert report.audit_trail[-1] == "request_human_review:approved"
