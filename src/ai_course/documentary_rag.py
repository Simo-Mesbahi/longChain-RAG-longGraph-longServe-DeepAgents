"""Production-minded building blocks for a persistent documentary RAG system."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, Field, model_validator

from ai_course.rag_basics import (
    AnswerGenerator,
    Citation,
    GeneratedAnswer,
    RagAnswer,
    RetrievedChunk,
    format_context,
    split_documents,
)

if TYPE_CHECKING:
    from langchain_chroma import Chroma

SUPPORTED_SUFFIXES = frozenset({".md", ".txt"})
MANIFEST_FILENAME = "manifest.json"
MAX_DOCUMENT_BYTES = 1_000_000


class CorpusError(ValueError):
    """Raised when a corpus cannot be loaded safely."""


class IndexConfigurationError(ValueError):
    """Raised when query-time settings do not match the persisted index."""


class RelevanceVectorStore(Protocol):
    """Vector-store capability required by retrieval and evaluation."""

    def similarity_search_with_relevance_scores(
        self,
        query: str,
        *,
        k: int,
    ) -> list[tuple[Document, float]]:
        """Return documents with normalized relevance scores."""
        ...


class IndexedDocument(BaseModel):
    """Auditable description of one source in an index."""

    source: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    characters: int = Field(ge=1)


class IndexManifest(BaseModel):
    """Configuration and provenance required to reopen an index safely."""

    schema_version: int = 1
    revision: str = Field(pattern=r"^[a-f0-9]{16}$")
    collection_alias: str
    collection_name: str
    corpus_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    embedding_provider: str
    embedding_model: str
    chunk_size: int = Field(gt=0)
    chunk_overlap: int = Field(ge=0)
    document_count: int = Field(gt=0)
    chunk_count: int = Field(gt=0)
    documents: list[IndexedDocument]
    built_at: datetime


class RetrievalEvaluationExample(BaseModel):
    """One labelled question used to evaluate retrieval without an LLM judge."""

    id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    question: str = Field(min_length=3)
    expected_sources: list[str] = Field(default_factory=list)
    answerable: bool
    reference_answer: str | None = None

    @model_validator(mode="after")
    def validate_reference(self) -> RetrievalEvaluationExample:
        if self.answerable and not self.expected_sources:
            raise ValueError("An answerable example requires at least one expected source")
        if not self.answerable and self.expected_sources:
            raise ValueError("An unanswerable example cannot declare expected sources")
        return self


class RetrievalCaseResult(BaseModel):
    """Per-question retrieval diagnostics."""

    id: str
    answerable: bool
    retrieved_sources: list[str]
    hit: bool | None = None
    source_recall: float | None = Field(default=None, ge=0.0, le=1.0)
    reciprocal_rank: float | None = Field(default=None, ge=0.0, le=1.0)


class RetrievalEvaluationSummary(BaseModel):
    """Reference-based retrieval metrics kept separate from generation quality."""

    examples: int = Field(ge=1)
    answerable_examples: int = Field(ge=0)
    unanswerable_examples: int = Field(ge=0)
    hit_rate_at_k: float = Field(ge=0.0, le=1.0)
    source_recall_at_k: float = Field(ge=0.0, le=1.0)
    mean_reciprocal_rank: float = Field(ge=0.0, le=1.0)
    empty_retrieval_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    k: int = Field(ge=1)
    min_score: float = Field(ge=0.0, le=1.0)
    cases: list[RetrievalCaseResult]


def load_corpus_documents(
    corpus_dir: Path,
    *,
    max_document_bytes: int = MAX_DOCUMENT_BYTES,
) -> list[Document]:
    """Load a deterministic Markdown/text corpus with provenance metadata."""
    root = corpus_dir.resolve()
    if not root.is_dir():
        raise CorpusError(f"Corpus directory does not exist: {corpus_dir}")
    if max_document_bytes < 1:
        raise ValueError("max_document_bytes must be positive")

    paths = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink() and path.suffix.casefold() in SUPPORTED_SUFFIXES
    )
    if not paths:
        raise CorpusError("The corpus contains no supported .md or .txt documents")

    documents: list[Document] = []
    for path in paths:
        size = path.stat().st_size
        if size > max_document_bytes:
            raise CorpusError(f"Document exceeds {max_document_bytes} bytes: {path.name}")

        try:
            content = path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
        except UnicodeDecodeError as error:
            raise CorpusError(f"Document is not valid UTF-8: {path.name}") from error
        if not content:
            raise CorpusError(f"Document is empty: {path.name}")

        source = path.relative_to(root).as_posix()
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": source,
                    "title": _extract_title(content, path.stem),
                    "sha256": _sha256_text(content),
                    "file_type": path.suffix.casefold().lstrip("."),
                },
            )
        )
    return documents


def build_persistent_index(
    corpus_dir: Path,
    index_dir: Path,
    embeddings: Embeddings,
    *,
    embedding_provider: str,
    embedding_model: str,
    collection_alias: str = "insurance-documents",
    chunk_size: int = 650,
    chunk_overlap: int = 100,
) -> tuple[Chroma, IndexManifest]:
    """Rebuild and persist a versioned Chroma collection plus its manifest."""
    documents = load_corpus_documents(corpus_dir)
    chunks = split_documents(
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    corpus_sha256 = fingerprint_documents(documents)
    revision = _index_revision(
        corpus_sha256=corpus_sha256,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    collection_name = f"{_normalize_collection_name(collection_alias)}-{revision[:12]}"

    from langchain_chroma import Chroma

    index_dir.mkdir(parents=True, exist_ok=True)
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(index_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )
    vector_store.reset_collection()
    vector_store.add_documents(
        documents=chunks,
        ids=[str(chunk.metadata["chunk_id"]) for chunk in chunks],
    )

    manifest = IndexManifest(
        revision=revision,
        collection_alias=collection_alias,
        collection_name=collection_name,
        corpus_sha256=corpus_sha256,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        document_count=len(documents),
        chunk_count=len(chunks),
        documents=[
            IndexedDocument(
                source=str(document.metadata["source"]),
                sha256=str(document.metadata["sha256"]),
                characters=len(document.page_content),
            )
            for document in documents
        ],
        built_at=datetime.now(UTC),
    )
    _write_manifest(index_dir, manifest)
    return vector_store, manifest


def open_persistent_index(
    index_dir: Path,
    embeddings: Embeddings,
    *,
    embedding_provider: str,
    embedding_model: str,
) -> tuple[Chroma, IndexManifest]:
    """Open an existing index only when its embedding configuration matches."""
    manifest = load_index_manifest(index_dir)
    if manifest.embedding_provider != embedding_provider:
        raise IndexConfigurationError(
            "Embedding provider mismatch: "
            f"index={manifest.embedding_provider}, requested={embedding_provider}"
        )
    if manifest.embedding_model != embedding_model:
        raise IndexConfigurationError(
            "Embedding model mismatch: "
            f"index={manifest.embedding_model}, requested={embedding_model}"
        )

    from langchain_chroma import Chroma

    vector_store = Chroma(
        collection_name=manifest.collection_name,
        embedding_function=embeddings,
        persist_directory=str(index_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )
    if len(vector_store.get(include=[])["ids"]) != manifest.chunk_count:
        raise IndexConfigurationError("Persisted collection does not match its manifest")
    return vector_store, manifest


def load_index_manifest(index_dir: Path) -> IndexManifest:
    """Read and validate the persisted index manifest."""
    path = index_dir / MANIFEST_FILENAME
    if not path.is_file():
        raise IndexConfigurationError(f"Index manifest not found: {path}")
    try:
        return IndexManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise IndexConfigurationError(f"Invalid index manifest: {path}") from error


def fingerprint_documents(documents: list[Document]) -> str:
    """Return an order-independent fingerprint of source names and contents."""
    if not documents:
        raise ValueError("At least one document is required")
    digest = hashlib.sha256()
    records = sorted(
        (str(document.metadata["source"]), _sha256_text(document.page_content))
        for document in documents
    )
    for source, content_hash in records:
        digest.update(source.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content_hash.encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def corpus_matches_manifest(corpus_dir: Path, manifest: IndexManifest) -> bool:
    """Detect source changes that require re-indexing."""
    return fingerprint_documents(load_corpus_documents(corpus_dir)) == manifest.corpus_sha256


def retrieve_relevant_chunks(
    vector_store: RelevanceVectorStore,
    query: str,
    *,
    k: int = 4,
    min_score: float = 0.2,
) -> list[RetrievedChunk]:
    """Retrieve evidence using normalized relevance scores where higher is better."""
    if not query.strip():
        raise ValueError("query cannot be empty")
    if k < 1:
        raise ValueError("k must be at least 1")
    if not 0.0 <= min_score <= 1.0:
        raise ValueError("min_score must be between 0 and 1")

    matches = vector_store.similarity_search_with_relevance_scores(query, k=k)
    return [
        RetrievedChunk(
            chunk_id=str(document.metadata["chunk_id"]),
            source=str(document.metadata["source"]),
            content=document.page_content,
            score=float(score),
        )
        for document, score in matches
        if score >= min_score
    ]


def answer_documentary_question(
    vector_store: RelevanceVectorStore,
    generator: AnswerGenerator,
    question: str,
    *,
    k: int = 4,
    min_score: float = 0.2,
) -> RagAnswer:
    """Answer from retrieved evidence and reject every unverifiable citation."""
    chunks = retrieve_relevant_chunks(vector_store, question, k=k, min_score=min_score)
    if not chunks:
        return _refusal(0)

    generated = generator.invoke({"question": question, "context": format_context(chunks)})
    if not isinstance(generated, GeneratedAnswer):
        raise TypeError("Generator must return a GeneratedAnswer instance")
    if not generated.answerable:
        return _refusal(len(chunks))

    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    unknown_ids = set(generated.cited_chunk_ids) - chunks_by_id.keys()
    if unknown_ids:
        raise ValueError(f"Generated answer contains unknown citations: {sorted(unknown_ids)}")
    if not generated.cited_chunk_ids:
        raise ValueError("An answerable response must cite at least one retrieved chunk")

    citations = [
        Citation(chunk_id=chunk_id, source=chunks_by_id[chunk_id].source)
        for chunk_id in dict.fromkeys(generated.cited_chunk_ids)
    ]
    return RagAnswer(
        answer=generated.answer,
        answered=True,
        citations=citations,
        retrieved_chunks=len(chunks),
    )


def load_evaluation_dataset(path: Path) -> list[RetrievalEvaluationExample]:
    """Load a JSONL evaluation dataset and reject duplicate identifiers."""
    if not path.is_file():
        raise ValueError(f"Evaluation dataset not found: {path}")

    examples: list[RetrievalEvaluationExample] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            example = RetrievalEvaluationExample.model_validate_json(line)
        except ValueError as error:
            raise ValueError(f"Invalid evaluation example on line {line_number}") from error
        if example.id in seen_ids:
            raise ValueError(f"Duplicate evaluation id: {example.id}")
        seen_ids.add(example.id)
        examples.append(example)

    if not examples:
        raise ValueError("Evaluation dataset cannot be empty")
    return examples


def evaluate_retrieval(
    vector_store: RelevanceVectorStore,
    examples: list[RetrievalEvaluationExample],
    *,
    k: int = 4,
    min_score: float = 0.2,
) -> RetrievalEvaluationSummary:
    """Compute retrieval metrics without treating retrieval as an answerability judge."""
    if not examples:
        raise ValueError("At least one evaluation example is required")

    cases: list[RetrievalCaseResult] = []
    for example in examples:
        chunks = retrieve_relevant_chunks(
            vector_store,
            example.question,
            k=k,
            min_score=min_score,
        )
        retrieved_sources = list(dict.fromkeys(chunk.source for chunk in chunks))
        if example.answerable:
            expected = set(example.expected_sources)
            found = expected.intersection(retrieved_sources)
            source_recall = len(found) / len(expected)
            first_rank = next(
                (
                    rank
                    for rank, source in enumerate(retrieved_sources, start=1)
                    if source in expected
                ),
                None,
            )
            reciprocal_rank = 0.0 if first_rank is None else 1.0 / first_rank
            hit = bool(found)
        else:
            hit = None
            source_recall = None
            reciprocal_rank = None

        cases.append(
            RetrievalCaseResult(
                id=example.id,
                answerable=example.answerable,
                retrieved_sources=retrieved_sources,
                hit=hit,
                source_recall=source_recall,
                reciprocal_rank=reciprocal_rank,
            )
        )

    answerable_cases = [case for case in cases if case.answerable]
    unanswerable_cases = [case for case in cases if not case.answerable]
    return RetrievalEvaluationSummary(
        examples=len(cases),
        answerable_examples=len(answerable_cases),
        unanswerable_examples=len(unanswerable_cases),
        hit_rate_at_k=_mean([float(case.hit) for case in answerable_cases if case.hit is not None]),
        source_recall_at_k=_mean(
            [case.source_recall for case in answerable_cases if case.source_recall is not None]
        ),
        mean_reciprocal_rank=_mean(
            [case.reciprocal_rank for case in answerable_cases if case.reciprocal_rank is not None]
        ),
        empty_retrieval_rate=(
            _mean([float(not case.retrieved_sources) for case in unanswerable_cases])
            if unanswerable_cases
            else None
        ),
        k=k,
        min_score=min_score,
        cases=cases,
    )


def _write_manifest(index_dir: Path, manifest: IndexManifest) -> None:
    path = index_dir / MANIFEST_FILENAME
    temporary_path = index_dir / f".{MANIFEST_FILENAME}.tmp"
    temporary_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(path)


def _index_revision(
    *,
    corpus_sha256: str,
    embedding_provider: str,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
) -> str:
    configuration = json.dumps(
        {
            "chunk_overlap": chunk_overlap,
            "chunk_size": chunk_size,
            "corpus_sha256": corpus_sha256,
            "embedding_model": embedding_model,
            "embedding_provider": embedding_provider,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_text(configuration)[:16]


def _normalize_collection_name(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-_").casefold()
    if len(normalized) < 3:
        raise ValueError("collection_alias must contain at least three valid characters")
    return normalized[:48]


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        heading = re.match(r"^#\s+(.+)$", line.strip())
        if heading:
            return heading.group(1).strip()
    return fallback.replace("_", " ").replace("-", " ").title()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _refusal(retrieved_chunks: int) -> RagAnswer:
    return RagAnswer(
        answer="Je ne dispose pas de preuves suffisantes dans les documents indexes.",
        answered=False,
        citations=[],
        retrieved_chunks=retrieved_chunks,
    )
