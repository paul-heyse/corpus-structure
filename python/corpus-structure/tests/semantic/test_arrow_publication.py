"""Actual pgpq binary COPY and source fencing under the restricted writer login."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from typing import Any

import psycopg
import pyarrow as pa
import pytest
from sqlalchemy import event, insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import arrow_publication as arrow
from corpus_structure.semantic.arrow_publication import (
    ArrowPublicationBatch,
    ArrowPublicationError,
    StaleAnalysisError,
    publish_arrow,
    stage_schema,
)
from corpus_structure.semantic.identity import fact_key, occurrence_key
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    EntityRow,
    EvidenceRow,
    FactRow,
    MembershipRow,
    MembershipSupportRow,
    OccurrenceRow,
    PublicationBatch,
    SelectionRow,
    SupportRow,
    ValueRow,
)

R = "release:test"
Z = "realization:test"
C = "https://example/Thing"
P = "https://example/label"


def seed(engine):
    """An explicit small registry; no application preparation or semantic result oracle."""
    with engine.begin() as conn:
        for name, values in (
            (
                "sem.release",
                dict(
                    release_id=R,
                    content_digest="test",
                    profile="test",
                    prepared_bytes=b"{}",
                    manifest_bytes=b"{}",
                ),
            ),
            ("sem.class_definition", dict(release_id=R, class_id=C, name="Thing", iri=C)),
            ("sem.property_definition", dict(release_id=R, property_id=P, name="label", iri=P)),
            (
                "sem.property_applicability",
                dict(
                    release_id=R,
                    class_id=C,
                    property_id=P,
                    range_name="string",
                    required=False,
                    multivalued=False,
                    constraint_scope="accepted_value",
                    constraints={"name": "label", "inlined": False, "case_policy": "casefold"},
                ),
            ),
            ("data.project", dict(project_id="p")),
            ("data.realization", dict(realization_id=Z, release_id=R, project_id="p")),
        ):
            conn.execute(insert(table(name)).values(**values))


def batch(identity="b", *, entity="e"):
    fact = fact_key(R, Z, entity, P, "Straße", {})
    occurrences = [occurrence_key(R, Z, "source", str(i) + identity) for i in (1, 2)]
    return PublicationBatch(
        R,
        Z,
        identity,
        entity=(EntityRow(entity),),
        membership=(MembershipRow(entity, C, "source assertion"),),
        typed_value=(ValueRow("v" + identity, "string", text_value="Straße"),),
        fact=(FactRow(fact, entity, P, "v" + identity),),
        occurrence=tuple(
            OccurrenceRow(key, fact, "source", str(i) + identity, "v" + identity)
            for i, key in zip((1, 2), occurrences, strict=True)
        ),
        support=tuple(SupportRow(fact, key) for key in occurrences),
        selection=(SelectionRow(fact),),
        evidence=(EvidenceRow("evidence" + identity, "urn:source", "line:1", "test", "1"),),
        membership_support=(MembershipSupportRow(entity, C, "evidence" + identity),),
    )


def test_exact_frozen_schema_and_content():
    candidate = ArrowPublicationBatch.from_rows(batch())
    assert candidate.content == batch().content
    assert candidate.content is candidate.content
    source = dict(candidate.relations)
    source["entity"] = source["entity"].rename_columns(["wrong"])
    with pytest.raises(ArrowPublicationError, match="schema"):
        ArrowPublicationBatch(R, Z, "bad", source)
    with pytest.raises(ArrowPublicationError, match="unknown"):
        ArrowPublicationBatch(R, Z, "bad", {"arbitrary": pa.table({})})
    with pytest.raises(TypeError):
        invalid: Any = candidate.relations
        invalid["entity"] = pa.table({})


def test_optional_numeric_projection_never_rounds_lexical():
    original = PublicationBatch(
        R,
        Z,
        "numeric",
        typed_value=(
            ValueRow(
                "a",
                "decimal",
                decimal_lexical="1.234567890123456789",
                numeric_value=Decimal("1.234567890123456789"),
            ),
            ValueRow("b", "decimal", decimal_lexical="9" * 39, numeric_value=Decimal("9" * 39)),
            ValueRow("c", "decimal", decimal_lexical="1e-1000", numeric_value=Decimal("1e-1000")),
            ValueRow("d", "integer", text_value="9" * 39, integer_value=10**39 - 1),
        ),
    )
    candidate = ArrowPublicationBatch.from_rows(original)
    rows = {r["value_id"]: r for r in candidate.relations["typed_value"].to_pylist()}
    assert rows["a"]["numeric_value"] == Decimal("1.234567890123456789")
    assert rows["b"]["numeric_value"] is None
    assert rows["c"]["numeric_value"] is None
    assert rows["d"]["integer_value"] is None
    assert [r["decimal_lexical"] for r in rows.values()] == [
        "1.234567890123456789",
        "9" * 39,
        "1e-1000",
        None,
    ]
    relation = pa.Table.from_pylist(
        [
            {
                "value_id": "bad",
                "kind": "decimal",
                "decimal_lexical": "1.11",
                "numeric_value": Decimal("1.12"),
            }
        ],
        schema=stage_schema("typed_value", decimals={"numeric_value": pa.decimal128(38, 2)}),
    )
    with pytest.raises(ArrowPublicationError, match="contradicts"):
        ArrowPublicationBatch(R, Z, "bad", {"typed_value": relation})


def test_native_arrow_copy_receipt_and_fence(semantic_db_engine, semantic_writer_engine):
    seed(semantic_db_engine)
    candidate = ArrowPublicationBatch.from_rows(batch(), expected_data_revision=0)
    receipt = publish_arrow(semantic_writer_engine, candidate)
    assert receipt.data_revision == 1
    # The old source revision is still valid for exact receipt recovery.
    assert publish_arrow(semantic_writer_engine, candidate) == receipt
    with semantic_db_engine.connect() as conn:
        assert bytes(conn.scalar(text("SELECT content FROM data.batch"))) == candidate.content
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 2
    stale = ArrowPublicationBatch.from_rows(
        batch("stale", entity="other"), expected_data_revision=0
    )
    with pytest.raises(StaleAnalysisError, match="recompute"):
        publish_arrow(semantic_writer_engine, stale)
    with semantic_writer_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.fact")) == 1
        assert conn.scalar(text("SELECT count(*) FROM sem.release")) == 1
    with semantic_writer_engine.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(
            text(
                "INSERT INTO data.entity(release_id,realization_id,entity_id) VALUES ('x','x','x')"
            )
        )


def test_native_binary_copy_invalid_null_is_atomic(semantic_db_engine, semantic_writer_engine):
    seed(semantic_db_engine)
    invalid = ArrowPublicationBatch(
        R,
        Z,
        "bad",
        {
            "entity": pa.Table.from_pylist([{"entity_id": None}], schema=stage_schema("entity")),
        },
    )
    with pytest.raises(DBAPIError):
        publish_arrow(semantic_writer_engine, invalid)
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 0
        assert conn.scalar(text("SELECT count(*) FROM data.entity")) == 0


def test_arrow_serialization_retry_replays_same_buffers(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
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

    monkeypatch.setattr(arrow, "stage_arrow", staged)
    event.listen(
        semantic_writer_engine,
        "handle_error",
        lambda ctx: states.append(getattr(ctx.original_exception, "sqlstate", None)),
    )
    candidates = [ArrowPublicationBatch.from_rows(batch(x, entity=x)) for x in ("a", "b")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(lambda c: publish_arrow(semantic_writer_engine, c), candidates))
    assert {r.data_revision for r in receipts} == {1, 2}
    assert "40001" in states
    assert len(seen) >= 3
    assert all(
        v == (id(c), c.batch_id, id(c.content))
        for c in candidates
        for v in seen
        if v[1] == c.batch_id
    )


def test_arrow_ambiguous_commit_resolves_receipt(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
    import psycopg

    seed(semantic_db_engine)
    original = semantic_writer_engine.dialect.do_commit
    commits = []

    def lost(driver):
        original(driver)
        commits.append(1)
        if len(commits) == 1:
            raise psycopg.OperationalError("lost after commit")

    monkeypatch.setattr(semantic_writer_engine.dialect, "do_commit", lost)
    assert (
        publish_arrow(
            semantic_writer_engine,
            ArrowPublicationBatch.from_rows(batch(), expected_data_revision=0),
        ).data_revision
        == 1
    )
    assert len(commits) == 1


def test_arrow_cancel_rolls_back(semantic_db_engine, semantic_writer_engine, monkeypatch):
    seed(semantic_db_engine)
    original = arrow.stage_arrow

    def cancelled(conn, candidate):
        original(conn, candidate)
        raise KeyboardInterrupt("cancelled after COPY")

    monkeypatch.setattr(arrow, "stage_arrow", cancelled)
    with pytest.raises(KeyboardInterrupt):
        publish_arrow(semantic_writer_engine, ArrowPublicationBatch.from_rows(batch()))
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 0
        assert conn.scalar(text("SELECT count(*) FROM data.entity")) == 0


def test_owned_readonly_buffers_and_batch_replay():
    import numpy as np

    source = np.array([0, 1], dtype=np.int64)
    relation = pa.Table.from_arrays(
        [
            pa.array(["p", "p"]),
            pa.array(["item", "item"]),
            pa.array(source),
            pa.array(["a", "b"]),
        ],
        schema=stage_schema("value_role"),
    )
    candidate = ArrowPublicationBatch(
        R,
        Z,
        "frozen",
        {
            "value_role": tuple(relation.to_batches(max_chunksize=1)),
        },
    )
    content = candidate.content
    source[0] = 99
    assert candidate.relations["value_role"].column("position").to_pylist() == [0, 1]
    assert candidate.content == content
    for chunk in candidate.relations["value_role"].column("position").chunks:
        assert all(not buf.is_mutable for buf in chunk.buffers() if buf is not None)
        with pytest.raises(TypeError):
            memoryview(chunk.buffers()[1])[0] = 9


def test_native_numeric_temporal_and_null_fidelity(semantic_db_engine, semantic_writer_engine):
    seed(semantic_db_engine)
    source = PublicationBatch(
        R,
        Z,
        "scalars",
        typed_value=(
            ValueRow("small", "decimal", decimal_lexical="1.2300", numeric_value=Decimal("1.2300")),
            ValueRow("large", "decimal", decimal_lexical="9" * 39, numeric_value=Decimal("9" * 39)),
            ValueRow(
                "tiny", "decimal", decimal_lexical="1e-1000", numeric_value=Decimal("1e-1000")
            ),
            ValueRow("integer", "integer", text_value="9" * 39, integer_value=10**39 - 1),
            ValueRow("date", "date", text_value="2026-10-29"),
            ValueRow("datetime", "datetime", text_value="2026-10-29T00:00:00.000001+00:00"),
            ValueRow("null", "null"),
            ValueRow("bool", "boolean", boolean_value=False),
        ),
    )
    candidate = ArrowPublicationBatch.from_rows(source)
    assert publish_arrow(semantic_writer_engine, candidate).data_revision == 1
    with semantic_db_engine.connect() as conn:
        values = {
            r.value_id: r
            for r in conn.execute(
                text(
                    "SELECT value_id,text_value,decimal_lexical,numeric_value::text n,"
                    "integer_value::text i,boolean_value FROM data.typed_value"
                )
            )
        }
        assert values["small"].n == "1.2300"
        assert values["large"].decimal_lexical == "9" * 39 and values["large"].n is None
        assert values["tiny"].decimal_lexical == "1e-1000" and values["tiny"].n is None
        assert values["integer"].text_value == "9" * 39 and values["integer"].i is None
        assert values["date"].text_value == "2026-10-29"
        assert values["datetime"].text_value == "2026-10-29T00:00:00.000001+00:00"
        assert values["null"].text_value is None and values["null"].boolean_value is None
        assert values["bool"].boolean_value is False


def test_native_malformed_copy_rolls_back(semantic_db_engine, semantic_writer_engine, monkeypatch):
    seed(semantic_db_engine)
    original = arrow._encoder

    class CorruptEncoder:
        def __init__(self, inner):
            self.inner = inner

        def write_header(self):
            return self.inner.write_header()

        def write_batch(self, chunk):
            return b"\x00"  # truncated row field count; never a valid COPY stream

        def finish(self):
            return self.inner.finish()

    candidate = ArrowPublicationBatch.from_rows(batch())
    monkeypatch.setattr(
        arrow, "_encoder", lambda name, schema: CorruptEncoder(original(name, schema))
    )
    with pytest.raises(psycopg.errors.BadCopyFileFormat):
        publish_arrow(semantic_writer_engine, candidate)
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 0
        assert conn.scalar(text("SELECT count(*) FROM data.entity")) == 0


def test_analysis_serialization_requires_recomputation(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
    seed(semantic_db_engine)
    barrier = Barrier(2)
    original = arrow.stage_arrow
    seen = []

    def staged(conn, candidate):
        seen.append(candidate.batch_id)
        original(conn, candidate)
        if seen.count(candidate.batch_id) == 1:
            barrier.wait(timeout=10)

    monkeypatch.setattr(arrow, "stage_arrow", staged)
    candidates = [
        ArrowPublicationBatch.from_rows(batch(x, entity=x), expected_data_revision=0)
        for x in ("a", "b")
    ]

    def attempt(candidate):
        try:
            return publish_arrow(semantic_writer_engine, candidate)
        except StaleAnalysisError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, candidates))
    assert sum(isinstance(r, StaleAnalysisError) for r in results) == 1
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 1
        assert conn.scalar(text("SELECT data_revision FROM data.realization")) == 1
