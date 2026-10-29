"""Native checks for the new migration history; fixture creates a uniquely owned database."""

from __future__ import annotations

import pytest
from decimal import Decimal
from sqlalchemy import Engine, inspect, insert, text
from sqlalchemy.exc import IntegrityError

from corpus_structure.semantic.metadata import metadata, table
from corpus_structure.semantic.migrations import current_revision, downgrade, upgrade


def test_native_bootstrap_and_subsequent_projection(semantic_db_engine: Engine) -> None:
    with semantic_db_engine.begin() as conn:
        assert current_revision(conn) is not None
        upgrade(conn)
        catalog = inspect(conn)
        assert {'sem', 'data'} <= set(catalog.get_schema_names())
        assert 'selected_fact' in catalog.get_view_names(schema='data')
        for item in metadata.tables.values():
            assert {c['name'] for c in catalog.get_columns(item.name, schema=item.schema)} == set(item.c.keys())
        nested = catalog.get_foreign_keys('typed_value', schema='data')
        assert any(fk['constrained_columns'] == ['realization_id','release_id','entity_id']
                   and fk['referred_table'] == 'entity'
                   and fk['referred_columns'] == ['realization_id','release_id','entity_id']
                   for fk in nested)
        assert not {'kb','meta'} & set(catalog.get_schema_names())


def _seed(conn) -> None:
    conn.execute(insert(table('sem.release')), [dict(release_id=x,content_digest=x,profile='test',prepared_bytes=b'{}',manifest_bytes=b'{}') for x in ['a','b']])
    conn.execute(insert(table('data.project')).values(project_id='p'))
    conn.execute(insert(table('data.realization')), [dict(realization_id='r'+x,project_id='p',release_id=x) for x in ['a','b']])
    conn.execute(insert(table('data.entity')).values(realization_id='ra',release_id='a',entity_id='e'))


def test_native_cross_realization_and_variant_constraints(semantic_db_engine: Engine) -> None:
    with semantic_db_engine.begin() as conn:
        _seed(conn)
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(insert(table('data.typed_value')).values(realization_id='rb',release_id='b',value_id='v',kind='entity',entity_id='e'))
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(insert(table('data.typed_value')).values(realization_id='ra',release_id='a',value_id='v',kind='entity',entity_id='e',text_value='hidden scalar'))
        conn.execute(insert(table('data.typed_value')).values(realization_id='ra',release_id='a',value_id='huge',kind='decimal',decimal_lexical='1e200000'))
        assert conn.scalar(text("SELECT decimal_lexical FROM data.typed_value WHERE value_id = 'huge'")) == '1e200000'
        large = '1234567890' * 1000
        conn.execute(insert(table('data.typed_value')).values(realization_id='ra',release_id='a',value_id='large-number',kind='decimal',decimal_lexical=large,numeric_value=Decimal(large)))
        conn.execute(insert(table('data.typed_value')).values(realization_id='ra',release_id='a',value_id='large-text',kind='string',text_value=large))
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(insert(table('data.typed_value')).values(realization_id='ra',release_id='a',value_id='fractional-integer',kind='integer',text_value='1',integer_value='1.5'))


def test_bootstrap_downgrade_refuses_destructive_reversal(semantic_db_engine: Engine) -> None:
    with semantic_db_engine.begin() as conn:
        before = current_revision(conn)
        with pytest.raises(RuntimeError, match='destructive'):
            downgrade(conn)
        assert current_revision(conn) == before
        assert 'selected_fact' in inspect(conn).get_view_names(schema='data')
