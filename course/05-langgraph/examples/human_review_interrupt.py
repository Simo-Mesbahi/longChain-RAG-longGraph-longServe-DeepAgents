"""Pause and resume a LangGraph workflow with human review."""

from langgraph.types import Command

from ai_course.investigation_graph import (
    EvidenceChunk,
    InvestigationPolicy,
    StaticEvidenceStore,
    build_investigation_graph,
    state_to_report,
)


def main() -> int:
    store = StaticEvidenceStore(
        [
            EvidenceChunk(
                chunk_id="fraud.md#chunk-000",
                source="fraud.md",
                content="Un score eleve ne prouve pas une fraude et impose une analyse humaine.",
            )
        ]
    )
    graph = build_investigation_graph(
        store,
        policy=InvestigationPolicy(min_score=0.2, review_score=0.9),
        interactive_review=True,
    )
    config = {"configurable": {"thread_id": "demo-human-review"}}

    paused = graph.invoke(
        {"question": "Un score de risque prouve-t-il une fraude ?"},
        config,
    )
    print(paused["__interrupt__"][0].value)

    resumed = graph.invoke(
        Command(
            resume={
                "approved": True,
                "notes": "Validation humaine pedagogique.",
                "replacement_answer": "Non, un score sert a prioriser et ne prouve pas une fraude.",
            }
        ),
        config,
    )
    print(state_to_report(resumed).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
