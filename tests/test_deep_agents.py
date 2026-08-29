import json

import pytest

from ai_course.deep_agents import (
    AgentTask,
    DeepAgentPolicy,
    FilePermission,
    InMemoryAgentFileSystem,
    LongTermMemory,
    PermissionApprovalRequired,
    PermissionDenied,
    build_default_subagents,
    build_investigation_plan,
    evaluate_quality_gate,
    normalize_agent_path,
    run_deep_investigation_agent,
)
from ai_course.investigation_graph import EvidenceChunk, StaticEvidenceStore


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
            ),
        ]
    )


def test_filesystem_permissions_are_first_match_wins() -> None:
    filesystem = InMemoryAgentFileSystem(
        permissions=[
            FilePermission(operations=["write"], paths=["/workspace/public/**"], mode="allow"),
            FilePermission(operations=["write"], paths=["/workspace/**"], mode="deny"),
        ]
    )

    filesystem.write_text("/workspace/public/report.md", "ok")
    with pytest.raises(PermissionDenied):
        filesystem.write_text("/workspace/private/report.md", "blocked")


def test_filesystem_interrupt_mode_requires_approval() -> None:
    filesystem = InMemoryAgentFileSystem(
        permissions=[
            FilePermission(operations=["write"], paths=["/reports/**"], mode="interrupt"),
        ]
    )

    with pytest.raises(PermissionApprovalRequired):
        filesystem.write_text("/reports/final.md", "needs approval")


def test_default_permissions_block_secrets_and_path_traversal() -> None:
    filesystem = InMemoryAgentFileSystem()

    with pytest.raises(PermissionDenied):
        filesystem.write_text("/secrets/api_key.txt", "secret")
    with pytest.raises(ValueError, match="cannot contain"):
        normalize_agent_path("/workspace/../secrets/key")


def test_plan_and_subagents_have_professional_contracts() -> None:
    tasks = build_investigation_plan("Quelle est la franchise ?")
    subagents = build_default_subagents()

    assert [task.id for task in tasks] == [
        "plan-objective",
        "retrieve-evidence",
        "verify-route",
        "draft-report",
        "quality-gate",
    ]
    assert tasks[-1].depends_on == ["draft-report"]
    assert {subagent.name for subagent in subagents} == {
        "planner",
        "researcher",
        "verifier",
        "writer",
        "quality_reviewer",
    }


def test_deep_agent_answers_and_offloads_intermediate_files() -> None:
    filesystem = InMemoryAgentFileSystem()
    report = run_deep_investigation_agent(
        "Quelle est la franchise degat des eaux ?",
        make_store(),
        filesystem=filesystem,
    )

    assert report.answered is True
    assert report.needs_human_review is False
    assert report.topic == "coverage"
    assert report.citations[0].source == "home.md"
    assert report.quality_gate.passed is True
    assert "/workspace/evidence.json" in report.files
    assert "/reports/investigation_report.md" in report.files
    assert all(task.status == "completed" for task in report.tasks)
    assert "180 euros" in filesystem.read_text("/reports/investigation_report.md")
    assert "raw evidence offloaded" in report.main_context[1]


def test_deep_agent_sensitive_question_routes_to_human_review_and_updates_memory() -> None:
    memory = LongTermMemory()
    report = run_deep_investigation_agent(
        "Un score de risque prouve-t-il une fraude ?",
        make_store(),
        policy=DeepAgentPolicy(review_score=0.95),
        memory=memory,
    )

    assert report.answered is False
    assert report.needs_human_review is True
    assert report.topic == "fraud"
    assert report.evidence_count == 1
    assert report.quality_gate.passed is True
    assert report.memory_updates == ["fraud_review_policy"]
    assert memory.recall("fraud_review_policy") is not None


def test_deep_agent_missing_context_requests_review_without_citations() -> None:
    report = run_deep_investigation_agent(
        "Quel remboursement existe pour une couronne dentaire ?",
        make_store(),
    )

    assert report.answered is False
    assert report.needs_human_review is True
    assert report.topic == "unknown"
    assert report.evidence_count == 0
    assert report.citations == []
    assert report.quality_gate.passed is True


def test_quality_gate_flags_bad_report_contract() -> None:
    tasks = [
        AgentTask(
            id="draft-report",
            title="Draft report",
            assigned_to="writer",
            status="completed",
        )
    ]
    gate = evaluate_quality_gate(
        report={
            "answered": True,
            "needs_human_review": False,
            "citations": [],
            "audit_trail": [],
        },
        tasks=tasks,
        files=[],
    )

    assert gate.passed is False
    assert "answered_cases_have_citations" in gate.notes
    assert "report_file_written" in gate.notes


def test_filesystem_json_outputs_are_readable() -> None:
    filesystem = InMemoryAgentFileSystem()
    run_deep_investigation_agent(
        "Quel est le delai pour declarer un vol ?",
        make_store(),
        filesystem=filesystem,
    )

    evidence_payload = json.loads(filesystem.read_text("/workspace/evidence.json"))
    verification_payload = json.loads(filesystem.read_text("/workspace/verification.json"))

    assert evidence_payload["evidence"][0]["source"] == "claim.md"
    assert verification_payload["next_action"] == "draft_answer"
