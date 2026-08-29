# Corrections - Module 06

## Exercice 1

Le script construit un petit dataset en memoire, lance une target function et transforme
`audit_trail` en trace locale. Les scores indiquent si la route, le topic, les citations et le
contrat de sortie respectent la reference.

## Exercice 2

`inputs` contient ce que l'application recoit. `outputs` contient ce qui est attendu. `metadata`
sert a filtrer et analyser les cas : domaine, risque, split, difficulte. Les separer evite de
melanger le signal de test avec le contexte d'analyse.

## Exercice 3

Si le projet est intact, les metriques principales doivent etre a `1.0`. Cela signifie que le
workflow actuel respecte les cas de reference du dataset.

## Exercice 4

`topic_accuracy` baisse. La regression est lisible car le score indique exactement le contrat qui
n'est plus respecte : le workflow classe le cas comme `fraud`, alors que la reference modifiee
attend `claim`.

## Exercice 5

La question porte sur une caracteristique sensible. Une bonne reference attend normalement
`topic="fraud"` ou une route de revue humaine, avec `fraud-review-policy.md` comme preuve
retrouvee, car le corpus indique que ces caracteristiques sont exclues du modele.

## Exercice 6

L'export reprend les `inputs`, `outputs` et `metadata` dans une forme prete pour
`Client.create_examples`. Ajouter `example_id` dans `metadata` permet de garder un identifiant
stable visible meme si l'outil d'import attribue ses propres identifiants internes.

## Exercice 7

Il faut installer l'extra `observability`, configurer les variables LangSmith, creer ou lire le
dataset, definir la target function et passer les evaluateurs a `evaluate()` ou au client SDK.

## Corrige du quiz

1. Une trace conserve une structure d'execution : etapes, entrees, sorties, erreurs, durees et relations parent-enfant.
2. Pour rejouer les memes cas et comparer les versions de maniere stable.
3. Les donnees donnees a l'application, par exemple `{"question": "..."}`.
4. La reference attendue ou les criteres qui permettent d'evaluer la sortie.
5. Executer l'application sur les inputs du dataset et retourner un dictionnaire de sortie.
6. Ils sont rapides, gratuits, reproductibles et adaptes aux contrats critiques.
7. Offline avant de deployer sur des cas controles ; online en production sur des interactions reelles.
8. Pour que le probleme ne revienne pas silencieusement dans une version future.
9. Pour filtrer, segmenter et expliquer les resultats par domaine, risque ou difficulte.
10. Parce qu'un juge LLM reste probabiliste ; il complete les tests mais ne garantit pas les contrats.
