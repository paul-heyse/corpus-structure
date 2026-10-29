"""Independent rows through actual PostgreSQL/ADBC and native DuckDB operations."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, localcontext
from types import MappingProxyType

import pyarrow as pa
import pytest
from sqlalchemy import insert, literal, select

from corpus_structure.semantic import PreparationProfile, SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.analytical_profile import AnalyticalProfile, analytical_inputs
from corpus_structure.semantic.analytics import (
    AnalysisScope, AnalyticalPacket, compile_projection, compile_sql, load_packet,
)
from corpus_structure.semantic.identity import fact_key, occurrence_key
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    EntityRow, EvidenceRow, FactRow, MembershipRow, MembershipSupportRow, OccurrenceRow, PublicationBatch, SupportRow, ValueRow,
    publish_batch,
)
from corpus_structure.semantic.query import SnapshotBinding, read_session
from corpus_structure.semantic.releases import persist_release


def prepared_inputs():
    source = b'''id: https://example/model
name: example
prefixes: {ex: 'https://example/'}
default_prefix: ex
types:
  string: {base: str, uri: "http://www.w3.org/2001/XMLSchema#string"}
classes:
  Thing:
    attributes:
      label: {required: false, multivalued: true}
'''
    bundle, dependencies = analytical_inputs(SourceBundle("example", (SourceArtifact("example", source),)))
    return bundle, dependencies, prepare_release(bundle, dependencies)


def empty_packet(prepared):
    compiled = compile_projection(prepared, SnapshotBinding(prepared.release_id, "z", 0, "cap"))
    return AnalyticalPacket(compiled.binding, compiled.projection_id, compiled.profile.digest,
                            MappingProxyType({p.name: pa.Table.from_pylist([], schema=p.schema) for p in compiled.relations}))


def with_rows(packet, name, rows):
    tables = dict(packet.relations)
    tables[name] = pa.Table.from_pylist(rows, schema=tables[name].schema)
    return replace(packet, relations=MappingProxyType(tables))


def scoped(packet, **row):
    return {"release_id": packet.binding.release_id, "realization_id": "z", **row}


def test_profile_is_explicit_hashed_and_validated():
    bundle, dependencies, prepared = prepared_inputs()
    assert AnalyticalProfile.from_release(prepared).scale == 12
    changed = replace(dependencies, artifacts=(replace(dependencies.artifacts[0], content=dependencies.artifacts[0].content.replace(b'"HALF_EVEN"', b'"HALF_UP"')),))
    with pytest.raises(ValueError, match="analytical-profile"):
        prepare_release(bundle, changed)
    with pytest.raises(ValueError, match="no admitted"):
        AnalyticalProfile.from_release(prepare_release(SourceBundle("example", (bundle.sources[0],))))


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
    for lexical in ("1e26", "1e200000", "NaN", "Infinity", "99999999999999999999999999.9999999999995"):
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
        with pytest.raises(RuntimeError, match="cancel"):
            with scope.reader(scope.fact_support()) as reader:
                assert reader.read_all().num_rows == 0
                raise RuntimeError("cancel")
        assert scope.disagreements().to_arrow_table().num_rows == 0
    scope.close()
    with pytest.raises(RuntimeError, match="closed"):
        scope.relation("fact")
    tables = dict(packet.relations)
    tables["fact"] = tables["fact"].replace_schema_metadata(None)
    with pytest.raises(ValueError, match="metadata"):
        AnalysisScope(replace(packet, relations=tables))


def test_native_relation_kernels_keep_occurrences_qualifications_and_roles():
    packet = empty_packet(prepared_inputs()[2])
    packet = with_rows(packet, "fact", [scoped(packet, fact_id=f, subject_id="e", property_id="https://example/label", object_value_id=v, qualification_value_id=q) for f,v,q in [("f2","v2",None),("f1","v1",None),("f3","v2","q")]])
    packet = with_rows(packet, "typed_value", [scoped(packet, value_id=v, kind=k, text_value=t, decimal_rounded=False) for v,k,t in [("v1","string","one"),("v2","string","two"),("q","record",None)]])
    packet = with_rows(packet, "value_role", [scoped(packet, parent_value_id="q", role="unit", position=0, child_value_id="v1")])
    packet = with_rows(packet, "occurrence", [scoped(packet, occurrence_id=o, fact_id="f1", source="s", item=o, batch_id="b", report_object_value_id="v1") for o in ("o2","o1")])
    packet = with_rows(packet, "support", [scoped(packet, fact_id="f1", occurrence_id=o) for o in ("o2","o1")])
    with AnalysisScope(packet) as scope:
        support = scope.fact_support().to_arrow_table().to_pylist()
        assert [s["occurrence_id"] for s in support[0]["supports"]] == ["o1","o2"]
        assert support[1]["supports"] == []
        assert [r["fact_id"] for r in scope.disagreements().to_arrow_table().to_pylist()] == ["f1","f2"]
        roles = scope.value_roles().to_arrow_table().to_pylist()
        assert roles[0]["roles"] == [{"role":"unit","position":0,"child_value_id":"v1","kind":"string","text_value":"one","decimal_value":None,"decimal_rounded":False,"entity_id":None}]
        aliases = scope.connection.sql("SELECT 'Thing' class_id, 'a' normalized, 'e' entity_id")
        references = scope.connection.sql("SELECT 'Thing' class_id, 'a' normalized, 'ref' entity_id")
        assert scope.alias_candidates(aliases, references).to_arrow_table().to_pylist() == [{"entity_id":"e","candidate_id":"ref"}]
        with pytest.raises(RuntimeError, match="cancel"):
            with scope.reader(scope.relation("fact"), batch_size=1) as reader:
                assert reader.read_next_batch().num_rows == 1
                raise RuntimeError("cancel")
        assert scope.relation("fact").to_arrow_table().num_rows == 3


def test_native_exported_snapshot_and_decimal_boundary(semantic_db_engine, semantic_reader_engine, semantic_writer_engine):
    bundle, dependencies, prepared = prepared_inputs()
    rid, realization = prepared.release_id, "z"
    with semantic_db_engine.begin() as owner:
        persist_release(owner, bundle, dependencies, PreparationProfile(), prepared)
        owner.execute(insert(table("data.project")).values(project_id="p"))
        owner.execute(insert(table("data.realization")).values(realization_id=realization,release_id=rid,project_id="p"))
    def batch(label):
        f = fact_key(rid, realization, "e", "https://example/label", label, {})
        occurrence = occurrence_key(rid, realization, "s", label)
        return PublicationBatch(rid,realization,label,entity=(EntityRow("e"),),membership=(MembershipRow("e","https://example/Thing","source"),),typed_value=(ValueRow("v"+label,"string",text_value=label), ValueRow("num"+label,"decimal",decimal_lexical="1.0000000000015",numeric_value=Decimal("1.0000000000015")), ValueRow("nativeinteger"+label,"integer",text_value="42",integer_value=Decimal(42)), *(ValueRow("float"+str(index)+label,"float",text_value=value.hex()) for index,value in enumerate((1.25,float.fromhex("0x0.0000000000001p-1022"),-0.0)))),fact=(FactRow(f,"e","https://example/label","v"+label),),occurrence=(OccurrenceRow(occurrence,f,"s",label,"v"+label),),support=(SupportRow(f,occurrence),),evidence=(EvidenceRow("ev"+label,"urn:s","line:1","test","1"),),membership_support=(MembershipSupportRow("e","https://example/Thing","ev"+label),))
    publish_batch(semantic_writer_engine,batch("100%quote'"))
    uri = semantic_reader_engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    with read_session(semantic_reader_engine, realization) as session:
        publish_batch(semantic_writer_engine,batch("later"))
        packet = load_packet(session, uri)
        assert packet.binding.data_revision == 1
    assert packet.relations["fact"].num_rows == 1
    lexical = packet.relations["typed_value"].to_pylist()
    numeric = next(r for r in lexical if r["kind"] == "decimal")
    assert numeric["decimal_lexical"] == "1.0000000000015"
    assert numeric["decimal_value"] == Decimal("1.000000000002")
    assert numeric["decimal_rounded"] is True
    integer = next(r for r in lexical if r["kind"] == "integer")
    assert integer["text_value"] == "42" and integer["integer_value"] == "42"
    assert integer["integer64_value"] == 42
    floats = {r["text_value"]: r["float64_value"].hex() for r in lexical if r["kind"] == "float"}
    assert floats == {"0x1.4000000000000p+0":"0x1.4000000000000p+0", "0x0.0000000000001p-1022":"0x0.0000000000001p-1022", "-0x0.0p+0":"-0x0.0p+0"}
    with AnalysisScope(packet) as scope:
        assert scope.fact_support().to_arrow_table().num_rows == 1
        assert scope.declared_view("https://example/label").to_arrow_table().num_rows == 1


def test_native_scalar_projection_preserves_source_and_missing_states():
    from corpus_structure.semantic.analytics import normalize_relation

    prepared = prepared_inputs()[2]
    compiled = compile_projection(prepared, SnapshotBinding(prepared.release_id,"z",0,"c"))
    projection = next(p for p in compiled.relations if p.name == "typed_value")
    raw_schema = pa.schema(list(projection.schema)[:-6])
    rows = [
        {"value_id":"i","kind":"integer","text_value":"9223372036854775807"},
        {"value_id":"t","kind":"datetime","text_value":"2026-10-29T01:02:03.123456789+02:00"},
        {"value_id":"date","kind":"date","text_value":"2026-10-29"},
        {"value_id":"float","kind":"float","text_value":"0x1.4000000000000p+0"},
        {"value_id":"unknown","kind":"missing","text_value":"unknown"},
        {"value_id":"null","kind":"null"},
        {"value_id":"entity","kind":"entity","entity_id":"nested-target"},
    ]
    raw = pa.Table.from_pylist([{"release_id":prepared.release_id,"realization_id":"z",**r} for r in rows],schema=raw_schema)
    result = normalize_relation(raw,projection,compiled.profile)
    assert result["integer64_value"][0].as_py() == 9223372036854775807
    assert result["datetime_value"].cast(pa.int64())[1].as_py() == 1793228523123456789
    assert result["float64_value"][3].as_py() == 1.25
    assert result["text_value"][1].as_py() == "2026-10-29T01:02:03.123456789+02:00"
    assert result["kind"].to_pylist()[-3:] == ["missing","null","entity"]
    assert result["entity_id"][-1].as_py() == "nested-target"
    for kind, lexical in [("integer","9223372036854775808"),("datetime","2026-10-29T01:02:03.1234567891Z")]:
        invalid = pa.Table.from_pylist([{"release_id":prepared.release_id,"realization_id":"z","value_id":"bad","kind":kind,"text_value":lexical}],schema=raw_schema)
        with pytest.raises(pa.ArrowInvalid):
            normalize_relation(invalid,projection,compiled.profile)
