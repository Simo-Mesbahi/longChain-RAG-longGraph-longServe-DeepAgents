# Exercices - Module 02

## Exercice 1 - Lire le schema

Ouvrez `src/ai_course/structured_output.py` et listez :

- les champs optionnels ;
- les valeurs possibles de `category` ;
- les contraintes appliquees a `amount_eur` et `summary` ;
- la regle imposee par le validateur metier.

**Critere de reussite** : vous savez expliquer ce qui est valide avant et apres le `model_validator`.

## Exercice 2 - Tester une entree incomplete

Executez `extract_claim.py` avec un texte sans identifiant et sans date. Observez `missing_fields` et `requires_human_review`.

**Question** : pourquoi le document ne doit-il pas etre rejete automatiquement ?

## Exercice 3 - Ajouter un champ

Ajoutez `policy_number: str | None` au schema. Integrez-le a la liste des champs suivis par le validateur et ajoutez deux tests : un cas present et un cas manquant.

## Exercice 4 - Validation stricte

Essayez de construire un `ClaimExtraction` avec un montant negatif, puis avec une categorie inexistante.

**Critere de reussite** : une `ValidationError` est levee dans les deux cas.

## Exercice 5 - Outil inconnu

Appelez `execute_tool_call` avec le nom `delete_claim`. Expliquez pourquoi l'application doit refuser cet appel meme si ses arguments semblent valides.

## Exercice 6 - Concevoir un outil de lecture

Creez un outil `get_policy_coverage(policy_number: str, incident_type: str)`. Il doit retourner une reponse fictive sans acces reseau et posseder :

- des annotations de types ;
- une docstring precise ;
- un schema Pydantic avec contraintes ;
- des tests pour les arguments valides et invalides.

Consultez les [corrections](solutions.md) apres avoir cherche votre propre solution.

