# Installation

## Prerequis

- Python 3.11 ou plus recent ;
- Git ;
- un terminal ;
- une cle API pour le fournisseur de modele choisi.

Python 3.11 est recommande pour conserver un bon equilibre entre compatibilite et modernite.

## Environnement virtuel

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Pour executer le projet avec un index Chroma persistant :

```bash
pip install -e ".[dev,rag]"
```

Les dependances optionnelles sont separees afin de conserver un environnement minimal pour les
premiers modules.

## Variables d'environnement

Dupliquez `.env.example` vers `.env`, puis remplacez les valeurs factices. Le fichier `.env` est ignore par Git.

| Variable | Obligatoire | Role |
|---|:---:|---|
| `MODEL_PROVIDER` | Oui | Fournisseur du modele |
| `MODEL_NAME` | Oui | Modele utilise par les exemples |
| `EMBEDDING_MODEL` | Pour le RAG reel | Modele utilise pour indexer et rechercher |
| `OPENAI_API_KEY` | Selon provider | Authentification OpenAI |
| `LANGSMITH_TRACING` | Non | Active les traces LangSmith |
| `LANGSMITH_API_KEY` | Non | Authentification LangSmith |

## Diagnostic

```bash
python --version
python -c "import langchain; print(langchain.__version__)"
pytest
```

Une erreur `ModuleNotFoundError` signifie generalement que l'environnement virtuel n'est pas active ou que les dependances n'ont pas ete installees dans le bon interpreteur.
