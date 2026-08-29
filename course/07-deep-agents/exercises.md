# Exercices - Module 07

Ces exercices renforcent les contrats importants d'un Deep Agent : planification, delegation,
fichiers, permissions et quality gate.

## Exercice 1 - Lire un plan d'agent

Lancez :

```bash
python course/07-deep-agents/examples/planning_demo.py
```

Questions :

1. Quel sous-agent intervient avant la recherche documentaire ?
2. Quelle tache produit `/workspace/verification.json` ?
3. Pourquoi le `quality_reviewer` depend-il du rapport final ?

## Exercice 2 - Modifier une permission

Dans `permissions_demo.py`, ajoutez une regle qui autorise l'ecriture dans :

```text
/reports/drafts/**
```

Puis verifiez que :

- `/reports/drafts/test.md` est autorise ;
- `/reports/final.md` demande une interruption ;
- `/secrets/key.txt` reste bloque avec les permissions par defaut.

## Exercice 3 - Ajouter un sous-agent

Ajoutez un sous-agent `compliance_reviewer` dans `build_default_subagents`.

Contraintes :

- son contrat systeme doit mentionner les donnees sensibles ;
- il doit utiliser seulement `read_file` et `write_file` ;
- un test doit verifier sa presence.

## Exercice 4 - Etendre le quality gate

Ajoutez un check `memory_updates_are_named` :

- il passe si chaque mise a jour memoire a une cle non vide ;
- il echoue si une cle est vide ou composee uniquement d'espaces.

Ecrivez un test qui couvre le cas d'echec.

## Exercice 5 - Scenario non answerable

Lancez le projet :

```bash
python projects/05-deep-agent-investigation-analyst/app.py \
  "Quel remboursement existe pour une couronne dentaire ?"
```

Expliquez pourquoi l'agent ne doit pas inventer de reponse.

## Exercice 6 - Passage au vrai SDK

Ouvrez le template :

```bash
python course/07-deep-agents/examples/create_deep_agent_template.py
```

Adaptez-le mentalement a votre projet :

- quels outils seraient de vrais appels Python ?
- quels chemins devraient etre autorises ?
- quelle action devrait demander une interruption ?

## Criteres de reussite

Votre solution est correcte si :

- les tests restent verts ;
- les fichiers sensibles restent bloques ;
- les reponses answerable ont des citations ;
- les demandes de revue humaine ne publient pas de citations ;
- les nouveaux contrats sont documentes.
