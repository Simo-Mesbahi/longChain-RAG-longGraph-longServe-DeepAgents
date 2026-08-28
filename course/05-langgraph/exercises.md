# Exercices - Module 05

## Exercice 1 - Lire l'audit trail

Executez :

```bash
python course/05-langgraph/examples/basic_workflow.py
```

Expliquez le role de chaque entree dans `audit_trail`.

## Exercice 2 - Modifier le seuil de revue

Dans `basic_workflow.py`, augmentez `review_score` a `0.95` pour une question sensible.

Que devient le routage ? Pourquoi cette decision est-elle dans le code et pas seulement dans le
prompt ?

## Exercice 3 - Question hors corpus

Lancez :

```bash
python projects/03-langgraph-investigation-workflow/app.py \
  "Quel remboursement existe pour une couronne dentaire ?"
```

Identifiez :

- `answered` ;
- `needs_human_review` ;
- `evidence_status` ;
- le dernier noeud execute.

## Exercice 4 - Desactiver la revue humaine

Relancez la meme question avec :

```bash
python projects/03-langgraph-investigation-workflow/app.py \
  "Quel remboursement existe pour une couronne dentaire ?" \
  --no-human-review-on-missing
```

Comparez le resultat avec l'exercice 3.

## Exercice 5 - Reprendre apres interruption

Executez :

```bash
python course/05-langgraph/examples/human_review_interrupt.py
```

Expliquez pourquoi le `thread_id` est necessaire pour reprendre le bon etat.

## Exercice 6 - Ajouter un noeud

Ajoutez un noeud `classify_sensitivity` apres `analyze_question`, puis faites passer le graphe
par ce noeud avant le retrieval.

Le noeud doit ajouter `high_sensitivity` dans l'etat lorsque la question contient `fraude`,
`exclusion`, `refus` ou `score`.

## Exercice 7 - Tester un routeur

Ecrivez un test qui appelle directement `route_after_verification` avec :

- `next_action="draft_answer"` ;
- `next_action="request_human_review"` ;
- une valeur invalide.

Pourquoi tester le routeur seul est-il utile ?

Les pistes de correction sont dans [solutions.md](solutions.md).
