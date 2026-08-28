# Exercices - Module 01

## Exercice 1 - Modifier les variables

Executez l'exemple avec les concepts `embeddings`, `tool calling` et `hallucination`. Comparez les reponses obtenues pour les niveaux `debutant` et `intermediaire`.

**Critere de reussite** : vous savez identifier quelles parties du prompt sont fixes et quelles parties sont variables.

## Exercice 2 - Changer le format

Modifiez le template afin d'obtenir exactement quatre sections : definition, fonctionnement, exemple en assurance et limite.

**Critere de reussite** : les quatre sections sont demandees dans le message utilisateur et le code reste reutilisable pour plusieurs concepts.

## Exercice 3 - Ajouter une contrainte metier

Ajoutez la regle suivante au message systeme :

> Ne transforme jamais un score de risque en accusation de fraude.

Testez avec le concept `score de risque de fraude`.

**Question** : pourquoi cette instruction ne suffit-elle pas, a elle seule, pour rendre une application conforme et sure ?

## Exercice 4 - Inspecter le message

Affichez le type de `response`, son contenu et ses metadonnees. Notez les differences observees selon le fournisseur utilise.

Les pistes de correction sont disponibles dans [solutions.md](solutions.md).

