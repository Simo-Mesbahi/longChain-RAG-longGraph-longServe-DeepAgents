# Corrections - Module 03

## Exercice 1

Des chunks courts ciblent mieux une information precise, mais perdent plus facilement le contexte. Des chunks longs conservent davantage de contexte, mais ajoutent du bruit et consomment plus de tokens. Le chevauchement protege les frontieres au prix de duplication.

## Exercice 2

`HashingEmbeddings` rapproche surtout les textes qui partagent des tokens. Il peut donc echouer sur des synonymes. Un modele d'embedding entraine apprend des regularites semantiques plus riches.

## Exercice 3

Un `k` eleve peut augmenter le recall, mais aussi introduire des passages non pertinents ou contradictoires. Le modele recoit alors plus de bruit et le cout de generation augmente.

## Exercice 4

Le seuil doit etre calibre sur plusieurs questions positives et negatives. Il faut observer les distributions de scores et mesurer les erreurs, pas optimiser un seul exemple.

## Exercice 5

`answer_question` construit l'ensemble des `chunk_id` reellement recuperes. Toute citation en dehors de cet ensemble provoque une `ValueError`.

## Corrige du quiz

1. Non, il ajoute du contexte au moment de la requete.
2. Pour filtrer, tracer, auditer et citer les sources.
3. Limiter la perte d'information aux frontieres entre chunks.
4. L'un vectorise le corpus, l'autre la requete ; certains modeles les traitent differemment.
5. Le nombre maximal de passages candidats recuperes.
6. Il depend du modele, de la metrique, du vector store et du corpus.
7. Non, la generation peut encore mal interpreter le passage.
8. Pour identifier si l'echec vient de la recherche ou de la synthese.
9. Refuser explicitement de repondre.
10. Pour empecher qu'une source inventee soit presentee comme preuve.

