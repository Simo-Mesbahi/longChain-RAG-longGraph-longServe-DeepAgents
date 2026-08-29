"""Execute the complete business acceptance suite."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ai_course.capstone_platform import build_capstone_store, run_acceptance_suite  # noqa: E402

store = build_capstone_store(ROOT / "projects/02-documentary-rag-assistant/data")
summary = run_acceptance_suite(store)

print(f"Release gate: {'PASS' if summary.release_gate_passed else 'BLOCKED'}")
print(f"Pass rate: {summary.pass_rate:.0%} ({summary.passed}/{summary.scenarios})")
for result in summary.results:
    status = "PASS" if result.passed else "FAIL"
    print(f"- {status} {result.scenario.id}: mode={result.response.mode_used}")
