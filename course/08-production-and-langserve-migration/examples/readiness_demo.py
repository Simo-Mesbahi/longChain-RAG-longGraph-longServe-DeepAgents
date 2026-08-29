"""Generate a production-readiness report for the portfolio platform."""

from __future__ import annotations

from ai_course.production_readiness import (
    build_default_service,
    build_demo_evidence,
    evaluate_production_readiness,
    render_readiness_report_markdown,
)


def main() -> int:
    report = evaluate_production_readiness(build_default_service(), build_demo_evidence())
    print(render_readiness_report_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
