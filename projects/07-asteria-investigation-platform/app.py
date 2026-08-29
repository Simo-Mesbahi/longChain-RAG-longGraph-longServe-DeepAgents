"""Command-line entry point for the Asteria capstone platform."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ai_course.capstone_platform import (  # noqa: E402
    CapstoneRequest,
    build_capstone_readiness,
    build_capstone_store,
    run_acceptance_suite,
    run_capstone_request,
)

PROJECT_DIR = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "projects" / "02-documentary-rag-assistant" / "data"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Asteria Investigation OS - capstone LangChain et Deep Agents"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask = subparsers.add_parser("ask", help="Executer une investigation documentaire")
    ask.add_argument("question")
    ask.add_argument(
        "--mode",
        choices=["auto", "rag", "graph", "deep_agent"],
        default="auto",
    )
    ask.add_argument(
        "--no-review",
        action="store_true",
        help="Refuser au lieu de demander une revue si les preuves manquent",
    )

    subparsers.add_parser("evaluate", help="Executer les scenarios d'acceptation metier")
    subparsers.add_parser("readiness", help="Afficher le gate de production")

    serve = subparsers.add_parser("serve", help="Demarrer l'API et le cockpit web")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "serve":
        try:
            import uvicorn
        except ImportError as error:
            raise RuntimeError('Installez les dependances avec pip install -e ".[api]"') from error
        uvicorn.run(
            "api:app",
            app_dir=str(PROJECT_DIR),
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
        return 0

    store = build_capstone_store(CORPUS_DIR)
    if args.command == "ask":
        result = run_capstone_request(
            CapstoneRequest(
                question=args.question,
                mode=args.mode,
                require_human_review_on_insufficient=not args.no_review,
            ),
            store,
        )
        print(result.model_dump_json(indent=2))
        return 0 if result.quality_gate_passed else 2
    if args.command == "evaluate":
        summary = run_acceptance_suite(store)
        print(summary.model_dump_json(indent=2))
        return 0 if summary.release_gate_passed else 2

    readiness = build_capstone_readiness()
    print(readiness.model_dump_json(indent=2))
    return 0 if readiness.status == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
