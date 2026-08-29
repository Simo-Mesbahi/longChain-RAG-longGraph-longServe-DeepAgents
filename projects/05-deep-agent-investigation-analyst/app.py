"""CLI for the Deep Agent investigation analyst portfolio project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_course.deep_agents import DeepAgentPolicy, run_deep_investigation_agent
from ai_course.documentary_rag import load_corpus_documents
from ai_course.investigation_graph import EvidenceChunk, StaticEvidenceStore
from ai_course.rag_basics import split_documents

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CORPUS_DIR = PROJECT_DIR.parents[0] / "02-documentary-rag-assistant" / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a deterministic Deep Agent over the insurance corpus."
    )
    parser.add_argument("objective", help="Investigation objective or user question")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--min-score", type=float, default=0.2)
    parser.add_argument("--review-score", type=float, default=0.9)
    parser.add_argument(
        "--no-human-review-on-missing",
        action="store_true",
        help="Return a refusal instead of a human-review request when evidence is missing.",
    )
    return parser.parse_args()


def build_store(corpus_dir: Path) -> StaticEvidenceStore:
    documents = load_corpus_documents(corpus_dir)
    chunks = split_documents(documents, chunk_size=650, chunk_overlap=100)
    return StaticEvidenceStore(
        [
            EvidenceChunk(
                chunk_id=str(chunk.metadata["chunk_id"]),
                source=str(chunk.metadata["source"]),
                content=chunk.page_content,
            )
            for chunk in chunks
        ]
    )


def main() -> int:
    args = parse_args()
    policy = DeepAgentPolicy(
        k=args.k,
        min_score=args.min_score,
        review_score=args.review_score,
        review_on_insufficient_evidence=not args.no_human_review_on_missing,
    )
    report = run_deep_investigation_agent(
        args.objective,
        build_store(args.corpus),
        policy=policy,
    )
    print(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
