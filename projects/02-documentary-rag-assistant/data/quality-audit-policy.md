# Politique Asteria - Qualite, audit et amelioration continue

> Document pedagogique fictif. Il decrit le controle qualite d'une plateforme RAG/agent.

## Controle des reponses

Une reponse est acceptable si elle repond a la question, cite au moins une source pertinente,
n'invente pas de clause absente du corpus et indique une revue humaine lorsque les preuves sont
insuffisantes. Les citations doivent correspondre aux documents recuperes pendant l'execution.

Les reponses sur la fraude, les exclusions et les refus d'indemnisation sont considerees sensibles.
Elles doivent privilegier l'explication, la demande de pieces et la revue humaine plutot qu'une
conclusion automatique.

## Evaluation metier

Le dataset d'evaluation doit contenir des questions factuelles, des questions de workflow, des
questions hors corpus et des questions sensibles. Chaque scenario precise le mode attendu, les
sources attendues, le statut repondu ou non repondu, et les garde-fous attendus.

Un changement de prompt, de chunking, de corpus ou de modele doit etre teste sur le dataset avant
deploiement. Si le taux de passage baisse, la release doit etre bloquee jusqu'a correction.

## Journalisation

Chaque execution doit produire un identifiant de requete, un identifiant de trace, le mode utilise,
les sources recuperees, les controles metier et le statut de readiness. Les traces ne doivent pas
contenir de cles API, de secrets ou de donnees inutiles.
