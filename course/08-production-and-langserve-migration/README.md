# Module 08 - Production et migration LangServe

> Statut : disponible.

Un prototype LLM peut impressionner en demo et casser tres vite en conditions reelles. La
production demande autre chose : contrats stables, validation, secrets, probes, logs, limites de
debit, evaluation, rollback et suivi des couts. Ce module transforme les briques precedentes en
service exploitable.

Il traite aussi LangServe avec precision : LangServe reste utile pour comprendre l'histoire de
l'ecosysteme LangChain, mais il est deprecie pour les nouveaux projets. Le chemin moderne consiste
a exposer des APIs typees pour les chaines simples et a deployer les workflows stateful via
LangGraph/LangSmith Deployment ou une infrastructure compatible.

## Objectifs pedagogiques

A la fin du module, vous saurez :

- definir un contrat API pour une application RAG/agent ;
- separer `/health` et `/ready` ;
- proteger les endpoints couteux ou sensibles ;
- limiter taille d'entree, timeout, concurrence et debit ;
- documenter les secrets sans les exposer ;
- evaluer une release avant production ;
- construire un plan de migration depuis LangServe ;
- preparer un deploiement Docker ou LangGraph/LangSmith ;
- expliquer une strategie de rollback.

## Pourquoi la production est differente

En local, on teste souvent le chemin heureux. En production, le systeme doit aussi gerer :

| Risque | Exemple | Protection |
|---|---|---|
| Hallucination | Reponse sans preuve | citations + refus + quality gate |
| Couts | Trop de requetes longues | rate limit + timeout + quotas |
| Securite | Endpoint public non protege | auth + gestion des secrets |
| Donnees | Fuite dans logs ou traces | filtrage + retention controlee |
| Regression | Nouveau prompt moins fiable | dataset + CI + dual-run |
| Incident | Release mauvaise | rollback documente |

## Contrat API minimal

Une plateforme d'investigation documentaire doit exposer peu de routes, mais bien les exposer.

| Method | Path | Role | Auth |
|---|---|---|:---:|
| GET | `/health` | Verifier que le processus repond | Non |
| GET | `/ready` | Verifier que le service peut recevoir du trafic | Non |
| POST | `/investigate` | Lancer RAG, LangGraph ou Deep Agent | Oui |
| POST | `/feedback` | Stocker retour humain/evaluation | Oui |
| GET | `/metrics` | Exposer metriques techniques et qualite | Oui |

`/health` et `/ready` ne disent pas la meme chose :

- `/health` : le processus vit ;
- `/ready` : le service a ses dependances et peut recevoir du trafic.

## Readiness score

Le module ajoute `src/ai_course/production_readiness.py`, qui produit un rapport de readiness.

Checks couverts :

- chemins API essentiels ;
- authentification des endpoints mutatifs ;
- rate limits ;
- CI ;
- tests ;
- documentation ;
- observabilite ;
- validation humaine ;
- secrets hors Git ;
- procedure de rollback ;
- dataset d'evaluation ;
- revue securite ;
- cible de deploiement.

Executer :

```bash
python course/08-production-and-langserve-migration/examples/readiness_demo.py
```

## Secrets et configuration

Les secrets ne doivent jamais etre dans Git. Le depot fournit seulement `.env.example`.

Variables typiques :

| Variable | Type | Exemple |
|---|---|---|
| `ENVIRONMENT` | config | `production` |
| `MODEL_PROVIDER` | config | `openai` |
| `MODEL_NAME` | config | `gpt-4.1-mini` |
| `OPENAI_API_KEY` | secret | configure dans l'hebergeur |
| `LANGSMITH_API_KEY` | secret | configure dans l'hebergeur |
| `ASTERIA_API_TOKEN` | secret | token d'appel API |

Une production sans secrets configures doit etre bloquee. En local, cela peut etre seulement un
etat `needs_work` si le projet utilise des mocks ou des embeddings deterministes.

## Observabilite

Une application LLM doit etre observable a deux niveaux :

| Niveau | Questions |
|---|---|
| Technique | latence, erreurs, timeouts, debit, cout |
| Metier | citations correctes, refus corrects, revue humaine, derive qualite |

LangSmith est naturel dans ce parcours parce que les modules precedents produisent deja des traces,
datasets et evaluateurs.

## Migration depuis LangServe

LangServe servait a exposer rapidement des `Runnable` via FastAPI. Pour les nouveaux projets, la
recommandation actuelle est de ne pas en faire la cible principale. La migration ne doit pas etre
un simple remplacement de dependance : elle doit stabiliser le contrat produit.

Plan recommande :

1. inventorier les routes `add_routes` et les clients `RemoteRunnable` ;
2. figer les schemas d'entree/sortie ;
3. separer les chaines LCEL simples des agents stateful ;
4. remplacer les clients legacy par clients HTTP types ou SDK LangGraph ;
5. executer old/new en parallele sur un dataset ;
6. basculer progressivement avec rollback.

Executer :

```bash
python course/08-production-and-langserve-migration/examples/migration_plan_demo.py
```

## Deploiement

Le projet du module contient trois artefacts utiles :

```text
projects/06-production-readiness-and-migration/Dockerfile
projects/06-production-readiness-and-migration/render.yaml
projects/06-production-readiness-and-migration/langgraph.json
```

Le fichier `langgraph.json` montre comment exporter un graphe deployable. C'est le point d'entree
attendu par les workflows LangGraph/LangSmith Deployment.

Executer le manifest :

```bash
python course/08-production-and-langserve-migration/examples/deployment_manifest_demo.py
```

## Projet du module

Le projet pratique est :

```text
projects/06-production-readiness-and-migration
```

Commandes principales :

```bash
python projects/06-production-readiness-and-migration/app.py readiness
python projects/06-production-readiness-and-migration/app.py migration-plan
python projects/06-production-readiness-and-migration/app.py manifest
python projects/06-production-readiness-and-migration/app.py health
```

API optionnelle :

```bash
pip install -e ".[rag,api]"
uvicorn api:app --app-dir projects/06-production-readiness-and-migration --host 0.0.0.0 --port 8000
```

## Tests metier production

Avant une release, lancez :

```bash
ruff check .
ruff format --check .
pytest
mkdocs build --strict
python projects/06-production-readiness-and-migration/app.py readiness
```

Puis testez trois questions :

| Scenario | Question | Attendu |
|---|---|---|
| Reponse citee | `Quelle est la franchise degat des eaux ?` | reponse avec citation |
| Delai sinistre | `Quel est le delai pour declarer un vol ?` | reponse avec source dossier |
| Non couvert | `Quel remboursement existe pour une couronne dentaire ?` | refus ou revue humaine |

## Definition of Done production

Une release est acceptable si :

- CI verte ;
- docs construites en strict ;
- endpoints documentes ;
- secrets hors Git ;
- probes configurees ;
- route sensible avec validation humaine ;
- traces et metriques disponibles ;
- dataset d'evaluation pret ;
- rollback decrit ;
- ancienne surface LangServe migree ou isolee.

## References officielles

- [LangServe GitHub](https://github.com/langchain-ai/langserve)
- [LangGraph deployment](https://docs.langchain.com/oss/python/langgraph/deploy)
- [LangSmith Deployment](https://docs.langchain.com/langsmith/deployment)
- [LangSmith Cloud deploy quickstart](https://docs.langchain.com/langsmith/deployment-quickstart)
- [LangGraph v1 migration guide](https://docs.langchain.com/oss/python/migrate/langgraph-v1)
- [LangChain release policy](https://docs.langchain.com/oss/python/release-policy)
