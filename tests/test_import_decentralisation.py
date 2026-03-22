from scripts.import_decentralisation import (
    extract_inline_tags, normalize_tag, pascal_to_kebab, extract_creation_date
)


def test_extrait_tags_inline():
    content = "Texte\n- #blockchain\n- #décentralisation\n- #économie\n"
    tags = extract_inline_tags(content)
    assert "blockchain" in tags
    assert "décentralisation" in tags


def test_normalise_tag_supprime_accents():
    assert normalize_tag("décentralisation") == "decentralisation"
    assert normalize_tag("Économie") == "economie"
    assert normalize_tag("auto-organisation") == "auto-organisation"


def test_pascal_to_kebab():
    assert pascal_to_kebab("Fragilite-des-systemes-centralises") == \
           "fragilite-des-systemes-centralises"
    assert pascal_to_kebab("Definition-et-interet-des-desir-paths") == \
           "definition-et-interet-des-desir-paths"


def test_extrait_date_creation():
    content = "**Créé le :** 2025-07-14T09:49:56.123Z\n"
    assert extract_creation_date(content) == "2025-07-14"


def test_extrait_date_creation_fallback():
    assert extract_creation_date("pas de date") == "2025-07-14"
