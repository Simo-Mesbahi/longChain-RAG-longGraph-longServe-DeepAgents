# Project 06 - Production Readiness and LangServe Migration

Ce projet prepare la future plateforme finale. Il ne se contente pas de lancer un script :
il formalise ce qu'un recruteur ou une equipe production attendent avant d'exposer une application
LLM en ligne.

## Objectif

Verifier que l'assistant d'investigation documentaire peut passer du prototype au service
production :

- contrat API clair ;
- probes `/health` et `/ready` ;
- authentification des routes couteuses ;
- limites de temps, taille et debit ;
- tests et CI ;
- observabilite ;
- validation humaine ;
- rollback ;
- migration depuis LangServe.

## Commandes

Rapport de readiness :

```bash
python projects/06-production-readiness-and-migration/app.py readiness
```

Rapport Markdown :

```bash
python projects/06-production-readiness-and-migration/app.py readiness --format markdown
```

Simuler un secret manquant :

```bash
python projects/06-production-readiness-and-migration/app.py readiness --missing-secret
```

Plan de migration LangServe :

```bash
python projects/06-production-readiness-and-migration/app.py migration-plan
```

Manifest deploiement :

```bash
python projects/06-production-readiness-and-migration/app.py manifest
```

Health payload :

```bash
python projects/06-production-readiness-and-migration/app.py health
```

## API optionnelle

Installer les dependances API :

```bash
pip install -e ".[rag,api]"
```

Lancer l'API :

```bash
uvicorn api:app --app-dir projects/06-production-readiness-and-migration --host 0.0.0.0 --port 8000
```

Endpoints :

| Method | Path | Role |
|---|---|---|
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe |
| POST | `/investigate` | Lance le Deep Agent local |

En production, configurez `ASTERIA_API_TOKEN` et appelez `/investigate` avec :

```text
Authorization: Bearer <token>
```

## Deploiement

Le projet contient :

- `Dockerfile` pour image applicative ;
- `render.yaml` comme exemple de service cloud ;
- `langgraph.json` pour montrer la structure attendue par un deploiement LangGraph/LangSmith ;
- `agent.py` qui exporte un graphe LangGraph local.

## Migration LangServe

La migration suit six etapes :

1. inventorier les routes `add_routes` ;
2. stabiliser les schemas Pydantic ;
3. separer chaines simples et agents stateful ;
4. remplacer les clients `RemoteRunnable` ;
5. executer old/new en parallele sur dataset ;
6. basculer avec rollback.

Le projet suit la recommandation actuelle : ne pas utiliser LangServe pour les nouveaux projets,
et preferer une route FastAPI typee ou un deploiement LangGraph/LangSmith pour les agents longs.

## Tests metier

```bash
python -m pytest tests/test_production_readiness.py
```

Controle attendu :

- service `ready` quand tous les signaux sont presents ;
- service `blocked` si les tests ou secrets production manquent ;
- endpoint `POST /investigate` bloque s'il n'est pas authentifie ;
- plan de migration priorise les routes stateful.
