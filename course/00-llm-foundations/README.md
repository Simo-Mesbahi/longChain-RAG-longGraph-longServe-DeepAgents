# Module 00 - Fondamentaux LLM

## Objectifs

A la fin de ce module, vous saurez distinguer modele, message, prompt, contexte et reponse. Vous saurez aussi proteger une cle API et identifier les principales limites d'une sortie generee.

## 1. Un LLM n'est pas une base de donnees

Un modele de langage estime une distribution de probabilite sur les prochains tokens. Il produit une suite plausible compte tenu du contexte, mais ne verifie pas automatiquement que chaque affirmation est vraie.

Cette distinction explique trois risques :

- une reponse peut etre fluide et fausse ;
- une connaissance peut etre obsolete ;
- une information absente du contexte peut etre inventee.

## 2. Les messages

Une conversation moderne utilise principalement trois roles :

| Role | Fonction |
|---|---|
| `system` | Definir le comportement et les regles generales |
| `user` | Exprimer la demande |
| `assistant` | Representer une reponse precedente du modele |

Le message systeme guide le modele, mais il ne constitue pas une garantie de securite. Les controles importants doivent aussi exister dans le code.

## 3. Parametres essentiels

**Temperature** : influence la variabilite de l'echantillonnage. Une valeur basse aide les taches d'extraction et de classification, sans rendre le modele deterministe au sens mathematique.

**Fenetre de contexte** : quantite maximale d'information utilisable pendant un appel. Un contexte plus long augmente souvent le cout et ne garantit pas une meilleure reponse.

**Max tokens** : limite de generation. Elle evite les sorties inutilement longues et aide a maitriser le cout.

## 4. Regles de fiabilite

1. Donner les informations necessaires dans le contexte.
2. Demander un format verifiable.
3. Valider les sorties dans le code.
4. Evaluer sur plusieurs exemples representatifs.
5. Prevoir le refus de repondre lorsque les preuves manquent.

## 5. Securite des secrets

Une cle API ne doit jamais etre ecrite directement dans un programme. Elle est chargee depuis l'environnement ou un gestionnaire de secrets. Le fichier `.env` local est ignore par Git.

## Exercice

Reformulez le prompt suivant pour preciser le public, le format et les limites :

> Parle-moi du RAG.

Une proposition de correction se trouve dans [solutions.md](solutions.md).

