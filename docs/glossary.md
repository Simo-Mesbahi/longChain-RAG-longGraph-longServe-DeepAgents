# Glossaire

**Agent**
: Systeme qui choisit dynamiquement des actions pour atteindre un objectif.

**Checkpointer**
: Composant LangGraph qui sauvegarde l'etat d'un thread afin de reprendre, inspecter ou
interrompre une execution.

**Canary release**
: Deploiement progressif d'une nouvelle version sur une faible part du trafic afin de detecter
les regressions avant une bascule complete.

**Business check**
: Invariant metier machine-readable verifie avant de publier une reponse ou une release.

**Capstone**
: Projet final qui rassemble plusieurs competences du parcours dans un produit testable et
deployable.

**Context offloading**
: Pattern qui consiste a ecrire les donnees volumineuses dans des fichiers afin de garder un
contexte principal court, inspectable et controle.

**Deep Agent**
: Agent concu pour les taches longues. Il combine planification, sous-agents, outils, fichiers,
memoire, permissions et observabilite.

**Embedding**
: Representation numerique d'un texte dans un espace vectoriel, utile pour mesurer une proximite semantique.

**Hallucination**
: Information generee avec assurance mais non soutenue par les donnees disponibles.

**Juge LLM**
: Modele utilise pour noter une sortie selon des criteres explicites. Il aide a evaluer des
reponses ouvertes, mais doit etre calibre et surveille.

**Human-in-the-loop**
: Pattern dans lequel une execution automatisee demande une validation ou une correction humaine
avant de continuer.

**Harness agentique**
: Couche d'orchestration qui encadre un agent avec des contrats, de la memoire, des outils, des
permissions et des procedures de verification.

**Evaluation offline**
: Evaluation lancee avant de deployer, sur un dataset controle, pour comparer des versions et
eviter les regressions.

**Evaluation online**
: Evaluation appliquee a des interactions de production afin de surveiller qualite, erreurs,
latence ou cout.

**Healthcheck**
: Endpoint ou commande qui verifie qu'un processus repond encore. Il ne garantit pas que toutes
les dependances metier sont pretes.

**Interrupt**
: Pause dynamique dans un graphe LangGraph. L'execution reprend ensuite avec `Command(resume=...)`.

**LangGraph**
: Runtime d'orchestration pour construire des workflows LLM stateful avec routage, persistence,
streaming et validation humaine.

**LangSmith**
: Plateforme d'observabilite et d'evaluation pour tracer, tester, comparer et monitorer des
applications LLM.

**LangSmith Deployment**
: Runtime de deploiement pour agents et workflows avec execution durable, streaming et scaling,
notamment pour les applications LangGraph.

**LangServe**
: Ancien projet permettant d'exposer des `Runnable` LangChain via FastAPI. Il est deprecie pour
les nouveaux projets et doit etre traite comme surface legacy.

**Long-term memory**
: Memoire durable contenant des faits stables ou preferences qui peuvent etre reutilises dans de
futures executions.

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

**Permission rule**
: Regle qui autorise, bloque ou interrompt une operation d'agent sur un chemin ou un outil.

**Rate limit**
: Limite de debit appliquee aux requetes afin de proteger couts, latence, ressources et securite.

**Readiness probe**
: Endpoint ou commande qui verifie qu'un service peut recevoir du trafic, y compris ses
dependances critiques.

**Release gate**
: Ensemble de conditions qui autorisent ou bloquent une mise en production, comme les tests,
scenarios metier, controles de securite et readiness.

**Rollback**
: Retour controle vers une version precedente connue comme saine apres un incident ou une
regression.

**Risk router**
: Composant qui choisit un moteur d'execution selon la complexite, la sensibilite et les garde-fous
requis par une demande.

**Skill**
: Capacite chargeable qui ajoute des instructions, fichiers ou procedures specialisees a un agent.

**SLO**
: Service Level Objective, objectif mesurable de qualite de service comme disponibilite, latence
ou taux d'erreur.

**Stateful**
: Qui conserve un etat utile entre plusieurs etapes ou interactions.

**Subagent**
: Agent specialise appele par l'agent principal pour realiser une tache precise et retourner un
resume controle.

**Tool calling**
: Mecanisme permettant a un modele de demander l'execution d'une fonction dont les arguments suivent un schema defini.

**Trace**
: Enregistrement structure des etapes, entrees, sorties, erreurs et durees d'une execution.

**Virtual filesystem**
: Systeme de fichiers controle utilise par un agent pour stocker plans, preuves, rapports et
memoire sans exposer directement tout l'environnement.

**Target function**
: Fonction evaluee par LangSmith. Elle recoit les `inputs` d'un exemple et retourne les sorties a
noter par les evaluateurs.
