# Exercices - Module 06

## Exercice 1 - Lire une trace locale

Executez :

```bash
python course/06-langsmith/examples/local_trace_report.py
```

Identifiez :

- le dataset utilise ;
- la target function ;
- les etapes de trace ;
- les scores produits.

## Exercice 2 - Inspecter le dataset

Ouvrez :

```text
projects/04-langsmith-quality-monitoring/evaluation/langsmith_cases.jsonl
```

Pour chaque ligne, reperez `inputs`, `outputs` et `metadata`. Expliquez pourquoi ces trois blocs
doivent rester separes.

## Exercice 3 - Evaluer le workflow LangGraph

Lancez :

```bash
python projects/04-langsmith-quality-monitoring/app.py evaluate-local
```

Notez les valeurs de :

- `route_accuracy` ;
- `citation_recall` ;
- `audit_contract` ;
- `answer_contract`.

## Exercice 4 - Creer une regression volontaire

Dans le dataset, modifiez temporairement le `topic` attendu de `fraud-score-review` en `claim`,
puis relancez l'evaluation locale.

Quelle metrique baisse ? Pourquoi cette regression est-elle facile a comprendre ?

## Exercice 5 - Ajouter un cas sensible

Ajoutez un exemple pour la question :

```text
Les caracteristiques de sante peuvent-elles etre utilisees par le modele ?
```

Definissez les sorties attendues, puis relancez l'evaluation.

## Exercice 6 - Exporter le dataset

Executez :

```bash
python projects/04-langsmith-quality-monitoring/app.py export-dataset
```

Comparez le fichier exporte avec le fichier source. Pourquoi l'export ajoute-t-il `example_id`
dans `metadata` ?

## Exercice 7 - Preparer une evaluation SDK

Executez :

```bash
python course/06-langsmith/examples/sdk_evaluation_template.py
```

Expliquez ce qu'il faudrait ajouter pour lancer une vraie experience dans LangSmith.

Les pistes de correction sont dans [solutions.md](solutions.md).
