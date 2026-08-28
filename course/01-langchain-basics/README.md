# Module 01 - Premiers pas avec LangChain

## Objectifs

- comprendre ce que LangChain abstrait ;
- initialiser un modele sans coupler toute l'application a un fournisseur ;
- construire un `ChatPromptTemplate` ;
- composer une chaine avec LCEL ;
- executer et inspecter la reponse.

## 1. Pourquoi LangChain ?

Une application LLM reelle combine souvent plusieurs composants : modeles, prompts, outils, retrieval, validation, streaming et traces. LangChain fournit des interfaces communes et un systeme de composition pour relier ces composants.

LangChain ne remplace ni l'architecture ni les tests. Il reduit le code d'integration et rend les composants plus faciles a remplacer.

## 2. Le modele

La fonction `init_chat_model` initialise un modele a partir d'un nom et d'un fournisseur. Les integrations restent dans des paquets separes, par exemple `langchain-openai`.

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    model="gpt-4.1-mini",
    model_provider="openai",
    temperature=0,
)
```

## 3. Le prompt template

Un template separe les instructions stables des donnees variables :

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "Tu es un formateur clair et precis."),
        ("human", "Explique {concept} pour un niveau {level}."),
    ]
)
```

Les valeurs de `concept` et `level` sont fournies au moment de l'invocation.

## 4. LCEL

```python
chain = prompt | model
response = chain.invoke({"concept": "RAG", "level": "debutant"})
print(response.content)
```

L'operateur `|` signifie que la sortie du prompt devient l'entree du modele. Les deux objets respectent l'interface `Runnable`.

## 5. Ce qu'il faut observer

- `response` est un message, pas une simple chaine de caracteres ;
- `response.content` contient le contenu principal ;
- les metadonnees peuvent contenir le modele, la raison d'arret et l'usage des tokens ;
- une execution reussie ne prouve pas que la reponse est correcte.

## Lancer l'exemple

```bash
python course/01-langchain-basics/examples/first_chain.py "SHAP"
```

Passez ensuite aux [exercices](exercises.md).

