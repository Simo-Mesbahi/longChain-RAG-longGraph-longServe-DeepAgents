"""Run one capstone request without starting the web API."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ai_course.capstone_platform import (  # noqa: E402
    CapstoneRequest,
    build_capstone_store,
    run_capstone_request,
)

store = build_capstone_store(ROOT / "projects/02-documentary-rag-assistant/data")
response = run_capstone_request(
    CapstoneRequest(question="Quelle est la franchise pour un degat des eaux ?"),
    store,
)

print(
    json.dumps(
        {
            "mode": response.mode_used,
            "status": response.status,
            "answer": response.answer,
            "citations": [citation.model_dump() for citation in response.citations],
            "checks": [check.model_dump() for check in response.business_checks],
        },
        indent=2,
        ensure_ascii=False,
    )
)
