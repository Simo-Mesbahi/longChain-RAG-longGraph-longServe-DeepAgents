"""Small, reusable LangChain building blocks for the first lessons."""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ai_course.settings import Settings


def build_teaching_prompt() -> ChatPromptTemplate:
    """Return a prompt that teaches one concept at a requested level."""
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Tu es un formateur en intelligence artificielle. "
                "Tu expliques avec precision, sans jargon inutile, et tu signales les limites.",
            ),
            (
                "human",
                "Explique le concept '{concept}' pour un niveau {level}. "
                "Donne une definition, un exemple et une erreur frequente.",
            ),
        ]
    )


def create_chat_model(
    settings: Settings,
    *,
    timeout: float = 30.0,
    max_retries: int = 3,
) -> BaseChatModel:
    """Create the configured chat model using LangChain's provider abstraction."""
    return init_chat_model(
        model=settings.model_name,
        model_provider=settings.model_provider,
        temperature=0,
        timeout=timeout,
        max_retries=max_retries,
    )


def build_teaching_chain(model: BaseChatModel) -> Runnable:
    """Compose the teaching prompt and chat model with LCEL."""
    return build_teaching_prompt() | model
