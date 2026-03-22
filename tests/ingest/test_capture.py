from capture import detect_type


def test_detecte_youtube_url_standard():
    assert detect_type("https://www.youtube.com/watch?v=abc") == "youtube"


def test_detecte_youtube_url_courte():
    assert detect_type("https://youtu.be/abc123") == "youtube"


def test_detecte_audio_mp3():
    assert detect_type("mon-fichier.mp3") == "audio"


def test_detecte_audio_m4a():
    assert detect_type("/chemin/vers/podcast.m4a") == "audio"


def test_detecte_audio_wav():
    assert detect_type("enregistrement.wav") == "audio"


def test_detecte_pdf():
    assert detect_type("article.pdf") == "pdf"


def test_inconnu_retourne_unknown():
    assert detect_type("fichier.xyz") == "unknown"
