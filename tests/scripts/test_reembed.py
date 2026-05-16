"""Test the reembed maintenance script: rebuilds vec tables as cosine."""

from unittest.mock import patch

from tests.conftest import make_embedding


def test_reembed_rebuilds_cosine_and_repopulates(tmp_settings):
    from infrastructure.db import init_db, get_vault_connection

    db_path = tmp_settings.vault_db_path
    init_db(db_path)

    conn = get_vault_connection(db_path)
    conn.execute(
        "INSERT INTO sources(uid, slug, source_type, date_added) "
        "VALUES ('s1', 'src-1', 'texte', '2026-05-16')"
    )
    conn.execute(
        "INSERT INTO chunks(uid, source_uid, position, content, token_count) "
        "VALUES ('c1', 's1', 0, 'hello world', 2)"
    )
    conn.commit()
    conn.close()

    with patch("scripts.reembed.load_settings", return_value=tmp_settings), \
         patch("infrastructure.embedding_provider.embed", return_value=make_embedding()):
        from scripts.reembed import reembed
        n_chunks, n_notes = reembed()

    assert (n_chunks, n_notes) == (1, 0)

    conn = get_vault_connection(db_path)
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'chunks_vec'"
    ).fetchone()[0]
    count = conn.execute("SELECT count(*) FROM chunks_vec").fetchone()[0]
    conn.close()

    assert "distance_metric=cosine" in sql
    assert count == 1
