import asyncio
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

import pytest

from ai_course.claim_intake import (
    ClaimIntakeService,
    ExtractionUnavailableError,
    IntakeStatus,
    RetryPolicy,
)
from ai_course.structured_output import ClaimCategory, ClaimExtraction


def make_claim(*, requires_review: bool = False) -> ClaimExtraction:
    return ClaimExtraction(
        claim_id=None if requires_review else "CLM-123456",
        incident_date=date(2026, 8, 14),
        amount_eur=1250.50,
        category=ClaimCategory.WATER_DAMAGE,
        summary="Degat des eaux dans la cuisine.",
        missing_fields=["claim_id"] if requires_review else [],
        requires_human_review=requires_review,
    )


class SequenceExtractor:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    async def ainvoke(self, text: str) -> ClaimExtraction:
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class SlowExtractor:
    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(self, text: str) -> ClaimExtraction:
        self.calls += 1
        await asyncio.sleep(0.05)
        return make_claim()


async def no_sleep(delay: float) -> None:
    return None


def run_async(factory: Callable[[], Awaitable[Any]]) -> Any:
    return asyncio.run(factory())


def test_complete_claim_is_accepted() -> None:
    extractor = SequenceExtractor([make_claim()])
    service = ClaimIntakeService(extractor)

    result = run_async(lambda: service.process("Declaration suffisamment longue pour extraction."))

    assert result.status is IntakeStatus.ACCEPTED
    assert result.attempts == 1
    assert result.warning is None


def test_incomplete_claim_needs_human_review() -> None:
    service = ClaimIntakeService(SequenceExtractor([make_claim(requires_review=True)]))

    result = run_async(lambda: service.process("Declaration incomplete mais assez longue."))

    assert result.status is IntakeStatus.NEEDS_REVIEW
    assert result.warning is not None


def test_transient_failure_is_retried() -> None:
    extractor = SequenceExtractor([ConnectionError("temporary"), make_claim()])
    service = ClaimIntakeService(
        extractor,
        retry_policy=RetryPolicy(max_attempts=2, initial_delay_seconds=0),
        sleep=no_sleep,
    )

    result = run_async(lambda: service.process("Declaration suffisamment longue pour retry."))

    assert result.attempts == 2
    assert extractor.calls == 2


def test_non_retryable_error_fails_immediately() -> None:
    extractor = SequenceExtractor([ValueError("invalid model output"), make_claim()])
    service = ClaimIntakeService(extractor, sleep=no_sleep)

    with pytest.raises(ValueError, match="invalid model output"):
        run_async(lambda: service.process("Declaration suffisamment longue pour validation."))

    assert extractor.calls == 1


def test_timeout_is_retried_then_reported() -> None:
    extractor = SlowExtractor()
    service = ClaimIntakeService(
        extractor,
        retry_policy=RetryPolicy(
            max_attempts=2,
            timeout_seconds=0.001,
            initial_delay_seconds=0,
        ),
        sleep=no_sleep,
    )

    with pytest.raises(ExtractionUnavailableError) as captured:
        run_async(lambda: service.process("Declaration suffisamment longue pour timeout."))

    assert captured.value.attempts == 2
    assert extractor.calls == 2


def test_short_input_is_rejected_before_extraction() -> None:
    extractor = SequenceExtractor([make_claim()])
    service = ClaimIntakeService(extractor)

    with pytest.raises(ValueError, match="at least 20"):
        run_async(lambda: service.process("Trop court"))

    assert extractor.calls == 0


@pytest.mark.parametrize(
    "policy",
    [
        {"max_attempts": 0},
        {"timeout_seconds": 0},
        {"initial_delay_seconds": -1},
    ],
)
def test_invalid_retry_policy_is_rejected(policy: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        RetryPolicy(**policy)
