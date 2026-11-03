"""Transport batch size does not determine the native authority transaction lifetime."""

from contextlib import contextmanager

import pytest

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.orchestrate import pdf_streaming
from corpus_structure.semantic import pdf_publication


@pytest.mark.parametrize("failure", [False, True])
def test_companion_chunks_prepare_outside_transactions_and_commit_independently(
    monkeypatch, failure
):
    active = False
    boundaries = []
    chunks = []

    @contextmanager
    def transaction(*args):
        nonlocal active
        assert not active
        active = True
        try:
            yield object()
        except Exception:
            boundaries.append("rollback")
            raise
        else:
            boundaries.append("commit")
        finally:
            active = False

    def records():
        for ordinal in range(130):
            assert not active, "source decoding must not retain the task row lock"
            yield {"ordinal": ordinal}

    def adopt(conn, build, family, rows, replay_key, *, start_ordinal, cancellation):
        assert active
        chunks.append((len(rows), start_ordinal, replay_key))
        if failure and len(chunks) == 2:
            raise RuntimeError("independent second chunk failure")

    monkeypatch.setattr(pdf_streaming, "_pdf_transaction", transaction)
    monkeypatch.setattr(pdf_publication, "adopt_pdf_companion_batch", adopt)
    from typing import Any, cast

    def run():
        pdf_streaming.adopt_pdf_companions(
            cast(Any, None), cast(Any, None), "health", records(), "replay",
            start_ordinal=10, check_active=lambda: None, cancellation=BorrowerCancellation(),
        )

    if failure:
        with pytest.raises(RuntimeError, match="second chunk"):
            run()
        assert boundaries == ["commit", "rollback"]
        assert chunks == [(64, 10, "replay:rows:10"), (64, 74, "replay:rows:74")]
    else:
        run()
        assert boundaries == ["commit", "commit", "commit"]
        assert chunks == [
            (64, 10, "replay:rows:10"), (64, 74, "replay:rows:74"), (2, 138, "replay:rows:138")
        ]
