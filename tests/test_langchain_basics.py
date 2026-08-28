from ai_course.langchain_basics import build_teaching_prompt


def test_teaching_prompt_formats_expected_messages() -> None:
    prompt = build_teaching_prompt()

    value = prompt.invoke({"concept": "RAG", "level": "debutant"})

    assert len(value.messages) == 2
    assert "RAG" in value.messages[1].content
    assert "debutant" in value.messages[1].content
    assert "limites" in value.messages[0].content

