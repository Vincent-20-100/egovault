from pathlib import Path
from scripts.ingest.audio import PROFILES
from scripts.ingest._core import slug


def test_profil_fast_plus_rapide_que_default():
    assert PROFILES["fast"]["model_size"] == "small"
    assert PROFILES["fast"]["beam_size"] < PROFILES["default"]["beam_size"]
    assert PROFILES["fast"]["cpu_threads"] > PROFILES["default"]["cpu_threads"]


def test_source_md_ne_contient_pas_copie_audio(tmp_path, monkeypatch):
    """Le drop-off ne doit pas contenir de fichier audio copié."""
    from scripts.ingest import _core
    monkeypatch.setattr(_core, "RAW_SOURCES", tmp_path)

    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"fake audio")

    # Simuler make_drop_off + vérifier qu'aucun .mp3 n'est dans le drop-off
    from scripts.ingest._core import make_drop_off
    folder = make_drop_off("Test", "audio",
                           extra_fields={"chemin_original": str(audio),
                                        "fichier_audio": audio.name})
    mp3_files = list(folder.glob("*.mp3"))
    assert mp3_files == [], "L'audio ne doit pas être copié dans le drop-off"
