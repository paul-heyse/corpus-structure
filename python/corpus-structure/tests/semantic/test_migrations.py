"""Native checks for the new migration history; fixture creates a uniquely owned database."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import Engine, insert, inspect, text
from sqlalchemy.exc import IntegrityError

from corpus_structure.semantic.metadata import metadata, table
from corpus_structure.semantic.migrations import current_revision, downgrade, upgrade


def test_native_bootstrap_and_subsequent_projection(semantic_bare_engine: Engine) -> None:
    with semantic_bare_engine.begin() as conn:
        assert current_revision(conn) is None
        upgrade(conn)
        catalog = inspect(conn)
        assert {"sem", "data"} <= set(catalog.get_schema_names())
        assert "selected_fact" in catalog.get_view_names(schema="data")
        for item in metadata.tables.values():
            assert {c["name"] for c in catalog.get_columns(item.name, schema=item.schema)} == set(
                item.c.keys()
            )
        nested = catalog.get_foreign_keys("typed_value", schema="data")
        assert any(
            fk["constrained_columns"] == ["realization_id", "release_id", "entity_id"]
            and fk["referred_table"] == "entity"
            and fk["referred_columns"] == ["realization_id", "release_id", "entity_id"]
            for fk in nested
        )
        assert "kb" in catalog.get_schema_names()
        assert "meta" not in catalog.get_schema_names()
        assert "claim" not in catalog.get_table_names(schema="kb")


def _seed(conn) -> tuple[str, str]:
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

    releases = []
    for label in ("a", "b"):
        bundle = SourceBundle(
            label,
            (
                SourceArtifact(
                    label,
                    (
                        f"id: https://example/{label}\nname: {label}\n"
                        "prefixes: {ex: 'https://example/'}\n"
                        "default_prefix: ex\nclasses: {}\n"
                    ).encode(),
                ),
            ),
        )
        prepared = prepare_release(bundle, ResolvedDependencies())
        persist_release(conn, bundle, ResolvedDependencies(), PreparationProfile(), prepared)
        releases.append(prepared.release_id)
    conn.execute(insert(table("data.project")).values(project_id="p"))
    conn.execute(
        insert(table("data.realization")),
        [
            dict(realization_id="r" + label, project_id="p", release_id=release)
            for label, release in zip(("a", "b"), releases, strict=True)
        ],
    )
    conn.execute(
        insert(table("data.entity")).values(
            realization_id="ra", release_id=releases[0], entity_id="e"
        )
    )
    return releases[0], releases[1]


def test_native_cross_realization_and_variant_constraints(semantic_db_engine: Engine) -> None:
    with semantic_db_engine.begin() as conn:
        release_a, release_b = _seed(conn)
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(
                insert(table("data.typed_value")).values(
                    realization_id="rb",
                    release_id=release_b,
                    value_id="v",
                    kind="entity",
                    entity_id="e",
                )
            )
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(
                insert(table("data.typed_value")).values(
                    realization_id="ra",
                    release_id=release_a,
                    value_id="v",
                    kind="entity",
                    entity_id="e",
                    text_value="hidden scalar",
                )
            )
        conn.execute(
            insert(table("data.typed_value")).values(
                realization_id="ra",
                release_id=release_a,
                value_id="huge",
                kind="decimal",
                decimal_lexical="1e200000",
            )
        )
        assert (
            conn.scalar(
                text("SELECT decimal_lexical FROM data.typed_value WHERE value_id = 'huge'")
            )
            == "1e200000"
        )
        large = "1234567890" * 1000
        conn.execute(
            insert(table("data.typed_value")).values(
                realization_id="ra",
                release_id=release_a,
                value_id="large-number",
                kind="decimal",
                decimal_lexical=large,
                numeric_value=Decimal(large),
            )
        )
        conn.execute(
            insert(table("data.typed_value")).values(
                realization_id="ra",
                release_id=release_a,
                value_id="large-text",
                kind="string",
                text_value=large,
            )
        )
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(
                insert(table("data.typed_value")).values(
                    realization_id="ra",
                    release_id=release_a,
                    value_id="fractional-integer",
                    kind="integer",
                    text_value="1",
                    integer_value="1.5",
                )
            )


def test_bootstrap_downgrade_refuses_destructive_reversal(semantic_db_engine: Engine) -> None:
    with semantic_db_engine.begin() as conn:
        before = current_revision(conn)
        with pytest.raises(RuntimeError, match="destructive"):
            downgrade(conn)
        assert current_revision(conn) == before
        assert "selected_fact" in inspect(conn).get_view_names(schema="data")


def test_partial_scalar_indexes_do_not_limit_exact_payload_size(semantic_db_engine: Engine) -> None:
    lexical = "9" * 10000
    with semantic_db_engine.begin() as conn:
        release_a, _release_b = _seed(conn)
        values = table("data.typed_value")
        conn.execute(
            insert(values),
            [
                dict(
                    realization_id="ra",
                    release_id=release_a,
                    value_id="text",
                    kind="string",
                    text_value=lexical,
                    decimal_lexical=None,
                    numeric_value=None,
                ),
                dict(
                    realization_id="ra",
                    release_id=release_a,
                    value_id="decimal",
                    kind="decimal",
                    text_value=None,
                    decimal_lexical=lexical,
                    numeric_value=Decimal(lexical),
                ),
            ],
        )
        assert (
            conn.scalar(text("SELECT text_value FROM data.typed_value WHERE value_id='text'"))
            == lexical
        )
        assert (
            conn.scalar(
                text("SELECT numeric_value::text FROM data.typed_value WHERE value_id='decimal'")
            )
            == lexical
        )
        predicates = [
            item["dialect_options"].get("postgresql_where", "")
            for item in inspect(conn).get_indexes("typed_value", schema="data")
        ]
        assert sum("octet_length" in p for p in predicates) == 2
