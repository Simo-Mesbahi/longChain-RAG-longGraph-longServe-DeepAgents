from datetime import date

import pytest
from pydantic import ValidationError

from ai_course.structured_output import (
    ClaimCategory,
    ClaimExtraction,
    execute_tool_call,
    get_claim_status,
)


def test_complete_claim_is_valid_without_human_review() -> None:
    claim = ClaimExtraction(
        claim_id="CLM-123456",
        incident_date=date(2026, 8, 14),
        amount_eur=1250.50,
        category=ClaimCategory.WATER_DAMAGE,
        summary="Degat des eaux dans la cuisine.",
        missing_fields=[],
        requires_human_review=False,
    )

    assert claim.amount_eur == 1250.50
    assert claim.requires_human_review is False


def test_incomplete_claim_requires_consistent_missing_fields() -> None:
    claim = ClaimExtraction(
        claim_id=None,
        incident_date=None,
        amount_eur=800,
        category=ClaimCategory.THEFT,
        summary="Vol de materiel informatique declare.",
        missing_fields=["claim_id", "incident_date"],
        requires_human_review=True,
    )

    assert set(claim.missing_fields) == {"claim_id", "incident_date"}


@pytest.mark.parametrize(
    ("missing_fields", "requires_human_review"),
    [([], True), (["claim_id"], False), (["amount_eur"], True)],
)
def test_inconsistent_review_metadata_is_rejected(
    missing_fields: list[str], requires_human_review: bool
) -> None:
    with pytest.raises(ValidationError):
        ClaimExtraction(
            claim_id=None,
            incident_date=date(2026, 8, 14),
            amount_eur=100,
            category=ClaimCategory.OTHER,
            summary="Demande synthetique pour le test.",
            missing_fields=missing_fields,
            requires_human_review=requires_human_review,
        )


def test_negative_amount_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ClaimExtraction(
            claim_id="CLM-123456",
            incident_date=date(2026, 8, 14),
            amount_eur=-1,
            category=ClaimCategory.OTHER,
            summary="Demande synthetique pour le test.",
            missing_fields=[],
            requires_human_review=False,
        )


def test_claim_status_tool_exposes_a_typed_schema() -> None:
    schema = get_claim_status.args_schema.model_json_schema()

    assert schema["required"] == ["claim_id"]
    assert schema["properties"]["claim_id"]["pattern"] == r"^CLM-[0-9]{6}$"


def test_allowed_tool_call_is_executed() -> None:
    result = execute_tool_call(
        {"name": "get_claim_status", "args": {"claim_id": "CLM-123456"}, "id": "call-1"}
    )

    assert result == {"claim_id": "CLM-123456", "status": "under_review"}


def test_invalid_tool_arguments_are_rejected() -> None:
    with pytest.raises(ValidationError):
        execute_tool_call({"name": "get_claim_status", "args": {"claim_id": "123"}, "id": "call-2"})


def test_unknown_tool_is_rejected() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        execute_tool_call({"name": "delete_claim", "args": {}, "id": "call-3"})
