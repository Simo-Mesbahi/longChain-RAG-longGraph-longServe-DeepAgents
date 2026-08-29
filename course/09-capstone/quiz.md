# Quiz - Module 09

## Questions

1. Pourquoi placer `capstone_platform.py` entre FastAPI et les moteurs ?
   - A. Pour rendre FastAPI obligatoire dans tous les tests.
   - B. Pour isoler les contrats et regles metier de la surface web.
   - C. Pour supprimer Pydantic.
   - D. Pour eviter toute CLI.

2. Quand le routeur choisit-il RAG par defaut ?
   - A. Pour une question factuelle ciblee et non sensible.
   - B. Pour toute decision de fraude.
   - C. Pour une investigation longue multi-etapes.
   - D. Uniquement quand LangGraph echoue.

3. Quelle information prouve qu'une citation est valide ?
   - A. Son texte est long.
   - B. Son `chunk_id` appartient aux preuves recuperees.
   - C. Elle contient le nom du modele.
   - D. Elle est affichee en couleur.

4. Pourquoi une question hors corpus peut-elle etre un test positif ?
   - A. Elle verifie que le systeme sait ne pas inventer.
   - B. Elle augmente toujours la precision.
   - C. Elle supprime le besoin d'evaluation.
   - D. Elle doit toujours produire une citation.

5. Quel comportement est attendu pour un score de fraude ?
   - A. Refus automatique du dossier.
   - B. Decision automatique si le score depasse 90 %.
   - C. Priorisation et validation humaine, jamais preuve unique.
   - D. Suppression du journal d'audit.

6. Que signifie `release_gate_passed` ?
   - A. L'interface s'est ouverte une fois.
   - B. Tous les scenarios et leurs assertions ont reussi.
   - C. Le modele a repondu rapidement.
   - D. Docker est installe sur le poste.

7. Pourquoi le rate limiter en memoire a-t-il une limite en production ?
   - A. Il ne sait pas compter.
   - B. Son etat n'est pas partage entre plusieurs instances.
   - C. Il oblige a utiliser LangServe.
   - D. Il rend l'API synchrone.

8. Quel fichier exporte le graphe vers le runtime LangGraph ?
   - A. `styles.css`
   - B. `langgraph.json`
   - C. `render.yaml`
   - D. `.env.example`

9. Pourquoi utiliser `textContent` pour afficher une reponse ?
   - A. Pour executer le HTML retourne par le modele.
   - B. Pour afficher le texte sans l'interpreter comme du code HTML.
   - C. Pour remplacer les tests API.
   - D. Pour compresser la reponse.

10. Quel signal doit bloquer une release ?
    - A. Une question couverte sans citation.
    - B. Un nom de fichier court.
    - C. Une interface sombre.
    - D. Une latence locale de quelques millisecondes.

## Reponses courtes

11. Donnez quatre champs utiles de `CapstoneResponse` pour un audit.

12. Expliquez la difference entre un test unitaire et un scenario d'acceptation metier dans ce
projet.

Les corrections sont dans `solutions.md`.
