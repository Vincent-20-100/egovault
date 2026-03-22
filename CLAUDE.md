Lire `docs/LLM.md` pour les instructions complètes.

---

## Tech Stack

- Python 3.x via `.venv/Scripts/python` (Windows)
- `faster-whisper` (transcription locale), `youtube-transcript-api`, `yt-dlp`
- Tests : `pytest` dans `tests/` (miroir de `scripts/`)

## Commandes

```bash
# Ingestion
.venv/Scripts/python capture.py "https://youtube.com/watch?v=..."
.venv/Scripts/python capture.py fichier.mp3 --title "Titre" --lang fr --fast

# Maintenance
.venv/Scripts/python scripts/vault_status.py
.venv/Scripts/python scripts/update_index.py
.venv/Scripts/python scripts/check_consistency.py

# Tests
.venv/Scripts/python -m pytest tests/
```

## Structure scripts

```
capture.py               ← point d'entrée unique (utilisateur)
scripts/
├── ingest/
│   ├── _core.py         ← utilitaires partagés (interne)
│   ├── youtube.py
│   └── audio.py
├── vault_status.py
├── update_index.py
├── check_consistency.py
└── clean_sources.py
```

## Conventions Python

- `_core.py` = interne au package, jamais appelé directement
- Handlers `ingest/` : un fichier par type de source, dépendances isolées
- Tests : `tests/ingest/test_audio.py` ↔ `scripts/ingest/audio.py`

## Conventions vault (voir docs/LLM.md pour le détail)

- Fichiers notes : `YYYY-MM-DD-titre-kebab-case.md`
- Tags : français, minuscules, sans accents, tirets
- Commits : `feat:` / `docs:` / `chore:` + description française

## Architecture cible (voir docs/AMELIORATIONS.md)

- `scripts/vault/` pas encore créé — scripts encore à plat dans `scripts/`
- Handler PDF : non implémenté
