"""Show deterministic routing decisions for representative objectives."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ai_course.capstone_platform import select_execution_mode  # noqa: E402

questions = [
    "Quelle est la franchise pour un degat des eaux ?",
    "Quelles pieces faut-il ajouter au dossier ?",
    "Analyse le risque de fraude associe au score.",
]

for question in questions:
    print(f"{select_execution_mode(question):>10} | {question}")
