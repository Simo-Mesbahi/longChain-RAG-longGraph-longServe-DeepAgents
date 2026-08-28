# Corrections - Module 04

## Exercice 1

Hit Rate@k, Recall@k et MRR disent si les bonnes sources arrivent dans le contexte. Les metriques
de generation disent si la reponse finale choisit correctement de repondre, cite les bonnes
sources et ressemble a la reference attendue.

## Exercice 2

Une source citee mais non attendue declenche `citation_outside_expected_sources` sur une question
repondable. `citation_precision` baisse, car une partie des sources citees ne correspond pas au
jeu de reference.

## Exercice 3

Un faux refus evite une hallucination, mais il echoue quand meme : l'information existe dans le
corpus et l'utilisateur ne l'obtient pas. Il faut donc mesurer les refus, pas seulement les
reponses inventees.

## Exercice 4

Une configuration plus large peut ameliorer le recall mais ajouter du bruit. Une configuration
plus precise peut mieux classer le premier resultat mais manquer une source utile. La decision
doit s'appuyer sur les cas qui regressent, pas seulement sur la meilleure moyenne.

## Exercice 5

Une bonne fiche relie un symptome a une hypothese testable. Exemple : si la source attendue est
absente du top-k, tester un autre chunking ou un autre `k`. Si elle est presente mais non citee,
tester le prompt, le schema de sortie ou la validation des citations.

## Exercice 6

Un juge LLM peut detecter une paraphrase correcte avec peu de mots communs, ou au contraire une
phrase lexicalement proche mais non fidele aux preuves. Il doit toutefois etre calibre, car il
peut varier et produire ses propres erreurs.

## Corrige du quiz

1. Pour savoir si l'echec vient de la recherche ou de la synthese.
2. La capacite du systeme a repondre aux questions repondables et a refuser les questions hors corpus.
3. Pour comparer des runs sans relancer un modele non deterministe et potentiellement payant.
4. La precision verifie la purete des sources citees ; le recall verifie si toutes les sources attendues sont citees.
5. Il ne comprend pas les synonymes, les paraphrases complexes ni la fidelite aux preuves.
6. Une question dont la reponse n'est pas presente dans le corpus indexe.
7. Parce que c'est aussi un modele probabiliste, sensible au prompt, au contexte et a la version.
8. Plus de bruit, plus de cout et plus de contradictions possibles dans le contexte.
9. Des faux refus, car des passages utiles peuvent etre filtres.
10. Quand les bonnes preuves sont deja dans le contexte mais que la reponse les utilise mal.
