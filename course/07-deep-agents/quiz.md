# Quiz - Module 07

## Questions

1. Quel probleme principal resout un Deep Agent par rapport a un agent simple ?
   - A. Il supprime le besoin de tests.
   - B. Il organise les taches longues avec planification, fichiers et delegation.
   - C. Il rend les embeddings inutiles.
   - D. Il empeche tout appel d'outil.

2. Pourquoi ecrire les resultats volumineux dans des fichiers ?
   - A. Pour reduire le contexte renvoye au fil principal.
   - B. Pour contourner les tests.
   - C. Pour rendre les citations optionnelles.
   - D. Pour eviter LangGraph.

3. Dans le modele de permissions du module, que signifie `interrupt` ?
   - A. Operation toujours autorisee.
   - B. Operation toujours refusee.
   - C. Operation demandant une validation humaine.
   - D. Operation ignoree silencieusement.

4. Quelle regle gagne si deux permissions matchent le meme chemin ?
   - A. La derniere.
   - B. La premiere.
   - C. La plus longue.
   - D. La plus permissive.

5. Quel sous-agent doit choisir entre reponse, refus et revue humaine ?
   - A. `planner`
   - B. `researcher`
   - C. `verifier`
   - D. `writer`

6. Pourquoi un quality gate est-il utile ?
   - A. Pour rendre l'agent plus creatif.
   - B. Pour verifier les contrats avant de retourner la sortie.
   - C. Pour remplacer les permissions.
   - D. Pour supprimer l'audit trail.

7. Quelle information ne doit pas etre accessible par defaut ?
   - A. `/workspace/plan.json`
   - B. `/reports/investigation_report.md`
   - C. `/.env`
   - D. `/workspace/evidence.json`

8. Quel outil d'observabilite est naturel pour evaluer un Deep Agent LangChain ?
   - A. LangSmith
   - B. pip
   - C. venv
   - D. pathlib

## Reponses courtes

9. Donnez un exemple de fait acceptable en memoire long terme.

10. Expliquez pourquoi un sous-agent doit retourner un resume plutot que tout son contexte.

Les corrections sont dans `solutions.md`.
