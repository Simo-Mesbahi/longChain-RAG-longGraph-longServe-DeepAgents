"""Typed extraction and safe tool execution examples for module 02."""

from datetime import date
from enum import StrEnum
from typing import Any

from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, model_validator


class ClaimCategory(StrEnum):
    """Small controlled vocabulary for the course's synthetic claims."""

    WATER_DAMAGE = "water_damage"
    THEFT = "theft"
    VEHICLE = "vehicle"
    HEALTH = "health"
    OTHER = "other"


class ClaimExtraction(BaseModel):
    """Validated information extracted from an unstructured claim."""

    claim_id: str | None = Field(default=None, pattern=r"^CLM-[0-9]{6}$")
    incident_date: date | None = None
    amount_eur: float | None = Field(default=None, ge=0)
    category: ClaimCategory
    summary: str = Field(min_length=10, max_length=500)
    missing_fields: list[str] = Field(default_factory=list)
    requires_human_review: bool

    @model_validator(mode="after")
    def validate_missing_fields(self) -> "ClaimExtraction":
        """Keep missing-field metadata consistent with the extracted values."""
        tracked_fields = ("claim_id", "incident_date", "amount_eur")
        actual_missing = {name for name in tracked_fields if getattr(self, name) is None}
        declared_missing = set(self.missing_fields)

        if declared_missing != actual_missing:
            raise ValueError(
                "missing_fields must exactly list absent claim_id, incident_date, and amount_eur"
            )
        if self.requires_human_review != bool(actual_missing):
            raise ValueError("requires_human_review must be true when a tracked field is missing")
        return self


def build_claim_extractor(model: BaseChatModel) -> Runnable:
    """Bind the claim schema to a chat model."""
    return model.with_structured_output(ClaimExtraction)


class ClaimStatusInput(BaseModel):
    """Arguments accepted by the read-only claim-status tool."""

    claim_id: str = Field(pattern=r"^CLM-[0-9]{6}$")


@tool(args_schema=ClaimStatusInput)
def get_claim_status(claim_id: str) -> dict[str, str]:
    """Return the synthetic workflow status for one insurance claim."""
    statuses = {
        "CLM-123456": "under_review",
        "CLM-654321": "documents_requested",
    }
    return {
        "claim_id": claim_id,
        "status": statuses.get(claim_id, "not_found"),
    }


ALLOWED_TOOLS: dict[str, BaseTool] = {get_claim_status.name: get_claim_status}


def execute_tool_call(tool_call: dict[str, Any]) -> Any:
    """Validate a model-requested tool name and arguments before execution."""
    tool_name = tool_call.get("name")
    if tool_name not in ALLOWED_TOOLS:
        raise ValueError(f"Tool is not allowed: {tool_name!r}")

    arguments = tool_call.get("args")
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a dictionary")

    return ALLOWED_TOOLS[tool_name].invoke(arguments)
