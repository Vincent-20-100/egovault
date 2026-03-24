L'objectif est de passer d'un système de stockage passif à une infrastructure d'inférence active. Actuellement, ton Vault Obsidian est une excellente carte (la structure), mais le RAG sur les sources brutes en est le territoire (la donnée). Sans l'indexation complète des sources, ton LLM est "myope" : il ne voit que tes résumés, pas la substance originelle.
Voici le pivot stratégique pour l'implémentation de cette feature "Deep Memory" :
1. Le Rationnel : Pourquoi l'Indexation Exhaustive ?
Le résumé (la note) est par définition une perte d'information. C'est un choix arbitraire fait au temps T.
 * Le problème : Dans six mois, tes besoins auront changé. Si tu n'as indexé que tes notes, tu ne pourras jamais demander au LLM de ré-extraire une info que tu avais jugée inutile lors de la première lecture.
 * La solution : En indexant le raw-content (chunks de transcripts/PDF), tu crées un Cold Storage dynamique. Le LLM peut alors "re-forensiquer" tes sources brutes sous un nouvel angle, sans que tu aies à relire le document.
2. Le Mécanisme : Hybridation "Namespace" & "Metadata"
On ne balance pas tout dans un index plat. Pour que l'agent reste performant, l'architecture doit supporter le Filtrage Pré-Sémantique.
 * Atomicité : Chaque document source est découpé en chunks de \approx 800 tokens avec un sliding window de 10% pour maintenir la cohérence contextuelle aux frontières.
 * Enrichissement des vecteurs : Chaque vecteur dans la DB doit porter un header de métadonnées miroir de ton YAML Obsidian :
   * source_id (PK) : Le slug du dossier source.
   * tags (Indexés) : La liste des thèmes hérités de la note liée.
   * timestamp/page : Pour le "Deep Linking" (renvoyer l'utilisateur au moment précis du média).
3. La Stratégie de Query (The Retrieval Flow)
C'est là que l'expertise intervient. On implémente un workflow de récupération à deux étages pour optimiser le ratio précision/rappel :
 * Narrowing (Filtrage) : L'agent identifie les source_id ou les tags pertinents via une recherche textuelle rapide sur tes notes Obsidian.
 * Vector Search (Précision) : On restreint la recherche de similarité cosinus uniquement aux vecteurs possédant ces métadonnées.
   * Intérêt : On élimine mathématiquement les collisions sémantiques (les "faux amis" entre deux domaines différents).
4. Intérêt Systémique pour EgoVault
 * Auditabilité : Le LLM peut désormais citer textuellement : "Dans ta note tu dis X, mais le transcript original à 12:04 précise Y".
 * Indépendance du Modèle : En ayant une base d'embeddings robuste (multilingual-e5 ou autre), tu peux changer de LLM (Claude à GPT-5 ou Llama-4) sans reconstruire ta mémoire. L'index devient ton actif principal, pas le modèle.
 * Scalabilité : Ton cerveau plafonne en volume de rappel ; cette DB ne plafonne pas. Plus tu ingères, plus les corrélations entre sources (via les tags communs) deviennent puissantes.
L'étape suivante pour nous : Définir si on part sur un stockage vectoriel local (type ChromaDB/DuckDB) pour garantir la latence zéro en local, ou si on expose une API pour que tes agents MCP puissent requêter ce "cerveau profond" de manière asynchrone.
Est-ce qu'on valide l'approche par ChromaDB pour garder la main sur les métadonnées en local ?
