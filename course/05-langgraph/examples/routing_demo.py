"""Show how different questions take different LangGraph routes."""

from ai_course.investigation_graph import (
    EvidenceChunk,
    InvestigationPolicy,
    StaticEvidenceStore,
    build_investigation_graph,
    state_to_report,
)

QUESTIONS = [
    "Quelle est la franchise degat des eaux ?",
    "Un score de risque prouve-t-il une fraude ?",
    "Quel remboursement existe pour une couronne dentaire ?",
]


def main() -> int:
    store = StaticEvidenceStore(
        [
            EvidenceChunk(
                chunk_id="home.md#chunk-000",
                source="home.md",
                content="La franchise degat des eaux est fixee a 180 euros par sinistre.",
            ),
            EvidenceChunk(
                chunk_id="fraud.md#chunk-000",
                source="fraud.md",
                content="Un score eleve ne prouve pas une fraude et impose une analyse humaine.",
            ),
        ]
    )
    graph = build_investigation_graph(
        store,
        policy=InvestigationPolicy(min_score=0.2, review_score=0.9),
    )

    for question in QUESTIONS:
        report = state_to_report(graph.invoke({"question": question}))
        print(
            {
                "question": question,
                "topic": report.topic,
                "answered": report.answered,
                "needs_human_review": report.needs_human_review,
                "audit_trail": report.audit_trail,
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
