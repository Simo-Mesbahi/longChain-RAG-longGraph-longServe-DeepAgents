"""CLI for the persistent documentary RAG portfolio project."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from ai_course.documentary_rag import (
    IndexConfigurationError,
    IndexManifest,
    answer_documentary_question,
    build_persistent_index,
    evaluate_retrieval,
    load_evaluation_dataset,
    load_index_manifest,
    open_persistent_index,
    retrieve_relevant_chunks,
)
from ai_course.langchain_basics import create_chat_model
from ai_course.rag_basics import HashingEmbeddings, build_answer_generator
from ai_course.settings import load_settings

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CORPUS_DIR = PROJECT_DIR / "data"
DEFAULT_INDEX_DIR = PROJECT_DIR / ".local" / "chroma"
DEFAULT_EVALUATION_PATH = PROJECT_DIR / "evaluation" / "questions.jsonl"
HASHING_MODEL = "hashing-sha256-256-v1"


@dataclass(frozen=True)
class EmbeddingConfiguration:
    embeddings: Embeddings
    provider: str
    model: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index, search, ask, and evaluate an insurance documentary RAG system."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Build a persistent Chroma index")
    index_parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_DIR)
    index_parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    index_parser.add_argument("--chunk-size", type=int, default=650)
    index_parser.add_argument("--chunk-overlap", type=int, default=100)
    index_parser.add_argument(
        "--offline",
        action="store_true",
        help="Use deterministic local embeddings instead of an API",
    )

    for name, help_text in (
        ("search", "Retrieve source chunks without calling a chat model"),
        ("ask", "Generate a validated answer with citations"),
    ):
        command_parser = subparsers.add_parser(name, help=help_text)
        command_parser.add_argument("question")
        _add_retrieval_arguments(command_parser)

    evaluation_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate retrieval against the labelled JSONL dataset",
    )
    evaluation_parser.add_argument("--dataset", type=Path, default=DEFAULT_EVALUATION_PATH)
    _add_retrieval_arguments(evaluation_parser)
    return parser.parse_args()


def _add_retrieval_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--min-score", type=float, default=0.2)


def build_embedding_configuration(*, offline: bool) -> EmbeddingConfiguration:
    if offline:
        return EmbeddingConfiguration(
            embeddings=HashingEmbeddings(dimensions=256),
            provider="hashing",
            model=HASHING_MODEL,
        )

    settings = load_settings()
    return EmbeddingConfiguration(
        embeddings=OpenAIEmbeddings(model=settings.embedding_model),
        provider="openai",
        model=settings.embedding_model,
    )


def configuration_from_manifest(manifest: IndexManifest) -> EmbeddingConfiguration:
    if manifest.embedding_provider == "hashing":
        if manifest.embedding_model != HASHING_MODEL:
            raise IndexConfigurationError(
                f"Unsupported local embedding model: {manifest.embedding_model}"
            )
        return build_embedding_configuration(offline=True)
    if manifest.embedding_provider == "openai":
        load_settings()  # Load .env before the provider reads OPENAI_API_KEY.
        return EmbeddingConfiguration(
            embeddings=OpenAIEmbeddings(model=manifest.embedding_model),
            provider="openai",
            model=manifest.embedding_model,
        )
    raise IndexConfigurationError(f"Unsupported embedding provider: {manifest.embedding_provider}")


def open_configured_index(index_dir: Path):
    manifest = load_index_manifest(index_dir)
    configuration = configuration_from_manifest(manifest)
    vector_store, manifest = open_persistent_index(
        index_dir,
        configuration.embeddings,
        embedding_provider=configuration.provider,
        embedding_model=configuration.model,
    )
    return vector_store, manifest


def run_index(args: argparse.Namespace) -> int:
    configuration = build_embedding_configuration(offline=args.offline)
    _, manifest = build_persistent_index(
        args.corpus,
        args.index_dir,
        configuration.embeddings,
        embedding_provider=configuration.provider,
        embedding_model=configuration.model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    print(manifest.model_dump_json(indent=2))
    return 0


def run_search(args: argparse.Namespace) -> int:
    vector_store, _ = open_configured_index(args.index_dir)
    chunks = retrieve_relevant_chunks(
        vector_store,
        args.question,
        k=args.k,
        min_score=args.min_score,
    )
    print(json.dumps([chunk.model_dump() for chunk in chunks], indent=2, ensure_ascii=False))
    return 0


def run_ask(args: argparse.Namespace) -> int:
    vector_store, _ = open_configured_index(args.index_dir)
    generator = build_answer_generator(create_chat_model(load_settings()))
    answer = answer_documentary_question(
        vector_store,
        generator,
        args.question,
        k=args.k,
        min_score=args.min_score,
    )
    print(answer.model_dump_json(indent=2))
    return 0


def run_evaluation(args: argparse.Namespace) -> int:
    vector_store, _ = open_configured_index(args.index_dir)
    examples = load_evaluation_dataset(args.dataset)
    summary = evaluate_retrieval(
        vector_store,
        examples,
        k=args.k,
        min_score=args.min_score,
    )
    print(summary.model_dump_json(indent=2))
    return 0


def main() -> int:
    args = parse_args()
    commands = {
        "index": run_index,
        "search": run_search,
        "ask": run_ask,
        "evaluate": run_evaluation,
    }
    try:
        return commands[args.command](args)
    except (IndexConfigurationError, ValueError) as error:
        print(f"Error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
