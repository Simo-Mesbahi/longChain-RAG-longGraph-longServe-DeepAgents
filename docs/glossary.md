# Glossaire

**Agent**
: Systeme qui choisit dynamiquement des actions pour atteindre un objectif.

**Embedding**
: Representation numerique d'un texte dans un espace vectoriel, utile pour mesurer une proximite semantique.

**Hallucination**
: Information generee avec assurance mais non soutenue par les donnees disponibles.

**Juge LLM**
: Modele utilise pour noter une sortie selon des criteres explicites. Il aide a evaluer des
reponses ouvertes, mais doit etre calibre et surveille.

**LCEL**
: LangChain Expression Language, syntaxe de composition des composants LangChain avec l'operateur `|`.

**LLM**
: Large Language Model, modele de langage entraine sur de grandes quantites de texte.

**RAG**
: Retrieval-Augmented Generation. Une etape de recherche fournit au modele un contexte issu de sources controlees avant la generation.

**Reranking**
: Reordonnancement d'une liste de passages deja recuperes afin de placer les meilleurs candidats
en tete avant la generation.

**Runnable**
: Composant LangChain invocable, composable et souvent compatible avec les executions synchrones, asynchrones, batch et streaming.

**Stateful**
: Qui conserve un etat utile entre plusieurs etapes ou interactions.

**Tool calling**
: Mecanisme permettant a un modele de demander l'execution d'une fonction dont les arguments suivent un schema defini.

**Trace**
: Enregistrement structure des etapes, entrees, sorties, erreurs et durees d'une execution.
