"""Actual pgpq binary COPY and source fencing under the restricted writer login."""
from dataclasses import replace
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pyarrow as pa
import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import arrow_publication as arrow
from corpus_structure.semantic.arrow_publication import (
    ArrowPublicationBatch, ArrowPublicationError, StaleAnalysisError,
    publish_arrow, publish_arrow_on_connection, stage_schema,
)
from corpus_structure.semantic.publication import PublicationBatch, ValueRow
from .test_publication import R, Z, batch, seed


def test_exact_frozen_schema_and_content():
    candidate = ArrowPublicationBatch.from_rows(batch())
    assert candidate.content == batch().content
    assert candidate.content is candidate.content
    source = dict(candidate.relations)
    source['entity'] = source['entity'].rename_columns(['wrong'])
    with pytest.raises(ArrowPublicationError, match='schema'):
        ArrowPublicationBatch(R, Z, 'bad', source)
    with pytest.raises(ArrowPublicationError, match='unknown'):
        ArrowPublicationBatch(R, Z, 'bad', {'arbitrary': pa.table({})})
    with pytest.raises(TypeError):
        candidate.relations['entity'] = pa.table({})


def test_optional_numeric_projection_never_rounds_lexical():
    original = PublicationBatch(R, Z, 'numeric', typed_value=(
        ValueRow('a', 'decimal', decimal_lexical='1.234567890123456789', numeric_value=Decimal('1.234567890123456789')),
        ValueRow('b', 'decimal', decimal_lexical='9' * 39, numeric_value=Decimal('9' * 39)),
        ValueRow('c', 'decimal', decimal_lexical='1e-1000', numeric_value=Decimal('1e-1000')),
        ValueRow('d', 'integer', text_value='9' * 39, integer_value=10**39-1),
    ))
    candidate = ArrowPublicationBatch.from_rows(original)
    rows = {r['value_id']: r for r in candidate.relations['typed_value'].to_pylist()}
    assert rows['a']['numeric_value'] is None  # shared scale 0 cannot represent it
    assert rows['b']['numeric_value'] is None
    assert rows['c']['numeric_value'] is None
    assert rows['d']['integer_value'] is None
    assert [r['decimal_lexical'] for r in rows.values()] == ['1.234567890123456789', '9'*39, '1e-1000', None]
    relation = pa.Table.from_pylist([{'value_id':'bad','kind':'decimal','decimal_lexical':'1.11',
                                    'numeric_value':Decimal('1.12')}],
                                  schema=stage_schema('typed_value', decimals={'numeric_value':pa.decimal128(38,2)}))
    with pytest.raises(ArrowPublicationError, match='contradicts'):
        ArrowPublicationBatch(R, Z, 'bad', {'typed_value':relation})


def test_native_arrow_copy_receipt_and_fence(semantic_db_engine, semantic_writer_engine):
    seed(semantic_db_engine)
    candidate = ArrowPublicationBatch.from_rows(batch(), expected_data_revision=0)
    receipt = publish_arrow(semantic_writer_engine, candidate)
    assert receipt.data_revision == 1
    # The old source revision is still valid for exact receipt recovery.
    assert publish_arrow(semantic_writer_engine, candidate) == receipt
    with semantic_db_engine.connect() as conn:
        assert bytes(conn.scalar(text('SELECT content FROM data.batch'))) == candidate.content
        assert conn.scalar(text('SELECT count(*) FROM data.occurrence')) == 2
    stale = ArrowPublicationBatch.from_rows(batch('stale', entity='other'), expected_data_revision=0)
    with pytest.raises(StaleAnalysisError, match='recompute'):
        publish_arrow(semantic_writer_engine, stale)
    with semantic_writer_engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM data.fact')) == 1
        assert conn.scalar(text('SELECT count(*) FROM sem.release')) == 1
    with semantic_writer_engine.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(text("INSERT INTO data.entity(release_id,realization_id,entity_id) VALUES ('x','x','x')"))


def test_native_binary_copy_invalid_null_is_atomic(semantic_db_engine, semantic_writer_engine):
    seed(semantic_db_engine)
    invalid = ArrowPublicationBatch(R, Z, 'bad', {
        'entity':pa.Table.from_pylist([{'entity_id':None}], schema=stage_schema('entity')),
    })
    with pytest.raises(DBAPIError):
        publish_arrow(semantic_writer_engine, invalid)
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM data.batch')) == 0
        assert conn.scalar(text('SELECT count(*) FROM data.entity')) == 0


def test_arrow_serialization_retry_replays_same_buffers(semantic_db_engine, semantic_writer_engine, monkeypatch):
    seed(semantic_db_engine)
    barrier = Barrier(2)
    original = arrow.stage_arrow
    seen = []
    states = []
    def staged(conn, candidate):
        seen.append((id(candidate), candidate.batch_id, id(candidate.content)))
        original(conn, candidate)
        if sum(v[1] == candidate.batch_id for v in seen) == 1:
            barrier.wait(timeout=10)
    monkeypatch.setattr(arrow, 'stage_arrow', staged)
    event.listen(semantic_writer_engine, 'handle_error', lambda ctx: states.append(getattr(ctx.original_exception,'sqlstate',None)))
    candidates = [ArrowPublicationBatch.from_rows(batch(x, entity=x)) for x in ('a','b')]
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(lambda c: publish_arrow(semantic_writer_engine,c), candidates))
    assert {r.data_revision for r in receipts} == {1,2}
    assert '40001' in states
    assert len(seen) >= 3
    assert all(v == (id(c), c.batch_id, id(c.content)) for c in candidates for v in seen if v[1] == c.batch_id)


def test_arrow_ambiguous_commit_resolves_receipt(semantic_db_engine, semantic_writer_engine, monkeypatch):
    import psycopg
    seed(semantic_db_engine)
    original = semantic_writer_engine.dialect.do_commit
    commits = []
    def lost(driver):
        original(driver)
        commits.append(1)
        if len(commits) == 1:
            raise psycopg.OperationalError('lost after commit')
    monkeypatch.setattr(semantic_writer_engine.dialect, 'do_commit', lost)
    assert publish_arrow(semantic_writer_engine, ArrowPublicationBatch.from_rows(batch(), expected_data_revision=0)).data_revision == 1
    assert len(commits) == 1


def test_arrow_cancel_rolls_back(semantic_db_engine, semantic_writer_engine, monkeypatch):
    seed(semantic_db_engine)
    original = arrow.stage_arrow
    def cancelled(conn, candidate):
        original(conn, candidate)
        raise KeyboardInterrupt('cancelled after COPY')
    monkeypatch.setattr(arrow, 'stage_arrow', cancelled)
    with pytest.raises(KeyboardInterrupt):
        publish_arrow(semantic_writer_engine, ArrowPublicationBatch.from_rows(batch()))
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM data.batch')) == 0
        assert conn.scalar(text('SELECT count(*) FROM data.entity')) == 0
