"""Extract a typed insurance claim from unstructured text."""

import argparse

from ai_course.langchain_basics import create_chat_model
from ai_course.settings import load_settings
from ai_course.structured_output import build_claim_extractor

DEFAULT_CLAIM = """
La demande CLM-123456 concerne un degat des eaux survenu le 14 aout 2026.
L'assure demande un remboursement de 1 250,50 euros pour les reparations de la cuisine.
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract a typed insurance claim.")
    parser.add_argument("text", nargs="?", default=DEFAULT_CLAIM, help="Claim text to extract")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = create_chat_model(load_settings())
    extractor = build_claim_extractor(model)
    result = extractor.invoke(args.text)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
