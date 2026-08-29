"""Show first-match filesystem permissions for a Deep Agent."""

from __future__ import annotations

import json

from ai_course.deep_agents import (
    FilePermission,
    InMemoryAgentFileSystem,
    PermissionApprovalRequired,
    PermissionDenied,
)


def main() -> int:
    filesystem = InMemoryAgentFileSystem(
        permissions=[
            FilePermission(operations=["write"], paths=["/workspace/public/**"], mode="allow"),
            FilePermission(operations=["write"], paths=["/workspace/**"], mode="deny"),
            FilePermission(operations=["write"], paths=["/reports/**"], mode="interrupt"),
        ]
    )

    filesystem.write_text("/workspace/public/notes.md", "visible working note")
    events = [
        {"path": "/workspace/public/notes.md", "result": "written"},
        {
            "path": "/workspace/private/notes.md",
            "decision": filesystem.check_permission(
                "write", "/workspace/private/notes.md"
            ).model_dump(mode="json"),
        },
        {
            "path": "/reports/final.md",
            "decision": filesystem.check_permission("write", "/reports/final.md").model_dump(
                mode="json"
            ),
        },
    ]

    try:
        filesystem.write_text("/workspace/private/notes.md", "blocked")
    except PermissionDenied as error:
        events.append({"path": "/workspace/private/notes.md", "error": str(error)})

    try:
        filesystem.write_text("/reports/final.md", "requires approval")
    except PermissionApprovalRequired as error:
        events.append({"path": "/reports/final.md", "error": str(error)})

    print(json.dumps(events, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
