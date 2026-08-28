"""Resilient application service for the insurance claim intake mini-project."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field

from ai_course.structured_output import ClaimExtraction


class AsyncClaimExtractor(Protocol):
    """Minimal interface required from an asynchronous extraction backend."""

    async def ainvoke(self, text: str) -> ClaimExtraction:
        """Extract one claim from text."""
        ...


class IntakeStatus(StrEnum):
    """Workflow statuses returned by the intake service."""

    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"


class IntakeResult(BaseModel):
    """Application-level result returned after successful extraction."""

    status: IntakeStatus
    claim: ClaimExtraction
    attempts: int = Field(ge=1)
    warning: str | None = None


@dataclass(frozen=True)
class RetryPolicy:
    """Timeout and exponential-backoff settings for one intake request."""

    max_attempts: int = 3
    timeout_seconds: float = 30.0
    initial_delay_seconds: float = 0.25

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds cannot be negative")


class ExtractionUnavailableError(RuntimeError):
    """Raised after all retryable extraction attempts have failed."""

    def __init__(self, attempts: int) -> None:
        self.attempts = attempts
        super().__init__(f"Claim extraction unavailable after {attempts} attempts")


class ClaimIntakeService:
    """Validate input, call an extractor, and classify the intake result."""

    def __init__(
        self,
        extractor: AsyncClaimExtractor,
        *,
        retry_policy: RetryPolicy | None = None,
        retryable_exceptions: tuple[type[Exception], ...] = (TimeoutError, ConnectionError),
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.extractor = extractor
        self.retry_policy = retry_policy or RetryPolicy()
        self.retryable_exceptions = retryable_exceptions
        self.sleep = sleep

    async def process(self, text: str) -> IntakeResult:
        """Process one claim and retry only explicitly transient failures."""
        normalized_text = text.strip()
        if len(normalized_text) < 20:
            raise ValueError("Claim text must contain at least 20 characters")

        policy = self.retry_policy
        for attempt in range(1, policy.max_attempts + 1):
            try:
                async with asyncio.timeout(policy.timeout_seconds):
                    claim = await self.extractor.ainvoke(normalized_text)
                if not isinstance(claim, ClaimExtraction):
                    raise TypeError("Extractor must return a ClaimExtraction instance")
                return self._build_result(claim, attempt)
            except self.retryable_exceptions as error:
                if attempt == policy.max_attempts:
                    raise ExtractionUnavailableError(attempt) from error
                delay = policy.initial_delay_seconds * (2 ** (attempt - 1))
                await self.sleep(delay)

        raise AssertionError("Retry loop exited unexpectedly")

    @staticmethod
    def _build_result(claim: ClaimExtraction, attempts: int) -> IntakeResult:
        if claim.requires_human_review:
            return IntakeResult(
                status=IntakeStatus.NEEDS_REVIEW,
                claim=claim,
                attempts=attempts,
                warning="Critical information is missing; human review is required.",
            )
        return IntakeResult(
            status=IntakeStatus.ACCEPTED,
            claim=claim,
            attempts=attempts,
        )
