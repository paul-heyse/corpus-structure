"""The interchange projections (P0-M-3): Arrow schemas and records, DuckDB types, JSON Schema `$id`.

Derivation conformance (coordinator decision 24): the Arrow projection and the Pydantic shapes are
two derivations of one model, so their agreement over these samples checks the derivations, not the
model; the samples are hand-written payloads of each kind, validated by the shapes first.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pytest
from jsonschema import Draft202012Validator
from pydantic import JsonValue, TypeAdapter

from corpus_structure.core import db, payloads, schemas
from corpus_structure.core._model import revision
from corpus_structure.core.batch import CitationFrame
from corpus_structure.core.options import RunOptions
from corpus_structure.core.parse_detail import ParseDetail
from corpus_structure.schema import interchange as ix
from corpus_structure.schema import model

MODEL = Path(model.__file__).resolve().parents[1] / "model"


@pytest.fixture(scope="module")
def projections() -> ix.Interchange:
    return ix.installed()


def all_schemas(p: ix.Interchange) -> dict[str, pa.Schema]:
    return {**p.tables, **p.payloads}


# --- Bytes ----------------------------------------------------------------------------------


def test_every_schema_round_trips_its_bytes(projections: ix.Interchange) -> None:
    for name, schema in all_schemas(projections).items():
        data = schema.serialize()
        back = pa.ipc.read_schema(pa.py_buffer(data))
        assert back.equals(schema, check_metadata=True), name
        assert back.serialize().to_pybytes() == data.to_pybytes(), name


def test_compiling_is_deterministic(projections: ix.Interchange) -> None:
    again = ix.compile_interchange(model.load())
    for name, schema in all_schemas(projections).items():
        other = all_schemas(again)[name]
        assert other.serialize().to_pybytes() == schema.serialize().to_pybytes(), name


def test_every_schema_names_its_revision_and_class(projections: ix.Interchange) -> None:
    for name, schema in all_schemas(projections).items():
        meta = schema.metadata
        assert meta[b"cs.model_revision"].decode() == revision.CONTENT_HASH, name
        assert meta[b"cs.class"].decode().split(":")[0] in ("core", "sys"), name
    assert projections.payload("mention").metadata[b"cs.payload"] == b"mention"
    stamped = ix.with_payload_schema_id(projections.payload("mention"), 42)
    assert stamped.metadata[b"cs.payload_schema_id"] == b"42"
    assert b"cs.payload_schema_id" not in projections.payload("mention").metadata


def test_no_extension_type_but_arrow_json(projections: ix.Interchange) -> None:
    def walk(typ: pa.DataType) -> list[pa.DataType]:
        inner = [typ.value_type] if pa.types.is_list(typ) else []
        return [typ, *(t for i in inner for t in walk(i))]

    for name, schema in all_schemas(projections).items():
        for field in schema:
            for typ in walk(field.type):
                if isinstance(typ, pa.ExtensionType):
                    assert typ.extension_name == "arrow.json", (name, field.name)


# --- Derivation conformance -----------------------------------------------------------------


def test_table_schemas_agree_with_the_generated_metadata(projections: ix.Interchange) -> None:
    tables = {n: t for n, t in db.metadata.tables.items() if not t.is_view}
    assert set(projections.tables) == set(tables)
    for name, table in tables.items():
        schema = projections.tables[name]
        assert schema.names == [c.name for c in table.columns], name
        for column in table.columns:
            assert schema.field(column.name).nullable == bool(column.nullable), (name, column.name)
    claim = projections.tables["kb.claim"]
    assert claim.field("qualifiers").type == ix.JSON
    assert claim.field("qualifiers").metadata == {b"cs.class": b"sys:ClaimQualifiers"}
    assert claim.field("confidence").type == pa.float32()
    assert projections.tables["ops.run"].field("cut_at").type == pa.timestamp("us", tz="UTC")


STORED_BATCH = {"unit_ref": "special/Normal.html#u1", "rendition": "ren:" + "0" * 32}

# One sample per payload kind, written by hand from D3 §6.2/§6.3 and checked by the shapes.
SAMPLES: dict[str, tuple[Any, list[Any]]] = {
    "author_markup": (
        payloads.AuthorMarkupPayload,
        [
            {"markup": "dfn", "value": "variance"},
            {"markup": "link", "value": {"href": "#d1"}, "target": "d1"},
        ],
    ),
    "mention": (
        payloads.MentionPayload,
        [
            {"label": "RandomVariable", "text": "X", "start": 0, "end": 1},
            {
                "label": "Symbol",
                "text": "x",
                "start": 3,
                "end": 4,
                "math": {"role": None},
                "attributes": {"style": {"label": "bold", "score": 0.5}},
                "math_ref": "seg:" + "1" * 32,
            },
        ],
    ),
    "relation": (
        payloads.RelationPayload,
        [
            {
                "label": "has_mean",
                "head": {"label": "a", "start": 0, "end": 1},
                "tail": {"label": "b", "start": 2, "end": 3},
                "joint": True,
            },
        ],
    ),
    "record": (
        payloads.RecordPayload,
        [
            {
                "structure": "s",
                "fields": {"f": [{"start": 0, "end": 1, "text": "a", "score": 1}]},
                "anchor": None,
            },
        ],
    ),
    "attribute": (
        payloads.AttributePayload,
        [
            {"mention_ref": {"ordinal": 1}, "group": "g", "value": 1},
        ],
    ),
    "classification": (
        payloads.ClassificationPayload,
        [
            {"task": "kind", "labels": [{"label": "theorem", "score": 0.75}], "feasible": False},
        ],
    ),
    "value": (
        payloads.ValuePayload,
        [
            {
                "value": {
                    "t": "formula",
                    "latex": "a",
                    "sympy": "Symbol('a')",
                    "parse": "ok",
                    "symbols": {},
                },
                "math_kind": "formula",
            },
        ],
    ),
    "scope": (
        payloads.ScopePayload,
        [
            {
                "mention_ref": {"ordinal": 1},
                "start": 3,
                "end": 4,
                "scope_segment": "seg:1",
                "extent": "section",
                "binding_site": {"mention_ref": {"task": 7, "ordinal": 0}, "start": 0, "end": 2},
            },
        ],
    ),
    "link": (
        payloads.LinkPayload,
        [
            {"candidate": "ent:1", "score": 0.9, "features": {}, "mention_ref": {"ordinal": 1}},
            {
                "candidate": "ent:2",
                "score": 0.1,
                "features": {"cos": 0.1},
                "pair": ["a", "b"],
                "rank": 2,
            },
        ],
    ),
    "judgment": (
        payloads.JudgmentPayload,
        [
            {
                "target": {"kind": "claim", "ref": "clm:1", "key_scheme": 1},
                "decision": "choose",
                "rationale": "r",
                "guideline_version": "1",
                "chosen": ["clm:1"],
                "faithful": True,
            },
        ],
    ),
    "verification": (
        payloads.VerificationPayload,
        [
            {
                "claim_key": "clm:0123456789abcdef0123456789abcdef",
                "verifier": "M19",
                "verdict": "refuted",
                "detail": {"rule": "stat.r1", "severity": "warning", "message": "m"},
            },
        ],
    ),
    "claim_proposal": (
        payloads.ClaimProposalPayload,
        [
            {"batch": STORED_BATCH, "schema_version": "a" * 64, "rationale": "none"},
        ],
    ),
    "task_cost": (payloads.Cost, [{"wall_ms": 12}, {"wall_ms": 3, "tokens_in": 10}]),
    "policy_action": (
        payloads.PolicyAction,
        [
            {"method": "llm.propose/default", "limit": 50, "then": "stop"},
        ],
    ),
    "intervention_target": (payloads.InterventionTarget, [{"kind": "claim", "ref": "clm:1"}]),
    "trigger_metrics": (payloads.TRIGGER_METRICS, [{"low_confidence": 0.4, "n": 3}, {}]),
    "compiled_artifact": (TypeAdapter(JsonValue), [{"tables": [1, "x"]}, "a text artifact"]),
    "run_options": (
        RunOptions,
        [
            {
                "agent_mode": "complete",
                "corpus": {"documents": ["doc:1"]},
                "configs": {"m/default": "cfg:1"},
                "method_configs": {},
                "fresh": ["extract.math"],
            },
        ],
    ),
    "parse_detail": (
        ParseDetail,
        [
            {"data_loss_warnings": 0},
            {"encoding": "utf-8", "data_loss_warnings": 2, "macro_notes": ["\\P"]},
        ],
    ),
    "citation_frame": (
        CitationFrame,
        [
            {"s1": {"locator": "special/Normal.html@sentence:Suppose", "text": "Suppose X."}},
        ],
    ),
    "golden_batch": (
        payloads.GoldenBatchPayload,
        [
            {
                "batch": {"unit_ref": "special/Normal.html#u1"},
                "citation_frame": {
                    "s1": {"locator": "special/Normal.html@sentence:Suppose", "text": "Suppose X."}
                },
            },
        ],
    ),
}


def _dump(shape: Any, sample: dict[str, Any]) -> Any:
    adapter = shape if isinstance(shape, TypeAdapter) else TypeAdapter(shape)
    return adapter.dump_python(adapter.validate_python(sample), mode="json")


def test_every_payload_kind_has_a_sample(projections: ix.Interchange) -> None:
    assert set(SAMPLES) == set(projections.kinds)


@pytest.mark.parametrize("kind", sorted(SAMPLES))
def test_shape_dumps_round_trip_through_the_arrow_projection(
    projections: ix.Interchange, kind: str
) -> None:
    shape, samples = SAMPLES[kind]
    dumps = [_dump(shape, s) for s in samples]
    schema = projections.payload(kind)
    table = ix.encode(schema, dumps)
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, schema) as writer:
        writer.write_table(table)
    back = pa.ipc.open_stream(sink.getvalue()).read_all()
    assert back.schema.equals(schema, check_metadata=True)
    assert ix.decode(back) == dumps
    # the shapes' fields are the projection's fields (a root class: its one attribute)
    model_shape = not isinstance(shape, TypeAdapter) and hasattr(shape, "model_fields")
    if model_shape and b"cs.root" not in (schema.metadata or {}):
        assert set(shape.model_fields) == set(schema.names), kind


def test_a_json_null_is_not_an_absent_value(projections: ix.Interchange) -> None:
    schema = projections.payload("record")
    table = ix.encode(
        schema, [{"structure": "s", "fields": {}, "anchor": None}, {"structure": "s", "fields": {}}]
    )
    assert table.column("anchor").to_pylist() == ["null", None]
    assert ix.decode(table) == [
        {"structure": "s", "fields": {}, "anchor": None},
        {"structure": "s", "fields": {}},
    ]


def test_a_required_field_given_null_is_refused(projections: ix.Interchange) -> None:
    with pytest.raises(ix.NullPolicyError, match="text: null where the schema forbids it"):
        ix.encode(projections.payload("mention"), [{"label": "L", "start": 0, "end": 1}])


def test_a_never_slot_given_null_is_refused(tmp_path: Path) -> None:
    text = (MODEL / "system.yaml").read_text(encoding="utf-8")
    old = "      gpu_ms: {range: integer, description: GPU time in milliseconds.}\n"
    assert text.count(old) == 1
    new = (
        "      gpu_ms: {range: integer, description: GPU time in milliseconds., "
        "annotations: {ci:null: never}}\n"
    )
    (tmp_path / "system.yaml").write_text(text.replace(old, new), encoding="utf-8")
    (tmp_path / "core.yaml").write_text((MODEL / "core.yaml").read_text(), encoding="utf-8")
    seeded = ix.compile_interchange(model.load(tmp_path / "core.yaml", tmp_path / "system.yaml"))
    schema = seeded.payload("task_cost")
    assert not schema.field("gpu_ms").nullable
    assert schema.field("gpu_ms").metadata == {b"cs.null": b"never"}
    with pytest.raises(ix.NullPolicyError, match="gpu_ms"):
        ix.encode(schema, [{"wall_ms": 1}])
    with pytest.raises(ix.NullPolicyError, match="gpu_ms"):
        ix.encode(schema, [{"wall_ms": 1, "gpu_ms": None}])
    assert ix.decode(ix.encode(schema, [{"wall_ms": 1, "gpu_ms": 2}])) == [
        {"wall_ms": 1, "gpu_ms": 2}
    ]


# --- DuckDB ---------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(SAMPLES))
def test_duckdb_reads_the_projection_with_its_types(
    projections: ix.Interchange, kind: str, tmp_path: Path
) -> None:
    shape, samples = SAMPLES[kind]
    schema = projections.payload(kind)
    table = ix.encode(schema, [_dump(shape, s) for s in samples])
    con = duckdb.connect()
    try:
        con.register("records", table)
        described = dict(
            con.execute(
                "SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM records)"
            ).fetchall()
        )
        assert described == ix.duckdb_columns(schema)
        # each record as a VARIANT, shredded by the generated spec into Parquet and read back
        con.execute(
            "CREATE TABLE p AS SELECT CAST(to_json(records) AS VARIANT) AS payload "
            "FROM (SELECT * FROM records) AS records"
        )
        path = tmp_path / f"{kind}.parquet"
        spec = projections.shredding(kind).replace("'", "''")
        con.execute(f"COPY p TO '{path}' (FORMAT parquet, SHREDDING {{'payload': '{spec}'}})")
        back = con.execute(f"SELECT CAST(payload AS JSON) FROM '{path}'").fetchall()
        original = con.execute("SELECT CAST(payload AS JSON) FROM p").fetchall()
        assert [json.loads(r[0]) for r in back] == [json.loads(r[0]) for r in original]
    finally:
        con.close()


def test_table_columns_have_duckdb_types(projections: ix.Interchange) -> None:
    con = duckdb.connect()
    try:
        for name, schema in projections.tables.items():
            columns = ", ".join(f'"{c}" {t}' for c, t in ix.duckdb_columns(schema).items())
            con.execute(f'CREATE TABLE "{name}" ({columns})')
            empty = pa.Table.from_pylist([], schema=schema)
            con.register("empty", empty)
            con.execute(f'INSERT INTO "{name}" SELECT * FROM empty')
            con.unregister("empty")
    finally:
        con.close()


# --- JSON Schema $id ------------------------------------------------------------------------


def test_every_committed_schema_carries_its_id_and_is_valid() -> None:
    files = sorted(schemas.DIRECTORY.glob("*.json"))
    assert {p.stem for p in files} == set(schemas.SCHEMAS())
    ids = set()
    for path in files:
        document = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(document)
        assert list(document)[:2] == ["$schema", "$id"], path.name
        assert document["$id"] == schemas.schema_id(path.stem), path.name
        assert document["$id"].split("/")[-2] == revision.CONTENT_HASH[:12]
        ids.add(document["$id"])
    assert len(ids) == len(files)


def test_a_schema_version_adds_its_segment() -> None:
    assert schemas.schema_id("batch.stored", "a" * 64, "b" * 64) == (
        f"{schemas.ID_ROOT}/{'a' * 12}/{'b' * 12}/batch.stored.json"
    )
