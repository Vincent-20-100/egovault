# Spec: Ingestion de Documents Visuels, Images et PDF Complexes (Lean Multimodal)

**Date :** 2026-08-15  
**Statut :** Draft — Prêt pour revue  
**Dépendances :** Unified ingest (`workflows/ingest.py`), VaultContext, `tools/media/`  
**Vision associée :** `docs/VISION-KNOWLEDGE-COMPILER.md` (Architecture cognitive, Tier 0/1)

---

## 1. Contexte & Problématique

Actuellement, l'ingestion de documents dans EgoVault présente trois limitations majeures :

1. **Les images isolées ne sont pas supportées** (schémas d'architecture, infographies, captures d'écran, photos de tableau blanc).
2. **L'extracteur PDF actuel (`pypdf`) est simpliste :**
   - Il détruit l'ordre de lecture des documents multi-colonnes.
   - Il transforme les tableaux en bouillie de texte.
   - Il ignore totalement les figures, graphiques et schémas.
3. **Les PDF scannés (pages sous forme d'images sans couche texte) échouent** (`EmptyContentError`).

### Le Piège du "Tout-VLM à l'ingestion" (Écarté)
Vouloir exécuter un modèle de vision (VLM) sur chaque image pour générer une description textuelle à l'ingestion est inefficace :
- **Coût de compute prohibitif :** Ralentit l'ingestion et consomme de la VRAM / des tokens API sur des centaines d'images potentiellement inutiles.
- **Perte d'information :** Un résumé textuel automatique dégrade la complexité d'un schéma ou d'un graphique technique.

### La Décision d'Architecture : Le modèle "Lean Pointer" (Lazy Evaluation)
1. **À l'ingestion (Tier 0 — 100 % déterministe & gratuit) :**
   - Découper et stocker les images de haute qualité dans `egovault-user/data/media/{slug}/`.
   - Insérer des pointeurs Markdown propres dans le transcript source et les chunks :  
     `![Figure 3: Légende native extraite du PDF](media/{slug}/fig_03.png)`.
   - Vectoriser le texte et les légendes environnantes (zéro inférence VLM).
2. **À la consommation (Tier 1 — À la demande) :**
   - **Pour l'humain dans Obsidian :** Visualisation directe de l'image haute définition incrustée dans les notes ou sources.
   - **Pour l'agent LLM via MCP :** L'agent dispose d'un outil MCP `get_media(path)` lui permettant de charger et d'inspecter l'image nativement *uniquement si sa réflexion le nécessite*.

---

## 2. Architecture & Pipeline d'Ingestion

```
SOURCE VISUELLE (PDF complexe, Image isolée, Scan)
                     │
                     ▼
          [Sonde Heuristique Rapide (5ms)]
                     │
     ┌───────────────┼────────────────────────┐
     │               │                        │
[PDF Numérique]  [PDF Scanné (<50 char/p)] [Image Isolée]
     │               │                        │
     ▼               ▼                        ▼
OpenDataLoader  Unlimited-OCR            Stockage binaire
/ PyMuPDF4LLM   / PaddleOCR              + Métadonnées
     │               │                        │
     └───────────────┬────────────────────────┘
                     ▼
          [Extraction Structurée]
   - Texte Markdown avec titres (#, ##)
   - Tableaux Markdown (| col1 | col2 |)
   - Figures découpées dans data/media/{slug}/
   - Liens insérés : ![Légende](media/{slug}/fig_xx.png)
                     │
                     ▼
        [Transcript Source (Layer 1)]
                     │
                     ▼
        Chunking ──► Embeddings Chunks ──► rag_ready
```

---

## 3. Détail des Stratégies par Type de Source

### 3.1 PDF Numérique avec Mise en Page Complexe (Tier 0.5 — CPU)
- **Moteur :** `opendataloader-pdf` (mode hybride déterministe) ou `pymupdf4llm`.
- **Comportement :**
  - Reconstruit l'ordre de lecture des articles scientifiques / livres multi-colonnes.
  - Convertit les tableaux natifs en tableaux Markdown.
  - Isole les images vectorielles et raster supérieures au seuil de taille (`min_image_size: 250x250px` pour ignorer les puces, logos et icônes).
  - Associe chaque image à son bloc de légende (`Figure X: ...`) trouvé à proximité dans la géométrie du PDF.

### 3.2 PDF Scanné / Image Pure (Tier 1 — OCR)
- **Détection automatique :** Si `nombre_caractères / nombre_pages < 50`.
- **Moteur :** `Unlimited-OCR` (Baidu / R-SWA, faible mémoire VRAM) ou `rapidocr` / Tesseract en fallback CPU.
- **Sortie :** Transcription continue en Markdown structuré.

### 3.3 Image Isolée (Infographie, Schéma, Capture d'écran)
- **Comportement :**
  - L'image originale est copiée dans `egovault-user/data/media/{slug}/source_image.<ext>`.
  - Le transcript initial est créé avec les métadonnées de base (nom de fichier, dimensions, date).
  - Un pointeur standard `![Titre / Slug](media/{slug}/source_image.<ext>)` est généré.
  - *Optionnel (si `vlm_captioning: true`) :* Génération asynchrone d'une docstring descriptive via VLM local (Ollama `qwen2.5-vl`) ou API.

---

## 4. Outils à Créer et Modifier

### 4.1 Nouveaux Composants

| Composant | Rôle |
|---|---|
| `tools/media/parse_document.py` | Parseur structurel PDF (OpenDataLoader/PyMuPDF) extrayant Markdown + images découpées |
| `tools/media/ocr_document.py` | Moteur OCR pour documents scannés sans couche texte |
| `tools/media/get_media.py` | Outil de lecture binaire / base64 d'un média local pour les surfaces MCP et API |

### 4.2 Composants Modifiés

| Composant | Modification |
|---|---|
| `workflows/ingest.py` | Ajout des extracteurs `"image"` et refonte de `"pdf"` / `"livre"` avec routage heuristique |
| `core/schemas.py` | Ajout optionnel d'un modèle `ExtractedMedia(path, width, height, caption)` |
| `mcp/server.py` | Exposition du tool MCP `get_media(source_uid, file_path)` pour inspection par l'agent |
| `config/system.yaml` | Nouvelle section de configuration `ingest.pdf` et `ingest.image` |

---

## 5. Configuration (`config/system.yaml`)

```yaml
# Configuration de l'ingestion visuelle et documents
ingest:
  pdf:
    strategy: auto                  # auto | fast_native | layout | ocr
    scanned_char_threshold: 50      # seuil de détection scan (caractères par page)
    extract_images: true            # découpe et sauvegarde les figures significatives
    min_image_dimension: 250        # largeur et hauteur min en pixels (filtre le bruit)
  
  image:
    supported_extensions:
      - .png
      - .jpg
      - .jpeg
      - .webp
      - .svg
    vlm_captioning: false           # false = Lean Pointer (défaut) ; true = appel VLM à l'ingestion
```

---

## 6. Interaction avec la Couche Notes (Tier 2)

- **Dans les Chunks (Tier 1) :** Les liens vers les images `![Caption](path)` restent présents dans le texte brut chunké pour que la recherche sémantique capture la légende.
- **Dans les Notes de Synthèse (Tier 2) :** L'agent rédacteur de note n'est **pas obligé** de recopier toutes les images. Il ne cite l'image `![[fig_xx.png]]` que si celle-ci représente un modèle mental ou un schéma clé synthétisé.

---

## 7. Plan de Test & Validation

1. **Test unitaire Layout PDF :** Ingestion d'un PDF à 2 colonnes avec 1 tableau et 1 graphique $\to$ Vérifier que l'ordre de lecture est respecté et que l'image est enregistrée dans `media/`.
2. **Test unitaire Scan PDF :** Ingestion d'un PDF composé de 3 pages scannées (0 texte natif) $\to$ Vérifier le basculement automatique en OCR et la génération du transcript.
3. **Test unitaire Image Isolée :** Ingestion d'un fichier `.png` $\to$ Vérifier la création de la source `image` et l'accessibilité du binaire via `get_media`.
4. **Test de non-régression :** Vérifier que les sources simples (texte, web, audio, youtube) continuent de fonctionner à 100 %.
