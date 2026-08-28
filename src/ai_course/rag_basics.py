"""Testable RAG primitives for the course's introductory retrieval module."""

import hashlib
import math
import re
from collections import defaultdict
from typing import Protocol

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field


class HashingEmbeddings(Embeddings):
    """Deterministic local embeddings for tests and offline demonstrations."""

    def __init__(self, dimensions: int = 128) -> None:
        if dimensions < 8:
            raise ValueError("dimensions must be at least 8")
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"\w+", text.casefold())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class RetrievedChunk(BaseModel):
    """A retrieved chunk together with provenance and similarity score."""

    chunk_id: str
    source: str
    content: str
    score: float


class GeneratedAnswer(BaseModel):
    """Structured answer requested from the generation model."""

    answer: str = Field(min_length=1)
    cited_chunk_ids: list[str] = Field(default_factory=list)
    answerable: bool


class Citation(BaseModel):
    """Citation resolved from a retrieved chunk, not invented by the model."""

    chunk_id: str
    source: str


class RagAnswer(BaseModel):
    """Final answer returned by the validated RAG pipeline."""

    answer: str
    answered: bool
    citations: list[Citation] = Field(default_factory=list)
    retrieved_chunks: int = Field(ge=0)


class AnswerGenerator(Protocol):
    """Minimal synchronous interface required from a generation backend."""

    def invoke(self, input: dict[str, str]) -> GeneratedAnswer:
        """Generate one structured answer from a question and context."""
        ...


def build_answer_generator(model: BaseChatModel) -> Runnable:
    """Build a structured generator constrained to retrieved evidence."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Tu reponds uniquement a partir du contexte fourni. "
                "Si le contexte ne suffit pas, answerable doit etre false. "
                "Chaque reponse answerable doit citer au moins un chunk_id "
                "present dans le contexte. "
                "N'invente jamais de source, de regle ou de decision d'assurance.",
            ),
            (
                "human",
                "Question:\n{question}\n\nContexte recupere:\n{context}",
            ),
        ]
    )
    return prompt | model.with_structured_output(GeneratedAnswer)


def split_documents(
    documents: list[Document],
    *,
    chunk_size: int = 500,
    chunk_overlap: int = 75,
) -> list[Document]:
    """Split documents and attach stable, source-aware chunk identifiers."""
    if not documents:
        raise ValueError("At least one document is required")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be between 0 and chunk_size - 1")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    chunks = splitter.split_documents(documents)
    source_counters: dict[str, int] = defaultdict(int)

    for chunk in chunks:
        source = str(chunk.metadata.get("source", "unknown"))
        index = source_counters[source]
        source_counters[source] += 1
        chunk.metadata["source"] = source
        chunk.metadata["chunk_id"] = f"{source}#chunk-{index:03d}"
    return chunks


def build_vector_store(chunks: list[Document], embeddings: Embeddings) -> InMemoryVectorStore:
    """Index chunks in LangChain's in-memory vector store."""
    if not chunks:
        raise ValueError("At least one chunk is required")
    vector_store = InMemoryVectorStore(embedding=embeddings)
    vector_store.add_documents(
        documents=chunks,
        ids=[str(chunk.metadata["chunk_id"]) for chunk in chunks],
    )
    return vector_store


def retrieve_chunks(
    vector_store: InMemoryVectorStore,
    query: str,
    *,
    k: int = 4,
    min_score: float = 0.2,
) -> list[RetrievedChunk]:
    """Retrieve and filter chunks using the selected store's similarity score."""
    if not query.strip():
        raise ValueError("query cannot be empty")
    if k < 1:
        raise ValueError("k must be at least 1")

    matches = vector_store.similarity_search_with_score(query, k=k)
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


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved evidence with identifiers visible to the model."""
    return "\n\n".join(
        f"[{chunk.chunk_id}]\nSource: {chunk.source}\n{chunk.content}" for chunk in chunks
    )


def answer_question(
    vector_store: InMemoryVectorStore,
    generator: AnswerGenerator,
    question: str,
    *,
    k: int = 4,
    min_score: float = 0.2,
) -> RagAnswer:
    """Retrieve evidence, generate an answer, and validate every citation."""
    chunks = retrieve_chunks(vector_store, question, k=k, min_score=min_score)
    if not chunks:
        return _refusal(0)

    generated = generator.invoke(
        {
            "question": question,
            "context": format_context(chunks),
        }
    )
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


def _refusal(retrieved_chunks: int) -> RagAnswer:
    return RagAnswer(
        answer="Je ne dispose pas de preuves suffisantes dans les documents indexes.",
        answered=False,
        citations=[],
        retrieved_chunks=retrieved_chunks,
    )
