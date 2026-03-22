# EgoVault — Foundation

_Ce document répond à une seule question : **pourquoi** ce projet existe._
_Il ne décrit pas comment le système fonctionne. Il ancre tous les choix qui suivront._
_Dernière mise à jour : 2026-03-22_

---

## Le problème fondamental

La connaissance humaine s'accumule dans des endroits morts.

Un podcast écouté, un livre lu, une réflexion notée — dans la semaine qui suit, 80% du contenu a disparu. Ce n'est pas un problème d'intelligence. C'est un problème d'infrastructure : nous n'avons pas de système qui capte, structure et rend disponible ce que nous absorbons.

En parallèle, les LLMs sont puissants mais amnésiques. Chaque conversation repart de zéro. Ils ne savent pas qui tu es, ce que tu as pensé hier, ce que tu as appris ce mois-ci. Leur intelligence est générale mais elle n't a pas accès à ta connaissance particulière.

**Ce projet construit le pont entre les deux.**

---

## Ce que ce projet est

Une infrastructure de mémoire à double usage :

**Pour l'humain** — un second cerveau. Un endroit où la connaissance s'accumule de façon structurée, où les connexions entre idées émergent organiquement, où retrouver une pensée de l'année passée prend deux secondes.

**Pour les LLMs** — une mémoire long-terme. Un corpus structuré, interrogeable, qui permet à n'importe quel LLM de travailler *avec* ta connaissance accumulée plutôt que de repartir de rien. Le LLM n'est plus générique : il est contextualisé par des années de pensée.

Ce n'est pas un outil de prise de notes. C'est une infrastructure cognitive.

---

## Ce que ce projet n'est pas

- Ce n'est **pas** un substitut à la pensée. La capture et la structuration servent la réflexion, elles ne la remplacent pas.
- Ce n'est **pas** un outil de productivité. L'objectif n'est pas de traiter plus de sources, mais de comprendre mieux.
- Ce n'est **pas** un système de gestion de fichiers amélioré. La valeur n'est pas dans les fichiers, elle est dans les **connexions** entre eux.
- Ce n'est **pas** un projet IA. L'IA est un outil dans le système. L'intelligence reste humaine.

---

## Les axiomes

Ces principes ne sont pas des règles techniques. Ce sont des vérités premières depuis lesquelles tout découle. Si une décision contredit un axiome, c'est l'axiome qui doit être challengé — pas ignoré.

### A1. La connaissance s'accumule, elle ne se supprime pas

Toute connaissance capturée a de la valeur, même si elle semble redondante ou erronée aujourd'hui. Le contexte change. Ce qui était faux devient vrai dans un autre cadre. Ce système ne supprime jamais — il archive, révise, connecte.

### A2. La friction à la capture est l'ennemi principal

Un système parfaitement structuré mais difficile à alimenter est un système mort. La priorité absolue est que capturer une source prenne le moins de temps et d'effort possible. La structuration vient après, pas pendant.

### A3. La structure émerge du contenu — elle ne lui est pas imposée

Les catégories, les thèmes, les connexions doivent naître de l'accumulation des notes, pas d'une taxonomie définie à l'avance. Un tag qui n'existe pas encore n'est pas un problème : il sera créé quand la réalité le demande.

### A4. Les connexions ont plus de valeur que les notes individuelles

Une note isolée est un fait. Une note connectée à d'autres est une compréhension. Le but du système est de maximiser les connexions pertinentes, pas le nombre de notes.

### A5. Le LLM est un outil, l'humain est l'autorité

Le LLM propose, structure, synthétise. L'humain valide, rejette, oriente. Aucune note n'est créée, aucun tag ajouté, aucun lien établi sans validation humaine explicite ou implicite. L'IA augmente la cognition — elle ne la remplace pas.

### A6. La réversibilité avant l'optimisation

Mieux vaut un système imparfait qu'on peut corriger qu'un système optimal qu'on ne peut pas défaire. Les décisions architecturales privilégient la réversibilité : Markdown plutôt que base de données propriétaire, fichiers locaux plutôt que cloud, formats ouverts partout.

---

## La vision lointaine

Dans dix ans, tu peux demander à n'importe quel LLM : *"Qu'est-ce que je pense de la décentralisation ?"* — et il peut te répondre avec précision, en croisant des notes de 2025 sur les fourmis, une réflexion de 2027 sur la démocratie directe, et une synthèse de 2029 sur les organisations auto-organisées.

Ce n'est pas de la recherche documentaire. C'est de la mémoire.

Le système aura réussi quand il sera invisible — quand capturer et retrouver une pensée sera aussi naturel que de se souvenir.

---

## Les questions ouvertes permanentes

Ces questions ne seront probablement jamais définitivement résolues. Elles doivent rester ouvertes pour challenger les décisions :

1. **Où s'arrête l'outil et où commence la dépendance ?** Un système qui pense à notre place appauvrit-il la mémoire naturelle ?
2. **La structure nuit-elle à la sérendipité ?** Les connexions algorithmiques sont-elles moins riches que les connexions intuitives ?
3. **Quel est le coût d'un système qui n'oublie jamais ?** L'oubli a une fonction cognitive. Que perd-on en tout gardant ?
4. **Pour qui ce système est-il conçu ?** Un outil trop personnel ne peut pas être partagé. Trop générique, il perd sa valeur.

---

## Ce document et les autres

| Fichier | Répond à |
|---------|----------|
| `FOUNDATION.md` | **Pourquoi** — philosophie, axiomes, vision |
| `DOCUMENTATION.md` | **Quoi** — architecture, décisions et leurs justifications |
| `AMELIORATIONS.md` | **Comment évoluer** — backlog, chantiers, brainstorm |
| `LLM.md` | **Comment faire** — protocoles opérationnels pour l'IA |
| `README.md` | **Comment démarrer** — installation, commandes |
