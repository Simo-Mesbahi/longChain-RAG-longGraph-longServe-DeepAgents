"""Print a reviewable deployment manifest."""

from __future__ import annotations

from ai_course.production_readiness import build_default_service, build_deployment_manifest


def main() -> int:
    manifest = build_deployment_manifest(build_default_service(), target="docker")
    print(manifest.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
