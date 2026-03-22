import pytest
from scripts.ingest.youtube import extract_video_id


def test_extrait_id_url_standard():
    assert extract_video_id("https://www.youtube.com/watch?v=e5do6xr3dS4") == "e5do6xr3dS4"


def test_extrait_id_url_courte():
    assert extract_video_id("https://youtu.be/e5do6xr3dS4") == "e5do6xr3dS4"


def test_extrait_id_url_avec_params():
    url = "https://www.youtube.com/watch?v=-dIpcRgGFxA&list=LL&index=4&t=994s"
    assert extract_video_id(url) == "-dIpcRgGFxA"


def test_extrait_id_url_invalide():
    with pytest.raises(ValueError):
        extract_video_id("https://example.com/video")
