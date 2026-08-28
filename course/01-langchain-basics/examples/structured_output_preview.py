"""Preview the structured-output pattern taught in module 02."""

from pydantic import BaseModel, Field

from ai_course.langchain_basics import create_chat_model
from ai_course.settings import load_settings


class ConceptExplanation(BaseModel):
    concept: str = Field(description="Name of the explained concept")
    definition: str = Field(description="Short and accurate definition")
    key_points: list[str] = Field(description="Three essential points")
    example: str = Field(description="One concrete example")
    limitation: str = Field(description="One important limitation")


def main() -> None:
    model = create_chat_model(load_settings())
    structured_model = model.with_structured_output(ConceptExplanation)
    result = structured_model.invoke("Explique le RAG a un Data Scientist junior.")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
