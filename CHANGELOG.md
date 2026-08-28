# Changelog

Toutes les modifications notables du projet sont documentees ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet utilise le versionnage semantique.

## [Unreleased]

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
- Configuration Python, Ruff, Pytest et GitHub Actions.
- Documentation de contribution, securite et feuille de route.
