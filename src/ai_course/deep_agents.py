"""Deterministic Deep Agents concepts for the course portfolio project."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from ai_course.investigation_graph import (
    EvidenceStore,
    InvestigationPolicy,
    Topic,
    analyze_question,
    draft_answer,
    draft_refusal,
    request_human_review,
    state_to_report,
    verify_evidence,
)
from ai_course.rag_basics import Citation

SubagentRole = Literal["planner", "researcher", "verifier", "writer", "quality_reviewer"]
TaskStatus = Literal["pending", "completed", "blocked"]
PermissionOperation = Literal["read", "write", "delete"]
PermissionMode = Literal["allow", "deny", "interrupt"]


class PermissionDenied(RuntimeError):
    """Raised when an agent filesystem operation is denied."""


class PermissionApprovalRequired(RuntimeError):
    """Raised when a filesystem operation requires human approval."""


class FilePermission(BaseModel):
    """Path-based rule inspired by Deep Agents filesystem permissions."""

    operations: list[PermissionOperation] = Field(min_length=1)
    paths: list[str] = Field(min_length=1)
    mode: PermissionMode = "allow"

    @model_validator(mode="after")
    def validate_paths(self) -> FilePermission:
        for path in self.paths:
            if not path.startswith("/"):
                raise ValueError("permission paths must be absolute")
        return self


class PermissionDecision(BaseModel):
    """Decision returned by the first matching permission rule."""

    operation: PermissionOperation
    path: str
    mode: PermissionMode
    allowed: bool
    requires_approval: bool = False
    reason: str


class VirtualFile(BaseModel):
    """File stored in the local educational agent filesystem."""

    path: str
    content: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class InMemoryAgentFileSystem:
    """Small virtual filesystem with first-match permission evaluation."""

    def __init__(
        self,
        *,
        permissions: list[FilePermission] | None = None,
    ) -> None:
        self.permissions = permissions if permissions is not None else default_permissions()
        self._files: dict[str, VirtualFile] = {}

    def check_permission(self, operation: PermissionOperation, path: str) -> PermissionDecision:
        """Return the permission decision for an operation and normalized path."""
        normalized = normalize_agent_path(path)
        for rule in self.permissions:
            if operation in rule.operations and any(
                _path_matches(pattern, normalized) for pattern in rule.paths
            ):
                return PermissionDecision(
                    operation=operation,
                    path=normalized,
                    mode=rule.mode,
                    allowed=rule.mode == "allow",
                    requires_approval=rule.mode == "interrupt",
                    reason=f"matched {rule.mode} rule for {rule.paths}",
                )
        return PermissionDecision(
            operation=operation,
            path=normalized,
            mode="allow",
            allowed=True,
            reason="no matching rule; permissive Deep Agents default",
        )

    def write_text(
        self,
        path: str,
        content: str,
        *,
        metadata: Mapping[str, str | int | float | bool | None] | None = None,
    ) -> None:
        """Write a text file after permission evaluation."""
        normalized = normalize_agent_path(path)
        decision = self.check_permission("write", normalized)
        _raise_for_decision(decision)
        self._files[normalized] = VirtualFile(
            path=normalized,
            content=content,
            metadata=dict(metadata or {}),
        )

    def read_text(self, path: str) -> str:
        """Read a text file after permission evaluation."""
        normalized = normalize_agent_path(path)
        decision = self.check_permission("read", normalized)
        _raise_for_decision(decision)
        if normalized not in self._files:
            raise FileNotFoundError(normalized)
        return self._files[normalized].content

    def delete(self, path: str) -> None:
        """Delete a file after permission evaluation."""
        normalized = normalize_agent_path(path)
        decision = self.check_permission("delete", normalized)
        _raise_for_decision(decision)
        self._files.pop(normalized, None)

    def list_paths(self, prefix: str = "/") -> list[str]:
        """List files under a prefix after read permission evaluation."""
        normalized = normalize_agent_path(prefix)
        decision = self.check_permission("read", normalized)
        _raise_for_decision(decision)
        if normalized == "/":
            return sorted(self._files)
        return sorted(
            path for path in self._files if path == normalized or path.startswith(f"{normalized}/")
        )


class AgentTask(BaseModel):
    """One planned task delegated to a specialized subagent."""

    id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(min_length=3)
    assigned_to: SubagentRole
    depends_on: list[str] = Field(default_factory=list)
    status: TaskStatus = "pending"
    output_path: str | None = None
    summary: str | None = None

    @model_validator(mode="after")
    def validate_dependencies(self) -> AgentTask:
        if self.id in self.depends_on:
            raise ValueError("a task cannot depend on itself")
        if self.output_path is not None:
            normalize_agent_path(self.output_path)
        return self


class SubagentSpec(BaseModel):
    """Configuration contract for a delegated subagent."""

    name: SubagentRole
    description: str = Field(min_length=10)
    tools: list[str] = Field(default_factory=list)
    system_contract: str = Field(min_length=10)
    output_contract: str = Field(min_length=10)


class SubagentResult(BaseModel):
    """Concise result returned to the main agent after delegation."""

    subagent: SubagentRole
    task_id: str
    summary: str = Field(min_length=1)
    files_written: list[str] = Field(default_factory=list)
    context_chars_returned: int = Field(ge=0)


class DeepAgentPolicy(BaseModel):
    """Runtime policy for the educational deep investigation agent."""

    k: int = Field(default=1, ge=1)
    min_score: float = Field(default=0.2, ge=0.0, le=1.0)
    review_score: float = Field(default=0.9, ge=0.0, le=1.0)
    review_on_insufficient_evidence: bool = True
    max_subagent_summary_chars: int = Field(default=700, ge=120)

    def to_investigation_policy(self) -> InvestigationPolicy:
        """Reuse the previous LangGraph routing policy."""
        return InvestigationPolicy(
            k=self.k,
            min_score=self.min_score,
            review_score=self.review_score,
            review_on_insufficient_evidence=self.review_on_insufficient_evidence,
        )


class LongTermMemory(BaseModel):
    """Minimal durable-memory shape used by the course examples."""

    facts: dict[str, str] = Field(default_factory=dict)

    def remember(self, key: str, value: str) -> None:
        """Store a stable fact learned during a run."""
        if not key.strip():
            raise ValueError("memory key cannot be empty")
        if not value.strip():
            raise ValueError("memory value cannot be empty")
        self.facts[key] = value

    def recall(self, key: str) -> str | None:
        """Read one remembered fact."""
        return self.facts.get(key)


class QualityGate(BaseModel):
    """Final quality gate for a delegated deep-agent run."""

    passed: bool
    checks: dict[str, bool]
    notes: list[str] = Field(default_factory=list)


class DeepAgentRunReport(BaseModel):
    """Public report returned by the educational Deep Agent workflow."""

    objective: str
    answer: str
    answered: bool
    needs_human_review: bool
    topic: Topic
    evidence_status: str | None = None
    evidence_count: int = Field(ge=0)
    citations: list[Citation] = Field(default_factory=list)
    tasks: list[AgentTask]
    subagent_results: list[SubagentResult]
    files: list[str] = Field(default_factory=list)
    main_context: list[str] = Field(default_factory=list)
    audit_trail: list[str] = Field(default_factory=list)
    quality_gate: QualityGate
    memory_updates: list[str] = Field(default_factory=list)


def default_permissions() -> list[FilePermission]:
    """Return conservative permissions for the educational deep-agent project."""
    return [
        FilePermission(operations=["read", "write", "delete"], paths=["/secrets/**"], mode="deny"),
        FilePermission(
            operations=["read", "write", "delete"], paths=["/.env", "/.env.*"], mode="deny"
        ),
        FilePermission(
            operations=["read", "write", "delete"], paths=["/workspace/**"], mode="allow"
        ),
        FilePermission(operations=["read", "write", "delete"], paths=["/reports/**"], mode="allow"),
        FilePermission(operations=["read", "write"], paths=["/memories/**"], mode="allow"),
        FilePermission(operations=["read"], paths=["/"], mode="allow"),
        FilePermission(operations=["read", "write", "delete"], paths=["/**"], mode="deny"),
    ]


def build_default_subagents() -> list[SubagentSpec]:
    """Define the specialized subagents used by the project."""
    return [
        SubagentSpec(
            name="planner",
            description="Turns the objective into explicit tasks and dependencies.",
            tools=["write_file"],
            system_contract="Create a short auditable plan before any retrieval or writing.",
            output_contract="Return task ids, dependencies, and file paths only.",
        ),
        SubagentSpec(
            name="researcher",
            description="Retrieves documentary evidence and offloads raw findings to files.",
            tools=["search_evidence", "write_file"],
            system_contract="Search only the approved corpus and never invent a source.",
            output_contract="Return a concise summary and write full evidence to a file.",
        ),
        SubagentSpec(
            name="verifier",
            description="Checks evidence sufficiency and sensitive-routing constraints.",
            tools=["read_file", "write_file"],
            system_contract="Verify whether the answer can be drafted or must be reviewed.",
            output_contract="Return evidence status, next action, and reasons.",
        ),
        SubagentSpec(
            name="writer",
            description="Drafts the final response from verified evidence or a controlled refusal.",
            tools=["read_file", "write_file"],
            system_contract="Write only claims supported by verified evidence.",
            output_contract="Return an answer, citations, and review status.",
        ),
        SubagentSpec(
            name="quality_reviewer",
            description="Runs final contract checks before returning the answer.",
            tools=["read_file", "write_file"],
            system_contract="Block outputs without audit trail, citations, or review rationale.",
            output_contract="Return pass/fail checks and short notes.",
        ),
    ]


def build_investigation_plan(objective: str) -> list[AgentTask]:
    """Build a deterministic task plan for a long-running investigation."""
    if not objective.strip():
        raise ValueError("objective is required")
    return [
        AgentTask(
            id="plan-objective",
            title="Clarify objective, topic, risk signals, and execution contract",
            assigned_to="planner",
            output_path="/workspace/plan.json",
        ),
        AgentTask(
            id="retrieve-evidence",
            title="Retrieve and offload documentary evidence",
            assigned_to="researcher",
            depends_on=["plan-objective"],
            output_path="/workspace/evidence.json",
        ),
        AgentTask(
            id="verify-route",
            title="Verify evidence sufficiency and select the safe route",
            assigned_to="verifier",
            depends_on=["retrieve-evidence"],
            output_path="/workspace/verification.json",
        ),
        AgentTask(
            id="draft-report",
            title="Draft cited answer, controlled refusal, or human-review request",
            assigned_to="writer",
            depends_on=["verify-route"],
            output_path="/reports/investigation_report.md",
        ),
        AgentTask(
            id="quality-gate",
            title="Run final quality and safety checks",
            assigned_to="quality_reviewer",
            depends_on=["draft-report"],
            output_path="/workspace/quality_gate.json",
        ),
    ]


def run_deep_investigation_agent(
    objective: str,
    evidence_store: EvidenceStore,
    *,
    policy: DeepAgentPolicy | None = None,
    filesystem: InMemoryAgentFileSystem | None = None,
    memory: LongTermMemory | None = None,
) -> DeepAgentRunReport:
    """Run a deterministic Deep Agents-inspired investigation workflow."""
    if not objective.strip():
        raise ValueError("objective is required")

    policy = policy or DeepAgentPolicy()
    filesystem = filesystem or InMemoryAgentFileSystem()
    memory = memory or LongTermMemory()
    tasks = build_investigation_plan(objective)
    subagent_results: list[SubagentResult] = []
    main_context: list[str] = []
    audit_trail: list[str] = []
    memory_updates: list[str] = []

    analysis_update = analyze_question({"question": objective})
    audit_trail.extend(["planner:start", "planner:completed"])
    _write_json(
        filesystem,
        "/workspace/plan.json",
        {
            "objective": objective,
            "analysis": _jsonable(analysis_update),
            "tasks": [task.model_dump(mode="json") for task in tasks],
        },
    )
    requires_review = analysis_update["requires_human_review"]
    _complete_task(
        tasks,
        "plan-objective",
        summary=f"topic={analysis_update['topic']}; review={requires_review}",
    )
    _append_subagent_result(
        subagent_results,
        main_context,
        policy,
        SubagentResult(
            subagent="planner",
            task_id="plan-objective",
            summary=f"Plan ready for topic {analysis_update['topic']}.",
            files_written=["/workspace/plan.json"],
            context_chars_returned=0,
        ),
    )

    evidence = evidence_store.search(
        str(analysis_update["normalized_question"]),
        k=policy.k,
        min_score=policy.min_score,
    )
    audit_trail.extend(["researcher:start", f"researcher:evidence:{len(evidence)}"])
    _write_json(
        filesystem,
        "/workspace/evidence.json",
        {"evidence": [chunk.model_dump(mode="json") for chunk in evidence]},
    )
    _complete_task(
        tasks,
        "retrieve-evidence",
        summary=f"{len(evidence)} evidence chunks written to /workspace/evidence.json",
    )
    _append_subagent_result(
        subagent_results,
        main_context,
        policy,
        SubagentResult(
            subagent="researcher",
            task_id="retrieve-evidence",
            summary=f"{len(evidence)} evidence chunks found; raw evidence offloaded to file.",
            files_written=["/workspace/evidence.json"],
            context_chars_returned=0,
        ),
    )

    state: dict[str, Any] = {
        "question": objective,
        "normalized_question": analysis_update["normalized_question"],
        "topic": analysis_update["topic"],
        "risk_signals": analysis_update["risk_signals"],
        "requires_human_review": analysis_update["requires_human_review"],
        "evidence": [chunk.model_dump(mode="json") for chunk in evidence],
        "audit_trail": list(analysis_update["audit_trail"]),
    }
    verification_update = verify_evidence(state, policy.to_investigation_policy())
    state.update(verification_update)
    audit_trail.extend(["verifier:start", f"verifier:{state['evidence_status']}"])
    _write_json(
        filesystem,
        "/workspace/verification.json",
        {
            "evidence_status": state["evidence_status"],
            "next_action": state["next_action"],
            "risk_signals": state["risk_signals"],
            "requires_human_review": state["requires_human_review"],
        },
    )
    _complete_task(
        tasks,
        "verify-route",
        summary=f"route={state['next_action']}; evidence_status={state['evidence_status']}",
    )
    next_action = state["next_action"]
    evidence_status = state["evidence_status"]
    _append_subagent_result(
        subagent_results,
        main_context,
        policy,
        SubagentResult(
            subagent="verifier",
            task_id="verify-route",
            summary=f"Selected route {next_action} with status {evidence_status}.",
            files_written=["/workspace/verification.json"],
            context_chars_returned=0,
        ),
    )

    writer_update = _run_writer(state)
    state.update(writer_update)
    report = state_to_report(state)
    audit_trail.extend(["writer:start", "writer:completed"])
    filesystem.write_text(
        "/reports/investigation_report.md",
        format_markdown_report(report.model_dump(mode="json")),
        metadata={"subagent": "writer", "task_id": "draft-report"},
    )
    _complete_task(
        tasks,
        "draft-report",
        summary="Final report written to /reports/investigation_report.md",
    )
    answered = report.answered
    needs_human_review = report.needs_human_review
    _append_subagent_result(
        subagent_results,
        main_context,
        policy,
        SubagentResult(
            subagent="writer",
            task_id="draft-report",
            summary=f"Drafted final report; answered={answered}; review={needs_human_review}.",
            files_written=["/reports/investigation_report.md"],
            context_chars_returned=0,
        ),
    )

    if report.topic == "fraud":
        memory_key = "fraud_review_policy"
        memory.remember(
            memory_key,
            "Questions about fraud scores or refusals require evidence and human validation.",
        )
        filesystem.write_text(
            "/memories/fraud_review_policy.md",
            memory.recall(memory_key) or "",
            metadata={"topic": "fraud"},
        )
        memory_updates.append(memory_key)

    audit_trail.append("quality_reviewer:start")
    _complete_task(tasks, "quality-gate", summary="Quality gate running")
    quality_gate = evaluate_quality_gate(
        report=report.model_dump(mode="json"),
        tasks=tasks,
        files=filesystem.list_paths("/"),
    )
    audit_trail.append(f"quality_reviewer:passed:{quality_gate.passed}")
    _write_json(filesystem, "/workspace/quality_gate.json", quality_gate.model_dump(mode="json"))
    _complete_task(
        tasks,
        "quality-gate",
        summary="Quality gate passed" if quality_gate.passed else "Quality gate failed",
    )
    _append_subagent_result(
        subagent_results,
        main_context,
        policy,
        SubagentResult(
            subagent="quality_reviewer",
            task_id="quality-gate",
            summary="Quality gate passed." if quality_gate.passed else "Quality gate failed.",
            files_written=["/workspace/quality_gate.json"],
            context_chars_returned=0,
        ),
    )

    return DeepAgentRunReport(
        objective=objective,
        answer=report.answer,
        answered=report.answered,
        needs_human_review=report.needs_human_review,
        topic=report.topic,
        evidence_status=report.evidence_status,
        evidence_count=report.evidence_count,
        citations=report.citations,
        tasks=tasks,
        subagent_results=subagent_results,
        files=filesystem.list_paths("/"),
        main_context=main_context,
        audit_trail=[*audit_trail, *report.audit_trail],
        quality_gate=quality_gate,
        memory_updates=memory_updates,
    )


def evaluate_quality_gate(
    *,
    report: Mapping[str, Any],
    tasks: list[AgentTask],
    files: list[str],
) -> QualityGate:
    """Evaluate final output contracts before returning a Deep Agent answer."""
    answered = bool(report.get("answered", False))
    needs_human_review = bool(report.get("needs_human_review", False))
    citations = report.get("citations", [])
    audit_trail = report.get("audit_trail", [])
    checks = {
        "all_tasks_completed": all(task.status == "completed" for task in tasks),
        "evidence_file_written": "/workspace/evidence.json" in files,
        "report_file_written": "/reports/investigation_report.md" in files,
        "audit_trail_present": isinstance(audit_trail, list) and bool(audit_trail),
        "answered_cases_have_citations": (not answered) or bool(citations),
        "review_cases_do_not_publish_citations": (not needs_human_review) or not citations,
        "terminal_route_is_exclusive": not (answered and needs_human_review),
    }
    notes = [name for name, passed in checks.items() if not passed]
    return QualityGate(passed=all(checks.values()), checks=checks, notes=notes)


def format_markdown_report(report: Mapping[str, Any]) -> str:
    """Format the final investigation report as a compact Markdown artifact."""
    citations = report.get("citations", [])
    citation_lines = []
    if isinstance(citations, list):
        for citation in citations:
            if isinstance(citation, Mapping):
                citation_lines.append(f"- {citation.get('source')} ({citation.get('chunk_id')})")
    if not citation_lines:
        citation_lines.append("- Aucune citation publiee.")

    return "\n".join(
        [
            "# Rapport d'investigation",
            "",
            f"Question: {report.get('question', '')}",
            f"Topic: {report.get('topic', 'unknown')}",
            f"Evidence status: {report.get('evidence_status', 'unknown')}",
            f"Answered: {report.get('answered', False)}",
            f"Needs human review: {report.get('needs_human_review', False)}",
            "",
            "## Reponse",
            "",
            str(report.get("answer", "")),
            "",
            "## Citations",
            "",
            *citation_lines,
            "",
        ]
    )


def normalize_agent_path(path: str) -> str:
    """Normalize virtual filesystem paths and reject traversal."""
    if not path or not path.startswith("/"):
        raise ValueError("agent paths must be absolute")
    parts = [part for part in path.split("/") if part]
    if any(part == ".." for part in parts):
        raise ValueError("agent paths cannot contain '..'")
    normalized = "/" + "/".join(parts)
    return "/" if normalized == "/" else normalized


def _run_writer(state: Mapping[str, Any]) -> dict[str, object]:
    next_action = state.get("next_action")
    if next_action == "draft_answer":
        return draft_answer(dict(state))
    if next_action == "draft_refusal":
        return draft_refusal(dict(state))
    if next_action == "request_human_review":
        return request_human_review(dict(state))
    raise ValueError(f"Unknown next_action: {next_action}")


def _complete_task(tasks: list[AgentTask], task_id: str, *, summary: str) -> None:
    for task in tasks:
        if task.id == task_id:
            task.status = "completed"
            task.summary = summary
            return
    raise ValueError(f"Unknown task id: {task_id}")


def _append_subagent_result(
    results: list[SubagentResult],
    main_context: list[str],
    policy: DeepAgentPolicy,
    result: SubagentResult,
) -> None:
    summary = result.summary.strip()
    if len(summary) > policy.max_subagent_summary_chars:
        summary = summary[: policy.max_subagent_summary_chars - 3].rstrip() + "..."
    updated = result.model_copy(update={"summary": summary, "context_chars_returned": len(summary)})
    results.append(updated)
    main_context.append(f"{updated.subagent}: {updated.summary}")


def _write_json(
    filesystem: InMemoryAgentFileSystem,
    path: str,
    payload: Mapping[str, Any],
) -> None:
    filesystem.write_text(
        path,
        json.dumps(_jsonable(payload), indent=2, sort_keys=True),
        metadata={"content_type": "application/json"},
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _raise_for_decision(decision: PermissionDecision) -> None:
    if decision.mode == "allow":
        return
    if decision.mode == "interrupt":
        raise PermissionApprovalRequired(decision.reason)
    raise PermissionDenied(decision.reason)


def _path_matches(pattern: str, path: str) -> bool:
    normalized_pattern = normalize_agent_path(pattern.replace("**", "__DOUBLE_STAR__"))
    normalized_pattern = normalized_pattern.replace("__DOUBLE_STAR__", "**")
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3]
        return path == prefix or path.startswith(f"{prefix}/")
    regex = "^" + re.escape(normalized_pattern).replace("\\*", "[^/]*") + "$"
    return re.match(regex, path) is not None
