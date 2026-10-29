"""Independent native checks of publication under real restricted logins."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from threading import Barrier
from typing import Any

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

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
    RoleRow,
    SelectionRow,
    SupportRow,
    ValueRow,
    publish_batch,
    publish_on_connection,
)

R = "release:test"
Z = "realization:test"
C = "https://example/Thing"
P = "https://example/label"


def seed(engine, *, scope="accepted_value", unique=False):
    with engine.begin() as conn:
        conn.execute(
            insert(table("sem.release")).values(
                release_id=R,
                content_digest="test",
                profile="test",
                prepared_bytes=b"{}",
                manifest_bytes=b"{}",
            )
        )
        conn.execute(
            insert(table("sem.class_definition")).values(
                release_id=R, class_id=C, name="Thing", iri=C
            )
        )
        conn.execute(
            insert(table("sem.property_definition")).values(
                release_id=R, property_id=P, name="label", iri=P
            )
        )
        conn.execute(
            insert(table("sem.property_applicability")).values(
                release_id=R,
                class_id=C,
                property_id=P,
                range_name="string",
                required=False,
                multivalued=False,
                constraint_scope=scope,
                constraints={"name": "label", "inlined": False, "case_policy": "casefold"},
            )
        )
        if unique:
            conn.execute(
                insert(table("sem.identity_slot")).values(
                    release_id=R, class_id=C, group_id="0", position=0, property_id=P
                )
            )
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(realization_id=Z, release_id=R, project_id="p")
        )


def batch(identity="b", *, entity="e", label="Straße", selected=True):
    f = fact_key(R, Z, entity, P, label, {})
    o1 = occurrence_key(R, Z, "source", "1" + identity)
    o2 = occurrence_key(R, Z, "source", "2" + identity)
    return PublicationBatch(
        R,
        Z,
        identity,
        entity=(EntityRow(entity),),
        membership=(MembershipRow(entity, C, "source assertion"),),
        typed_value=(ValueRow("v" + identity, "string", text_value=label),),
        fact=(FactRow(f, entity, P, "v" + identity),),
        occurrence=(
            OccurrenceRow(o1, f, "source", "1" + identity, "v" + identity),
            OccurrenceRow(o2, f, "source", "2" + identity, "v" + identity),
        ),
        support=(SupportRow(f, o1), SupportRow(f, o2)),
        selection=(SelectionRow(f),) if selected else (),
        evidence=(EvidenceRow("evidence" + identity, "urn:source", "line:1", "test", "1"),),
        membership_support=(MembershipSupportRow(entity, C, "evidence" + identity),),
    )


def test_batch_is_immutable_and_numeric_receipt_encoding():
    value = PublicationBatch(
        R,
        Z,
        "b",
        typed_value=(
            ValueRow("n", "decimal", decimal_lexical="100", numeric_value=Decimal("1E+2")),
        ),
    )
    assert b'"100"' in value.content
    with pytest.raises(FrozenInstanceError):
        invalid_mutation: Any = value
        invalid_mutation.batch_id = "other"
    with pytest.raises(TypeError):
        invalid_rows: Any = [EntityRow("e")]
        PublicationBatch(R, Z, "b", entity=invalid_rows)


def test_native_copy_atomic_idempotent_distinct_occurrences(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    candidate = batch()
    first = publish_batch(semantic_writer_engine, candidate)
    assert first.data_revision == 1
    assert publish_batch(semantic_writer_engine, candidate) == first
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 2
        assert conn.scalar(text("SELECT count(*) FROM data.fact")) == 1
        assert conn.scalar(text("SELECT count(*) FROM data.support")) == 2
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 1
        assert bytes(conn.scalar(text("SELECT content FROM data.batch"))) == candidate.content
    with pytest.raises(DBAPIError):
        publish_batch(semantic_writer_engine, replace(candidate, entity=(EntityRow("wrong"),)))


def test_native_rejects_bad_identity_and_leaves_no_partial_state(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    candidate = batch()
    bad = replace(candidate, occurrence=(replace(candidate.occurrence[0], occurrence_id="forged"),))
    with pytest.raises(DBAPIError):
        publish_batch(semantic_writer_engine, bad)
    with semantic_db_engine.connect() as conn:
        for name in ("entity", "typed_value", "fact", "occurrence", "batch"):
            assert conn.scalar(text(f"SELECT count(*) FROM data.{name}")) == 0
        assert conn.scalar(text("SELECT data_revision FROM data.realization")) == 0


def test_native_null_missing_range_and_nested_scope_fk(semantic_db_engine, semantic_writer_engine):
    seed(semantic_db_engine)
    candidate = batch()
    for value in (
        ValueRow("vb", "null"),
        ValueRow("vb", "string"),
        ValueRow("vb", "entity", entity_id="foreign-entity"),
    ):
        with pytest.raises(DBAPIError):
            publish_batch(
                semantic_writer_engine,
                replace(
                    candidate,
                    typed_value=(value,),
                    fact=(replace(candidate.fact[0], object_value_id="vb"),),
                ),
            )
    with pytest.raises(DBAPIError):
        publish_batch(
            semantic_writer_engine,
            replace(candidate, value_role=(RoleRow("vb", "item", 0, "foreign-value"),)),
        )


def test_restricted_role_cannot_bypass_or_replace_stage(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine
):
    seed(semantic_db_engine)
    for engine, statement in (
        (semantic_writer_engine, "INSERT INTO data.entity VALUES ('x','y','z')"),
        (semantic_writer_engine, "CREATE TEMP TABLE sp_entity(entity_id text)"),
        (semantic_reader_engine, "SELECT data.begin_stage()"),
    ):
        with pytest.raises(DBAPIError), engine.begin() as conn:
            conn.execute(text(statement))
    with (
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        conn.execute(text("SELECT data.begin_stage()"))
        for statement in (
            "DROP TABLE pg_temp.sp_entity",
            "ALTER TABLE pg_temp.sp_entity ADD COLUMN hidden text",
            "CREATE TRIGGER malicious BEFORE INSERT ON pg_temp.sp_entity "
            "EXECUTE FUNCTION pg_catalog.suppress_redundant_updates_trigger()",
            "SELECT data.begin_stage()",
        ):
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(text(statement))
    with (
        semantic_db_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        conn.execute(text("CREATE TEMP TABLE sp_entity(entity_id text)"))
        with pytest.raises(DBAPIError), conn.begin_nested():
            conn.execute(text("SELECT data.begin_stage()"))


def test_selected_value_cardinality_retains_unselected_conflicts(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    publish_batch(semantic_writer_engine, batch())
    publish_batch(semantic_writer_engine, batch("conflict", label="Other", selected=False))
    with pytest.raises(DBAPIError):
        publish_batch(
            semantic_writer_engine,
            PublicationBatch(
                R,
                Z,
                "select-conflict",
                selection=(SelectionRow(fact_key(R, Z, "e", P, "Other", {})),),
            ),
        )
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.fact")) == 2
        assert conn.scalar(text("SELECT count(*) FROM data.selection")) == 1
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 4


def test_concurrent_casefold_unique_candidates_have_independent_expected_state(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine, unique=True)
    barrier = Barrier(2)

    def attempt(candidate):
        barrier.wait(timeout=10)
        try:
            return publish_batch(semantic_writer_engine, candidate)
        except DBAPIError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(attempt, batch("a", entity="a", label="Straße")),
            pool.submit(attempt, batch("b", entity="b", label="STRASSE")),
        ]
        results = [f.result(timeout=30) for f in futures]
    assert sum(result is not None for result in results) == 1
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.entity")) == 1
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 1
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 2


def test_connection_api_never_commits_and_requires_serializable(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    with (
        semantic_writer_engine.connect() as conn,
        conn.begin(),
        pytest.raises(DBAPIError),
        conn.begin_nested(),
    ):
        publish_on_connection(conn, batch())
    with (
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        assert publish_on_connection(conn, batch()).data_revision == 1
        conn.rollback()
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 0


def test_serialization_retry_restages_same_immutable_batches(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
    from sqlalchemy import event

    from corpus_structure.semantic import publication

    seed(semantic_db_engine)
    barrier = Barrier(2)
    original = publication.stage_batch
    seen = []
    states = []

    def staged(conn, candidate):
        seen.append((id(candidate), candidate.batch_id, candidate.content))
        original(conn, candidate)
        if sum(item[1] == candidate.batch_id for item in seen) == 1:
            barrier.wait(timeout=10)

    def failed(context):
        states.append(getattr(context.original_exception, "sqlstate", None))

    monkeypatch.setattr(publication, "stage_batch", staged)
    event.listen(semantic_writer_engine, "handle_error", failed)
    candidates = (batch("a", entity="a"), batch("b", entity="b"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda candidate: publish_batch(semantic_writer_engine, candidate), candidates)
        )
    assert {receipt.data_revision for receipt in results} == {1, 2}
    assert "40001" in states
    assert len(seen) >= 3
    for candidate in candidates:
        assert all(
            item == (id(candidate), candidate.batch_id, candidate.content)
            for item in seen
            if item[1] == candidate.batch_id
        )
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 2
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 4


def test_ambiguous_committed_connection_loss_resolves_exact_receipt(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
    import psycopg

    seed(semantic_db_engine)
    original = semantic_writer_engine.dialect.do_commit
    commits = []

    def committed_then_lost(driver):
        original(driver)
        commits.append(1)
        if len(commits) == 1:
            raise psycopg.OperationalError("injected connection loss after server commit")

    monkeypatch.setattr(semantic_writer_engine.dialect, "do_commit", committed_then_lost)
    candidate = batch()
    assert publish_batch(semantic_writer_engine, candidate).data_revision == 1
    assert len(commits) == 1
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 1
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 2


def test_native_recursive_record_shape_and_entity_reference(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    record = "https://example/Record"
    with semantic_db_engine.begin() as conn:
        conn.execute(
            insert(table("sem.class_definition")).values(
                release_id=R, class_id=record, name="Record", iri=record
            )
        )
        conn.execute(
            insert(table("sem.property_definition")).values(
                release_id=R,
                property_id="https://example/target",
                name="target",
                iri="https://example/target",
            )
        )
        conn.execute(
            insert(table("sem.property_applicability")).values(
                release_id=R,
                class_id=record,
                property_id="https://example/target",
                range_name="Thing",
                required=True,
                multivalued=False,
                constraint_scope="shape",
                constraints={"name": "target", "inlined": False},
            )
        )
        conn.execute(
            table("sem.property_applicability")
            .update()
            .where(table("sem.property_applicability").c.class_id == C)
            .values(range_name="Record", constraints={"name": "label", "inlined": True})
        )
    candidate = batch()
    key = fact_key(R, Z, "e", P, {"target": "e"}, {})
    candidate = replace(
        candidate,
        typed_value=(
            ValueRow("record", "record", datatype=record),
            ValueRow("ref", "entity", entity_id="e"),
        ),
        value_role=(RoleRow("record", "target", 0, "ref"),),
        fact=(FactRow(key, "e", P, "record"),),
        occurrence=(),
        support=(),
        selection=(SelectionRow(key),),
    )
    assert publish_batch(semantic_writer_engine, candidate).data_revision == 1
    for value in (
        ValueRow("bad", "string", text_value="e", datatype=record),
        ValueRow("bad", "record", datatype=record),
    ):
        bad = replace(
            candidate,
            batch_id="bad",
            typed_value=(value,),
            value_role=(),
            fact=(FactRow("forged", "e", P, "bad"),),
            selection=(),
        )
        with pytest.raises(DBAPIError):
            publish_batch(semantic_writer_engine, bad)


def test_native_identity_vectors_scalars_unicode_and_exact_decimals(
    semantic_db_engine, semantic_writer_engine
):
    import json
    from datetime import UTC, date, datetime

    from corpus_structure.semantic.identity import _meaning, canonical_bytes

    seed(semantic_db_engine)
    values = (
        ("unicode", ValueRow("unicode", "string", text_value='é𝄞\n\t\\"\u2028'), 'é𝄞\n\t\\"\u2028'),
        ("integer", ValueRow("integer", "integer", text_value="9" * 4000), int("9" * 4000)),
        (
            "decimal",
            ValueRow("decimal", "decimal", decimal_lexical="0." + "0" * 17000 + "1"),
            Decimal("0." + "0" * 17000 + "1"),
        ),
        ("date", ValueRow("date", "date", text_value="2026-10-29"), date(2026, 10, 29)),
        (
            "datetime",
            ValueRow("datetime", "datetime", text_value="2026-10-29T12:34:56.123456+00:00"),
            datetime(2026, 10, 29, 12, 34, 56, 123456, tzinfo=UTC),
        ),
        ("float", ValueRow("float", "float", text_value=(1.5).hex()), 1.5),
        (
            "subnormal",
            ValueRow(
                "subnormal", "float", text_value=float.fromhex("0x0.0000000000001p-1022").hex()
            ),
            float.fromhex("0x0.0000000000001p-1022"),
        ),
        ("negative-zero", ValueRow("negative-zero", "float", text_value=(-0.0).hex()), -0.0),
        ("boolean", ValueRow("boolean", "boolean", boolean_value=False), False),
    )
    candidate = PublicationBatch(R, Z, "vectors", typed_value=tuple(row for _, row, _ in values))
    publish_batch(semantic_writer_engine, candidate)
    with semantic_db_engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        for value_id, _, semantic in values:
            actual = conn.scalar(
                text("SELECT data.canonical_json(data.value_meaning(:r,:z,:v))"),
                {"r": R, "z": Z, "v": value_id},
            )
            assert actual.encode() == canonical_bytes(_meaning(semantic))
            assert json.loads(actual) == _meaning(semantic)
    for value in (
        ValueRow("bad", "float", text_value="0x1.0000000000000p+1024"),
        ValueRow("bad", "float", text_value="0x0.0000000000000p-1022"),
        ValueRow("bad", "datetime", text_value="2026-10-29T12:34:56.000000+00:00"),
        ValueRow("bad", "datetime", text_value="2026-10-29T24:00:00+00:00"),
        ValueRow("bad", "decimal", decimal_lexical="NaN"),
    ):
        with pytest.raises(DBAPIError):
            publish_batch(
                semantic_writer_engine, PublicationBatch(R, Z, "bad", typed_value=(value,))
            )


def test_native_bound_comparison_is_lossless_beyond_numeric_capacity(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    huge = "9" * 150000
    with semantic_db_engine.begin() as conn:
        conn.execute(
            table("sem.property_applicability")
            .update()
            .values(
                range_name="decimal",
                constraints={"name": "label", "native_minimum": huge, "native_maximum": huge},
            )
        )
    candidate = batch()
    fact = fact_key(R, Z, "e", P, Decimal(huge), {})
    candidate = replace(
        candidate,
        typed_value=(ValueRow("huge", "decimal", decimal_lexical=huge),),
        fact=(FactRow(fact, "e", P, "huge"),),
        occurrence=(),
        support=(),
        selection=(SelectionRow(fact),),
    )
    assert publish_batch(semantic_writer_engine, candidate).data_revision == 1
    with semantic_db_engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        assert (
            conn.scalar(text("SELECT data.compare_decimal(:a,:b)"), {"a": huge, "b": "1" + huge})
            == -1
        )
        assert (
            conn.scalar(
                text("SELECT data.compare_decimal(:a,:b)"), {"a": "-" + huge, "b": "-1" + huge}
            )
            == 1
        )


def test_native_constraints_prepares_datatype_aliases_and_scientific_bounds():
    import yaml

    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.publication import admit_release, native_constraints

    source = {
        "id": "https://example/alias",
        "name": "alias",
        "prefixes": {"ex": "https://example/"},
        "default_prefix": "ex",
        "types": {
            "decimal": {"base": "Decimal"},
            "Amount": {"typeof": "decimal"},
            "Cost": {"typeof": "Amount"},
        },
        "classes": {"Thing": {"attributes": {"cost": {"range": "Cost", "minimum_value": "1e10"}}}},
    }
    prepared = prepare_release(
        SourceBundle("alias", (SourceArtifact("alias", yaml.safe_dump(source).encode()),))
    )
    admit_release(prepared)
    constraints = native_constraints(prepared)
    assert constraints["https://example/Thing", "https://example/cost"]["native_range"] == "decimal"
    assert (
        constraints["https://example/Thing", "https://example/cost"]["native_minimum"]
        == "10000000000"
    )


def test_independent_value_encodings_merge_fact_and_preserve_reports(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    first = batch("one")
    second = batch("two")
    assert first.fact[0].fact_id == second.fact[0].fact_id
    assert first.fact[0].object_value_id != second.fact[0].object_value_id
    publish_batch(semantic_writer_engine, first)
    publish_batch(semantic_writer_engine, second)
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.fact")) == 1
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 4
        assert set(conn.scalars(text("SELECT report_object_value_id FROM data.occurrence"))) == {
            "vone",
            "vtwo",
        }


def test_replacing_selection_preserves_occurrences_and_identity_uses_selected_scope(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine, unique=True)
    first = batch("one")
    second = batch("two", label="Other", selected=False)
    publish_batch(semantic_writer_engine, first)
    publish_batch(semantic_writer_engine, second)
    replace_selection = PublicationBatch(
        R,
        Z,
        "replace",
        selection=(
            SelectionRow(first.fact[0].fact_id, False),
            SelectionRow(second.fact[0].fact_id),
        ),
    )
    assert publish_batch(semantic_writer_engine, replace_selection).data_revision == 3
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 4
        assert conn.scalar(text("SELECT count(*) FROM data.fact")) == 2
        assert conn.scalar(text("SELECT fact_id FROM data.selection")) == second.fact[0].fact_id


def test_existing_value_tree_cannot_be_extended_by_a_later_batch(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    first = PublicationBatch(
        R,
        Z,
        "one",
        typed_value=(ValueRow("tree", "mapping"), ValueRow("child", "string", text_value="first")),
        value_role=(RoleRow("tree", "a", 0, "child"),),
    )
    publish_batch(semantic_writer_engine, first)
    extend = PublicationBatch(
        R,
        Z,
        "two",
        typed_value=(ValueRow("other", "string", text_value="changed"),),
        value_role=(RoleRow("tree", "b", 0, "other"),),
    )
    with pytest.raises(DBAPIError):
        publish_batch(semantic_writer_engine, extend)
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.value_role")) == 1
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 1


def test_constraint_capability_refusal_and_optional_ontology_metadata():
    from dataclasses import replace

    from corpus_structure.semantic.publication import admit_release
    from corpus_structure.semantic.types import (
        ClassDefinition,
        Diagnostic,
        PreparedRelease,
        PropertyDefinition,
    )

    prop = PropertyDefinition(
        "p", "https://example/p", "float", False, False, None, None, "0", None, None, False
    )
    definition = ClassDefinition("Thing", C, (), (prop,), ())
    prepared = PreparedRelease("r", b"{}", (definition,), (), (), (), (), (), (), ())
    with pytest.raises(ValueError, match="float bounds"):
        admit_release(prepared)
    unconstrained = replace(
        prepared, definitions=(replace(definition, properties=(replace(prop, minimum=None),)),)
    )
    admit_release(
        replace(
            unconstrained,
            diagnostics=(
                Diagnostic("unchecked_term", "vocab", "not4curation:unchecked", "unchecked"),
            ),
        )
    )
    with pytest.raises(ValueError, match="unchecked"):
        admit_release(
            replace(
                unconstrained,
                diagnostics=(
                    Diagnostic("unchecked_term", "vocab", "meaning:unknown:unchecked", "unchecked"),
                ),
            )
        )


def _qualification_schema(engine, *, score=False):
    q = "https://example/Qualification"
    with engine.begin() as conn:
        conn.execute(
            insert(table("sem.class_definition")).values(
                release_id=R, class_id=q, name="Qualification", iri=q
            )
        )
        properties = [
            ("modality", "string", True, "meaning"),
            ("polarity", "boolean", True, "meaning"),
            ("attribution", "string", False, "provenance"),
        ]
        if score:
            properties.append(("score", "decimal", False, "meaning"))
        for name, rng, required, role in properties:
            iri = "https://example/" + name
            conn.execute(
                insert(table("sem.property_definition")).values(
                    release_id=R, property_id=iri, name=name, iri=iri
                )
            )
            constraints = {"name": name, "key_role": role, "inlined": False}
            if name == "score":
                constraints["minimum"] = "0"
            conn.execute(
                insert(table("sem.property_applicability")).values(
                    release_id=R,
                    class_id=q,
                    property_id=iri,
                    range_name=rng,
                    required=required,
                    multivalued=False,
                    constraint_scope="accepted_value" if name == "score" else "shape",
                    constraints=constraints,
                )
            )
    return q


def _qualified(candidate, qclass, *, attribution="reporter", score=None):
    prefix = candidate.batch_id
    values = [
        ValueRow(prefix + "q", "record", datatype=qclass),
        ValueRow(prefix + "modality", "string", text_value="asserted"),
        ValueRow(prefix + "polarity", "boolean", boolean_value=True),
        ValueRow(prefix + "attribution", "string", text_value=attribution),
    ]
    roles = [
        RoleRow(prefix + "q", "modality", 0, prefix + "modality"),
        RoleRow(prefix + "q", "polarity", 0, prefix + "polarity"),
        RoleRow(prefix + "q", "attribution", 0, prefix + "attribution"),
    ]
    meaning: dict[str, Any] = {"modality": "asserted", "polarity": True}
    if score is not None:
        values.append(ValueRow(prefix + "score", "decimal", decimal_lexical=str(score)))
        roles.append(RoleRow(prefix + "q", "score", 0, prefix + "score"))
        meaning["score"] = Decimal(score)
    f = fact_key(R, Z, "e", P, "Straße", meaning)
    return replace(
        candidate,
        typed_value=(*candidate.typed_value, *values),
        value_role=tuple(roles),
        fact=(replace(candidate.fact[0], fact_id=f, qualification_value_id=prefix + "q"),),
        occurrence=tuple(
            replace(o, fact_id=f, report_qualification_value_id=prefix + "q")
            for o in candidate.occurrence
        ),
        support=tuple(replace(s, fact_id=f) for s in candidate.support),
        selection=(SelectionRow(f),) if candidate.selection else (),
    )


def test_equal_fact_keeps_each_occurrence_full_provenance_qualification(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    qclass = _qualification_schema(semantic_db_engine)
    first = _qualified(batch("one"), qclass, attribution="Alice")
    second = _qualified(batch("two"), qclass, attribution="Bob")
    assert first.fact[0].fact_id == second.fact[0].fact_id
    publish_batch(semantic_writer_engine, first)
    publish_batch(semantic_writer_engine, second)
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.fact")) == 1
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 4
        assert set(
            conn.scalars(
                text(
                    "SELECT tv.text_value FROM data.occurrence o JOIN data.value_role vr "
                    "ON vr.release_id=o.release_id AND vr.realization_id=o.realization_id "
                    "AND vr.parent_value_id=o.report_qualification_value_id "
                    "AND vr.role='attribution' JOIN data.typed_value tv "
                    "ON tv.release_id=vr.release_id AND tv.realization_id=vr.realization_id "
                    "AND tv.value_id=vr.child_value_id"
                )
            )
        ) == {"Alice", "Bob"}


def test_selected_qualification_closure_enforces_accepted_bounds(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    qclass = _qualification_schema(semantic_db_engine, score=True)
    candidate = _qualified(batch("one", selected=False), qclass, score="-1")
    assert publish_batch(semantic_writer_engine, candidate).data_revision == 1
    with pytest.raises(DBAPIError):
        publish_batch(
            semantic_writer_engine,
            PublicationBatch(R, Z, "select", selection=(SelectionRow(candidate.fact[0].fact_id),)),
        )
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.selection")) == 0
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 2


def test_raw_decimal_and_integer_lexicals_keep_exact_receipt_but_share_meaning(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    candidate = PublicationBatch(
        R,
        Z,
        "lexical",
        typed_value=(
            ValueRow("a", "decimal", decimal_lexical="+0001.2000e2"),
            ValueRow("b", "decimal", decimal_lexical="120"),
            ValueRow("c", "integer", text_value="+000120"),
            ValueRow("d", "integer", text_value="120"),
            ValueRow("zero", "decimal", decimal_lexical="-0.000e200000"),
        ),
    )
    publish_batch(semantic_writer_engine, candidate)
    with semantic_db_engine.begin() as conn:
        assert bytes(conn.scalar(text("SELECT content FROM data.batch"))) == candidate.content
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        assert conn.scalar(
            text("SELECT data.value_meaning(:r,:z,'a')=data.value_meaning(:r,:z,'b')"),
            {"r": R, "z": Z},
        )
        assert conn.scalar(
            text("SELECT data.value_meaning(:r,:z,'c')=data.value_meaning(:r,:z,'d')"),
            {"r": R, "z": Z},
        )
        assert conn.scalar(text("SELECT data.decimal_canonical('-0.000e200000')")) == "0"


def test_report_entity_reference_cannot_masquerade_as_equal_string(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    with semantic_db_engine.begin() as conn:
        conn.execute(
            table("sem.property_applicability")
            .update()
            .values(range_name="Thing", constraints={"name": "label", "inlined": False})
        )
    candidate = batch("entity")
    fact = fact_key(R, Z, "e", P, "e", {})
    candidate = replace(
        candidate,
        typed_value=(
            ValueRow("reference", "entity", entity_id="e"),
            ValueRow("report-reference", "entity", entity_id="e"),
            ValueRow("equal-string", "string", text_value="e"),
        ),
        fact=(FactRow(fact, "e", P, "reference"),),
        occurrence=tuple(
            replace(o, fact_id=fact, report_object_value_id="report-reference")
            for o in candidate.occurrence
        ),
        support=tuple(replace(s, fact_id=fact) for s in candidate.support),
        selection=(SelectionRow(fact),),
    )
    assert publish_batch(semantic_writer_engine, candidate).data_revision == 1
    forged_occurrence = OccurrenceRow(
        occurrence_key(R, Z, "source", "forged-reference"),
        fact,
        "source",
        "forged-reference",
        "equal-string",
    )
    with pytest.raises(DBAPIError, match="declared range"):
        publish_batch(
            semantic_writer_engine,
            PublicationBatch(R, Z, "forged-reference", occurrence=(forged_occurrence,)),
        )
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 1
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 2


def test_report_record_class_must_match_even_when_field_meaning_is_equal(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    expected_class = "https://example/ExpectedRecord"
    other_class = "https://example/OtherRecord"
    with semantic_db_engine.begin() as conn:
        conn.execute(
            insert(table("sem.class_definition")),
            [
                dict(
                    release_id=R, class_id=expected_class, name="ExpectedRecord", iri=expected_class
                ),
                dict(release_id=R, class_id=other_class, name="OtherRecord", iri=other_class),
            ],
        )
        conn.execute(
            table("sem.property_applicability")
            .update()
            .values(range_name="ExpectedRecord", constraints={"name": "label", "inlined": True})
        )
    candidate = batch("record")
    fact = fact_key(R, Z, "e", P, {}, {})
    candidate = replace(
        candidate,
        typed_value=(
            ValueRow("expected-record", "record", datatype=expected_class),
            ValueRow("report-record", "record", datatype=expected_class),
            ValueRow("other-record", "record", datatype=other_class),
        ),
        fact=(FactRow(fact, "e", P, "expected-record"),),
        occurrence=tuple(
            replace(o, fact_id=fact, report_object_value_id="report-record")
            for o in candidate.occurrence
        ),
        support=tuple(replace(s, fact_id=fact) for s in candidate.support),
        selection=(SelectionRow(fact),),
    )
    assert publish_batch(semantic_writer_engine, candidate).data_revision == 1
    forged_occurrence = OccurrenceRow(
        occurrence_key(R, Z, "source", "forged-class"),
        fact,
        "source",
        "forged-class",
        "other-record",
    )
    with pytest.raises(DBAPIError, match="declared range"):
        publish_batch(
            semantic_writer_engine,
            PublicationBatch(R, Z, "forged-class", occurrence=(forged_occurrence,)),
        )
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 2


def test_unused_alias_payloads_and_scalar_datatypes_are_refused(
    semantic_db_engine, semantic_writer_engine
):
    seed(semantic_db_engine)
    record = "https://example/Record"
    with semantic_db_engine.begin() as conn:
        conn.execute(
            insert(table("sem.class_definition")).values(
                release_id=R, class_id=record, name="Record", iri=record
            )
        )
    for value in (
        ValueRow("v", "interval", datatype=record),
        ValueRow("v", "expression", text_value="ignored expression", datatype=record),
        ValueRow("v", "missing", text_value="ignored reason", datatype=record),
    ):
        with pytest.raises(DBAPIError, match="unsupported physical value alias"):
            publish_batch(
                semantic_writer_engine,
                PublicationBatch(R, Z, "alias-" + value.kind, typed_value=(value,)),
            )
    for value in (
        ValueRow("v", "string", text_value="retained text", datatype=record),
        ValueRow("v", "boolean", boolean_value=True, datatype=record),
        ValueRow("v", "sequence", datatype=record),
    ):
        with pytest.raises(DBAPIError, match="datatype is supported only"):
            publish_batch(
                semantic_writer_engine,
                PublicationBatch(R, Z, "datatype-" + value.kind, typed_value=(value,)),
            )
    assert (
        publish_batch(
            semantic_writer_engine,
            PublicationBatch(
                R, Z, "typed-record", typed_value=(ValueRow("v", "record", datatype=record),)
            ),
        ).data_revision
        == 1
    )
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 1
        assert conn.scalar(text("SELECT kind FROM data.typed_value")) == "record"
