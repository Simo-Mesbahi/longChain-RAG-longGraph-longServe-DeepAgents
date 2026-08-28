# Exercices - Module 04

## Exercice 1 - Lire un rapport de generation

Executez :

```bash
python projects/02-documentary-rag-assistant/app.py evaluate-generation
```

Relevez :

- `answerability_accuracy` ;
- `citation_precision` ;
- `citation_recall` ;
- `lexical_f1` ;
- les `error_tags` de chaque cas.

Expliquez pourquoi ces metriques ne mesurent pas la meme chose que Hit Rate@k ou MRR.

## Exercice 2 - Creer une mauvaise prediction

Copiez une ligne de `evaluation/sample_predictions.jsonl` dans un fichier temporaire, puis
remplacez une citation attendue par `invented.md`.

Relancez l'evaluation de generation avec :

```bash
python projects/02-documentary-rag-assistant/app.py evaluate-generation \
  --predictions votre_fichier.jsonl
```

Quel `error_tag` apparait ? Quelle metrique baisse ?

## Exercice 3 - Simuler un faux refus

Sur une question repondable, modifiez la prediction pour mettre :

```json
"answered": false
```

et une reponse de refus.

Expliquez pourquoi un faux refus peut etre rassurant en apparence mais mauvais pour
l'utilisateur.

## Exercice 4 - Comparer le retrieval

Executez :

```bash
python course/04-advanced-rag/examples/compare_retrieval_configs.py
```

Comparez les configurations `precise`, `balanced` et `broad`.

Pour chaque configuration, notez :

- le nombre de chunks ;
- Hit Rate@k ;
- Source Recall@k ;
- MRR ;
- le taux de retrieval vide sur les questions hors corpus.

## Exercice 5 - Rediger une fiche d'analyse d'erreur

Choisissez un cas dont le score n'est pas parfait. Redigez une fiche courte :

- question ;
- comportement attendu ;
- comportement observe ;
- composant probablement responsable ;
- changement a tester ;
- metrique qui doit s'ameliorer.

## Exercice 6 - Brancher un juge LLM

Si vous disposez d'une cle API, executez :

```bash
python course/04-advanced-rag/examples/evaluate_with_llm_judge.py
```

Comparez les scores du juge avec les metriques deterministes. Identifiez un cas ou le juge
apporte une information que `lexical_f1` ne voit pas.

Les pistes de correction sont dans [solutions.md](solutions.md).
