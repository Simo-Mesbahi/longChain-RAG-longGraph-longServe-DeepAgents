"""Environment-based settings shared by the course examples."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    model_provider: str
    model_name: str
    embedding_model: str


def load_settings() -> Settings:
    """Load non-secret model settings after reading a local .env file."""
    load_dotenv()
    return Settings(
        model_provider=os.getenv("MODEL_PROVIDER", "openai"),
        model_name=os.getenv("MODEL_NAME", "gpt-4.1-mini"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
    )
