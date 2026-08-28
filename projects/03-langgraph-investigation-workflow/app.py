"""CLI for the LangGraph documentary investigation workflow."""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_course.documentary_rag import load_corpus_documents
from ai_course.investigation_graph import (
    EvidenceChunk,
    InvestigationPolicy,
    StaticEvidenceStore,
    build_investigation_graph,
    state_to_report,
)
from ai_course.rag_basics import split_documents

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CORPUS_DIR = PROJECT_DIR.parents[0] / "02-documentary-rag-assistant" / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a controlled LangGraph workflow over the insurance corpus."
    )
    parser.add_argument("question")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--min-score", type=float, default=0.2)
    parser.add_argument("--review-score", type=float, default=0.55)
    parser.add_argument("--no-human-review-on-missing", action="store_true")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--review-note", default="")
    parser.add_argument("--replacement-answer", default=None)
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
    policy = InvestigationPolicy(
        k=args.k,
        min_score=args.min_score,
        review_score=args.review_score,
        review_on_insufficient_evidence=not args.no_human_review_on_missing,
    )
    graph = build_investigation_graph(build_store(args.corpus), policy=policy)

    input_state: dict[str, object] = {"question": args.question}
    if args.approve or args.review_note or args.replacement_answer:
        input_state["human_decision"] = {
            "approved": args.approve,
            "notes": args.review_note,
            "replacement_answer": args.replacement_answer,
        }

    state = graph.invoke(input_state)
    print(state_to_report(state).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
