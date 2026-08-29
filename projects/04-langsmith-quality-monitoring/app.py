"""CLI for LangSmith-style quality monitoring of the investigation workflow."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ai_course.documentary_rag import load_corpus_documents
from ai_course.investigation_graph import (
    EvidenceChunk,
    InvestigationPolicy,
    StaticEvidenceStore,
    build_investigation_graph,
    state_to_report,
)
from ai_course.langsmith_evaluation import (
    evaluate_local_experiment,
    load_langsmith_dataset,
    run_local_experiment,
    sync_examples_to_langsmith,
    write_langsmith_dataset_export,
)
from ai_course.rag_basics import split_documents

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_PATH = PROJECT_DIR / "evaluation" / "langsmith_cases.jsonl"
DEFAULT_CORPUS_DIR = PROJECT_DIR.parents[0] / "02-documentary-rag-assistant" / "data"
DEFAULT_EXPORT_PATH = PROJECT_DIR / ".local" / "langsmith_dataset_export.jsonl"
DEFAULT_DATASET_NAME = "Asteria Investigation Workflow Quality"
DEFAULT_EXPERIMENT_NAME = "langgraph-investigation-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate and export LangSmith-style datasets for the LangGraph workflow."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = subparsers.add_parser(
        "evaluate-local",
        help="Run deterministic local evaluators over the graph workflow",
    )
    evaluate_parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    evaluate_parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_DIR)
    evaluate_parser.add_argument("--experiment-name", default=DEFAULT_EXPERIMENT_NAME)
    evaluate_parser.add_argument("--k", type=int, default=1)
    evaluate_parser.add_argument("--min-score", type=float, default=0.2)
    evaluate_parser.add_argument("--review-score", type=float, default=0.9)
    evaluate_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path for the full local experiment and summary JSON",
    )

    export_parser = subparsers.add_parser(
        "export-dataset",
        help="Write a JSONL file ready for LangSmith bulk example creation",
    )
    export_parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    export_parser.add_argument("--output", type=Path, default=DEFAULT_EXPORT_PATH)

    sync_parser = subparsers.add_parser(
        "sync-dataset",
        help="Create a LangSmith dataset with the official SDK",
    )
    sync_parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    sync_parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    sync_parser.add_argument(
        "--description",
        default="Evaluation cases for the Asteria LangGraph investigation workflow.",
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


def build_target(
    corpus_dir: Path,
    policy: InvestigationPolicy,
) -> Callable[[dict[str, str]], Mapping[str, Any]]:
    graph = build_investigation_graph(build_store(corpus_dir), policy=policy)

    def target(inputs: dict[str, str]) -> dict[str, Any]:
        state = graph.invoke({"question": inputs["question"]})
        report = state_to_report(state)
        payload = report.model_dump(mode="json")
        payload["evidence_sources"] = _evidence_sources(state)
        return payload

    return target


def run_evaluate_local(args: argparse.Namespace) -> int:
    examples = load_langsmith_dataset(args.dataset)
    policy = InvestigationPolicy(
        k=args.k,
        min_score=args.min_score,
        review_score=args.review_score,
    )
    experiment = run_local_experiment(
        examples,
        build_target(args.corpus, policy),
        experiment_name=args.experiment_name,
        metadata={
            "module": "06-langsmith",
            "target": "projects/03-langgraph-investigation-workflow",
            "k": args.k,
            "min_score": args.min_score,
            "review_score": args.review_score,
        },
    )
    summary = evaluate_local_experiment(examples, experiment)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {
                    "experiment": experiment.model_dump(mode="json"),
                    "summary": summary.model_dump(mode="json"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    print(summary.model_dump_json(indent=2))
    return 0


def run_export_dataset(args: argparse.Namespace) -> int:
    examples = load_langsmith_dataset(args.dataset)
    path = write_langsmith_dataset_export(examples, args.output)
    print(json.dumps({"path": str(path), "examples": len(examples)}, indent=2))
    return 0


def run_sync_dataset(args: argparse.Namespace) -> int:
    examples = load_langsmith_dataset(args.dataset)
    result = sync_examples_to_langsmith(
        examples,
        dataset_name=args.dataset_name,
        description=args.description,
    )
    print(json.dumps(result, indent=2))
    return 0


def _evidence_sources(state: Mapping[str, Any]) -> list[str]:
    evidence = state.get("evidence", [])
    if not isinstance(evidence, list):
        return []

    sources: list[str] = []
    for item in evidence:
        if isinstance(item, Mapping):
            source = item.get("source")
            if isinstance(source, str) and source:
                sources.append(source)
    return list(dict.fromkeys(sources))


def main() -> int:
    args = parse_args()
    commands = {
        "evaluate-local": run_evaluate_local,
        "export-dataset": run_export_dataset,
        "sync-dataset": run_sync_dataset,
    }
    try:
        return commands[args.command](args)
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
