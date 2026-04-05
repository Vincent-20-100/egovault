from core.uid import generate_uid, make_slug, make_unique_slug


def test_generate_uid_is_uuid4_format():
    uid = generate_uid()
    assert len(uid) == 36
    parts = uid.split("-")
    assert len(parts) == 5
    assert parts[2].startswith("4")  # version 4


def test_make_slug_basic():
    assert make_slug("Hello World") == "hello-world"


def test_make_slug_accents():
    assert make_slug("Élasticité des Prix") == "elasticite-des-prix"


def test_make_slug_special_chars():
    # non-alphanum → hyphen, then collapsed
    assert make_slug("C++ & Python!") == "c-python"


def test_make_slug_already_clean():
    assert make_slug("bitcoin") == "bitcoin"


def test_make_slug_leading_trailing_hyphens():
    assert make_slug("  --hello--  ") == "hello"


def test_make_slug_consecutive_hyphens_collapsed():
    assert make_slug("hello   world") == "hello-world"


def test_make_slug_within_80_chars():
    # 15-char words separated by spaces → slug <= 80 chars
    title = "un " + "a" * 78
    result = make_slug(title)
    assert len(result) <= 80


def test_make_slug_truncate_at_last_hyphen():
    # "un-" + 78 a's = 81 chars → cuts at hyphen → "un"
    title = "un " + "a" * 78
    result = make_slug(title)
    assert result == "un"


def test_make_slug_truncate_no_hyphen_case():
    # single word longer than 80 chars → hard truncate at 80
    title = "a" * 100
    result = make_slug(title)
    assert result == "a" * 80


def test_make_unique_slug_no_collision():
    assert make_unique_slug("Test Title", set()) == "test-title"


def test_make_unique_slug_first_collision():
    existing = {"test-title"}
    assert make_unique_slug("Test Title", existing) == "test-title-2"


def test_make_unique_slug_multiple_collisions():
    existing = {"test-title", "test-title-2", "test-title-3"}
    assert make_unique_slug("Test Title", existing) == "test-title-4"
