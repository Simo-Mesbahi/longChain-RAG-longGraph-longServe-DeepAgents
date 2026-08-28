# Corrections - Module 01

## Exercice 2

Le message utilisateur peut devenir :

```python
(
    "human",
    "Explique '{concept}' pour un niveau {level}. "
    "Reponds avec exactement quatre sections : Definition, Fonctionnement, "
    "Exemple en assurance, Limite.",
)
```

Le mot `exactement` reduit les variations, mais seule une sortie structuree permettra de valider le format par le code. Ce sera l'objet du module 02.

## Exercice 3

Une instruction dans le prompt peut etre ignoree, contournee ou mal interpretee. Une application a impact eleve doit egalement imposer des controles applicatifs, journaliser les decisions, limiter les actions possibles et conserver une validation humaine.

## Exercice 4

```python
print(type(response))
print(response.content)
print(response.response_metadata)
print(response.usage_metadata)
```

Les metadonnees ne sont pas entierement standardisees entre fournisseurs. Le code de production doit gerer les champs absents.

