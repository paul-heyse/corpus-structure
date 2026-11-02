"""Actual pgpq binary COPY and source fencing under the restricted writer login."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from threading import Barrier
from typing import Any, cast

import psycopg
import pyarrow as pa
import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import arrow_publication as arrow
from corpus_structure.semantic.arrow_publication import (
    ArrowPublicationBatch,
    ArrowPublicationError,
    SnapshotDerivedPublication,
    StaleAnalysisError,
    publish_arrow,
    stage_schema,
)
from corpus_structure.semantic.identity import fact_key, occurrence_key
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

from .test_publication import fixture_model
from .test_publication import seed as seed_publication

R = fixture_model()[1].release_id
Z = "realization:test"
C = "https://example/Thing"
P = "https://example/label"


def seed(engine):
    """Use the immutable archive and the current composed inference protocol."""
    prepared = seed_publication(engine)
    assert prepared.release_id == R


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


def derived_rows(result, *, identity=None, expected_data_revision=None):
    return SnapshotDerivedPublication.from_rows(
        replace(result.batch, batch_id=identity) if identity is not None else result.batch,
        source=replace(result.binding, data_revision=expected_data_revision)
        if expected_data_revision is not None
        else result.binding,
        operation_id="publish_inference",
        projection_id="accepted",
    )


def inference_fixture(admin, writer):
    from .test_inference import compute, setup

    binding, _ = setup(admin, writer, [("a", "b"), ("b", "c")], rules=("transitive",))
    return compute(writer, binding)


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
    result = inference_fixture(semantic_db_engine, semantic_writer_engine)
    candidate = derived_rows(result)
    receipt = publish_arrow(semantic_writer_engine, candidate)
    assert receipt.data_revision == 2
    # The old source revision is still valid for exact receipt recovery.
    assert publish_arrow(semantic_writer_engine, candidate) == receipt
    with semantic_db_engine.connect() as conn:
        assert (
            bytes(
                conn.scalar(
                    text("SELECT content FROM data.batch WHERE batch_id=:batch"),
                    {"batch": candidate.batch_id},
                )
            )
            == candidate.content
        )
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 2
    stale = derived_rows(result, identity="stale")
    with pytest.raises(StaleAnalysisError, match="recompute"):
        publish_arrow(semantic_writer_engine, stale)
    with semantic_writer_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.fact")) == 3
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
            ArrowPublicationBatch.from_rows(batch()),
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
    from corpus_structure.semantic.arrow_transfer import ArrowWriteProfile

    original = ArrowWriteProfile.new_encoder

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
        ArrowWriteProfile, "new_encoder", lambda profile: CorruptEncoder(original(profile))
    )
    with pytest.raises(psycopg.errors.BadCopyFileFormat):
        publish_arrow(semantic_writer_engine, candidate)
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 0
        assert conn.scalar(text("SELECT count(*) FROM data.entity")) == 0


def test_analysis_serialization_requires_recomputation(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
    result = inference_fixture(semantic_db_engine, semantic_writer_engine)
    barrier = Barrier(2)
    original = arrow.stage_arrow
    seen = []

    def staged(conn, candidate):
        seen.append(candidate.batch_id)
        original(conn, candidate)
        if seen.count(candidate.batch_id) == 1:
            barrier.wait(timeout=10)

    monkeypatch.setattr(arrow, "stage_arrow", staged)
    candidates = [derived_rows(result, identity=x) for x in ("a", "b")]

    def attempt(candidate):
        try:
            return publish_arrow(semantic_writer_engine, candidate)
        except StaleAnalysisError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, candidates))
    assert sum(isinstance(r, StaleAnalysisError) for r in results) == 1
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 2
        assert conn.scalar(text("SELECT data_revision FROM data.realization")) == 2


def test_derived_publication_requires_explicit_intent_and_keeps_it_disjoint():
    from corpus_structure.semantic.arrow_publication import AppendPublication
    from corpus_structure.semantic.query import SnapshotBinding

    source = SnapshotBinding(R, Z, 0, "capture")
    derived = SnapshotDerivedPublication.from_rows(
        batch(), source=source, operation_id="publish_inference", projection_id="accepted"
    )
    assert not isinstance(derived, AppendPublication)
    assert derived.source == source
    with pytest.raises(ArrowPublicationError, match="operation, projection"):
        SnapshotDerivedPublication.from_rows(
            batch(), source=source, operation_id="", projection_id="captured"
        )
    with pytest.raises(TypeError):
        from typing import Any, cast

        cast(Any, AppendPublication.from_rows)(batch(), expected_data_revision=0)


@pytest.mark.parametrize(
    "changes",
    [
        {"operation": "arbitrary-analysis"},
        {"contract": "captured"},
        {"projection": "unbound"},
        {"source_release": "another-release"},
        {"cut": 1},
        {"profile": "unadmitted-profile"},
    ],
)
def test_native_derived_model_binding_refuses_unbound_intent(
    semantic_db_engine,
    semantic_writer_engine,
    changes,
):
    result = inference_fixture(semantic_db_engine, semantic_writer_engine)
    candidate = ArrowPublicationBatch.from_rows(result.batch)
    binding = result.binding
    params = dict(
        r=binding.release_id,
        z=binding.realization_id,
        b=candidate.batch_id,
        content=candidate.content,
        source_release=binding.release_id,
        source_realization=binding.realization_id,
        revision=binding.data_revision,
        capture="capture",
        operation="publish_inference",
        projection="accepted",
        contract="accepted",
        cut=None,
        profile=None,
    )
    params.update(changes)
    with (
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
        pytest.raises(DBAPIError),
    ):
        arrow.stage_arrow(conn, candidate)
        conn.execute(
            text(
                "SELECT data.publish_derived_batch_v2(:r,:z,:b,:content,"
                ":source_release,:source_realization,:revision,:capture,"
                ":operation,:projection,:contract,:cut,:profile)"
            ),
            params,
        )
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 1


def test_native_legacy_derived_abi_cannot_admit_new_intent(
    semantic_db_engine,
    semantic_writer_engine,
):
    seed(semantic_db_engine)
    candidate = ArrowPublicationBatch.from_rows(batch())
    with (
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
        pytest.raises(DBAPIError, match="model-bound v2 ABI"),
    ):
        arrow.stage_arrow(conn, candidate)
        conn.execute(
            text(
                "SELECT data.publish_derived_batch(:r,:z,:b,:content,"
                ":r,:z,0,'capture','publish_inference','accepted')"
            ),
            {"r": R, "z": Z, "b": candidate.batch_id, "content": candidate.content},
        )


def test_native_inference_effect_refuses_assertion_rows(semantic_db_engine, semantic_writer_engine):
    seed(semantic_db_engine)
    from corpus_structure.semantic.query import SnapshotBinding

    source = SnapshotBinding(R, Z, 0, "capture")
    candidate = SnapshotDerivedPublication.from_rows(
        batch(), source=source, operation_id="publish_inference", projection_id="accepted"
    )
    with pytest.raises(DBAPIError, match="source/assertion transport rows"):
        publish_arrow(semantic_writer_engine, candidate)


def test_native_inference_effect_requires_staged_proof(semantic_db_engine, semantic_writer_engine):
    from corpus_structure.semantic.inference import InferenceResult

    result = inference_fixture(semantic_db_engine, semantic_writer_engine)
    forged = InferenceResult(
        result.binding, replace(result.batch, derivation=(), derivation_premise=())
    )
    with pytest.raises(DBAPIError, match="lacks its staged proof conclusion"):
        publish_arrow(semantic_writer_engine, derived_rows(forged))


def test_derived_composes_actual_owned_transport_without_another_freeze(monkeypatch):
    from corpus_structure.semantic.query import SnapshotBinding

    owned = arrow.AppendPublication.from_rows(batch())
    content = owned.content

    def no_second_freeze(*args, **kwargs):
        raise AssertionError("owned transport was frozen again")

    monkeypatch.setattr(arrow.AppendPublication, "__init__", no_second_freeze)
    derived = SnapshotDerivedPublication.from_transport(
        owned,
        source=SnapshotBinding(R, Z, 0, "capture"),
        operation_id="publish_inference",
        projection_id="accepted",
    )
    assert derived.transport is owned
    assert derived.content is content
    with pytest.raises(ArrowPublicationError, match="owned AppendPublication"):
        SnapshotDerivedPublication.from_transport(
            cast(Any, batch()),
            source=SnapshotBinding(R, Z, 0, "capture"),
            operation_id="publish_inference",
            projection_id="accepted",
        )


def test_derived_row_adapter_freezes_each_stage_only_once(monkeypatch):
    from corpus_structure.semantic.query import SnapshotBinding

    original = arrow.AppendPublication.__init__
    calls = []

    def counted(self, *args, **kwargs):
        calls.append(args)
        original(self, *args, **kwargs)

    monkeypatch.setattr(arrow.AppendPublication, "__init__", counted)
    derived = SnapshotDerivedPublication.from_rows(
        batch(),
        source=SnapshotBinding(R, Z, 0, "capture"),
        operation_id="publish_inference",
        projection_id="accepted",
    )
    assert len(calls) == 1
    assert derived.content == batch().content


@pytest.mark.parametrize("lost", [False, True])
def test_inference_retries_and_recovers_using_actual_lowered_transport(monkeypatch, lost):
    from sqlalchemy import create_engine

    from corpus_structure.semantic import inference, publication
    from corpus_structure.semantic.publication import PublicationReceipt
    from corpus_structure.semantic.query import SnapshotBinding

    rows = PublicationBatch(
        R,
        Z,
        "overflow",
        typed_value=(
            ValueRow("huge", "decimal", decimal_lexical="9" * 39, numeric_value=Decimal("9" * 39)),
        ),
    )
    result = inference.InferenceResult(SnapshotBinding(R, Z, 0, "capture"), rows)
    seen = []
    receipt = PublicationReceipt("overflow", 1, "receipt")

    def publish(conn, transport):
        seen.append(transport)
        assert transport.content != rows.content
        assert transport.relations["typed_value"]["numeric_value"].to_pylist() == [None]
        if len(seen) == 1:
            if lost:
                raise psycopg.OperationalError("lost after publication")
            raise psycopg.errors.SerializationFailure("retry")
        return receipt

    def lookup(engine, transport):
        assert transport is seen[0]
        assert transport.content is seen[0].content
        return receipt

    monkeypatch.setattr(arrow, "publish_arrow_on_connection", publish)
    monkeypatch.setattr(publication, "lookup_receipt", lookup)
    engine = create_engine("sqlite://")
    try:
        if lost:
            # This fabricated no-code error occurs before commit: it proves neither
            # connection loss nor ambiguous commit, and must not trigger receipt lookup.
            from corpus_structure.core.db.store import (
                DatabaseCause,
                EffectKnowledge,
                operation_failure,
            )

            with pytest.raises(psycopg.OperationalError) as error:
                inference.publish_inference(engine, result, attempts=2)
            failure = operation_failure(error.value).failure
            assert failure.cause is DatabaseCause.UNKNOWN_OPERATIONAL
            assert failure.effects is EffectKnowledge.ROLLED_BACK
        else:
            assert inference.publish_inference(engine, result, attempts=2) == receipt
    finally:
        engine.dispose()
    assert len(seen) == (1 if lost else 2)
    assert all(transport is seen[0] for transport in seen)


def test_encoder_failure_discards_stream_and_fresh_replay_is_atomic(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
    from corpus_structure.semantic.arrow_transfer import ArrowWriteProfile

    seed(semantic_db_engine)
    candidate = ArrowPublicationBatch.from_rows(batch("encoder-replay"))
    factory = ArrowWriteProfile.new_encoder
    finished = []

    class FailedEncoder:
        def __init__(self, encoder):
            self.encoder = encoder

        def write_header(self):
            return self.encoder.write_header()

        def write_batch(self, rows):
            self.encoder.write_batch(rows)
            raise ValueError("forced encoder failure after buffering")

        def finish(self):
            finished.append(True)
            raise AssertionError("failed encoder must never be finished")

    def fail_entity(profile):
        encoder = factory(profile)
        return FailedEncoder(encoder) if profile.operation == "publication:entity" else encoder

    with monkeypatch.context() as patch:
        patch.setattr(ArrowWriteProfile, "new_encoder", fail_entity)
        with pytest.raises(ValueError, match="forced encoder failure"):
            publish_arrow(semantic_writer_engine, candidate)
    assert finished == []
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 0
        assert conn.scalar(text("SELECT count(*) FROM data.entity")) == 0
    assert publish_arrow(semantic_writer_engine, candidate).batch_id == "encoder-replay"
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 1
        assert conn.scalar(text("SELECT count(*) FROM data.entity")) == 1
