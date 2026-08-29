# Corrections - Module 09

## Quiz

1. B
2. A
3. B
4. A
5. C
6. B
7. B
8. B
9. B
10. A

11. Exemples : `request_id`, `trace_id`, `mode_used`, `citations`, `evidence`, `tasks`,
`audit_trail`, `business_checks`, `latency_ms` et `production_status`.

12. Un test unitaire verifie une fonction ou un invariant isole. Un scenario d'acceptation traverse
le contrat public complet avec une question metier, un moteur attendu, un comportement, des sources
et tous les quality gates. Les deux sont necessaires : precision locale et confiance produit.

## Exercice 1

Le mode RAG expose quatre etapes simples. LangGraph expose son audit de noeuds et de routage. Le
Deep Agent produit cinq taches specialisees, des resultats de sous-agents et des fichiers virtuels.
Le mode `auto` doit choisir LangGraph pour la question sur les pieces du dossier.

## Exercice 2

Avec la revue active, la plateforme renvoie `review_required` : un humain peut enrichir le dossier.
Avec `--no-review`, elle renvoie un refus controle. Dans les deux cas, aucune citation ne doit etre
inventee et `answered` reste faux.

## Exercice 3

Exemple :

```python
scenario = BusinessScenario(
    id="claim-theft-delay",
    title="Delai de declaration d'un vol",
    question="Quel est le delai pour declarer un vol ?",
    expected_mode="rag",
    expected_answered=True,
    expected_human_review=False,
    expected_sources=["claim-handling-procedure.md"],
)

summary = run_acceptance_suite(store, scenarios=[scenario])
assert summary.release_gate_passed is True
```

## Exercice 4

Une attente volontairement fausse doit produire un resultat avec `passed=false`. Le detail des
`assertions` permet d'identifier le contrat viole sans lire tous les logs.

## Exercice 5

`/health` confirme que le processus repond. `/ready` retourne le score de readiness et les blocages.
Lorsque `ASTERIA_API_TOKEN` est absent, le mode local accepte les appels. Lorsqu'il est configure,
les endpoints `POST` exigent `Authorization: Bearer ...`.

## Exercice 6

`textContent` traite une sortie comme du texte. Un passage contenant `<script>` reste visible comme
texte et n'est pas execute. `innerHTML` ne doit etre utilise que pour du contenu entierement controle
et constant, jamais pour une sortie de modele ou une donnee documentaire.

## Exercice 7

Exemple de check :

```python
_check(
    "bounded-evidence",
    "Volume de preuves public",
    len(response.evidence) <= 4,
    "La reponse expose au maximum quatre passages.",
    "La reponse expose trop de passages.",
)
```

Le test doit construire une reponse avec cinq passages ou utiliser un store controle afin de
verifier le chemin d'echec.

## Exercice 8

La note de release doit permettre a une personne qui n'a pas developpe la version de comprendre ce
qui change, pourquoi elle est acceptable et comment revenir a la derniere version saine. Un simple
"tests verts" n'est pas une procedure de rollback.
