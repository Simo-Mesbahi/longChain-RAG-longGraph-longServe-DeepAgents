from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_course.capstone_platform import (
    BusinessScenario,
    CapstoneRequest,
    build_capstone_readiness,
    build_capstone_store,
    default_business_scenarios,
    run_acceptance_suite,
    run_capstone_request,
    select_execution_mode,
)

CORPUS_DIR = Path("projects/02-documentary-rag-assistant/data")


@pytest.fixture(scope="module")
def store():
    return build_capstone_store(CORPUS_DIR)


def test_capstone_request_normalizes_visible_whitespace() -> None:
    request = CapstoneRequest(question="  Quelle   est la franchise ?  ")

    assert request.question == "Quelle est la franchise ?"


def test_capstone_request_rejects_short_question() -> None:
    with pytest.raises(ValidationError, match="question"):
        CapstoneRequest(question="  ?  ")


@pytest.mark.parametrize(
    ("question", "mode"),
    [
        ("Quelle est la franchise ?", "rag"),
        ("Quelles pieces faut-il ajouter au dossier ?", "graph"),
        ("Analyse le risque de fraude de ce score.", "deep_agent"),
    ],
)
def test_auto_mode_selects_the_smallest_safe_engine(question: str, mode: str) -> None:
    assert select_execution_mode(question) == mode


def test_explicit_mode_overrides_auto_routing() -> None:
    assert select_execution_mode("Analyse le risque de fraude.", "graph") == "graph"


def test_rag_run_returns_grounded_citations_and_business_checks(store) -> None:
    response = run_capstone_request(
        CapstoneRequest(question="Quelle est la franchise pour un degat des eaux ?"),
        store,
    )

    assert response.mode_used == "rag"
    assert response.answered is True
    assert response.citations[0].source in {
        "compensation-rules.md",
        "home-protection-policy.md",
        "water-damage-playbook.md",
    }
    assert response.status == "completed"
    assert response.confidence > 0
    assert all(check.passed for check in response.business_checks)


def test_graph_run_exposes_workflow_and_audit_trail(store) -> None:
    response = run_capstone_request(
        CapstoneRequest(
            question="Quelles pieces et justificatifs faut-il fournir pour un degat des eaux ?"
        ),
        store,
    )

    assert response.mode_used == "graph"
    assert response.answered is True
    assert response.tasks[0].id == "analyze"
    assert "draft_answer" in response.audit_trail


def test_deep_agent_routes_fraud_to_human_review(store) -> None:
    response = run_capstone_request(
        CapstoneRequest(
            question="Un score automatique peut-il prouver une fraude et refuser le dossier ?"
        ),
        store,
    )

    assert response.mode_used == "deep_agent"
    assert response.answered is False
    assert response.needs_human_review is True
    assert response.status == "review_required"
    assert response.files
    assert response.quality_gate_passed is True


def test_unsupported_question_requests_review_without_citations(store) -> None:
    response = run_capstone_request(
        CapstoneRequest(question="Quel remboursement existe pour une couronne dentaire ?"),
        store,
    )

    assert response.answered is False
    assert response.needs_human_review is True
    assert response.citations == []
    assert response.evidence == []
    assert all(check.passed for check in response.business_checks)


def test_readiness_gate_is_green_for_documented_demo() -> None:
    report = build_capstone_readiness()

    assert report.status == "ready"
    assert report.score == 1.0
    assert "projects/07-asteria-investigation-platform" in report.manifest.command


def test_default_acceptance_suite_is_a_release_gate(store) -> None:
    summary = run_acceptance_suite(store)

    assert summary.scenarios == 4
    assert summary.passed == 4
    assert summary.failed == 0
    assert summary.pass_rate == 1.0
    assert summary.release_gate_passed is True


def test_acceptance_suite_rejects_empty_scenario_list(store) -> None:
    with pytest.raises(ValueError, match="at least one"):
        run_acceptance_suite(store, scenarios=[])


def test_acceptance_suite_reports_a_wrong_expectation(store) -> None:
    scenario = BusinessScenario(
        id="wrong-mode",
        title="Intentionally wrong expectation",
        question="Quelle est la franchise pour un degat des eaux ?",
        expected_mode="deep_agent",
        expected_answered=True,
        expected_human_review=False,
        expected_sources=["home-protection-policy.md"],
    )

    summary = run_acceptance_suite(store, scenarios=[scenario])

    assert summary.release_gate_passed is False
    assert summary.results[0].assertions["mode"] is False


def test_business_scenarios_have_unique_ids() -> None:
    scenarios = default_business_scenarios()

    assert len({scenario.id for scenario in scenarios}) == len(scenarios)
