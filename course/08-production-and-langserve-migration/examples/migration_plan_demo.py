"""Display the LangServe migration plan used in the course."""

from __future__ import annotations

import json

from ai_course.production_readiness import (
    build_langserve_migration_plan,
    default_legacy_routes,
)


def main() -> int:
    steps = build_langserve_migration_plan(default_legacy_routes())
    print(
        json.dumps([step.model_dump(mode="json") for step in steps], indent=2, ensure_ascii=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
