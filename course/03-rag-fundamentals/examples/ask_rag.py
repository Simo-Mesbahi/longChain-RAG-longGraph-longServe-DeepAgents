"""Run the complete RAG pipeline with OpenAI embeddings and a chat model."""

import argparse
from pathlib import Path

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from ai_course.langchain_basics import create_chat_model
from ai_course.rag_basics import (
    answer_question,
    build_answer_generator,
    build_vector_store,
    split_documents,
)
from ai_course.settings import load_settings

DATA_PATH = Path(__file__).parents[1] / "data" / "insurance_guide.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask the insurance RAG pipeline.")
    parser.add_argument("question", help="Question answered from the indexed guide")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    document = Document(
        page_content=DATA_PATH.read_text(encoding="utf-8"),
        metadata={"source": DATA_PATH.name},
    )
    chunks = split_documents([document], chunk_size=450, chunk_overlap=60)
    embeddings = OpenAIEmbeddings(model=settings.embedding_model)
    vector_store = build_vector_store(chunks, embeddings)
    generator = build_answer_generator(create_chat_model(settings))
    answer = answer_question(vector_store, generator, args.question, min_score=0.2)
    print(answer.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
