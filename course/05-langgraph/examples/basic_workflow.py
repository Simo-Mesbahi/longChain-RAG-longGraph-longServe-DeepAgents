"""Run the LangGraph investigation workflow on one local question."""

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
                chunk_id="home-policy.md#chunk-000",
                source="home-policy.md",
                content="La franchise degat des eaux est fixee a 180 euros par sinistre.",
            )
        ]
    )
    graph = build_investigation_graph(
        store,
        policy=InvestigationPolicy(k=2, min_score=0.2, review_score=0.8),
    )
    state = graph.invoke({"question": "Quelle est la franchise degat des eaux ?"})
    print(state_to_report(state).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
