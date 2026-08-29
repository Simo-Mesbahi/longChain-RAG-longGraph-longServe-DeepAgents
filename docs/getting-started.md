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

Pour lancer l'API optionnelle du module production :

```bash
pip install -e ".[dev,rag,api]"
```

Les dependances optionnelles sont separees afin de conserver un environnement minimal pour les
premiers modules.

Pour lancer la plateforme capstone :

```bash
pip install -e ".[dev,api]"
python projects/07-asteria-investigation-platform/app.py serve --reload
```

Le cockpit est ensuite disponible sur `http://127.0.0.1:8000` et OpenAPI sur
`http://127.0.0.1:8000/api/docs`.

## Variables d'environnement

Dupliquez `.env.example` vers `.env`, puis remplacez les valeurs factices. Le fichier `.env` est ignore par Git.

| Variable | Obligatoire | Role |
|---|:---:|---|
| `MODEL_PROVIDER` | Oui | Fournisseur du modele |
| `MODEL_NAME` | Oui | Modele utilise par les exemples |
| `EMBEDDING_MODEL` | Pour le RAG reel | Modele utilise pour indexer et rechercher |
| `OPENAI_API_KEY` | Selon provider | Authentification OpenAI |
| `ASTERIA_API_TOKEN` | Production | Token d'appel de l'API portfolio |
| `LANGSMITH_TRACING` | Non | Active les traces LangSmith |
| `LANGSMITH_API_KEY` | Non | Authentification LangSmith |

## Diagnostic

```bash
python --version
python -c "import langchain; print(langchain.__version__)"
pytest
```

Validation complete du capstone :

```bash
make quality
make capstone-evaluate
make capstone-ready
```

Une erreur `ModuleNotFoundError` signifie generalement que l'environnement virtuel n'est pas active ou que les dependances n'ont pas ete installees dans le bon interpreteur.
