# Corrections - Module 02

## Exercice 1

Les champs `claim_id`, `incident_date` et `amount_eur` sont optionnels. La categorie appartient a un enum ferme. Le montant doit etre positif ou nul et le resume doit contenir au moins dix caracteres.

Le validateur calcule les champs reellement absents, les compare a `missing_fields` et impose une revue humaine lorsqu'au moins un champ critique manque.

## Exercice 2

Un document incomplet peut etre legitime ou completable. Le rejeter automatiquement ferait perdre une demande potentiellement valide. Le systeme retourne donc une structure exploitable tout en demandant une revue humaine.

## Exercice 4

```python
from pydantic import ValidationError

from ai_course.structured_output import ClaimCategory, ClaimExtraction

try:
    ClaimExtraction(
        claim_id="CLM-123456",
        incident_date=None,
        amount_eur=-1,
        category=ClaimCategory.WATER_DAMAGE,
        summary="Degat des eaux declare.",
        missing_fields=["incident_date"],
        requires_human_review=True,
    )
except ValidationError as error:
    print(error)
```

## Exercice 5

Le nom d'un outil est une frontiere d'autorisation. Le modele ne doit pas pouvoir inventer ou selectionner une fonction destructive simplement en produisant des arguments bien formes.

## Exercice 6 - Proposition

```python
from langchain.tools import tool
from pydantic import BaseModel, Field


class CoverageInput(BaseModel):
    policy_number: str = Field(pattern=r"^POL-[0-9]{6}$")
    incident_type: str = Field(min_length=3)


@tool(args_schema=CoverageInput)
def get_policy_coverage(policy_number: str, incident_type: str) -> dict[str, object]:
    """Return a synthetic coverage result for one policy and incident type."""
    return {
        "policy_number": policy_number,
        "incident_type": incident_type,
        "covered": True,
    }
```

Dans un projet reel, la source de donnees, les droits d'acces, les timeouts et les erreurs doivent aussi etre controles.

## Corrige du quiz

1. Non, le texte peut rester mal forme ou ne pas respecter les types.
2. Une instance Pydantic validee, si l'appel reussit.
3. Non, il faut une evaluation semantique et des tests sur des exemples.
4. Le schema d'entree construit a partir des types ou fourni explicitement.
5. Un nom, des arguments structures et un identifiant.
6. Non. L'application doit executer et renvoyer le resultat, ou utiliser un agent.
7. Pour limiter l'execution aux actions explicitement autorisees.
8. Lorsqu'une operation d'ecriture n'est pas idempotente.
9. Une action sensible, irreversible ou a fort impact.
10. Oui. Une structure correcte ne garantit pas la verite du contenu.

