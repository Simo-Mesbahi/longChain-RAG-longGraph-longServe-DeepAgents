"""CLI for production readiness and LangServe migration checks."""

from __future__ import annotations

import argparse
import json

from ai_course.production_readiness import (
    build_default_service,
    build_demo_evidence,
    build_deployment_manifest,
    build_health_payload,
    build_langserve_migration_plan,
    default_legacy_routes,
    evaluate_production_readiness,
    readiness_report_to_json,
    render_readiness_report_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate production readiness and LangServe migration plans."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    readiness = subparsers.add_parser("readiness", help="Print the readiness report")
    readiness.add_argument("--environment", default="production")
    readiness.add_argument("--format", choices=["json", "markdown"], default="json")
    readiness.add_argument("--missing-secret", action="store_true")
    readiness.add_argument("--disable-observability", action="store_true")
    readiness.add_argument("--local-target", action="store_true")

    subparsers.add_parser("migration-plan", help="Print the LangServe migration plan")
    subparsers.add_parser("manifest", help="Print the deployment manifest")
    subparsers.add_parser("health", help="Print a production-style health payload")
    return parser.parse_args()


def run_readiness(args: argparse.Namespace) -> int:
    service = build_default_service(environment=args.environment)
    evidence = build_demo_evidence(
        deployment_target="local" if args.local_target else "docker",
    ).model_copy(
        update={
            "secrets_configured": not args.missing_secret,
            "observability_enabled": not args.disable_observability,
        }
    )
    report = evaluate_production_readiness(service, evidence)
    if args.format == "markdown":
        print(render_readiness_report_markdown(report))
    else:
        print(readiness_report_to_json(report))
    return 0 if report.status != "blocked" else 2


def run_migration_plan() -> int:
    steps = build_langserve_migration_plan(default_legacy_routes())
    print(
        json.dumps([step.model_dump(mode="json") for step in steps], indent=2, ensure_ascii=False)
    )
    return 0


def run_manifest() -> int:
    manifest = build_deployment_manifest(build_default_service())
    print(manifest.model_dump_json(indent=2))
    return 0


def run_health() -> int:
    service = build_default_service()
    report = evaluate_production_readiness(service, build_demo_evidence())
    print(json.dumps(build_health_payload(service, report.checks), indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    args = parse_args()
    try:
        if args.command == "readiness":
            return run_readiness(args)
        if args.command == "migration-plan":
            return run_migration_plan()
        if args.command == "manifest":
            return run_manifest()
        if args.command == "health":
            return run_health()
    except ValueError as error:
        print(f"Error: {error}")
        return 2
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
