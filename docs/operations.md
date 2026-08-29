# Runbook de production

Ce runbook decrit comment valider, demarrer, observer et restaurer la plateforme Asteria.

## Preflight

```bash
ruff check .
ruff format --check .
pytest
mkdocs build --strict
python projects/07-asteria-investigation-platform/app.py evaluate
python projects/07-asteria-investigation-platform/app.py readiness
```

La release est interdite si un test, un scenario metier ou un check bloquant echoue.

## Demarrage

Local :

```bash
python -m pip install -e ".[dev,api]"
python projects/07-asteria-investigation-platform/app.py serve
```

Docker :

```bash
docker compose -f projects/07-asteria-investigation-platform/docker-compose.yml up --build -d
```

## Probes

| Probe | Succes | Echec |
|---|---|---|
| `GET /health` | processus repond, aucun blocage | redemarrer ou inspecter les logs |
| `GET /ready` | `status=ready`, aucun blocage | retirer du trafic et corriger le check |

Une liveness probe ne doit pas lancer un agent, appeler un modele couteux ou verifier tout le
corpus. Une readiness probe peut verifier davantage de dependances, avec un timeout court.

## Verification metier

Apres chaque deploiement :

1. appeler `/health` puis `/ready` ;
2. executer la suite `/api/v1/evaluations` ;
3. poser la question sur la franchise et verifier la citation ;
4. poser la question fraude et verifier la revue humaine ;
5. poser la question dentaire et verifier l'absence de citation.

## Signaux minimum

- debit et taux d'erreur HTTP ;
- p50, p95 et p99 de latence ;
- taux de retrieval vide ;
- taux de reponses avec citations valides ;
- taux d'escalade humaine ;
- pass rate des scenarios metier ;
- cout modele et embeddings si les integrations reelles sont actives.

## Incident

1. retirer la version du trafic si `/ready` est bloque ;
2. conserver logs, trace id, version et question de reproduction ;
3. verifier si le probleme est HTTP, retrieval, routage, moteur ou donnees ;
4. desactiver le moteur concerne ou revenir a la version saine ;
5. transformer l'incident en scenario ou test de regression ;
6. documenter la cause et la correction.

## Rollback

Conserver pour chaque release :

- le tag d'image courant ;
- le dernier tag sain ;
- la commande de redeploiement ;
- le commit Git ;
- le resultat des scenarios metier.

Apres rollback, relancer probes et suite d'acceptation. Un retour arriere technique sans verification
metier n'est pas termine.

## Secrets

`OPENAI_API_KEY`, `LANGSMITH_API_KEY` et `ASTERIA_API_TOKEN` sont configures par l'hebergeur. Toute
valeur publiee doit etre revoquee et remplacee, meme si le commit est supprime ensuite.
