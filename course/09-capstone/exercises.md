# Exercices - Module 09

Ces exercices conduisent du contrat applicatif a une release complete. Ils utilisent le corpus
synthetique du projet 02 et ne demandent aucune cle API.

## Exercice 1 - Comparer les moteurs

Executez la meme question dans les quatre modes :

```bash
python projects/07-asteria-investigation-platform/app.py ask \
  "Quelles pieces faut-il fournir pour un degat des eaux ?" --mode auto
```

Remplacez ensuite `auto` par `rag`, `graph` et `deep_agent`.

Comparez :

- le moteur utilise ;
- le nombre de taches ;
- l'audit trail ;
- les fichiers produits ;
- la latence.

## Exercice 2 - Tester une question hors corpus

Posez :

```text
Quel remboursement existe pour une couronne dentaire ?
```

Verifiez que :

- `answered` vaut `false` ;
- aucune citation n'est retournee ;
- `needs_human_review` vaut `true` avec la configuration par defaut ;
- tous les business checks passent.

Relancez avec `--no-review` et expliquez la difference entre revue et refus.

## Exercice 3 - Ajouter un scenario metier

Creez un `BusinessScenario` sur le delai de declaration d'un vol.

Attendu :

- mode RAG ;
- reponse produite ;
- source `claim-handling-procedure.md` ;
- aucun besoin de revue humaine.

Passez ce scenario a `run_acceptance_suite` et ajoutez un test Pytest.

## Exercice 4 - Provoquer un release gate rouge

Modifiez uniquement l'attente de votre scenario pour demander le mauvais moteur. Le code applicatif
ne doit pas etre modifie.

Verifiez :

- `release_gate_passed == false` ;
- `failed == 1` ;
- l'assertion `mode` explique l'echec.

## Exercice 5 - Tester l'API

Demarrez le serveur puis appelez :

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl http://127.0.0.1:8000/api/v1/platform
```

Configurez ensuite `ASTERIA_API_TOKEN` et verifiez qu'un `POST /api/v1/investigations` sans token
retourne `401`, tandis qu'un Bearer token valide autorise l'execution.

## Exercice 6 - Examiner la securite frontend

Dans `frontend/assets/app.js`, identifiez comment les reponses sont ajoutees au DOM.

Expliquez pourquoi `textContent` est prefere a `innerHTML` pour :

- la question ;
- la reponse ;
- les passages de preuve ;
- les evenements d'audit.

## Exercice 7 - Ajouter un invariant metier

Ajoutez un check `bounded-evidence` qui echoue si plus de quatre passages sont exposes dans une
reponse publique.

Le check doit :

- etre ajoute dans `evaluate_business_checks` ;
- posseder un identifiant stable ;
- expliquer le succes et l'echec ;
- etre couvert par un test.

## Exercice 8 - Preparer une release

Executez :

```bash
ruff check .
ruff format --check .
pytest
mkdocs build --strict
python projects/07-asteria-investigation-platform/app.py evaluate
python projects/07-asteria-investigation-platform/app.py readiness
```

Redigez ensuite une note de release contenant : version, commit, tests, pass rate, changement
fonctionnel, risque principal et commande de rollback.

## Soutenance

Presentez le projet en dix minutes :

1. probleme metier et limites ;
2. contrat public ;
3. routeur ;
4. demonstration des trois moteurs ;
5. question hors corpus ;
6. fraude et validation humaine ;
7. release gate ;
8. architecture de deploiement.

Une bonne soutenance montre aussi un echec controle, pas seulement le chemin heureux.
