from pathlib import Path

import pytest
from langchain_core.documents import Document

from ai_course.documentary_rag import (
    CorpusError,
    IndexConfigurationError,
    RetrievalEvaluationExample,
    answer_documentary_question,
    build_persistent_index,
    corpus_matches_manifest,
    evaluate_retrieval,
    fingerprint_documents,
    load_corpus_documents,
    load_evaluation_dataset,
    load_index_manifest,
    open_persistent_index,
    retrieve_relevant_chunks,
)
from ai_course.rag_basics import GeneratedAnswer, HashingEmbeddings


class StubStore:
    def __init__(self, results: dict[str, list[tuple[Document, float]]]) -> None:
        self.results = results

    def similarity_search_with_relevance_scores(
        self,
        query: str,
        *,
        k: int,
    ) -> list[tuple[Document, float]]:
        return self.results.get(query, [])[:k]


class StubGenerator:
    def __init__(self, answer: GeneratedAnswer) -> None:
        self.answer = answer
        self.calls = 0

    def invoke(self, input: dict[str, str]) -> GeneratedAnswer:
        self.calls += 1
        return self.answer


def make_chunk(source: str, chunk_id: str, content: str = "Evidence") -> Document:
    return Document(
        page_content=content,
        metadata={"source": source, "chunk_id": chunk_id},
    )


def write_corpus(root: Path) -> None:
    (root / "nested").mkdir(parents=True)
    (root / "water.md").write_text(
        "# Water policy\n\nLa franchise degat des eaux est de 180 euros.",
        encoding="utf-8",
    )
    (root / "nested" / "fraud.txt").write_text(
        "Un score eleve priorise le dossier mais ne prouve pas une fraude.",
        encoding="utf-8",
    )
    (root / "ignored.json").write_text('{"ignored": true}', encoding="utf-8")


def test_load_corpus_is_deterministic_and_adds_provenance(tmp_path: Path) -> None:
    write_corpus(tmp_path)

    documents = load_corpus_documents(tmp_path)

    assert [document.metadata["source"] for document in documents] == [
        "nested/fraud.txt",
        "water.md",
    ]
    assert documents[1].metadata["title"] == "Water policy"
    assert len(documents[0].metadata["sha256"]) == 64


def test_empty_invalid_and_oversized_corpora_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="no supported"):
        load_corpus_documents(tmp_path)

    (tmp_path / "empty.md").write_text("", encoding="utf-8")
    with pytest.raises(CorpusError, match="empty"):
        load_corpus_documents(tmp_path)

    (tmp_path / "empty.md").write_text("too long", encoding="utf-8")
    with pytest.raises(CorpusError, match="exceeds"):
        load_corpus_documents(tmp_path, max_document_bytes=2)


def test_fingerprint_changes_with_content_but_not_input_order(tmp_path: Path) -> None:
    write_corpus(tmp_path)
    documents = load_corpus_documents(tmp_path)

    first = fingerprint_documents(documents)
    reordered = fingerprint_documents(list(reversed(documents)))
    documents[0].page_content += " changed"

    assert first == reordered
    assert fingerprint_documents(documents) != first


def test_persistent_index_reopens_and_detects_corpus_changes(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    index_dir = tmp_path / "index"
    write_corpus(corpus_dir)
    embeddings = HashingEmbeddings(dimensions=64)

    store, manifest = build_persistent_index(
        corpus_dir,
        index_dir,
        embeddings,
        embedding_provider="hashing",
        embedding_model="hashing-test-64",
        chunk_size=200,
        chunk_overlap=20,
    )

    assert manifest.document_count == 2
    assert manifest.chunk_count >= 2
    assert load_index_manifest(index_dir) == manifest
    assert corpus_matches_manifest(corpus_dir, manifest) is True
    assert store.similarity_search("franchise 180 euros", k=1)[0].metadata["source"] == "water.md"

    reopened, reopened_manifest = open_persistent_index(
        index_dir,
        embeddings,
        embedding_provider="hashing",
        embedding_model="hashing-test-64",
    )
    assert reopened_manifest.revision == manifest.revision
    assert reopened.similarity_search("score fraude", k=1)[0].metadata["source"] == (
        "nested/fraud.txt"
    )

    (corpus_dir / "water.md").write_text("# Changed\n\nNew content", encoding="utf-8")
    assert corpus_matches_manifest(corpus_dir, manifest) is False


def test_index_rejects_embedding_configuration_mismatch(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    index_dir = tmp_path / "index"
    write_corpus(corpus_dir)
    embeddings = HashingEmbeddings(dimensions=64)
    build_persistent_index(
        corpus_dir,
        index_dir,
        embeddings,
        embedding_provider="hashing",
        embedding_model="hashing-test-64",
    )

    with pytest.raises(IndexConfigurationError, match="model mismatch"):
        open_persistent_index(
            index_dir,
            embeddings,
            embedding_provider="hashing",
            embedding_model="another-model",
        )


def test_retrieval_filters_by_normalized_relevance() -> None:
    store = StubStore(
        {
            "question": [
                (make_chunk("relevant.md", "relevant.md#chunk-000"), 0.8),
                (make_chunk("noise.md", "noise.md#chunk-000"), 0.1),
            ]
        }
    )

    chunks = retrieve_relevant_chunks(store, "question", k=2, min_score=0.5)

    assert [chunk.source for chunk in chunks] == ["relevant.md"]
    assert chunks[0].score == pytest.approx(0.8)


@pytest.mark.parametrize(
    ("query", "k", "min_score"),
    [("", 1, 0.2), ("valid", 0, 0.2), ("valid", 1, -0.1), ("valid", 1, 1.1)],
)
def test_retrieval_rejects_invalid_parameters(query: str, k: int, min_score: float) -> None:
    with pytest.raises(ValueError):
        retrieve_relevant_chunks(StubStore({}), query, k=k, min_score=min_score)


def test_answer_uses_only_retrieved_citations() -> None:
    chunk = make_chunk("policy.md", "policy.md#chunk-000", "Franchise de 180 euros.")
    store = StubStore({"franchise": [(chunk, 0.9)]})
    generator = StubGenerator(
        GeneratedAnswer(
            answer="La franchise est de 180 euros.",
            cited_chunk_ids=["policy.md#chunk-000"],
            answerable=True,
        )
    )

    result = answer_documentary_question(store, generator, "franchise", min_score=0.2)

    assert result.answered is True
    assert result.citations[0].source == "policy.md"
    assert generator.calls == 1


def test_answer_refuses_without_evidence_and_rejects_unknown_citation() -> None:
    no_evidence_generator = StubGenerator(
        GeneratedAnswer(answer="unused", cited_chunk_ids=[], answerable=True)
    )
    refused = answer_documentary_question(
        StubStore({}),
        no_evidence_generator,
        "unknown",
        min_score=0.5,
    )
    assert refused.answered is False
    assert no_evidence_generator.calls == 0

    chunk = make_chunk("policy.md", "policy.md#chunk-000")
    invented_generator = StubGenerator(
        GeneratedAnswer(
            answer="Invented",
            cited_chunk_ids=["invented.md#chunk-999"],
            answerable=True,
        )
    )
    with pytest.raises(ValueError, match="unknown citations"):
        answer_documentary_question(
            StubStore({"known": [(chunk, 0.9)]}),
            invented_generator,
            "known",
        )


def test_evaluate_retrieval_computes_component_metrics() -> None:
    store = StubStore(
        {
            "question one": [(make_chunk("a.md", "a#0"), 0.9)],
            "question two": [
                (make_chunk("noise.md", "noise#0"), 0.9),
                (make_chunk("c.md", "c#0"), 0.8),
            ],
            "question three": [],
        }
    )
    examples = [
        RetrievalEvaluationExample(
            id="q1",
            question="question one",
            expected_sources=["a.md", "b.md"],
            answerable=True,
        ),
        RetrievalEvaluationExample(
            id="q2",
            question="question two",
            expected_sources=["c.md"],
            answerable=True,
        ),
        RetrievalEvaluationExample(
            id="q3",
            question="question three",
            expected_sources=[],
            answerable=False,
        ),
    ]

    summary = evaluate_retrieval(store, examples, k=2, min_score=0.2)

    assert summary.hit_rate_at_k == pytest.approx(1.0)
    assert summary.source_recall_at_k == pytest.approx(0.75)
    assert summary.mean_reciprocal_rank == pytest.approx(0.75)
    assert summary.empty_retrieval_rate == pytest.approx(1.0)
    assert summary.cases[-1].hit is None


def test_evaluation_dataset_validation(tmp_path: Path) -> None:
    dataset = tmp_path / "questions.jsonl"
    dataset.write_text(
        '{"id":"one","question":"valid question","expected_sources":["a.md"],'
        '"answerable":true}\n'
        '{"id":"two","question":"unknown question","expected_sources":[],'
        '"answerable":false}\n',
        encoding="utf-8",
    )

    examples = load_evaluation_dataset(dataset)

    assert len(examples) == 2
    assert examples[0].answerable is True

    dataset.write_text(
        dataset.read_text(encoding="utf-8").replace('"two"', '"one"'), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Duplicate"):
        load_evaluation_dataset(dataset)
