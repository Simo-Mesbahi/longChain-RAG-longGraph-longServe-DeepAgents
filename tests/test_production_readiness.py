import pytest

from ai_course.production_readiness import (
    EndpointContract,
    LangServeRoute,
    ServiceMetadata,
    assert_no_secret_like_values,
    build_api_contract,
    build_default_service,
    build_demo_evidence,
    build_deployment_manifest,
    build_health_payload,
    build_langserve_migration_plan,
    evaluate_production_readiness,
    render_readiness_report_markdown,
)


def test_default_contract_contains_health_ready_and_investigate() -> None:
    endpoints = build_api_contract()
    by_path = {endpoint.path: endpoint for endpoint in endpoints}

    assert {"/health", "/ready", "/investigate"}.issubset(by_path)
    assert by_path["/health"].auth_required is False
    assert by_path["/ready"].idempotent is True
    assert by_path["/investigate"].auth_required is True


def test_readiness_report_ready_when_all_evidence_present() -> None:
    report = evaluate_production_readiness(
        build_default_service(),
        build_demo_evidence(deployment_target="docker"),
    )

    assert report.status == "ready"
    assert report.score == 1.0
    assert report.blocking_failures == []
    assert report.manifest.healthcheck_path == "/health"


def test_readiness_report_blocks_on_missing_secrets_in_production() -> None:
    evidence = build_demo_evidence().model_copy(update={"secrets_configured": False})
    report = evaluate_production_readiness(build_default_service(), evidence)

    assert report.status == "blocked"
    assert "secrets_configured" in [check.id for check in report.blocking_failures]


def test_local_environment_can_warn_without_secret_blocking() -> None:
    service = build_default_service(environment="local")
    evidence = build_demo_evidence(deployment_target="local").model_copy(
        update={"secrets_configured": False}
    )
    report = evaluate_production_readiness(service, evidence)

    assert report.status == "needs_work"
    assert not any(check.id == "secrets_configured" for check in report.blocking_failures)


def test_auth_check_flags_unprotected_mutating_endpoint() -> None:
    endpoints = [
        EndpointContract(
            path="/health",
            method="GET",
            purpose="Liveness probe for infrastructure.",
            auth_required=False,
            idempotent=True,
        ),
        EndpointContract(
            path="/ready",
            method="GET",
            purpose="Readiness probe for infrastructure.",
            auth_required=False,
            idempotent=True,
        ),
        EndpointContract(
            path="/investigate",
            method="POST",
            purpose="Run a full investigation workflow.",
            auth_required=False,
            idempotent=False,
        ),
    ]

    report = evaluate_production_readiness(
        build_default_service(),
        build_demo_evidence(),
        endpoints=endpoints,
    )

    assert report.status == "blocked"
    assert "auth_for_mutations" in [check.id for check in report.blocking_failures]


def test_langserve_migration_plan_prioritizes_stateful_routes() -> None:
    steps = build_langserve_migration_plan(
        [
            LangServeRoute(path="/rag", runnable_name="rag_chain"),
            LangServeRoute(
                path="/agent",
                runnable_name="agent_graph",
                uses_remote_runnable=True,
                streaming=True,
                stateful=True,
            ),
        ]
    )

    split_step = next(step for step in steps if step.id == "split-simple-and-stateful")
    assert split_step.risk == "high"
    assert "/agent" in split_step.affected_routes
    assert "langgraph.json" in split_step.target_surface


def test_migration_plan_requires_routes() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_langserve_migration_plan([])


def test_deployment_manifest_has_probes_and_required_secrets() -> None:
    manifest = build_deployment_manifest(ServiceMetadata(name="demo-api", version="1.2.3"))

    assert manifest.healthcheck_path == "/health"
    assert manifest.readiness_path == "/ready"
    assert "OPENAI_API_KEY" in manifest.secrets
    assert manifest.scaling["min_instances"] == 1


def test_markdown_report_contains_checks_endpoints_and_migration() -> None:
    report = evaluate_production_readiness(build_default_service(), build_demo_evidence())
    markdown = render_readiness_report_markdown(report)

    assert "Production readiness" in markdown
    assert "Authentication on mutating endpoints" in markdown
    assert "`/investigate`" in markdown
    assert "LangServe migration" in markdown


def test_health_payload_degraded_on_warning_and_down_on_blocking_failure() -> None:
    ready_report = evaluate_production_readiness(build_default_service(), build_demo_evidence())
    assert build_health_payload(ready_report.service, ready_report.checks)["status"] == "ok"

    blocked_report = evaluate_production_readiness(
        build_default_service(),
        build_demo_evidence().model_copy(update={"tests_passed": False}),
    )
    payload = build_health_payload(blocked_report.service, blocked_report.checks)
    assert payload["status"] == "down"
    assert payload["blocking_failures"] == ["tests_passed"]


def test_secret_like_values_are_rejected_before_publication() -> None:
    assert_no_secret_like_values({"public": "ok"})
    with pytest.raises(ValueError, match="secret-like"):
        assert_no_secret_like_values({"OPENAI_API_KEY": "sk-thisLooksLikeASecret123456"})
