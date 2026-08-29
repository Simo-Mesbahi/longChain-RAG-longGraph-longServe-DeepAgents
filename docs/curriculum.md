# Programme complet

## Bloc 1 - Fondations

### Module 00 : Python et LLM

Messages, roles, tokens, temperature, contexte, hallucinations, cout, latence, secrets et premiere invocation.

### Module 01 : LangChain

Modeles, prompts, messages, LCEL, runnables, configuration et composition d'une premiere chaine.

### Module 02 : Sorties structurees et outils

Schemas Pydantic, validation, tool calling, erreurs, retries, timeouts et idempotence.

## Bloc 2 - RAG

### Module 03 : Fondamentaux RAG

Ingestion, parsing, chunking, embeddings, indexation, retrieval, generation et citations.

### Module 04 : RAG avance

Predictions sauvegardees, evaluation separee du retrieval et de la generation, correction,
fidelite, completude, refus de repondre, comparaison de configurations et juge LLM optionnel.

## Bloc 3 - Orchestration

### Module 05 : LangGraph

Etat, noeuds, aretes, routage conditionnel, checkpointers, interruptions, reprise avec
`Command(resume=...)` et validation humaine.

### Module 06 : LangSmith

Traces, runs, projets, datasets, target functions, evaluateurs de code, evaluations offline et
online, monitoring et transformation des echecs en tests de regression.

## Bloc 4 - Agents avances

### Module 07 : Deep Agents

Deep Agents comme harness au-dessus de LangGraph, planification explicite, sous-agents,
offloading du contexte dans des fichiers, permissions `allow`/`deny`/`interrupt`, backends,
memoire long terme, skills, quality gate et observabilite LangSmith.

Livrables :

- cours complet `course/07-deep-agents` ;
- exemples de planification, permissions et template SDK ;
- projet `Deep Agent Investigation Analyst` sans cle API ;
- tests de permissions, routage, memoire et contrats de publication.

### Module 08 : Production

Contrats API, healthchecks, readiness probes, authentification, secrets, timeouts, rate limits,
observabilite, datasets d'evaluation, rollback, Docker, manifest de deploiement et migration des
anciens projets LangServe vers des APIs typees ou LangGraph/LangSmith Deployment.

Livrables :

- cours complet `course/08-production-and-langserve-migration` ;
- helpers `production_readiness` ;
- projet `Production Readiness and LangServe Migration` ;
- Dockerfile, `render.yaml`, `langgraph.json` et API optionnelle.

### Module 09 : Projet final

Assistant d'investigation documentaire en assurance avec preuves, routage, validation humaine, traces et evaluations.

## Evaluation

Chaque bloc combine :

- questions de comprehension ;
- exercices de code ;
- tests automatises ;
- revue d'architecture ;
- mini-projet documente.
