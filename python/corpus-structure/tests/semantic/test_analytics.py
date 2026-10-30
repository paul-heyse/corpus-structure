"""Independent rows through actual PostgreSQL/ADBC and native DuckDB operations."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, localcontext
from types import MappingProxyType

import pyarrow as pa
import pytest
from sqlalchemy import insert, literal, select

from corpus_structure.semantic import (
    PreparationProfile,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.analytical_profile import AnalyticalProfile, analytical_inputs
from corpus_structure.semantic.analytics import (
    AnalysisScope,
    AnalyticalPacket,
    compile_projection,
    compile_sql,
    load_packet,
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
    SupportRow,
    ValueRow,
    publish_batch,
)
from corpus_structure.semantic.query import SnapshotBinding, read_session
from corpus_structure.semantic.releases import persist_release


def prepared_inputs():
    source = b"""id: https://example/model
name: example
prefixes: {ex: 'https://example/'}
default_prefix: ex
types:
  string: {base: str, uri: "http://www.w3.org/2001/XMLSchema#string"}
classes:
  Thing:
    attributes:
      label: {required: false, multivalued: true}
"""
    bundle, dependencies = analytical_inputs(
        SourceBundle("example", (SourceArtifact("example", source),))
    )
    return bundle, dependencies, prepare_release(bundle, dependencies)


def empty_packet(prepared):
    compiled = compile_projection(prepared, SnapshotBinding(prepared.release_id, "z", 0, "cap"))
    return AnalyticalPacket(
        compiled.binding,
        compiled.projection_id,
        compiled.profile.digest,
        MappingProxyType(
            {p.name: pa.Table.from_pylist([], schema=p.schema) for p in compiled.relations}
        ),
        scale=compiled.profile.scale,
    )


def with_rows(packet, name, rows):
    tables = dict(packet.relations)
    tables[name] = pa.Table.from_pylist(rows, schema=tables[name].schema)
    return replace(packet, relations=MappingProxyType(tables))


def scoped(packet, **row):
    return {"release_id": packet.binding.release_id, "realization_id": "z", **row}


def test_profile_is_explicit_hashed_and_validated():
    bundle, dependencies, prepared = prepared_inputs()
    assert AnalyticalProfile.from_release(prepared).scale == 12
    changed = replace(
        dependencies,
        artifacts=(
            replace(
                dependencies.artifacts[0],
                content=dependencies.artifacts[0].content.replace(b'"HALF_EVEN"', b'"HALF_UP"'),
            ),
        ),
    )
    with pytest.raises(ValueError, match="analytical-profile"):
        prepare_release(bundle, changed)
    with pytest.raises(ValueError, match="no admitted"):
        AnalyticalProfile.from_release(
            prepare_release(SourceBundle("example", (bundle.sources[0],)))
        )


def test_decimal_boundary_is_half_even_context_independent_and_refuses_overflow():
    profile = AnalyticalProfile.from_release(prepared_inputs()[2])
    with localcontext() as context:
        context.prec = 3
        assert profile.decimal("1.0000000000005") == (Decimal("1.000000000000"), True)
        assert profile.decimal("1.0000000000015") == (Decimal("1.000000000002"), True)
        assert profile.decimal("-1.0000000000015") == (Decimal("-1.000000000002"), True)
        assert profile.decimal("9.0") == (Decimal("9.000000000000"), False)
        assert profile.quotient(Decimal(1), Decimal(3)) == (Decimal("0.333333333333"), True)
        assert profile.quotient(Decimal(1), Decimal(2)) == (Decimal("0.500000000000"), False)
    for lexical in (
        "1e26",
        "1e200000",
        "NaN",
        "Infinity",
        "99999999999999999999999999.9999999999995",
    ):
        with pytest.raises(ValueError, match="outside"):
            profile.decimal(lexical)


def test_core_sql_preserves_quotes_and_percent():
    sql = compile_sql(select(literal("O'Reilly 100%_\\")))
    assert "O''Reilly 100%_" in sql
    assert "100%%" not in sql


def test_empty_scope_metadata_rejection_and_reader_cancellation():
    packet = empty_packet(prepared_inputs()[2])
    with AnalysisScope(packet) as scope:
        assert scope.fact_support().to_arrow_table().num_rows == 0
        assert scope.value_roles().to_arrow_table().num_rows == 0
        with (
            pytest.raises(RuntimeError, match="cancel"),
            scope.reader(scope.fact_support()) as reader,
        ):
            assert reader.read_all().num_rows == 0
            raise RuntimeError("cancel")
        assert scope.disagreements().to_arrow_table().num_rows == 0
    scope.close()
    with pytest.raises(RuntimeError, match="closed"):
        scope.relation("fact")
    tables = dict(packet.relations)
    tables["fact"] = packet.to_table("fact").replace_schema_metadata(None)
    with pytest.raises(ValueError, match="metadata"):
        AnalysisScope(replace(packet, relations=tables))


def test_native_relation_kernels_keep_occurrences_qualifications_and_roles():
    packet = empty_packet(prepared_inputs()[2])
    packet = with_rows(
        packet,
        "fact",
        [
            scoped(
                packet,
                fact_id=f,
                subject_id="e",
                property_id="https://example/label",
                object_value_id=v,
                qualification_value_id=q,
                qualification_key="different" if q else '["mapping",[]]',
            )
            for f, v, q in [("f2", "v2", None), ("f1", "v1", None), ("f3", "v2", "q")]
        ],
    )
    packet = with_rows(
        packet,
        "typed_value",
        [
            scoped(packet, value_id=v, kind=k, text_value=t, decimal_rounded=False)
            for v, k, t in [("v1", "string", "one"), ("v2", "string", "two"), ("q", "record", None)]
        ],
    )
    packet = with_rows(
        packet,
        "value_role",
        [scoped(packet, parent_value_id="q", role="unit", position=0, child_value_id="v1")],
    )
    packet = with_rows(
        packet,
        "occurrence",
        [
            scoped(
                packet,
                occurrence_id=o,
                fact_id="f1",
                source="s",
                item=o,
                batch_id="b",
                report_object_value_id="v1",
            )
            for o in ("o2", "o1")
        ],
    )
    packet = with_rows(
        packet, "support", [scoped(packet, fact_id="f1", occurrence_id=o) for o in ("o2", "o1")]
    )
    with AnalysisScope(packet) as scope:
        support = scope.fact_support().to_arrow_table().to_pylist()
        assert [s["occurrence_id"] for s in support[0]["supports"]] == ["o1", "o2"]
        assert support[1]["supports"] == []
        assert [r["fact_id"] for r in scope.disagreements().to_arrow_table().to_pylist()] == [
            "f1",
            "f2",
        ]
        roles = scope.value_roles().to_arrow_table().to_pylist()
        assert roles[0]["roles"] == [
            {
                "role": "unit",
                "position": 0,
                "child_value_id": "v1",
                "kind": "string",
                "text_value": "one",
                "decimal_value": None,
                "decimal_rounded": False,
                "entity_id": None,
            }
        ]
        aliases = scope.connection.sql("SELECT 'Thing' class_id, 'a' normalized, 'e' entity_id")
        references = scope.connection.sql(
            "SELECT 'Thing' class_id, 'a' normalized, 'ref' entity_id"
        )
        assert scope.alias_candidates(aliases, references).to_arrow_table().to_pylist() == [
            {"entity_id": "e", "candidate_id": "ref", "matches": 1}
        ]
        with (
            pytest.raises(RuntimeError, match="cancel"),
            scope.reader(scope.relation("fact"), batch_size=1) as reader,
        ):
            assert reader.read_next_batch().num_rows == 1
            raise RuntimeError("cancel")
        assert scope.relation("fact").to_arrow_table().num_rows == 3


@pytest.mark.parametrize("mode", ["resident", "spooled"])
def test_native_exported_snapshot_and_decimal_boundary(
    semantic_db_engine, semantic_reader_engine, semantic_writer_engine, mode
):
    bundle, dependencies, prepared = prepared_inputs()
    rid, realization = prepared.release_id, "z"
    with semantic_db_engine.begin() as owner:
        persist_release(owner, bundle, dependencies, PreparationProfile(), prepared)
        owner.execute(insert(table("data.project")).values(project_id="p"))
        owner.execute(
            insert(table("data.realization")).values(
                realization_id=realization, release_id=rid, project_id="p"
            )
        )

    def batch(label):
        f = fact_key(rid, realization, "e", "https://example/label", label, {})
        occurrence = occurrence_key(rid, realization, "s", label)
        return PublicationBatch(
            rid,
            realization,
            label,
            entity=(EntityRow("e"),),
            membership=(MembershipRow("e", "https://example/Thing", "source"),),
            typed_value=(
                ValueRow("v" + label, "string", text_value=label),
                ValueRow(
                    "num" + label,
                    "decimal",
                    decimal_lexical="1.0000000000015",
                    numeric_value=Decimal("1.0000000000015"),
                ),
                ValueRow(
                    "nativeinteger" + label, "integer", text_value="42", integer_value=Decimal(42)
                ),
                *(
                    ValueRow("float" + str(index) + label, "float", text_value=value.hex())
                    for index, value in enumerate(
                        (1.25, float.fromhex("0x0.0000000000001p-1022"), -0.0)
                    )
                ),
            ),
            fact=(FactRow(f, "e", "https://example/label", "v" + label),),
            occurrence=(OccurrenceRow(occurrence, f, "s", label, "v" + label),),
            support=(SupportRow(f, occurrence),),
            evidence=(EvidenceRow("ev" + label, "urn:s", "line:1", "test", "1"),),
            membership_support=(MembershipSupportRow("e", "https://example/Thing", "ev" + label),),
        )

    publish_batch(semantic_writer_engine, batch("100%quote'"))
    uri = semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    with read_session(semantic_reader_engine, realization) as session:
        publish_batch(semantic_writer_engine, batch("later"))
        packet = load_packet(session, uri, mode=mode, batch_size=2)
        assert packet.binding.data_revision == 1
    assert packet.relations["fact"].num_rows == 1
    lexical = [row for batch in packet.iter_batches("typed_value",batch_size=2) for row in batch.to_pylist()]
    numeric = next(r for r in lexical if r["kind"] == "decimal")
    assert numeric["decimal_lexical"] == "1.0000000000015"
    assert numeric["decimal_value"] == Decimal("1.000000000002")
    assert numeric["decimal_rounded"] is True
    integer = next(r for r in lexical if r["kind"] == "integer")
    assert integer["text_value"] == "42" and integer["integer_value"] == "42"
    assert integer["integer64_value"] == 42
    floats = {r["text_value"]: r["float64_value"].hex() for r in lexical if r["kind"] == "float"}
    assert floats == {
        "0x1.4000000000000p+0": "0x1.4000000000000p+0",
        "0x0.0000000000001p-1022": "0x0.0000000000001p-1022",
        "-0x0.0p+0": "-0x0.0p+0",
    }
    with AnalysisScope(packet) as scope:
        assert scope.fact_support().to_arrow_table().num_rows == 1
        assert scope.declared_view("https://example/label").to_arrow_table().num_rows == 1
    packet.close()


def test_native_scalar_projection_preserves_source_and_missing_states():
    from corpus_structure.semantic.analytics import normalize_relation

    prepared = prepared_inputs()[2]
    compiled = compile_projection(prepared, SnapshotBinding(prepared.release_id, "z", 0, "c"))
    projection = next(p for p in compiled.relations if p.name == "typed_value")
    raw_schema = pa.schema(list(projection.schema)[:-6])
    rows = [
        {"value_id": "i", "kind": "integer", "text_value": "9223372036854775807"},
        {"value_id": "t", "kind": "datetime", "text_value": "2026-10-29T01:02:03.123456789+02:00"},
        {"value_id": "date", "kind": "date", "text_value": "2026-10-29"},
        {"value_id": "float", "kind": "float", "text_value": "0x1.4000000000000p+0"},
        {"value_id": "unknown", "kind": "missing", "text_value": "unknown"},
        {"value_id": "null", "kind": "null"},
        {"value_id": "entity", "kind": "entity", "entity_id": "nested-target"},
    ]
    raw = pa.Table.from_pylist(
        [{"release_id": prepared.release_id, "realization_id": "z", **r} for r in rows],
        schema=raw_schema,
    )
    result = normalize_relation(raw, projection, compiled.profile)
    assert result["integer64_value"][0].as_py() == 9223372036854775807
    assert result["datetime_value"].cast(pa.int64())[1].as_py() == 1793228523123456789
    assert result["float64_value"][3].as_py() == 1.25
    assert result["text_value"][1].as_py() == "2026-10-29T01:02:03.123456789+02:00"
    assert result["kind"].to_pylist()[-3:] == ["missing", "null", "entity"]
    assert result["entity_id"][-1].as_py() == "nested-target"
    numeric_only = pa.Table.from_pylist(
        [
            {
                "release_id": prepared.release_id,
                "realization_id": "z",
                "value_id": "int-only",
                "kind": "integer",
                "integer_value": "42",
            }
        ],
        schema=raw_schema,
    )
    assert (
        normalize_relation(numeric_only, projection, compiled.profile)["integer64_value"][0].as_py()
        == 42
    )
    for kind, lexical in [
        ("integer", "9223372036854775808"),
        ("datetime", "2026-10-29T01:02:03.1234567891Z"),
    ]:
        invalid = pa.Table.from_pylist(
            [
                {
                    "release_id": prepared.release_id,
                    "realization_id": "z",
                    "value_id": "bad",
                    "kind": kind,
                    "text_value": lexical,
                }
            ],
            schema=raw_schema,
        )
        with pytest.raises(pa.ArrowInvalid):
            normalize_relation(invalid, projection, compiled.profile)


def test_packet_rejects_retagged_cross_scope_rows():
    packet = empty_packet(prepared_inputs()[2])
    for changed in ({"release_id": "other"}, {"realization_id": "other"}):
        invalid = with_rows(packet, "entity", [{**scoped(packet, entity_id="e"), **changed}])
        with pytest.raises(ValueError, match="row scope"):
            AnalysisScope(invalid)


def test_fusion_distinct_typed_sets_and_candidate_count():
    packet = empty_packet(prepared_inputs()[2])
    evidence_type = pa.struct([("evidence_id", pa.string()), ("source_uri", pa.string())])
    schema = pa.schema(
        [
            ("fact_id", pa.string()),
            ("occurrence_id", pa.string()),
            ("evidence", pa.list_(evidence_type)),
        ]
    )
    source = pa.Table.from_pylist(
        [
            {
                "fact_id": "f",
                "occurrence_id": "o2",
                "evidence": [
                    {"evidence_id": "e2", "source_uri": "urn:2"},
                    {"evidence_id": "e1", "source_uri": "urn:1"},
                ],
            },
            {
                "fact_id": "f",
                "occurrence_id": "o1",
                "evidence": [{"evidence_id": "e1", "source_uri": "urn:1"}],
            },
            {"fact_id": "f", "occurrence_id": "o2", "evidence": []},
            {"fact_id": "g", "occurrence_id": "o3", "evidence": []},
        ],
        schema=schema,
    )
    with AnalysisScope(packet) as scope:
        result = scope.fuse(scope.connection.from_arrow(source)).to_arrow_table().to_pylist()
    assert result == [
        {
            "fact_id": "f",
            "supports": ["o1", "o2"],
            "candidates": 3,
            "evidence": [
                {"evidence_id": "e1", "source_uri": "urn:1"},
                {"evidence_id": "e2", "source_uri": "urn:2"},
            ],
        },
        {"fact_id": "g", "supports": ["o3"], "candidates": 1, "evidence": []},
    ]


def test_declared_views_reuse_native_set_kernel_and_independent_expected_rows():
    from corpus_structure.semantic.analytical_kernels import (
        VIEW_ALTERNATIVES,
        VIEW_CLAIMS,
        VIEW_ENTITIES,
        VIEW_IDENTITY,
        ViewSpec,
    )

    packet = replace(empty_packet(prepared_inputs()[2]), property_ids=("https://example/label",))
    p = "https://example/label"
    claims = pa.Table.from_pylist(
        [
            {
                "claim": "f1",
                "predicate": p,
                "subject": "e1",
                "object": "e2",
                "statement": "qualified",
            },
            {
                "claim": "f2",
                "predicate": p,
                "subject": "e1",
                "object": "e3",
                "statement": "qualified",
            },
            {"claim": "f3", "predicate": p, "subject": "e2", "object": "e3", "statement": "other"},
        ],
        schema=VIEW_CLAIMS,
    )
    entities = pa.Table.from_pylist(
        [
            {"entity": e, "key": e, "type": "Thing", "label": label}
            for e, label in [("e1", "A"), ("e2", "B"), ("e3", "C")]
        ],
        schema=VIEW_ENTITIES,
    )
    identity = pa.Table.from_pylist(
        [
            {"entity": "e1", "slot": "code", "value": "I1"},
            {"entity": "e2", "slot": "code", "value": "I2"},
        ],
        schema=VIEW_IDENTITY,
    )
    alternatives = pa.Table.from_pylist(
        [{"group": "g", "claim": f} for f in ("f1", "f3")], schema=VIEW_ALTERNATIVES
    )
    specs = [
        ViewSpec("label", frozenset({p}), p, "subject", "object", "object", "label"),
        ViewSpec(
            "identity", frozenset({p}), p, "subject", "subject", "subject", "identity", "code"
        ),
    ]
    with AnalysisScope(packet) as scope:
        c, e, i, a = (
            scope.connection.from_arrow(t) for t in (claims, entities, identity, alternatives)
        )
        result = scope.views(c, e, i, a, specs).to_arrow_table().to_pylist()
    expected = [
        {"claim": "f1", "view": "alternative_of", "facts": ["f3"]},
        {"claim": "f1", "view": "identity", "facts": ["I1"]},
        {"claim": "f1", "view": "label", "facts": ["C"]},
        {"claim": "f1", "view": "same_slot", "facts": ["f2"]},
        {"claim": "f2", "view": "alternative_of", "facts": []},
        {"claim": "f2", "view": "identity", "facts": ["I1"]},
        {"claim": "f2", "view": "label", "facts": []},
        {"claim": "f2", "view": "same_slot", "facts": ["f1"]},
        {"claim": "f3", "view": "alternative_of", "facts": ["f1"]},
        {"claim": "f3", "view": "identity", "facts": ["I2"]},
        {"claim": "f3", "view": "label", "facts": []},
        {"claim": "f3", "view": "same_slot", "facts": []},
    ]
    assert result == expected


def test_concurrent_scopes_own_separate_scratch_and_preserve_parent(tmp_path):
    packet = empty_packet(prepared_inputs()[2])
    sentinel = tmp_path / "keep"
    sentinel.write_text("unrelated")
    with AnalysisScope(packet, scratch_path=tmp_path) as first:
        first_path = first.connection.sql("SELECT current_setting('temp_directory')").fetchall()[0][
            0
        ]
        with AnalysisScope(packet, scratch_path=tmp_path) as second:
            second_path = second.connection.sql(
                "SELECT current_setting('temp_directory')"
            ).fetchall()[0][0]
            assert first_path != second_path
            assert len(list(tmp_path.iterdir())) == 3
        assert len(list(tmp_path.iterdir())) == 2
    assert list(tmp_path.iterdir()) == [sentinel]
    assert sentinel.read_text() == "unrelated"


def test_declared_profile_scale_changes_release_and_packet_shape():
    bundle, _, default = prepared_inputs()
    bundle6, deps6 = analytical_inputs(
        SourceBundle("example", (bundle.sources[0],)),
        profile=b'{"version":"analytical-1","precision":38,"scale":6,"rounding":"HALF_EVEN","overflow":"refuse"}',
    )
    prepared6 = prepare_release(bundle6, deps6)
    profile6 = AnalyticalProfile.from_release(prepared6)
    assert prepared6.release_id != default.release_id
    assert profile6.decimal("1.1234565") == (Decimal("1.123456"), True)
    packet6 = empty_packet(prepared6)
    assert packet6.relations["typed_value"].schema.field("decimal_value").type == pa.decimal128(
        38, 6
    )
    with AnalysisScope(packet6):
        pass
    with pytest.raises(ValueError, match="shape"):
        AnalysisScope(replace(packet6, scale=12))


def test_disagreement_slots_use_qualification_meaning_not_row_id():
    packet = empty_packet(prepared_inputs()[2])
    packet = with_rows(
        packet,
        "fact",
        [
            scoped(
                packet,
                fact_id=f,
                subject_id="e",
                property_id="https://example/label",
                object_value_id=v,
                qualification_value_id=q,
                qualification_key=key,
            )
            for f, v, q, key in [
                ("f1", "v1", "q1", "canonical"),
                ("f2", "v2", "q2", "canonical"),
                ("f3", "v3", "q3", "other"),
            ]
        ],
    )
    with AnalysisScope(packet) as scope:
        assert [r["fact_id"] for r in scope.disagreements().to_arrow_table().to_pylist()] == [
            "f1",
            "f2",
        ]


def test_native_qualification_key_excludes_provenance_and_preserves_occurrence_values(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine
):
    import yaml

    from corpus_structure.semantic.publication import RoleRow

    original = prepared_inputs()[0].sources[0]
    source = yaml.safe_load(original.content)
    source["prefixes"]["cs"] = "https://corpus-structure.dev/semantic/"
    source["classes"]["Qualification"] = {
        "attributes": {
            "certainty": {"required": True},
            "attribution": {"annotations": {"cs:key_role": "provenance"}},
        }
    }
    bundle, deps = analytical_inputs(
        SourceBundle("example", (SourceArtifact("example", yaml.safe_dump(source).encode()),))
    )
    prepared = prepare_release(bundle, deps)
    r, z, p = prepared.release_id, "z", "https://example/label"
    with semantic_db_engine.begin() as owner:
        persist_release(owner, bundle, deps, PreparationProfile(), prepared)
        owner.execute(insert(table("data.project")).values(project_id="p"))
        owner.execute(
            insert(table("data.realization")).values(realization_id=z, release_id=r, project_id="p")
        )
    values = [ValueRow("certainty", "string", text_value="asserted")]
    facts, occurrences, supports, roles = [], [], [], []
    for n, (label, attribution) in enumerate((("one", "A"), ("two", "B"))):
        q, v, a = "q" + str(n), "v" + str(n), "a" + str(n)
        values.extend(
            (
                ValueRow(q, "record", datatype="https://example/Qualification"),
                ValueRow(v, "string", text_value=label),
                ValueRow(a, "string", text_value=attribution),
            )
        )
        roles.extend((RoleRow(q, "certainty", 0, "certainty"), RoleRow(q, "attribution", 0, a)))
        f = prepared.fact_identity(
            z, "e", p, label, {"certainty": "asserted", "attribution": attribution}
        )
        o = occurrence_key(r, z, "s", str(n))
        facts.append(FactRow(f, "e", p, v, q))
        occurrences.append(OccurrenceRow(o, f, "s", str(n), v, q))
        supports.append(SupportRow(f, o))
    batch = PublicationBatch(
        r,
        z,
        "b",
        entity=(EntityRow("e"),),
        membership=(MembershipRow("e", "https://example/Thing", "source"),),
        typed_value=tuple(values),
        value_role=tuple(roles),
        fact=tuple(facts),
        occurrence=tuple(occurrences),
        support=tuple(supports),
        evidence=(EvidenceRow("ev", "urn:s", "line:1", "test", "1"),),
        membership_support=(MembershipSupportRow("e", "https://example/Thing", "ev"),),
    )
    publish_batch(semantic_writer_engine, batch)
    uri = semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    with read_session(semantic_reader_engine, z) as session:
        packet = load_packet(session, uri)
    captured = packet.to_table("fact").to_pylist()
    assert len({f["qualification_value_id"] for f in captured}) == 2
    assert len({f["qualification_key"] for f in captured}) == 1
    with AnalysisScope(packet) as scope:
        assert {f["fact_id"] for f in scope.disagreements().to_arrow_table().to_pylist()} == {
            f.fact_id for f in facts
        }
    assert {
        row["report_qualification_value_id"] for row in packet.to_table("occurrence").to_pylist()
    } == {"q0", "q1"}


def test_borrowed_handles_refuse_after_close_while_materialized_results_detach():
    scope = AnalysisScope(empty_packet(prepared_inputs()[2]))
    relation = scope.connection.sql("SELECT 1 AS value").project("value + 1 AS value")
    detached = relation.to_arrow_table()
    reader = relation.to_arrow_reader()
    delayed_fetch = relation.fetchall
    scope.close()
    assert detached.to_pylist() == [{"value": 2}]
    for operation in (
        delayed_fetch,
        lambda: reader.read_all(),
        lambda: scope.connection.sql("SELECT 2"),
    ):
        with pytest.raises(RuntimeError, match="scope is closed"):
            operation()


def test_candidate_input_has_explicit_universe_without_fabricated_capture():
    from corpus_structure.semantic.analytics import CandidateInput

    packet = empty_packet(prepared_inputs()[2])
    candidate = CandidateInput(
        packet.binding,
        packet.projection_id,
        packet.profile_digest,
        "cut-1",
        "asserted-positive-candidates",
        {
            "candidate_input": pa.Table.from_pylist(
                [],
                schema=pa.schema(
                    [
                        pa.field("fact_id", pa.string()),
                        pa.field("occurrence_id", pa.string()),
                        pa.field(
                            "evidence", pa.list_(pa.struct([pa.field("evidence_id", pa.string())]))
                        ),
                    ],
                    metadata={
                        **(packet.relations["fact"].schema.metadata or {}),
                        b"cs.relation": b"candidate_input",
                    },
                ),
            )
        },
        scale=packet.scale,
    )
    with AnalysisScope(candidate) as scope:
        assert scope.connection.sql("SELECT 3").fetchall() == [(3,)]
    with pytest.raises(ValueError, match="cut and decision universe"):
        replace(candidate, cut_id="")
    with pytest.raises(ValueError, match="actual candidate_input relation"):
        replace(candidate, relations={})
    with AnalysisScope(candidate) as scope:
        assert scope.fuse(scope.relation("candidate_input")).to_arrow_table().num_rows == 0
        with pytest.raises(ValueError, match="bound candidate universe"):
            scope.fuse(scope.connection.from_arrow(candidate.relations["candidate_input"]))


def test_projection_policy_fields_drive_compiler_refusal():
    import json

    from corpus_structure.semantic import PreparationProfile
    from corpus_structure.semantic.composed import composed_dependencies

    bundle, deps, _ = prepared_inputs()
    prepared = prepare_release(
        bundle, composed_dependencies(deps), PreparationProfile(version="semantic-2")
    )
    row = next(r for r in prepared.registry_rows if r.kind == "execution_model")
    body = json.loads(row.body)
    captured = next(p for p in body["projections"] if p["id"] == "captured")
    for field, wrong in (
        ("universe", "cut_candidates"),
        ("values", "exact"),
        ("collections", "set"),
        ("arithmetic_profile", None),
    ):
        changed = json.loads(row.body)
        product = next(p for p in changed["projections"] if p["id"] == "captured")
        product["analytical_policy"][field] = wrong
        changed_row = replace(row, body=json.dumps(changed).encode())
        mutated = replace(
            prepared,
            registry_rows=tuple(changed_row if r is row else r for r in prepared.registry_rows),
        )
        with pytest.raises(ValueError) as refusal:
            compile_projection(mutated, SnapshotBinding(prepared.release_id, "z", 0, "capture"))
        message = str(refusal.value)
        assert "policy is not supported" in message or "analytical_policy." + field in message
    assert captured["analytical_policy"]["universe"] == "full_spine"
    from corpus_structure.semantic.analytics import CANDIDATE_SCHEMA, CandidateInput
    from corpus_structure.semantic.domain_operations import CutInput

    cut = CutInput(
        1,
        2,
        "p",
        prepared,
        "output",
        (),
        (),
        PublicationBatch(prepared.release_id, "output", "cut"),
        {},
        {},
        SnapshotBinding(prepared.release_id, "source", 0, "cut:1"),
    )
    candidates = pa.Table.from_pylist([], schema=CANDIDATE_SCHEMA)
    packet = CandidateInput.from_cut(
        prepared, cut, candidates=candidates, decision_universe="policy"
    )
    assert packet.run_id == 2 and packet.target_realization_id == "output"
    assert set(packet.relations) == {"candidate_input"}
    forged = pa.Table.from_pylist(
        [{"fact_id": "foreign", "occurrence_id": "o", "evidence": []}], schema=CANDIDATE_SCHEMA
    )
    with pytest.raises(ValueError, match="complete cut occurrence/evidence universe"):
        CandidateInput.from_cut(prepared, cut, candidates=forged, decision_universe="policy")


def test_cleanup_attempts_all_and_retains_failures(monkeypatch):
    scope = AnalysisScope(empty_packet(prepared_inputs()[2]))
    events = []

    class Reader:
        def __init__(self, fail):
            self.fail = fail

        def close(self):
            events.append(self.fail)
            if self.fail:
                raise ValueError("first reader failure")

    monkeypatch.setattr(scope, "_readers", [Reader(True), Reader(False)])
    with pytest.raises(ExceptionGroup, match="analysis cleanup failed"):
        scope.close()
    assert events == [True, False]
    assert len(scope.cleanup_failures) == 1
    assert not __import__("pathlib").Path(scope._scratch.name).exists()
    scope.close()


def test_constructor_retains_invalid_input_and_cleanup_failure(monkeypatch):
    from corpus_structure.semantic import analytics

    packet = empty_packet(prepared_inputs()[2])
    original_cleanup = analytics.TemporaryDirectory.cleanup

    def broken_cleanup(self):
        original_cleanup(self)
        raise OSError("scratch cleanup failed")

    monkeypatch.setattr(analytics.TemporaryDirectory, "cleanup", broken_cleanup)
    # The constructor's empty captured spine is independently invalid.
    with pytest.raises(ExceptionGroup) as failure:
        AnalysisScope(replace(packet, relations={}))
    assert isinstance(failure.value.exceptions[0], ValueError)
    assert "complete normalized spine" in str(failure.value.exceptions[0])
    cleanup = failure.value.exceptions[1]
    assert isinstance(cleanup, BaseExceptionGroup)
    assert "scratch cleanup failed" in str(cleanup.exceptions[0])


def test_reader_adopts_native_relation_reader_and_releases_it():
    import duckdb

    with duckdb.connect(":memory:") as connection:
        relation = connection.sql("SELECT 7 AS value")
        with AnalysisScope(empty_packet(prepared_inputs()[2])) as scope:
            with scope.reader(relation) as reader:
                assert reader.read_all().to_pylist() == [{"value": 7}]
            assert scope._readers == []


def test_cleanup_cancellation_remains_primary_after_body_failure(monkeypatch):
    import asyncio
    from pathlib import Path

    scope = AnalysisScope(empty_packet(prepared_inputs()[2]))
    attempted = []

    class CancelledReader:
        def close(self):
            attempted.append("cancelled")
            raise asyncio.CancelledError("reader cancelled")

    class OtherReader:
        def close(self):
            attempted.append("other")

    monkeypatch.setattr(scope, "_readers", [CancelledReader(), OtherReader()])
    with pytest.raises(asyncio.CancelledError) as failure, scope:
        raise ValueError("analysis failed first")
    assert attempted == ["cancelled", "other"]
    assert isinstance(failure.value.__cause__, ValueError)
    assert not Path(scope._scratch.name).exists()


def test_scope_closes_connections_created_by_borrowed_cursor():
    import duckdb

    scope = AnalysisScope(empty_packet(prepared_inputs()[2]))
    temporary = scope.connection.cursor()
    temporary.close()
    assert scope.connection.sql("SELECT 1").fetchall() == [(1,)]
    cursor = scope.connection.cursor()
    native = cursor._native
    assert cursor.sql("SELECT 42").fetchall() == [(42,)]
    scope.close()
    with pytest.raises(duckdb.ConnectionException, match="closed"):
        native.sql("SELECT 42")
    with pytest.raises(RuntimeError, match="scope is closed"):
        cursor.sql("SELECT 42")


def _operation_view_inputs(scope, *, label="view_claims"):
    from corpus_structure.semantic.analytical_kernels import (
        VIEW_ALTERNATIVES,
        VIEW_CLAIMS,
        VIEW_ENTITIES,
        VIEW_IDENTITY,
        ViewSpec,
    )

    p = "https://example/label"
    tables = (
        pa.Table.from_pylist(
            [{"claim": "c", "predicate": p, "subject": "e", "object": "e", "statement": None}],
            schema=VIEW_CLAIMS,
        ),
        pa.Table.from_pylist(
            [{"entity": "e", "key": "e", "type": "Thing", "label": label}], schema=VIEW_ENTITIES
        ),
        pa.Table.from_pylist([], schema=VIEW_IDENTITY),
        pa.Table.from_pylist([], schema=VIEW_ALTERNATIVES),
    )
    return tuple(scope.connection.from_arrow(table) for table in tables), [
        ViewSpec("label", frozenset({p}), p, "subject", "subject", "subject", "label")
    ]


def test_native_single_input_binding_preserves_literals_and_leaves_no_name():
    with AnalysisScope(empty_packet(prepared_inputs()[2])) as scope:
        source = scope.connection.from_arrow(pa.table({"key": ["k"], "meaning": ["v"]}))
        bound = scope._query_input(
            source, "meanings", "SELECT key, 'meanings' AS literal FROM meanings"
        )
        assert bound.fetchall() == [("k", "meanings")]
        assert bound.fetchall() == [("k", "meanings")]
        with pytest.raises(Exception, match="meanings"):
            scope.connection.table("meanings")
        assert scope._views == []
        assert not any(name.startswith("op") for name in scope._registered)


def test_multiple_lazy_view_macro_invocations_retain_their_own_inputs():
    packet = replace(empty_packet(prepared_inputs()[2]), property_ids=("https://example/label",))
    with AnalysisScope(packet) as scope:
        inputs, specs = _operation_view_inputs(scope, label="view_claims")
        first = scope.views(inputs[0], inputs[1], inputs[2], inputs[3], specs)
        second_inputs, _ = _operation_view_inputs(scope, label="second")
        second = scope.views(
            second_inputs[0], second_inputs[1], second_inputs[2], second_inputs[3], specs
        )
        expected = [
            {"claim": "c", "view": "alternative_of", "facts": []},
            {"claim": "c", "view": "label", "facts": ["view_claims"]},
            {"claim": "c", "view": "same_slot", "facts": []},
        ]
        assert first.to_arrow_table().to_pylist() == expected
        assert second.to_arrow_table().to_pylist()[1]["facts"] == ["second"]
        assert first.to_arrow_table().to_pylist() == expected
        assert len(scope._views) == 8
    with pytest.raises(RuntimeError, match="scope is closed"):
        first.fetchall()


def test_view_binding_rejects_foreign_owner_before_catalog_mutation():
    packet = replace(empty_packet(prepared_inputs()[2]), property_ids=("https://example/label",))
    with AnalysisScope(packet) as first, AnalysisScope(packet) as second:
        inputs, specs = _operation_view_inputs(first)
        foreign, _ = _operation_view_inputs(second)
        with pytest.raises(ValueError, match="belong to this analysis scope"):
            first.views(inputs[0], foreign[1], inputs[2], inputs[3], specs)
        assert first._views == []
        assert not any(name.startswith("op") for name in first._registered)
        child = first.connection.cursor()
        child_relation = child.sql("SELECT 'x' AS fact_id, 'o' AS occurrence_id, [] AS evidence")
        with pytest.raises(ValueError, match="scope's analytical connection"):
            first.fuse(child_relation)


def test_native_views_empty_inputs_and_duplicate_spec_refusal():
    from corpus_structure.semantic.analytical_kernels import VIEW_CLAIMS

    packet = replace(empty_packet(prepared_inputs()[2]), property_ids=("https://example/label",))
    with AnalysisScope(packet) as scope:
        inputs, specs = _operation_view_inputs(scope)
        empty = scope.connection.from_arrow(pa.Table.from_pylist([], schema=VIEW_CLAIMS))
        assert (
            scope.views(empty, inputs[1], inputs[2], inputs[3], specs).to_arrow_table().num_rows
            == 0
        )
        with pytest.raises(ValueError, match="view names repeat"):
            scope.views(inputs[0], inputs[1], inputs[2], inputs[3], [*specs, *specs])
