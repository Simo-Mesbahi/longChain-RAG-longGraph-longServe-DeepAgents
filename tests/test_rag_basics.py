import pytest
from langchain_core.documents import Document

from ai_course.rag_basics import (
    GeneratedAnswer,
    HashingEmbeddings,
    answer_question,
    build_vector_store,
    format_context,
    retrieve_chunks,
    split_documents,
)

DOCUMENTS = [
    Document(
        page_content=(
            "Un degat des eaux doit etre declare rapidement. "
            "Les photos et factures des reparations servent de justificatifs."
        ),
        metadata={"source": "water-guide.md"},
    ),
    Document(
        page_content=(
            "Apres un vol, l'assure doit fournir le depot de plainte et la liste des biens. "
            "La decision finale appartient au gestionnaire."
        ),
        metadata={"source": "theft-guide.md"},
    ),
]


class StubGenerator:
    def __init__(self, answer: GeneratedAnswer) -> None:
        self.answer = answer
        self.calls = 0

    def invoke(self, input: dict[str, str]) -> GeneratedAnswer:
        self.calls += 1
        return self.answer


def make_store():
    chunks = split_documents(DOCUMENTS, chunk_size=200, chunk_overlap=20)
    return build_vector_store(chunks, HashingEmbeddings())


def test_hashing_embeddings_are_deterministic_and_normalized() -> None:
    embeddings = HashingEmbeddings()

    first = embeddings.embed_query("degat des eaux")
    second = embeddings.embed_query("degat des eaux")

    assert first == second
    assert sum(value * value for value in first) == pytest.approx(1.0)


def test_split_documents_adds_unique_chunk_ids() -> None:
    chunks = split_documents(DOCUMENTS, chunk_size=55, chunk_overlap=10)
    chunk_ids = [chunk.metadata["chunk_id"] for chunk in chunks]

    assert len(chunks) > len(DOCUMENTS)
    assert len(chunk_ids) == len(set(chunk_ids))
    assert all("source" in chunk.metadata for chunk in chunks)


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (100, -1), (100, 100)],
)
def test_invalid_chunk_configuration_is_rejected(chunk_size: int, chunk_overlap: int) -> None:
    with pytest.raises(ValueError):
        split_documents(
            DOCUMENTS,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )


def test_retrieval_returns_relevant_source() -> None:
    chunks = retrieve_chunks(
        make_store(),
        "Quels justificatifs fournir pour un degat des eaux ?",
        k=2,
        min_score=0.1,
    )

    assert chunks
    assert chunks[0].source == "water-guide.md"


def test_context_exposes_chunk_ids_and_sources() -> None:
    chunks = retrieve_chunks(make_store(), "vol depot de plainte", k=1, min_score=0.1)

    context = format_context(chunks)

    assert chunks[0].chunk_id in context
    assert chunks[0].source in context


def test_no_evidence_returns_refusal_without_generation() -> None:
    generator = StubGenerator(
        GeneratedAnswer(answer="Should not be used", cited_chunk_ids=[], answerable=True)
    )

    result = answer_question(
        make_store(),
        generator,
        "Question completement absente du corpus",
        min_score=1.1,
    )

    assert result.answered is False
    assert result.citations == []
    assert generator.calls == 0


def test_answer_resolves_only_retrieved_citations() -> None:
    store = make_store()
    retrieved = retrieve_chunks(store, "vol depot de plainte", k=1, min_score=0.1)
    generator = StubGenerator(
        GeneratedAnswer(
            answer="Il faut fournir un depot de plainte.",
            cited_chunk_ids=[retrieved[0].chunk_id],
            answerable=True,
        )
    )

    result = answer_question(
        store,
        generator,
        "Que fournir apres un vol ?",
        k=1,
        min_score=0.1,
    )

    assert result.answered is True
    assert result.citations[0].source == "theft-guide.md"


def test_unknown_citation_is_rejected() -> None:
    generator = StubGenerator(
        GeneratedAnswer(
            answer="Reponse non fiable.",
            cited_chunk_ids=["invented#chunk-999"],
            answerable=True,
        )
    )

    with pytest.raises(ValueError, match="unknown citations"):
        answer_question(
            make_store(),
            generator,
            "Quels justificatifs pour un degat des eaux ?",
            min_score=0.1,
        )


def test_unanswerable_generation_returns_refusal() -> None:
    generator = StubGenerator(
        GeneratedAnswer(
            answer="Information insuffisante.",
            cited_chunk_ids=[],
            answerable=False,
        )
    )

    result = answer_question(
        make_store(),
        generator,
        "Quels justificatifs pour un degat des eaux ?",
        min_score=0.1,
    )

    assert result.answered is False
    assert result.retrieved_chunks > 0
