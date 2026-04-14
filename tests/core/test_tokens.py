from core.tokens import estimate_tokens, WORDS_PER_TOKEN


def test_empty_string_is_zero_tokens():
    assert estimate_tokens("") == 0


def test_whitespace_only_is_zero_tokens():
    assert estimate_tokens("   \n\t  ") == 0


def test_single_word_estimates_one_token():
    # 1 word / 0.75 = 1.33 → round → 1
    assert estimate_tokens("hello") == 1


def test_short_sentence_estimates_proportional_tokens():
    # 9 words / 0.75 = 12
    text = "the quick brown fox jumps over the lazy dog"
    assert estimate_tokens(text) == 12


def test_constant_value():
    assert WORDS_PER_TOKEN == 0.75
