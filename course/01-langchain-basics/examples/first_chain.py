"""Run the first LangChain teaching chain from the command line."""

import argparse

from ai_course.langchain_basics import build_teaching_chain, create_chat_model
from ai_course.settings import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explain one AI concept with LangChain.")
    parser.add_argument("concept", help="Concept to explain, for example RAG or SHAP")
    parser.add_argument("--level", default="debutant", help="Expected learner level")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    model = create_chat_model(settings)
    chain = build_teaching_chain(model)
    response = chain.invoke({"concept": args.concept, "level": args.level})
    print(response.content)


if __name__ == "__main__":
    main()
