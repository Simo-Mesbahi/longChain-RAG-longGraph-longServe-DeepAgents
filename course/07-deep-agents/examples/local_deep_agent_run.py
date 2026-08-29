"""Run the educational Deep Agent without any external API key."""

from __future__ import annotations

from ai_course.deep_agents import DeepAgentPolicy, run_deep_investigation_agent
from ai_course.investigation_graph import EvidenceChunk, StaticEvidenceStore


def build_store() -> StaticEvidenceStore:
    return StaticEvidenceStore(
        [
            EvidenceChunk(
                chunk_id="home.md#chunk-000",
                source="home.md",
                content="La franchise degat des eaux est fixee a 180 euros par sinistre.",
            ),
            EvidenceChunk(
                chunk_id="claim.md#chunk-000",
                source="claim.md",
                content="Un vol doit etre declare dans les deux jours ouvres.",
            ),
            EvidenceChunk(
                chunk_id="fraud.md#chunk-000",
                source="fraud.md",
                content="Un score eleve ne prouve pas une fraude et impose une analyse humaine.",
            ),
        ]
    )


def main() -> int:
    report = run_deep_investigation_agent(
        "Quelle est la franchise degat des eaux ?",
        build_store(),
        policy=DeepAgentPolicy(k=1, min_score=0.2, review_score=0.9),
    )
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
