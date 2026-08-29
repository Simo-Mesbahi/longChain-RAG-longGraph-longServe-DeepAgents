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
retrieval et de la generation sur des artefacts JSONL.

Competences : ingestion, embeddings, vector store, citations, refus, Hit Rate@k, Recall@k, MRR,
answerability, precision/recall des citations et juge LLM optionnel.

[Ouvrir le projet sur GitHub](https://github.com/Simo-Mesbahi/longChain-RAG-longGraph-longServe-DeepAgents/tree/main/projects/02-documentary-rag-assistant)

## 03 - LangGraph Investigation Workflow

Le corpus documentaire est orchestre par un graphe d'etat : analyse de la question, retrieval,
verification des preuves, reponse citee, refus ou revue humaine.

Competences : LangGraph, StateGraph, routing conditionnel, checkpointer, interruption,
human-in-the-loop et audit trail.

[Ouvrir le projet sur GitHub](https://github.com/Simo-Mesbahi/longChain-RAG-longGraph-longServe-DeepAgents/tree/main/projects/03-langgraph-investigation-workflow)

## 04 - LangSmith Quality Monitoring

Le workflow LangGraph est evalue comme une cible LangSmith : dataset `inputs`/`outputs`/`metadata`,
runs locaux, traces derivees de l'audit trail, evaluateurs deterministes et export compatible
avec `Client.create_examples`.

Competences : observabilite, traces, datasets, target function, evaluateurs offline, monitoring
qualite, export LangSmith et tests de regression.

[Ouvrir le projet sur GitHub](https://github.com/Simo-Mesbahi/longChain-RAG-longGraph-longServe-DeepAgents/tree/main/projects/04-langsmith-quality-monitoring)

## 05 - Deep Agent Investigation Analyst

Le workflow documentaire devient un agent long : planification, sous-agents specialises,
fichiers intermediaires, permissions, memoire long terme et quality gate final. Le projet reste
deterministe afin d'etre execute en CI sans cle API.

Competences : Deep Agents, planning, context offloading, permissions, memoire, subagents,
quality gate, audit trail et passage progressif vers le SDK officiel.

[Ouvrir le projet sur GitHub](https://github.com/Simo-Mesbahi/longChain-RAG-longGraph-longServe-DeepAgents/tree/main/projects/05-deep-agent-investigation-analyst)

## Suite du fil rouge

Les prochains projets ajoutent la couche production, l'API, les controles d'exploitation et la
migration depuis les anciens projets LangServe, puis aboutissent a un assistant d'investigation
documentaire deployable.
