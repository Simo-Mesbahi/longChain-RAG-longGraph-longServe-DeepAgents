"""Compare retrieval configurations on the documentary RAG dataset."""

from pathlib import Path
from tempfile import TemporaryDirectory

from ai_course.documentary_rag import (
    build_persistent_index,
    evaluate_retrieval,
    load_evaluation_dataset,
)
from ai_course.rag_basics import HashingEmbeddings

ROOT_DIR = Path(__file__).resolve().parents[3]
PROJECT_DIR = ROOT_DIR / "projects" / "02-documentary-rag-assistant"
HASHING_MODEL = "hashing-sha256-256-v1"

CONFIGURATIONS = [
    {"name": "precise", "chunk_size": 420, "chunk_overlap": 50, "k": 3, "min_score": 0.2},
    {"name": "balanced", "chunk_size": 650, "chunk_overlap": 100, "k": 4, "min_score": 0.2},
    {"name": "broad", "chunk_size": 900, "chunk_overlap": 150, "k": 5, "min_score": 0.15},
]


def main() -> int:
    examples = load_evaluation_dataset(PROJECT_DIR / "evaluation" / "questions.jsonl")
    embeddings = HashingEmbeddings(dimensions=256)

    with TemporaryDirectory() as temporary_dir:
        rows = []
        for config in CONFIGURATIONS:
            store, manifest = build_persistent_index(
                PROJECT_DIR / "data",
                Path(temporary_dir) / str(config["name"]),
                embeddings,
                embedding_provider="hashing",
                embedding_model=HASHING_MODEL,
                collection_alias=f"rag-eval-{config['name']}",
                chunk_size=int(config["chunk_size"]),
                chunk_overlap=int(config["chunk_overlap"]),
            )
            summary = evaluate_retrieval(
                store,
                examples,
                k=int(config["k"]),
                min_score=float(config["min_score"]),
            )
            rows.append(
                {
                    "name": config["name"],
                    "chunk_count": manifest.chunk_count,
                    "k": summary.k,
                    "min_score": summary.min_score,
                    "hit_rate_at_k": summary.hit_rate_at_k,
                    "source_recall_at_k": summary.source_recall_at_k,
                    "mean_reciprocal_rank": summary.mean_reciprocal_rank,
                    "empty_retrieval_rate": summary.empty_retrieval_rate,
                }
            )

    for row in rows:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
