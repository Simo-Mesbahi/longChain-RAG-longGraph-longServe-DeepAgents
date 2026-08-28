"""Command-line entry point for the Insurance Claim Intake mini-project."""

import argparse
import asyncio

from ai_course.claim_intake import ClaimIntakeService, ExtractionUnavailableError, RetryPolicy
from ai_course.langchain_basics import create_chat_model
from ai_course.settings import load_settings
from ai_course.structured_output import build_claim_extractor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract and validate one insurance claim.")
    parser.add_argument("text", help="Unstructured insurance claim text")
    parser.add_argument("--timeout", type=float, default=30.0, help="Seconds per attempt")
    parser.add_argument("--max-attempts", type=int, default=3, help="Maximum attempts")
    return parser.parse_args()


async def run() -> int:
    args = parse_args()
    policy = RetryPolicy(max_attempts=args.max_attempts, timeout_seconds=args.timeout)

    # Keep retries in the service layer to avoid multiplying provider attempts.
    model = create_chat_model(load_settings(), timeout=args.timeout, max_retries=0)
    service = ClaimIntakeService(
        build_claim_extractor(model),
        retry_policy=policy,
    )

    try:
        result = await service.process(args.text)
    except ExtractionUnavailableError as error:
        print(f"Extraction failed after {error.attempts} attempts.")
        return 1

    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
