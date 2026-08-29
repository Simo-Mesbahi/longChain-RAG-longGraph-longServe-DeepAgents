# Contribuer

Merci de contribuer a ce cours. Les contributions peuvent corriger une erreur, clarifier une explication, ajouter un test ou proposer un exercice.

## Principes

- Le contenu pedagogique est redige en francais clair.
- Le code, les identifiants et les messages d'erreur sont en anglais.
- Un exemple doit etre minimal, executable et accompagne d'une explication.
- Aucun secret, jeu de donnees prive ou document confidentiel ne doit etre ajoute.
- Une nouvelle fonctionnalite doit inclure les tests adaptes.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
```

## Qualite

```bash
ruff check .
ruff format --check .
pytest
mkdocs build --strict
python projects/07-asteria-investigation-platform/app.py evaluate
```

## Pull request

1. Creez une branche courte et descriptive.
2. Limitez la pull request a un objectif coherent.
3. Expliquez ce qui change et comment le verifier.
4. Verifiez que la CI est verte.
