"""Run deterministic retrieval without an API key or generation model."""

import argparse
from pathlib import Path

from langchain_core.documents import Document

from ai_course.rag_basics import (
    HashingEmbeddings,
    build_vector_store,
    retrieve_chunks,
    split_documents,
)

DATA_PATH = Path(__file__).parents[1] / "data" / "insurance_guide.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search the local insurance guide.")
    parser.add_argument("query", help="Question or search query")
    parser.add_argument("--top-k", type=int, default=3, help="Number of chunks")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    document = Document(
        page_content=DATA_PATH.read_text(encoding="utf-8"),
        metadata={"source": DATA_PATH.name},
    )
    chunks = split_documents([document], chunk_size=450, chunk_overlap=60)
    vector_store = build_vector_store(chunks, HashingEmbeddings())

    for chunk in retrieve_chunks(vector_store, args.query, k=args.top_k, min_score=0.05):
        print(f"{chunk.chunk_id} | score={chunk.score:.3f}")
        print(chunk.content)
        print()


if __name__ == "__main__":
    main()
