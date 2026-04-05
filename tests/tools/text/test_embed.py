from tests.conftest import make_embedding, EMBEDDING_DIMS


def test_embed_text_returns_vector(ctx):
    from tools.text.embed import embed_text

    result = embed_text("hello", ctx)

    assert isinstance(result, list)
    assert len(result) == EMBEDDING_DIMS


def test_embed_text_delegates_to_provider(ctx):
    """embed_text must call ctx.embed and pass the text through."""
    from tools.text.embed import embed_text

    received: list[str] = []

    def tracking_embed(text: str) -> list[float]:
        received.append(text)
        return make_embedding()

    ctx.embed = tracking_embed

    embed_text("test text", ctx)

    assert len(received) == 1
    assert received[0] == "test text"
