# Corrections - Module 05

## Exercice 1

`audit_trail` montre le chemin reel suivi par le graphe. Il aide a distinguer l'analyse, le
retrieval, la verification, puis la reponse ou la revue humaine.

## Exercice 2

Un `review_score` plus eleve rend la revue humaine plus probable sur les questions sensibles. Ce
choix est dans le code car il represente une politique de risque testable et auditable.

## Exercice 3

Une question hors corpus ne doit pas produire une reponse inventee. Par defaut, le workflow passe
en revue humaine lorsque les preuves sont insuffisantes.

## Exercice 4

Avec `--no-human-review-on-missing`, le graphe refuse directement. Les deux comportements sont
acceptables selon le produit, mais ils doivent etre explicites et mesures.

## Exercice 5

Le `thread_id` identifie la conversation ou le dossier dont les checkpoints doivent etre repris.
Sans lui, le graphe ne sait pas quel etat interrompu doit continuer.

## Exercice 6

Le noeud doit rester petit : lire la question, detecter les termes sensibles, retourner une mise
a jour d'etat. Le routeur ou `verify_evidence` peut ensuite utiliser ce champ.

## Exercice 7

Tester le routeur seul permet de verifier la politique de transition sans relancer tout le
workflow. C'est utile lorsque les graphes grandissent.

## Corrige du quiz

1. LangChain compose des briques LLM ; LangGraph orchestre des workflows stateful.
2. Les donnees partagees par les noeuds : question, preuves, statut, reponse, audit, etc.
3. Non. Un noeud peut etre du code deterministe, un retriever, un outil ou un appel LLM.
4. Choisir le prochain noeud selon l'etat courant.
5. Pour tracer le chemin execute et analyser les erreurs.
6. A sauvegarder l'etat du graphe entre les etapes.
7. Pour associer les checkpoints a un thread precis.
8. Il met le graphe en pause et expose une demande au caller.
9. Avec `Command(resume=...)` et la meme configuration de thread.
10. Parce qu'elles doivent etre reproductibles, testables et auditables.
