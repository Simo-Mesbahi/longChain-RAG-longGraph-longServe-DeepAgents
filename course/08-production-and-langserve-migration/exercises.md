# Exercices - Module 08

Ces exercices transforment un prototype LLM en service exploitable : contrat API, readiness,
secrets, monitoring, migration LangServe et rollback.

## Exercice 1 - Lire un rapport de readiness

Lancez :

```bash
python course/08-production-and-langserve-migration/examples/readiness_demo.py
```

Questions :

1. Quel est le score de readiness ?
2. Quels checks seraient bloquants en production ?
3. Pourquoi `/health` et `/ready` sont-ils separes ?

## Exercice 2 - Simuler un secret manquant

Lancez :

```bash
python projects/06-production-readiness-and-migration/app.py readiness --missing-secret
```

Expliquez pourquoi le service doit etre bloque en environnement `production`, mais seulement
marque `needs_work` en environnement `local`.

## Exercice 3 - Proteger une route mutante

Dans un test, creez un endpoint `POST /investigate` avec `auth_required=False`.

Attendu :

- le rapport est `blocked` ;
- le check `auth_for_mutations` echoue ;
- la remediation explique qu'il faut une authentification.

## Exercice 4 - Inventorier une API LangServe legacy

Ajoutez une route legacy :

```python
LangServeRoute(
    path="/legacy-chat",
    runnable_name="chat_chain",
    exposes_playground=True,
    uses_remote_runnable=True,
)
```

Puis relancez :

```bash
python course/08-production-and-langserve-migration/examples/migration_plan_demo.py
```

Verifiez que la nouvelle route apparait dans les etapes de migration.

## Exercice 5 - Construire un manifest Docker

Lancez :

```bash
python course/08-production-and-langserve-migration/examples/deployment_manifest_demo.py
```

Verifiez :

- la commande de demarrage ;
- les variables d'environnement ;
- les secrets ;
- les chemins de probes.

## Exercice 6 - Rediger une procedure de rollback

Redigez une procedure de rollback courte :

- version courante ;
- derniere version saine ;
- commande de retour arriere ;
- controle `/health` ;
- controle metier avec une question RAG connue.

## Criteres de reussite

Votre module production est acceptable si :

- les contrats API sont explicites ;
- les secrets ne sont pas dans Git ;
- les tests, docs et CI sont verts ;
- les decisions sensibles gardent une validation humaine ;
- la migration LangServe est reversible ;
- les endpoints de production ont des probes et du monitoring.
