"""Display the deterministic Deep Agent plan and subagent contracts."""

from __future__ import annotations

import json

from ai_course.deep_agents import build_default_subagents, build_investigation_plan


def main() -> int:
    objective = "Quelle est la franchise degat des eaux ?"
    payload = {
        "objective": objective,
        "tasks": [task.model_dump(mode="json") for task in build_investigation_plan(objective)],
        "subagents": [subagent.model_dump(mode="json") for subagent in build_default_subagents()],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
