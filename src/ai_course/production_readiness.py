"""Production readiness and LangServe migration helpers for the course."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

EnvironmentName = Literal["local", "development", "staging", "production"]
HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
CheckCategory = Literal[
    "api",
    "security",
    "reliability",
    "observability",
    "evaluation",
    "deployment",
    "migration",
]
CheckStatus = Literal["pass", "warn", "fail"]
ReadinessStatus = Literal["ready", "needs_work", "blocked"]
DeploymentTarget = Literal["local", "docker", "generic_cloud", "langsmith_deployment"]
MigrationRisk = Literal["low", "medium", "high"]


class ServiceMetadata(BaseModel):
    """Public identity of a production service."""

    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    version: str = Field(min_length=1)
    environment: EnvironmentName = "production"
    owner: str | None = None
    public_base_url: str | None = None
    git_sha: str | None = Field(default=None, pattern=r"^[a-f0-9]{7,40}$")

    @model_validator(mode="after")
    def validate_public_url(self) -> ServiceMetadata:
        if self.public_base_url is not None and not self.public_base_url.startswith(
            ("https://", "http://")
        ):
            raise ValueError("public_base_url must start with http:// or https://")
        return self


class RuntimeLimits(BaseModel):
    """Operational limits that must be visible before deployment."""

    request_timeout_seconds: int = Field(default=120, gt=0, le=600)
    max_input_chars: int = Field(default=8_000, ge=100, le=100_000)
    max_concurrency: int = Field(default=8, ge=1, le=1_000)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=100_000)


class EndpointContract(BaseModel):
    """HTTP contract exposed by a production LLM application."""

    path: str = Field(pattern=r"^/")
    method: HttpMethod
    purpose: str = Field(min_length=10)
    auth_required: bool = True
    idempotent: bool
    streaming: bool = False
    timeout_seconds: int = Field(default=120, gt=0, le=600)
    rate_limited: bool = True
    request_schema: dict[str, Any] = Field(default_factory=dict)
    response_schema: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_contract(self) -> EndpointContract:
        if self.method in {"GET", "DELETE"} and not self.idempotent:
            raise ValueError(f"{self.method} endpoints must be idempotent")
        if self.path != "/" and self.path.endswith("/"):
            raise ValueError("endpoint paths must not end with '/'")
        return self


class ProductionEvidence(BaseModel):
    """Observable facts gathered before a production release."""

    ci_enabled: bool
    tests_passed: bool
    docs_built: bool
    observability_enabled: bool
    human_review_enabled: bool
    rate_limits_enabled: bool
    secrets_configured: bool
    rollback_documented: bool
    deployment_target: DeploymentTarget = "generic_cloud"
    evaluation_dataset_ready: bool = True
    security_review_done: bool = True


class ProductionCheck(BaseModel):
    """One readiness check with remediation guidance."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    category: CheckCategory
    title: str = Field(min_length=3)
    status: CheckStatus
    blocking: bool = False
    detail: str = Field(min_length=1)
    remediation: str | None = None


class DeploymentManifest(BaseModel):
    """Deployment contract that can be reviewed without opening infra code."""

    target: DeploymentTarget
    service: ServiceMetadata
    image_name: str
    command: list[str] = Field(min_length=1)
    ports: list[int] = Field(default_factory=lambda: [8000])
    env_vars: list[str] = Field(default_factory=list)
    secrets: list[str] = Field(default_factory=list)
    healthcheck_path: str = "/health"
    readiness_path: str = "/ready"
    scaling: dict[str, int] = Field(
        default_factory=lambda: {"min_instances": 1, "max_instances": 3}
    )

    @model_validator(mode="after")
    def validate_probe_paths(self) -> DeploymentManifest:
        if self.healthcheck_path == self.readiness_path:
            raise ValueError("healthcheck_path and readiness_path must be distinct")
        return self


class LangServeRoute(BaseModel):
    """Legacy LangServe surface to migrate."""

    path: str = Field(pattern=r"^/")
    runnable_name: str = Field(min_length=1)
    exposes_playground: bool = False
    uses_remote_runnable: bool = False
    streaming: bool = False
    stateful: bool = False


class MigrationStep(BaseModel):
    """One auditable step in a LangServe migration."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=3)
    legacy_surface: str
    target_surface: str
    rationale: str
    validation: str
    risk: MigrationRisk = "medium"
    affected_routes: list[str] = Field(default_factory=list)
    done: bool = False


class ReadinessReport(BaseModel):
    """Complete production-readiness result."""

    service: ServiceMetadata
    status: ReadinessStatus
    score: float = Field(ge=0.0, le=1.0)
    checks: list[ProductionCheck]
    endpoints: list[EndpointContract]
    manifest: DeploymentManifest
    migration_steps: list[MigrationStep] = Field(default_factory=list)

    @property
    def failed_checks(self) -> list[ProductionCheck]:
        """Return failing checks."""
        return [check for check in self.checks if check.status == "fail"]

    @property
    def blocking_failures(self) -> list[ProductionCheck]:
        """Return failing checks that block a production release."""
        return [check for check in self.failed_checks if check.blocking]


def build_default_service(
    *,
    environment: EnvironmentName = "production",
) -> ServiceMetadata:
    """Return the service identity used by the production project."""
    return ServiceMetadata(
        name="asteria-investigation-platform",
        version="0.1.0",
        environment=environment,
        owner="Simo Mesbahi",
    )


def build_default_runtime_limits() -> RuntimeLimits:
    """Return conservative defaults for an LLM service."""
    return RuntimeLimits()


def build_api_contract(
    *,
    limits: RuntimeLimits | None = None,
) -> list[EndpointContract]:
    """Build the API contract for the future investigation platform."""
    limits = limits or build_default_runtime_limits()
    return [
        EndpointContract(
            path="/health",
            method="GET",
            purpose="Liveness probe for infrastructure and load balancers.",
            auth_required=False,
            idempotent=True,
            rate_limited=False,
            timeout_seconds=5,
            response_schema={"status": "ok"},
        ),
        EndpointContract(
            path="/ready",
            method="GET",
            purpose="Readiness probe checking dependencies before receiving traffic.",
            auth_required=False,
            idempotent=True,
            rate_limited=False,
            timeout_seconds=5,
            response_schema={"status": "ready"},
        ),
        EndpointContract(
            path="/investigate",
            method="POST",
            purpose="Run the controlled RAG, LangGraph, or Deep Agent investigation workflow.",
            auth_required=True,
            idempotent=False,
            timeout_seconds=limits.request_timeout_seconds,
            request_schema={
                "question": "string",
                "mode": "rag | graph | deep_agent",
                "max_input_chars": limits.max_input_chars,
            },
            response_schema={
                "answer": "string",
                "answered": "boolean",
                "citations": "array",
                "needs_human_review": "boolean",
            },
        ),
        EndpointContract(
            path="/feedback",
            method="POST",
            purpose="Record human feedback used for evaluation and regression tests.",
            auth_required=True,
            idempotent=False,
            timeout_seconds=30,
            request_schema={"run_id": "string", "accepted": "boolean", "notes": "string"},
            response_schema={"stored": "boolean"},
        ),
        EndpointContract(
            path="/metrics",
            method="GET",
            purpose="Expose operational and quality counters for monitoring.",
            auth_required=True,
            idempotent=True,
            timeout_seconds=5,
            response_schema={"requests": "integer", "errors": "integer"},
        ),
    ]


def build_demo_evidence(
    *,
    deployment_target: DeploymentTarget = "docker",
) -> ProductionEvidence:
    """Return a passing evidence set for the portfolio demo."""
    return ProductionEvidence(
        ci_enabled=True,
        tests_passed=True,
        docs_built=True,
        observability_enabled=True,
        human_review_enabled=True,
        rate_limits_enabled=True,
        secrets_configured=True,
        rollback_documented=True,
        deployment_target=deployment_target,
        evaluation_dataset_ready=True,
        security_review_done=True,
    )


def build_deployment_manifest(
    service: ServiceMetadata,
    *,
    target: DeploymentTarget = "docker",
) -> DeploymentManifest:
    """Return an auditable deployment manifest for the platform."""
    return DeploymentManifest(
        target=target,
        service=service,
        image_name=f"{service.name}:{service.version}",
        command=[
            "uvicorn",
            "api:app",
            "--app-dir",
            "projects/06-production-readiness-and-migration",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        env_vars=[
            "ENVIRONMENT",
            "MODEL_PROVIDER",
            "MODEL_NAME",
            "EMBEDDING_MODEL",
            "LANGSMITH_TRACING",
            "LANGSMITH_PROJECT",
        ],
        secrets=["OPENAI_API_KEY", "LANGSMITH_API_KEY", "ASTERIA_API_TOKEN"],
        healthcheck_path="/health",
        readiness_path="/ready",
        scaling={"min_instances": 1, "max_instances": 3},
    )


def evaluate_production_readiness(
    service: ServiceMetadata,
    evidence: ProductionEvidence,
    *,
    endpoints: Sequence[EndpointContract] | None = None,
    migration_steps: Sequence[MigrationStep] | None = None,
) -> ReadinessReport:
    """Evaluate whether a service is ready to be exposed beyond local development."""
    endpoints = list(endpoints or build_api_contract())
    migration_steps = list(
        migration_steps or build_langserve_migration_plan(default_legacy_routes())
    )
    checks = [
        *_api_contract_checks(endpoints),
        *_evidence_checks(service, evidence),
    ]
    score = _readiness_score(checks)
    status = _readiness_status(checks, score)
    return ReadinessReport(
        service=service,
        status=status,
        score=score,
        checks=checks,
        endpoints=endpoints,
        manifest=build_deployment_manifest(service, target=evidence.deployment_target),
        migration_steps=migration_steps,
    )


def default_legacy_routes() -> list[LangServeRoute]:
    """Return a representative LangServe inventory for the course migration."""
    return [
        LangServeRoute(
            path="/rag",
            runnable_name="documentary_rag_chain",
            exposes_playground=True,
            streaming=False,
            stateful=False,
        ),
        LangServeRoute(
            path="/investigation",
            runnable_name="langgraph_investigation_workflow",
            uses_remote_runnable=True,
            streaming=True,
            stateful=True,
        ),
    ]


def build_langserve_migration_plan(routes: Sequence[LangServeRoute]) -> list[MigrationStep]:
    """Build a controlled migration plan away from LangServe."""
    if not routes:
        raise ValueError("at least one LangServe route is required")

    affected_routes = [route.path for route in routes]
    highest_risk = _migration_risk(routes)
    stateful_routes = [route.path for route in routes if route.stateful]
    streaming_routes = [route.path for route in routes if route.streaming]
    target_for_stateful = "LangGraph app exported through langgraph.json and LangSmith Deployment"
    target_for_simple = "Typed FastAPI endpoint or LangGraph-compatible app"
    stateful_validation = "Stateful routes are exported in langgraph.json; simple routes use APIs."
    remote_runnable_rationale = (
        "Clients should depend on explicit contracts, not deprecated surfaces."
    )
    dual_run_rationale = (
        "Dual-run evaluation detects answer, citation, latency, and error regressions."
    )
    dual_run_validation = (
        "Dataset pass rate, citation precision, refusal behavior, and p95 latency pass."
    )
    rollback_rationale = "A reversible release protects users while new runtime receives traffic."

    return [
        MigrationStep(
            id="inventory-routes",
            title="Inventory existing LangServe routes",
            legacy_surface="LangServe add_routes and RemoteRunnable clients",
            target_surface="Migration inventory",
            rationale="A migration starts by freezing the current API surface and runnable names.",
            validation="Every legacy route has an owner, schema, dataset, and client list.",
            risk="low",
            affected_routes=affected_routes,
            done=True,
        ),
        MigrationStep(
            id="stabilize-contracts",
            title="Stabilize request and response contracts",
            legacy_surface="Runnable input and output inferred at runtime",
            target_surface="Explicit Pydantic schemas and HTTP contracts",
            rationale="Production clients need stable schemas, examples, and validation errors.",
            validation="Contract tests compare old and new payloads on representative examples.",
            risk="medium",
            affected_routes=affected_routes,
        ),
        MigrationStep(
            id="split-simple-and-stateful",
            title="Separate simple chains from stateful agents",
            legacy_surface="All runnables served through LangServe",
            target_surface=f"{target_for_simple}; {target_for_stateful}",
            rationale="LCEL chains and long-running agents do not have the same runtime needs.",
            validation=stateful_validation,
            risk=highest_risk,
            affected_routes=stateful_routes or affected_routes,
        ),
        MigrationStep(
            id="replace-remote-runnable",
            title="Replace RemoteRunnable clients",
            legacy_surface="RemoteRunnable client calls",
            target_surface="Typed HTTP client, LangGraph SDK, or platform client",
            rationale=remote_runnable_rationale,
            validation="Client integration tests pass against the new endpoint in staging.",
            risk="medium",
            affected_routes=[route.path for route in routes if route.uses_remote_runnable]
            or affected_routes,
        ),
        MigrationStep(
            id="dual-run-evaluation",
            title="Run old and new services in parallel",
            legacy_surface="LangServe production route",
            target_surface="New production route in staging or canary",
            rationale=dual_run_rationale,
            validation=dual_run_validation,
            risk=highest_risk,
            affected_routes=streaming_routes or affected_routes,
        ),
        MigrationStep(
            id="cutover-and-rollback",
            title="Cut over with rollback",
            legacy_surface="LangServe public traffic",
            target_surface="New production deployment",
            rationale=rollback_rationale,
            validation="Health, readiness, traces, alerts, and rollback command are verified.",
            risk=highest_risk,
            affected_routes=affected_routes,
        ),
    ]


def build_health_payload(
    service: ServiceMetadata,
    checks: Sequence[ProductionCheck],
) -> dict[str, Any]:
    """Return a health payload compatible with liveness and readiness probes."""
    failures = [check for check in checks if check.status == "fail" and check.blocking]
    warnings = [check for check in checks if check.status == "warn"]
    if failures:
        status = "down"
    elif warnings:
        status = "degraded"
    else:
        status = "ok"

    return {
        "service": service.name,
        "version": service.version,
        "environment": service.environment,
        "status": status,
        "blocking_failures": [check.id for check in failures],
        "warnings": [check.id for check in warnings],
    }


def render_readiness_report_markdown(report: ReadinessReport) -> str:
    """Render a readiness report as a reviewable Markdown artifact."""
    check_lines = [
        "| Check | Category | Status | Blocking | Remediation |",
        "|---|---|---:|:---:|---|",
    ]
    for check in report.checks:
        check_lines.append(
            "| {title} | {category} | {status} | {blocking} | {remediation} |".format(
                title=check.title,
                category=check.category,
                status=check.status,
                blocking="yes" if check.blocking else "no",
                remediation=check.remediation or "-",
            )
        )

    endpoint_lines = [
        "| Method | Path | Auth | Purpose |",
        "|---|---|:---:|---|",
    ]
    for endpoint in report.endpoints:
        endpoint_lines.append(
            f"| {endpoint.method} | `{endpoint.path}` | "
            f"{'yes' if endpoint.auth_required else 'no'} | {endpoint.purpose} |"
        )

    migration_lines = [
        "| Step | Risk | Validation |",
        "|---|:---:|---|",
    ]
    for step in report.migration_steps:
        migration_lines.append(f"| {step.title} | {step.risk} | {step.validation} |")

    return "\n".join(
        [
            f"# Production readiness - {report.service.name}",
            "",
            f"Status: **{report.status}**",
            f"Score: **{report.score:.0%}**",
            "",
            "## Checks",
            "",
            *check_lines,
            "",
            "## API contract",
            "",
            *endpoint_lines,
            "",
            "## LangServe migration",
            "",
            *migration_lines,
            "",
        ]
    )


def readiness_report_to_json(report: ReadinessReport) -> str:
    """Serialize a readiness report with stable indentation."""
    return json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False)


def _api_contract_checks(endpoints: Sequence[EndpointContract]) -> list[ProductionCheck]:
    paths = {endpoint.path for endpoint in endpoints}
    mutating_endpoints = [
        endpoint for endpoint in endpoints if endpoint.method in {"POST", "PUT", "PATCH"}
    ]
    unprotected_mutations = [
        endpoint.path for endpoint in mutating_endpoints if not endpoint.auth_required
    ]
    unbounded_endpoints = [
        endpoint.path
        for endpoint in endpoints
        if endpoint.method in {"POST", "PUT", "PATCH"} and not endpoint.rate_limited
    ]
    missing_core_paths = sorted({"/health", "/ready", "/investigate"} - paths)

    return [
        _check(
            "core_api_paths",
            "api",
            "Core API paths",
            not missing_core_paths,
            detail="Core paths are present."
            if not missing_core_paths
            else f"Missing paths: {', '.join(missing_core_paths)}",
            remediation="Expose /health, /ready, and /investigate before deployment.",
            blocking=True,
        ),
        _check(
            "auth_for_mutations",
            "security",
            "Authentication on mutating endpoints",
            not unprotected_mutations,
            detail="All mutating endpoints require authentication."
            if not unprotected_mutations
            else f"Unprotected mutating endpoints: {', '.join(unprotected_mutations)}",
            remediation="Require an API token, OAuth, or gateway auth on mutating endpoints.",
            blocking=True,
        ),
        _check(
            "rate_limits_for_mutations",
            "reliability",
            "Rate limits on expensive endpoints",
            not unbounded_endpoints,
            detail="Expensive endpoints are rate limited."
            if not unbounded_endpoints
            else f"Missing rate limits: {', '.join(unbounded_endpoints)}",
            remediation="Add request throttling before exposing expensive LLM endpoints.",
            blocking=False,
        ),
    ]


def _evidence_checks(
    service: ServiceMetadata,
    evidence: ProductionEvidence,
) -> list[ProductionCheck]:
    production_like = service.environment in {"staging", "production"}
    local_target_in_prod = production_like and evidence.deployment_target == "local"
    return [
        _check(
            "ci_enabled",
            "deployment",
            "Continuous integration",
            evidence.ci_enabled,
            detail="CI is configured." if evidence.ci_enabled else "CI is missing.",
            remediation="Run lint, formatting, tests, and docs build on every push.",
            blocking=True,
        ),
        _check(
            "tests_passed",
            "evaluation",
            "Automated tests",
            evidence.tests_passed,
            detail="Automated tests passed."
            if evidence.tests_passed
            else "Tests are failing or not executed.",
            remediation="Fix failing tests before release.",
            blocking=True,
        ),
        _check(
            "docs_built",
            "deployment",
            "Documentation build",
            evidence.docs_built,
            detail="Documentation builds strictly."
            if evidence.docs_built
            else "Documentation build is not validated.",
            remediation="Run mkdocs build --strict in CI.",
            blocking=False,
        ),
        _check(
            "observability_enabled",
            "observability",
            "Observability",
            evidence.observability_enabled,
            detail="Tracing and quality metrics are available."
            if evidence.observability_enabled
            else "No tracing or quality metrics are configured.",
            remediation="Enable LangSmith tracing or equivalent structured telemetry.",
            blocking=False,
        ),
        _check(
            "human_review_enabled",
            "security",
            "Human review route",
            evidence.human_review_enabled,
            detail="Sensitive decisions can route to human review."
            if evidence.human_review_enabled
            else "No human-review route is available.",
            remediation="Keep human validation for high-impact insurance decisions.",
            blocking=True,
        ),
        _check(
            "rate_limits_enabled",
            "reliability",
            "Global rate limiting",
            evidence.rate_limits_enabled,
            detail="Global rate limiting is enabled."
            if evidence.rate_limits_enabled
            else "Global rate limiting is missing.",
            remediation="Add an API gateway, middleware, or provider-level rate limit.",
            blocking=False,
        ),
        _check(
            "secrets_configured",
            "security",
            "Secrets configured outside Git",
            evidence.secrets_configured,
            detail="Required secrets are configured outside source control."
            if evidence.secrets_configured
            else "Required secrets are missing or still placeholders.",
            remediation="Configure provider keys and tokens in the deployment secret store.",
            blocking=production_like,
        ),
        _check(
            "rollback_documented",
            "deployment",
            "Rollback procedure",
            evidence.rollback_documented,
            detail="Rollback procedure is documented."
            if evidence.rollback_documented
            else "Rollback procedure is missing.",
            remediation="Document the last known good version and rollback command.",
            blocking=production_like,
        ),
        _check(
            "evaluation_dataset_ready",
            "evaluation",
            "Evaluation dataset",
            evidence.evaluation_dataset_ready,
            detail="Reference dataset is ready."
            if evidence.evaluation_dataset_ready
            else "Reference evaluation dataset is missing.",
            remediation="Create questions, expected routes, and citation expectations.",
            blocking=False,
        ),
        _check(
            "security_review_done",
            "security",
            "Security review",
            evidence.security_review_done,
            detail="Security review is complete."
            if evidence.security_review_done
            else "Security review is not complete.",
            remediation="Review auth, secrets, file permissions, logs, and data retention.",
            blocking=production_like,
        ),
        _check(
            "deployment_target",
            "deployment",
            "Production deployment target",
            not local_target_in_prod,
            detail=f"Deployment target is {evidence.deployment_target}."
            if not local_target_in_prod
            else "Production cannot run as a local-only target.",
            remediation="Use Docker, a cloud runtime, or LangSmith Deployment for production.",
            blocking=True,
        ),
    ]


def _check(
    check_id: str,
    category: CheckCategory,
    title: str,
    condition: bool,
    *,
    detail: str,
    remediation: str,
    blocking: bool,
) -> ProductionCheck:
    return ProductionCheck(
        id=check_id,
        category=category,
        title=title,
        status="pass" if condition else "fail",
        blocking=blocking,
        detail=detail,
        remediation=None if condition else remediation,
    )


def _readiness_score(checks: Sequence[ProductionCheck]) -> float:
    if not checks:
        return 0.0
    values = {"pass": 1.0, "warn": 0.5, "fail": 0.0}
    return round(sum(values[check.status] for check in checks) / len(checks), 4)


def _readiness_status(
    checks: Sequence[ProductionCheck],
    score: float,
) -> ReadinessStatus:
    blocking_failures = [check for check in checks if check.status == "fail" and check.blocking]
    failures = [check for check in checks if check.status == "fail"]
    if blocking_failures:
        return "blocked"
    if failures or score < 0.9:
        return "needs_work"
    return "ready"


def _migration_risk(routes: Sequence[LangServeRoute]) -> MigrationRisk:
    if any(route.stateful and route.streaming for route in routes):
        return "high"
    if any(route.stateful or route.uses_remote_runnable for route in routes):
        return "medium"
    return "low"


def assert_no_secret_like_values(payload: Mapping[str, Any]) -> None:
    """Fail fast when a report accidentally contains obvious secret-looking values."""
    serialized = json.dumps(payload, ensure_ascii=False)
    patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"lsv2_[A-Za-z0-9_=-]{16,}",
        r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_-]{16,}",
    ]
    for pattern in patterns:
        if re.search(pattern, serialized):
            raise ValueError("payload contains a secret-like value")
