# Exercices - Module 03

## Exercice 1 - Observer les chunks

Affichez pour chaque chunk son `chunk_id`, son `start_index`, sa longueur et ses 80 premiers caracteres.

Testez ensuite trois configurations :

- `chunk_size=250`, `chunk_overlap=30` ;
- `chunk_size=450`, `chunk_overlap=60` ;
- `chunk_size=800`, `chunk_overlap=100`.

Expliquez ce que vous gagnez et perdez dans chaque cas.

## Exercice 2 - Comprendre les embeddings

Avec `HashingEmbeddings`, comparez les similarites des groupes suivants :

- `degat des eaux` et `justificatifs degat des eaux` ;
- `degat des eaux` et `remboursement sante` ;
- deux phrases semantiquement proches sans mots communs.

Pourquoi le troisieme cas montre-t-il la limite de cet embedder pedagogique ?

## Exercice 3 - Modifier `k`

Executez la meme question avec `k=1`, `k=2` et `k=5`. Notez les chunks recuperes et les scores.

**Question** : pourquoi augmenter `k` ne garantit-il pas une meilleure reponse ?

## Exercice 4 - Tester le refus

Posez une question absente du corpus, par exemple sur l'assurance voyage. Augmentez progressivement `min_score` et observez quand le pipeline refuse de repondre.

Ne concluez pas qu'un seuil trouve sur cet exemple sera adapte a toutes les questions.

## Exercice 5 - Attaque sur les citations

Modifiez le fake generator d'un test pour retourner `invented.pdf#chunk-999`. Verifiez que la validation bloque la reponse.

## Exercice 6 - Ajouter une source

Creez un second document synthetique sur l'assurance automobile avec une metadonnee `source` distincte. Indexez les deux documents et verifiez que la citation finale pointe vers la bonne source.

Les pistes de correction sont dans [solutions.md](solutions.md).

