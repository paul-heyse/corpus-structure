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
from corpus_structure.semantic.typed_generation import generated_identifiers, generated_source
from semantic.analytics_support import prepared_inputs

REPO = Path(__file__).resolve().parents[4]


def test_generated_surface_is_current_and_attaches_existing_table():
    assert Path(_typed_columns.__file__).read_text() == generated_source()
    assert _typed_columns.data_occurrence is metadata.tables["data.occurrence"]
    from corpus_structure.semantic import identifiers
    assert Path(identifiers.__file__).read_text() == generated_identifiers()


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
        "from corpus_structure.semantic._typed_columns import data_occurrence_columns, sem_runtime_binding_columns\n"
        "from corpus_structure.semantic.identifiers import ReleaseId, RealizationId, RuntimeId\n"
        "def needs_release(value: ColumnElement[ReleaseId]) -> None: pass\n"
        "def needs_runtime(value: ColumnElement[RuntimeId]) -> None: pass\n"
        "def needs_text(value: ColumnElement[str]) -> None: pass\n"
        "def needs_integer(value: ColumnElement[int]) -> None: pass\n"
        "needs_text(data_occurrence_columns.occurrence_id)\n"
        "needs_release(data_occurrence_columns.release_id)\n"
        "needs_runtime(sem_runtime_binding_columns.runtime_id)\n"
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
        stream.write("needs_runtime(data_occurrence_columns.release_id)\n")
    bad = subprocess.run(command, capture_output=True, text=True, check=False)
    output = bad.stdout + bad.stderr
    assert bad.returncode != 0
    assert "absent_modeled_column" in output
    assert "needs_integer" in output
    assert "needs_release" in output
    assert "needs_runtime" in output


def test_two_native_invocations_reuse_preparation_and_return_independent_rows(
    commit_db_engine, commit_writer_engine, monkeypatch
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
    with commit_db_engine.begin() as conn:
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
            commit_writer_engine,
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
        with commit_db_engine.connect() as conn:
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
    from corpus_structure.semantic.native_call_contracts import OperationFieldBinding
    from corpus_structure.semantic.types import PreparationError

    def mutate(model):
        model["classes"]["occurrence"]["attributes"]["realization_id"]["annotations"]["cp:type_source"] = target

    _, _, _, resolve = _correspondence_bindings(_changed_physical_sources(mutate))
    with pytest.raises(PreparationError, match=message):
        resolve(OperationFieldBinding("realization_id", "physical:data.occurrence.realization_id", False), {})


def _changed_physical_sources(mutate):
    import yaml

    sources = dict(metadata.info["physical_sources"])
    changed = yaml.safe_load(sources["physical.yaml"])
    mutate(changed)
    sources["physical.yaml"] = yaml.safe_dump(changed, sort_keys=False).encode()
    return sources


def _correspondence_bindings(sources):
    from corpus_structure.semantic.native_call_sources import source_bindings

    return source_bindings((), logical_sources={"linkml:types": metadata.info["physical_linkml_types"]}, physical_sources=sources)


@pytest.mark.parametrize(
    "target,message",
    [
        ("physical:sem.release.release_id", "cyclic"),
        ("physical:data.occurrence.release_id", "cyclic"),
        ("physical:data.realization.realization_id", "nominal identifiers differ"),
        ("physical:ops.task.id", "encoding differs"),
    ],
)
def test_anchored_correspondence_is_validated_during_compilation(target, message):
    from corpus_structure.schema.physical import compile_physical
    from corpus_structure.schema.model import ModelError

    def mutate(model):
        slot = model["classes"]["release"]["attributes"]["release_id"]
        slot.setdefault("annotations", {})["cp:type_source"] = target

    with pytest.raises(ModelError, match=message):
        compile_physical(_changed_physical_sources(mutate), linkml_types=metadata.info["physical_linkml_types"])


def test_type_correspondence_keeps_local_nullable_and_constraints():
    from corpus_structure.semantic.native_call_contracts import OperationFieldBinding

    def mutate(model):
        slot = model["classes"]["occurrence"]["attributes"]["release_id"]
        slot["required"] = False
        slot["pattern"] = "local-pattern"

    inputs = _changed_physical_sources(mutate)
    _, nominal, _, resolve = _correspondence_bindings(inputs)
    resolved, facts = resolve(
        OperationFieldBinding("release_id", "physical:data.occurrence.release_id", False), {}
    )
    assert nominal("physical:data.occurrence.release_id") == "ReleaseId"
    assert resolved.nullable is True
    assert facts["pattern"] == "local-pattern"
    assert facts["reference"] == "physical:data.occurrence.release_id"
    assert facts["type_source"]["reference"] == "physical:sem.release.release_id"


def test_type_correspondence_rejects_conflicting_closed_members():
    from corpus_structure.semantic.native_call_contracts import OperationFieldBinding
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

    inputs = _changed_physical_sources(mutate)
    _, _, _, resolve = _correspondence_bindings(inputs)
    with pytest.raises(PreparationError, match="members differ"):
        resolve(
            OperationFieldBinding("members", "physical:data.occurrence.local_members", False), {}
        )


def test_type_correspondence_cannot_hide_behind_value_projection():
    from corpus_structure.semantic.native_call_contracts import OperationFieldBinding
    from corpus_structure.semantic.types import PreparationError

    def mutate(model):
        field = model["classes"]["occurrence"]["attributes"]["release_id"]
        field["annotations"]["cp:source"] = "physical:sem.release.release_id"
        field["annotations"]["cp:type_source"] = "physical:data.realization.realization_id"

    inputs = _changed_physical_sources(mutate)
    _, _, _, resolve = _correspondence_bindings(inputs)
    with pytest.raises(PreparationError, match="semantic identifiers differ"):
        resolve(OperationFieldBinding("release", "physical:data.occurrence.release_id", False), {})


def test_companion_generator_cannot_bypass_invalid_anchored_correspondence():
    import json
    import yaml

    from corpus_structure.schema.model import ModelError
    from corpus_structure.semantic.companion_projection import render_static_columns
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.pdf_domain import PREFIX, PdfDomainContract, pdf_domain_sources
    from corpus_structure.semantic.types import SourceArtifact

    contract, *sources = pdf_domain_sources()
    changed = []
    for source in sources:
        if source.name == PREFIX + "physical/physical.yaml":
            document = yaml.safe_load(source.content)
            field = document["classes"]["release"]["attributes"]["release_id"]
            field.setdefault("annotations", {})["cp:type_source"] = "physical:data.realization.realization_id"
            source = SourceArtifact(source.name, yaml.safe_dump(document, sort_keys=False).encode())
        changed.append(source)
    manifest = json.loads(contract.content)
    manifest["inputs"] = [{"name": source.name, "sha256": source.digest} for source in changed]
    captured = PdfDomainContract(canonical_bytes(manifest), tuple(changed))
    with pytest.raises(ModelError, match="physical nominal identifiers differ"):
        render_static_columns(captured)


def test_correspondence_preserves_value_projection_lineage_and_rejects_collection_mismatch():
    from corpus_structure.semantic.native_call_contracts import OperationFieldBinding
    from corpus_structure.semantic.types import PreparationError

    def mutate(model):
        fields = model["classes"]["occurrence"]["attributes"]
        fields["release_id"]["annotations"]["cp:source"] = "physical:sem.release.release_id"
        fields["many_release_ids"] = {"range": "string", "multivalued": True}
        fields["bad_release_id"] = {
            "range": "string",
            "annotations": {"cp:type_source": "physical:data.occurrence.many_release_ids"},
        }

    inputs = _changed_physical_sources(mutate)
    _, nominal, _, resolve = _correspondence_bindings(inputs)
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
    from corpus_structure.schema.physical import compile_physical
    from corpus_structure.schema.model import ModelError

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

    with pytest.raises(ModelError, match="cyclic"):
        compile_physical(_changed_physical_sources(mutate), linkml_types=metadata.info["physical_linkml_types"])


@pytest.mark.parametrize(
    "target, message",
    [
        ("physical:data.occurrence.realization_id", "cyclic physical type correspondence"),
        ("physical:data.occurrence.missing_field", "field is unavailable"),
        ("physical:ops.task.id", "encoding differs"),
        ("physical:data.realization.realization_id", "nominal identifiers differ"),
    ],
)
def test_physical_nominal_correspondences_are_checked_without_execution_catalog(target, message):
    import yaml
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.physical import compile_physical

    sources = dict(metadata.info["physical_sources"])
    document = yaml.safe_load(sources["physical.yaml"])
    # Preserve each independent nominal declaration while deliberately corrupting its edge.
    cls = "occurrence" if target != "physical:data.realization.realization_id" else "release"
    field = "realization_id" if cls == "occurrence" else "release_id"
    document["classes"][cls]["attributes"][field].setdefault("annotations", {})["cp:type_source"] = target
    sources["physical.yaml"] = yaml.safe_dump(document).encode()
    with pytest.raises(ModelError, match=message):
        compile_physical(sources)


def test_current_wire_and_column_nominals_share_the_canonical_owner():
    from typing import Required, get_args, get_origin, get_type_hints
    from corpus_structure.semantic import identifiers
    from corpus_structure.semantic._data_operation_wire import WireRegisterDataDemandRequest

    release_type = get_type_hints(WireRegisterDataDemandRequest, include_extras=True)["release_id"]
    assert get_origin(release_type) is Required
    assert get_args(release_type) == (identifiers.ReleaseId,)
    assert metadata.tables["data.occurrence"].c.release_id.info["python_type"] == "corpus_structure.semantic.identifiers.ReleaseId"
    assert metadata.tables["data.occurrence"].c.realization_id.info["python_type"] == "corpus_structure.semantic.identifiers.RealizationId"
