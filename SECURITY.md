# Securite

## Signaler une vulnerabilite

N'ouvrez pas d'issue publique pour une vulnerabilite exploitable ou une fuite de secret. Utilisez les fonctionnalites privees de signalement de securite GitHub lorsque disponibles.

## Regles essentielles

- Ne committez jamais de cle API, token ou fichier `.env`.
- Utilisez des donnees synthetiques ou explicitement publiques.
- Considerez toute sortie d'un LLM comme non fiable avant validation.
- Validez les arguments des outils et limitez leurs permissions.
- Isolez l'execution de code genere dans un environnement sandboxe.
- Conservez une validation humaine pour les decisions a impact eleve.

Une cle publiee doit etre revoquee immediatement, meme si le commit est ensuite supprime.

