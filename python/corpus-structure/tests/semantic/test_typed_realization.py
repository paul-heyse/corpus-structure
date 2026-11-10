"""Model generation, actual static consumer checks and invocation-bound preparation."""

import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pyarrow as pa
import pytest
from sqlalchemy import Column, MetaData, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateColumn

from corpus_structure.schema.relational import render_typed_column_class
from corpus_structure.semantic import _typed_columns
from corpus_structure.semantic.analytics import compile_projection, compile_sql
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.pdf_record_model import record_arrow_schema, record_write_profile
from corpus_structure.semantic.query import SnapshotBinding
from corpus_structure.semantic.typed_generation import generated_source

from .test_analytics import prepared_inputs

REPO = Path(__file__).resolve().parents[4]


def test_generated_surface_is_current_and_attaches_existing_table():
    assert Path(_typed_columns.__file__).read_text() == generated_source()
    assert _typed_columns.data_occurrence is metadata.tables["data.occurrence"]


def test_one_modeled_field_updates_static_native_and_arrow_products():
    changed = MetaData()
    target = metadata.tables["ops.pdf_stage_native"].to_metadata(changed)
    target.append_column(Column("modeled_extra", Text, nullable=False))
    generated = render_typed_column_class("ChangedColumns", target.columns)
    assert "modeled_extra: Named[str]" in generated
    native = str(CreateColumn(target.c.modeled_extra).compile(dialect=postgresql.dialect()))
    assert "modeled_extra TEXT NOT NULL" in native
    arrow = record_arrow_schema(target.fullname, model=changed)
    assert arrow.field("modeled_extra") == pa.field(
        "modeled_extra",
        pa.string(),
        nullable=False,
        metadata={"postgresql": "text", "constraints": "{}"},
    )
    write_profile = record_write_profile(target.fullname, release_id="r", model=changed)
    assert write_profile.fields[-1].wire_type == "text"


def test_shape_reused_with_independent_invocation_values_and_changed_profile(monkeypatch):
    from corpus_structure.semantic import analytics

    prepared = replace(prepared_inputs()[2])
    original = analytics._prepare_projection_shapes
    calls = []

    def prepare(scale):
        calls.append(scale)
        return original(scale)

    monkeypatch.setattr(analytics, "_prepare_projection_shapes", prepare)
    first = compile_projection(
        prepared, SnapshotBinding(prepared.release_id, "one", 1, "capture-1")
    )
    second = compile_projection(
        prepared, SnapshotBinding(prepared.release_id, "two%_o'", 2, "capture-2")
    )
    assert calls == [12]
    assert first.projection_id == second.projection_id
    for value, projection in (("one", first), ("two%_o'", second)):
        sql = compile_sql(projection.relations[0].statement)
        assert ("'one'" if value == "one" else "'two%_o'''") in sql
        capture = projection.relations[0].schema.metadata[b"cs.capture"]
        assert capture == projection.binding.capture_id.encode()
    monkeypatch.setattr(analytics, "COMPILER_VERSION", "changed-compiler")
    third = compile_projection(prepared, replace(first.binding, capture_id="new"))
    assert calls == [12, 12]
    assert third.projection_id != first.projection_id


@pytest.mark.skipif(shutil.which("pyrefly") is None, reason="blocked: pyrefly not on PATH")
def test_actual_static_consumer_refuses_wrong_column_and_incompatible_type(tmp_path):
    source = tmp_path / "consumer.py"
    source.write_text(
        "from sqlalchemy import select\n"
        "from sqlalchemy.sql.elements import ColumnElement\n"
        "from corpus_structure.semantic._typed_columns import data_occurrence_columns\n"
        "from corpus_structure.semantic._operation_ids import ReleaseId, RealizationId\n"
        "def needs_release(value: ColumnElement[ReleaseId]) -> None: pass\n"
        "def needs_text(value: ColumnElement[str]) -> None: pass\n"
        "def needs_integer(value: ColumnElement[int]) -> None: pass\n"
        "needs_text(data_occurrence_columns.occurrence_id)\n"
        "needs_release(data_occurrence_columns.release_id)\n"
        "select(data_occurrence_columns.occurrence_id)\n"
    )
    pyrefly = shutil.which("pyrefly")
    assert pyrefly is not None
    command = [pyrefly, "check", "--config", str(REPO / "pyproject.toml"), str(source)]
    good = subprocess.run(command, capture_output=True, text=True, check=False)
    assert good.returncode == 0, good.stdout + good.stderr
    with source.open("a") as stream:
        stream.write("select(data_occurrence_columns.absent_modeled_column)\n")
        stream.write("needs_integer(data_occurrence_columns.occurrence_id)\n")
        stream.write("needs_release(data_occurrence_columns.realization_id)\n")
    bad = subprocess.run(command, capture_output=True, text=True, check=False)
    output = bad.stdout + bad.stderr
    assert bad.returncode != 0
    assert "absent_modeled_column" in output
    assert "needs_integer" in output
    assert "needs_release" in output


def test_two_native_invocations_reuse_preparation_and_return_independent_rows(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
    from sqlalchemy import insert

    from corpus_structure.semantic import analytics
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import EntityRow, PublicationBatch, publish_batch
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.types import PreparationProfile

    bundle, dependencies, cached = prepared_inputs()
    prepared = replace(cached)
    pins = ("first", "second%_o'")
    with semantic_db_engine.begin() as conn:
        persist_release(
            conn, bundle, dependencies, PreparationProfile(version="semantic-2"), prepared
        )
        conn.execute(insert(table("data.project")).values(project_id="prepared-pins"))
        for realization in pins:
            conn.execute(
                insert(table("data.realization")).values(
                    realization_id=realization,
                    release_id=prepared.release_id,
                    project_id="prepared-pins",
                )
            )
    for realization in pins:
        publish_batch(
            semantic_writer_engine,
            PublicationBatch(
                prepared.release_id,
                realization,
                "batch:" + realization,
                entity=(EntityRow("entity:" + realization),),
            ),
        )
    original = analytics._prepare_projection_shapes
    prepared_scales = []

    def prepare(scale):
        prepared_scales.append(scale)
        return original(scale)

    monkeypatch.setattr(analytics, "_prepare_projection_shapes", prepare)
    for realization in pins:
        projection = compile_projection(
            prepared, SnapshotBinding(prepared.release_id, realization, 1, "capture:" + realization)
        )
        statement = next(row.statement for row in projection.relations if row.name == "entity")
        with semantic_db_engine.connect() as conn:
            assert [row["entity_id"] for row in conn.execute(statement).mappings()] == [
                "entity:" + realization
            ]
    assert prepared_scales == [12]


def test_selected_columns_reuse_nominal_anchors_and_keep_unbound_values_generic():
    source = generated_source()
    assert "release_id: Named[ReleaseId]" in source
    assert "realization_id: Named[RealizationId]" in source
    assert "occurrence_id: Named[str]" in source
    assert "FactId" not in source
    assert "family:Named[Literal[" in "".join(source.split())
    assert (
        _typed_columns.data_occurrence.c.release_id
        is metadata.tables["data.occurrence"].c.release_id
    )
    assert len(_typed_columns.TYPE_MODEL_ID) == 64


@pytest.mark.parametrize(
    "target, message",
    [
        ("physical:data.occurrence.realization_id", "cyclic field projection"),
        ("physical:data.occurrence.missing_field", "field is unavailable"),
        ("physical:ops.task.id", "encoding differs"),
    ],
)
def test_explicit_type_correspondence_refuses_invalid_sources(target, message):
    import yaml

    from corpus_structure.semantic.contracts import (
        OperationFieldBinding,
        compile_execution_model,
        trusted_execution_inputs,
    )
    from corpus_structure.semantic.operation_call_generation import source_bindings
    from corpus_structure.semantic.types import PreparationError, SourceArtifact

    inputs = trusted_execution_inputs()
    model = compile_execution_model(inputs)
    artifact = "pdf/record-physical.yaml"
    physical = next(s.content for s in inputs.implementations if s.name == artifact)
    changed = yaml.safe_load(physical)
    slot = changed["classes"]["occurrence"]["attributes"]["realization_id"]
    slot["annotations"]["cp:type_source"] = target
    changed_inputs = replace(
        inputs,
        implementations=tuple(
            SourceArtifact(s.name, yaml.safe_dump(changed, sort_keys=False).encode())
            if s.name == artifact
            else s
            for s in inputs.implementations
        ),
    )
    _, _, _, resolve = source_bindings(model, changed_inputs)
    with pytest.raises(PreparationError, match=message):
        resolve(
            OperationFieldBinding(
                "realization_id", "physical:data.occurrence.realization_id", False
            ),
            {},
        )


def _changed_correspondence_inputs(mutate):
    import yaml

    from corpus_structure.semantic.contracts import trusted_execution_inputs
    from corpus_structure.semantic.types import SourceArtifact

    inputs = trusted_execution_inputs()
    artifact = "pdf/record-physical.yaml"
    physical = next(source.content for source in inputs.implementations if source.name == artifact)
    changed = yaml.safe_load(physical)
    mutate(changed)
    return replace(
        inputs,
        implementations=tuple(
            SourceArtifact(source.name, yaml.safe_dump(changed, sort_keys=False).encode())
            if source.name == artifact
            else source
            for source in inputs.implementations
        ),
    )


@pytest.mark.parametrize(
    "target,message",
    [
        ("physical:sem.release.release_id", "cyclic"),
        ("physical:data.occurrence.release_id", "cyclic"),
        ("physical:data.realization.realization_id", "semantic identifiers differ"),
        ("physical:ops.task.id", "encoding differs"),
    ],
)
def test_anchored_correspondence_is_validated_during_compilation(target, message):
    from corpus_structure.semantic.contracts import compile_execution_model
    from corpus_structure.semantic.types import PreparationError

    def mutate(model):
        slot = model["classes"]["release"]["attributes"]["release_id"]
        slot.setdefault("annotations", {})["cp:type_source"] = target

    with pytest.raises(PreparationError, match=message):
        compile_execution_model(_changed_correspondence_inputs(mutate))


def test_type_correspondence_keeps_local_nullable_and_constraints():
    from corpus_structure.semantic.contracts import (
        OperationFieldBinding,
        compile_execution_model,
        trusted_execution_inputs,
    )
    from corpus_structure.semantic.operation_call_generation import source_bindings

    def mutate(model):
        slot = model["classes"]["occurrence"]["attributes"]["release_id"]
        slot["required"] = False
        slot["pattern"] = "local-pattern"

    inputs = _changed_correspondence_inputs(mutate)
    model = compile_execution_model(trusted_execution_inputs())
    _, nominal, _, resolve = source_bindings(model, inputs)
    resolved, facts = resolve(
        OperationFieldBinding("release_id", "physical:data.occurrence.release_id", False), {}
    )
    assert nominal("physical:data.occurrence.release_id") == "ReleaseId"
    assert resolved.nullable is True
    assert facts["pattern"] == "local-pattern"
    assert facts["reference"] == "physical:data.occurrence.release_id"
    assert facts["type_source"]["reference"] == "physical:sem.release.release_id"


def test_type_correspondence_rejects_conflicting_closed_members():
    from corpus_structure.semantic.contracts import (
        OperationFieldBinding,
        compile_execution_model,
        trusted_execution_inputs,
    )
    from corpus_structure.semantic.operation_call_generation import source_bindings
    from corpus_structure.semantic.types import PreparationError

    def mutate(model):
        model.setdefault("enums", {})["LocalMembers"] = {
            "permissible_values": {"one": {}, "two": {}}
        }
        model["enums"]["TargetMembers"] = {"permissible_values": {"one": {}}}
        fields = model["classes"]["occurrence"]["attributes"]
        fields["local_members"] = {
            "range": "LocalMembers",
            "annotations": {"cp:type_source": "physical:data.occurrence.target_members"},
        }
        fields["target_members"] = {"range": "TargetMembers"}

    inputs = _changed_correspondence_inputs(mutate)
    model = compile_execution_model(trusted_execution_inputs())
    _, _, _, resolve = source_bindings(model, inputs)
    with pytest.raises(PreparationError, match="members differ"):
        resolve(
            OperationFieldBinding("members", "physical:data.occurrence.local_members", False), {}
        )


def test_type_correspondence_cannot_hide_behind_value_projection():
    from corpus_structure.semantic.contracts import (
        OperationFieldBinding,
        compile_execution_model,
        trusted_execution_inputs,
    )
    from corpus_structure.semantic.operation_call_generation import source_bindings
    from corpus_structure.semantic.types import PreparationError

    def mutate(model):
        field = model["classes"]["occurrence"]["attributes"]["release_id"]
        field["annotations"]["cp:source"] = "physical:sem.release.release_id"
        field["annotations"]["cp:type_source"] = "physical:data.realization.realization_id"

    inputs = _changed_correspondence_inputs(mutate)
    model = compile_execution_model(trusted_execution_inputs())
    _, _, _, resolve = source_bindings(model, inputs)
    with pytest.raises(PreparationError, match="semantic identifiers differ"):
        resolve(OperationFieldBinding("release", "physical:data.occurrence.release_id", False), {})


@pytest.mark.parametrize("consumer", ["columns", "companions"])
def test_generators_cannot_bypass_invalid_anchored_correspondence(consumer, monkeypatch):
    from corpus_structure.semantic import contracts
    from corpus_structure.semantic.companion_projection import render_static_columns
    from corpus_structure.semantic.types import PreparationError

    def mutate(model):
        field = model["classes"]["release"]["attributes"]["release_id"]
        field.setdefault("annotations", {})["cp:type_source"] = (
            "physical:data.realization.realization_id"
        )

    inputs = _changed_correspondence_inputs(mutate)
    monkeypatch.setattr(contracts, "trusted_execution_inputs", lambda: inputs)
    with pytest.raises(PreparationError, match="semantic identifiers differ"):
        (generated_source if consumer == "columns" else render_static_columns)()


def test_correspondence_preserves_value_projection_lineage_and_rejects_collection_mismatch():
    from corpus_structure.semantic.contracts import (
        OperationFieldBinding,
        compile_execution_model,
        trusted_execution_inputs,
    )
    from corpus_structure.semantic.operation_call_generation import source_bindings
    from corpus_structure.semantic.types import PreparationError

    def mutate(model):
        fields = model["classes"]["occurrence"]["attributes"]
        fields["release_id"]["annotations"]["cp:source"] = "physical:sem.release.release_id"
        fields["many_release_ids"] = {"range": "string", "multivalued": True}
        fields["bad_release_id"] = {
            "range": "string",
            "annotations": {"cp:type_source": "physical:data.occurrence.many_release_ids"},
        }

    inputs = _changed_correspondence_inputs(mutate)
    model = compile_execution_model(trusted_execution_inputs())
    _, nominal, _, resolve = source_bindings(model, inputs)
    resolved, facts = resolve(
        OperationFieldBinding("release_id", "physical:data.occurrence.release_id", False), {}
    )
    assert nominal("physical:data.occurrence.release_id") == "ReleaseId"
    assert resolved.kind == "string"
    assert facts["projection"] == "physical:data.occurrence.release_id"
    assert facts["source"]["reference"] == "physical:sem.release.release_id"
    assert facts["type_source"]["reference"] == "physical:sem.release.release_id"
    with pytest.raises(PreparationError, match="encoding differs"):
        resolve(OperationFieldBinding("id", "physical:data.occurrence.bad_release_id", False), {})


@pytest.mark.parametrize("declaration", ["slot", "inherited_slot"])
def test_schema_slot_cannot_hide_anchored_self_correspondence(declaration):
    from corpus_structure.semantic.contracts import compile_execution_model
    from corpus_structure.semantic.types import PreparationError

    def mutate(model):
        release = model["classes"]["release"]
        field = release["attributes"].pop("release_id")
        field.setdefault("annotations", {})["cp:type_source"] = "physical:sem.release.release_id"
        model.setdefault("slots", {})["release_id"] = field
        if declaration == "slot":
            release.setdefault("slots", []).append("release_id")
        else:
            model["classes"]["PhysicalReleaseBase"] = {
                "in_subset": ["sem"],
                "slots": ["release_id"],
            }
            release["is_a"] = "PhysicalReleaseBase"

    with pytest.raises(PreparationError, match="cyclic"):
        compile_execution_model(_changed_correspondence_inputs(mutate))
