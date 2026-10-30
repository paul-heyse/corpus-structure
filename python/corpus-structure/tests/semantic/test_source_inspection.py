"""Actual source inspection keeps run/build custody and qualified range answers."""

import pytest

from corpus_structure.semantic.parsing_products import (
    prepare_parsing_product,
    store_parsing_product,
)
from corpus_structure.serve.source import SourceRequest, inspect_source

from .test_operations import setup
from .test_parsing_products import _native_build, product_values


def test_source_inspection_uses_retained_product_and_reports_partial_origins(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    prepared = setup(semantic_db_engine, observations=True, composed=True)
    with semantic_writer_engine.begin() as conn:
        run, task, attempt, rendition = _native_build(conn, prepared, b"a\xc3\xa9 ", tmp_path)
        product = prepare_parsing_product(product_values(), b"a\xc3\xa9 ")
        store_parsing_product(
            conn, task_id=task, attempt=attempt, holder="fixture", product=product
        )
    with semantic_reader_engine.begin() as conn:
        selection = dict(run_id=run, rendition_id=rendition, producing_task_id=task)
        answer = inspect_source(conn, SourceRequest(**selection, view="components", start=0, end=3))
        assert answer.outcome == "complete"
        assert answer.product_digest == product.digest
        assert [(row["start_offset"], row["end_offset"]) for row in answer.rows] == [(0, 2), (2, 3)]
        traced = inspect_source(conn, SourceRequest(**selection, view="trace", start=0, end=1))
        assert traced.outcome == "partial"
        with pytest.raises(ValueError, match="exact origin"):
            inspect_source(
                conn, SourceRequest(**selection, view="trace", start=0, end=1, require_exact=True)
            )
        missing = inspect_source(
            conn, SourceRequest(**{**selection, "producing_task_id": task + 100000})
        )
        assert missing.outcome == "unavailable" and missing.rows == []
        assert missing.diagnostics
