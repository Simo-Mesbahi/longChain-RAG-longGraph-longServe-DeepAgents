# Projets pratiques

Les projets transforment chaque bloc theorique en livrable testable et presentable. Les donnees
de demonstration sont synthetiques afin de pouvoir publier et reutiliser le depot sans exposer
d'informations personnelles.

## 01 - Insurance Claim Intake

Une declaration libre est transformee en objet Pydantic valide. Le service gere les timeouts,
les erreurs transitoires, les retries limites et les dossiers incomplets a revoir humainement.

Competences : structured output, validation, async, resilience et tests sans API.

[Ouvrir le projet sur GitHub](https://github.com/Simo-Mesbahi/longChain-RAG-longGraph-longServe-DeepAgents/tree/main/projects/01-insurance-claim-intake)

## 02 - Documentary RAG Assistant

Un corpus fictif d'assurance est charge, decoupe et stocke dans un index Chroma persistant. Le
pipeline recherche les preuves, impose des citations valides et mesure separement la qualite du
retrieval sur un dataset JSONL.

Competences : ingestion, embeddings, vector store, citations, refus, Hit Rate@k, Recall@k et MRR.

[Ouvrir le projet sur GitHub](https://github.com/Simo-Mesbahi/longChain-RAG-longGraph-longServe-DeepAgents/tree/main/projects/02-documentary-rag-assistant)

## Suite du fil rouge

Les prochains projets reutiliseront ces composants dans un workflow LangGraph, ajouteront une
validation humaine et des traces LangSmith, puis aboutiront a un assistant d'investigation
documentaire deployable.
