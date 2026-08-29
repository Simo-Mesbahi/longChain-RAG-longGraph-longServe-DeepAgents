# Corrections - Module 08

## Quiz

1. B
2. A
3. C
4. B
5. B
6. B
7. A
8. B

9. Exemples : CI absente, tests en echec, secrets manquants en production, route sensible sans
validation humaine, endpoint `POST` non authentifie, cible deploiement locale pour production.

10. Un endpoint LLM coute cher, peut etre lent et peut saturer les ressources. Le rate limit limite
les abus, protege la facture, stabilise la latence et rend les incidents plus controlables.

## Exercice 1

Le rapport de demo doit etre `ready` avec un score de 100 %. `/health` verifie que le processus
repond. `/ready` verifie que le service peut recevoir du trafic, ce qui peut inclure index,
configuration, modele, base de donnees ou dependances.

## Exercice 2

Un secret manquant bloque la production, car le service ne peut pas appeler ses dependances ou
authentifier ses clients. En local, c'est un probleme a corriger mais pas forcement un blocage :
on peut utiliser des mocks, embeddings deterministes ou donnees synthetiques.

## Exercice 3

Le check attendu est `auth_for_mutations`. Toute route qui modifie de l'etat, lance une execution
couteuse ou expose une decision metier doit etre protegee.

## Exercice 4

La route ajoutee doit apparaitre dans `affected_routes`, surtout dans les etapes d'inventaire,
stabilisation des contrats et remplacement des clients `RemoteRunnable`.

## Exercice 5

Le manifest doit permettre une revue rapide avant deploiement : commande, ports, variables,
secrets, healthcheck, readiness probe et strategie de scaling.

## Exercice 6

Une procedure acceptable :

```text
Version courante : 0.2.0
Derniere version saine : 0.1.0
Action : redeployer l'image asteria-investigation-platform:0.1.0
Verification infra : GET /health puis GET /ready
Verification metier : poser "Quelle est la franchise degat des eaux ?"
Critere : reponse citee avec home-protection-policy.md et quality gate OK
```
