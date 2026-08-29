# Changelog

Toutes les modifications notables du projet sont documentees ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet utilise le versionnage semantique.

## [Unreleased]

## [1.0.0] - 2026-08-29

### Added

- Structure pedagogique complete du parcours.
- Modules 00 et 01 avec exemples, exercices et corrections.
- Module 02 sur les sorties structurees, Pydantic et le tool calling securise.
- Extracteur type de demandes d'assurance et outil fictif en lecture seule.
- Tests des contraintes metier, schemas d'outils et autorisations d'execution.
- Mini-projet Insurance Claim Intake avec service asynchrone et CLI.
- Timeouts, retries selectifs, backoff exponentiel et statut de revue humaine.
- Module 03 sur le RAG, le chunking, les embeddings et la recherche vectorielle.
- Pipeline de reponse avec refus deterministe et validation stricte des citations.
- Recherche locale reproductible avec embeddings pedagogiques sans cle API.
- Assistant RAG documentaire avec corpus multi-sources et CLI complete.
- Index Chroma persistant, versionne et accompagne d'un manifeste auditable.
- Dataset JSONL et evaluation Hit Rate@k, Recall@k et MRR.
- Verification de la configuration d'embedding et detection des changements du corpus.
- Module 04 sur le RAG avance, les predictions sauvegardees et l'evaluation de generation.
- Metriques deterministes de generation : answerability, precision/recall des citations et F1 lexical.
- Interface de juge LLM structure pour correction, fidelite et completude.
- Commande `evaluate-generation` et predictions exemples pour le projet RAG documentaire.
- Module 05 sur LangGraph : etat, noeuds, aretes, routage, checkpointers et interruptions.
- Workflow d'investigation documentaire LangGraph avec revue humaine et audit trail.
- Module 06 sur LangSmith : traces, datasets, target functions, evaluateurs offline et online.
- Helpers d'evaluation LangSmith-style avec traces locales, metriques de contrat et export SDK.
- Projet LangSmith Quality Monitoring pour evaluer le workflow LangGraph sur un dataset versionne.
- Module 07 sur Deep Agents : planification, sous-agents, fichiers, permissions, memoire et skills.
- Helpers Deep Agents deterministes avec filesystem virtuel, quality gate et memoire long terme.
- Projet Deep Agent Investigation Analyst pour transformer le workflow documentaire en agent long.
- Module 08 sur la production : contrats API, readiness, healthchecks, Docker, rollback et migration LangServe.
- Helpers de readiness production avec checks bloquants, manifest de deploiement et plan de migration.
- Projet Production Readiness and LangServe Migration avec CLI, API FastAPI optionnelle, Dockerfile et `langgraph.json`.
- Module 09 capstone avec cours, exercices, quiz, corrections et exemples executables.
- Moteur Asteria unifie avec contrats Pydantic, routeur RAG/LangGraph/Deep Agent et quality gates.
- Plateforme Asteria Investigation OS avec cockpit responsive, API v1, CLI et export LangGraph.
- Suite d'acceptation metier utilisee comme release gate avant production.
- Docker Compose, blueprint Render, documentation d'architecture et runbook d'exploitation.
- Configuration Python, Ruff, Pytest et GitHub Actions.
- Documentation de contribution, securite et feuille de route.
