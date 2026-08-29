# Corrections - Module 07

## Quiz

1. B
2. A
3. C
4. B
5. C
6. B
7. C
8. A

9. Exemple : "Les questions sur un score de fraude doivent etre validees humainement avant
publication." Ce fait est stable, actionnable et lie a une politique explicite.

10. Un resume limite la pollution du contexte principal. Les donnees completes restent
inspectables dans les fichiers, mais le fil principal ne garde que ce qui est utile pour la
decision suivante.

## Exercice 1

1. Le `planner` intervient avant la recherche.
2. La tache `verify-route` produit `/workspace/verification.json`.
3. Le `quality_reviewer` doit lire le resultat final pour verifier les contrats de publication.

## Exercice 2

La nouvelle regle doit etre placee avant la regle plus generale qui interrompt `/reports/**`.
Les permissions sont evaluees en first-match-wins.

Exemple :

```python
FilePermission(operations=["write"], paths=["/reports/drafts/**"], mode="allow")
FilePermission(operations=["write"], paths=["/reports/**"], mode="interrupt")
```

## Exercice 3

Le sous-agent attendu ressemble a :

```python
SubagentSpec(
    name="compliance_reviewer",
    description="Checks sensitive data and publication constraints.",
    tools=["read_file", "write_file"],
    system_contract="Detect sensitive data before publication.",
    output_contract="Return compliance checks and required fixes.",
)
```

Pour l'ajouter proprement, il faut aussi etendre le type `SubagentRole`.

## Exercice 4

Le check doit etre strict : une cle vide ne doit pas passer. Il peut etre teste directement avec
`evaluate_quality_gate` si la fonction accepte les `memory_updates`, ou avec un helper dedie si
vous preferez garder le contrat actuel.

## Exercice 5

La question dentaire n'a pas de preuve dans le corpus synthetique. L'agent doit donc refuser ou
demander une revue humaine. Publier une reponse sans preuve casserait le contrat RAG et le contrat
Deep Agent.

## Exercice 6

Dans une implementation SDK reelle :

- `search_evidence` deviendrait un outil Python connecte au vector store ;
- `read_file` et `write_file` seraient encadres par les permissions Deep Agents ;
- l'ecriture du rapport final pourrait demander une interruption ;
- les traces seraient envoyees a LangSmith.
