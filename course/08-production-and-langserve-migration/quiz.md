# Quiz - Module 08

## Questions

1. Pourquoi LangServe ne doit-il plus etre le choix par defaut pour un nouveau projet ?
   - A. Parce qu'il ne peut pas servir de code Python.
   - B. Parce qu'il est deprecie et n'accepte plus de nouvelles fonctionnalites majeures.
   - C. Parce qu'il interdit les endpoints HTTP.
   - D. Parce qu'il remplace LangSmith.

2. Quelle difference principale existe entre `/health` et `/ready` ?
   - A. `/health` dit si le processus vit, `/ready` dit s'il peut recevoir du trafic.
   - B. `/health` sert aux utilisateurs, `/ready` sert aux prompts.
   - C. `/ready` est toujours authentifie.
   - D. Ils doivent toujours retourner des schemas differents.

3. Quel endpoint doit etre protege par authentification ?
   - A. `GET /health`
   - B. `GET /ready`
   - C. `POST /investigate`
   - D. Aucun endpoint.

4. Quel est le bon usage d'un rollback ?
   - A. Effacer l'historique Git.
   - B. Revenir a une version saine quand la nouvelle release degrade le service.
   - C. Supprimer les tests.
   - D. Changer les prompts sans tracer.

5. Quel signal est le plus utile pour une evaluation metier RAG ?
   - A. Nombre de lignes de code.
   - B. Precision des citations et refus quand les preuves manquent.
   - C. Couleur de l'interface.
   - D. Nom du modele uniquement.

6. Quelle cible est naturelle pour un agent LangGraph stateful en production ?
   - A. Un notebook local uniquement.
   - B. LangSmith Deployment ou une infra compatible LangGraph.
   - C. Un fichier CSV.
   - D. Un README.

7. Pourquoi remplacer `RemoteRunnable` cote client ?
   - A. Pour rendre les contrats clients explicites et eviter une surface legacy.
   - B. Pour supprimer l'API.
   - C. Pour enlever la validation.
   - D. Pour empecher le monitoring.

8. Quel fichier rend une application LangGraph deployable avec le CLI LangGraph ?
   - A. `README.md`
   - B. `langgraph.json`
   - C. `.gitignore`
   - D. `LICENSE`

## Reponses courtes

9. Donnez trois checks bloquants avant production.

10. Expliquez pourquoi un endpoint LLM couteux doit etre rate limited.

Les corrections sont dans `solutions.md`.
