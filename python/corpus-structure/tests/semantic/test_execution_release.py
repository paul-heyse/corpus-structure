"""Current operation archives and native semantic admission use exact captured inputs."""

import json
import sys
from dataclasses import replace
from hashlib import sha256

import pytest
import yaml
from sqlalchemy import select, text, update

from corpus_structure.semantic import releases
from corpus_structure.semantic.data_operation_admission import admit_data_operation_release
from corpus_structure.semantic.execution_admission import ExecutionAdmissionError
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.prepare import prepare_release
from semantic.archive_faults import administrative_archive_edit
from semantic.data_operation_kernel_support import STORAGE, prepare_kernel


def _prepare(*, schema=None, scope=None):
    captured = prepare_kernel(STORAGE)
    bundle, dependencies, profile = captured.bundle, captured.dependencies, captured.profile
    if schema is not None:
        bundle = replace(
            bundle,
            sources=(
                replace(bundle.sources[0], content=yaml.safe_dump(schema).encode()),
                *bundle.sources[1:],
            ),
        )
    if scope is not None:
        profile = replace(profile, constraint_scope=scope)
    prepared = prepare_release(bundle, dependencies, profile)
    return bundle, dependencies, profile, prepared


def _stage(connection, **kwargs):
    bundle, dependencies, profile, prepared = _prepare(**kwargs)
    releases.persist_release(connection, bundle, dependencies, profile, prepared)
    return bundle, dependencies, profile, prepared


def test_current_operation_inputs_and_products_reload_exactly_offline(
    commit_db_engine, monkeypatch
):
    with commit_db_engine.begin() as connection:
        bundle, dependencies, profile, prepared = _stage(connection)
        assert json.loads(prepared.manifest)["data_operation_model"]
        assert not any(item.name.startswith("execution/") for item in dependencies.artifacts)
        assert not any(row.kind == "execution_model" for row in prepared.registry_rows)
        monkeypatch.setitem(sys.modules, "corpus_structure.semantic.contracts", None)
        # Explicit verification rederives only these archived inputs; no retired
        # implementation snapshot supplies authority or current source discovery.
        assert releases.load_release(connection, prepared.release_id) == prepared
        assert (
            releases.persist_release(connection, bundle, dependencies, profile, prepared)
            == prepared.release_id
        )
        archived = table("sem.input")
        actual = dict(
            connection.execute(
                select(archived.c.input_name, archived.c.content).where(
                    archived.c.release_id == prepared.release_id,
                    archived.c.input_kind == "dependency",
                )
            ).all()
        )
        assert {name: bytes(content) for name, content in actual.items()} == {
            item.name: item.content
            for item in dependencies.artifacts
            if not (item.authoring_provenance or item.runtime_transport)
        }


@pytest.mark.parametrize("relation", ["input", "artifact", "registry_row", "release"])
def test_corrupt_current_archive_refuses_even_with_recomputed_digest(commit_db_engine, relation):
    with commit_db_engine.begin() as connection:
        _, dependencies, _, prepared = _stage(connection)
        target = table("sem." + relation)
        predicates = [target.c.release_id == prepared.release_id]
        if relation == "input":
            item = next(
                item for item in dependencies.artifacts if item.name.endswith("manifest.json")
            )
            predicates += [target.c.input_kind == "dependency", target.c.input_name == item.name]
            content = item.content + b"\n"
            values = dict(content=content, content_digest=sha256(content).hexdigest())
        elif relation == "artifact":
            predicates += [target.c.artifact_name == "data_operations.json"]
            content = b'{"version":"forged-model"}'
            values = dict(content=content, content_digest=sha256(content).hexdigest())
        elif relation == "registry_row":
            row = prepared.registry_rows[0]
            predicates += [target.c.kind == row.kind, target.c.name == row.name]
            values = dict(body=b'{"forged":true}')
        else:
            content = connection.scalar(select(target.c.prepared_bytes).where(*predicates))
            archive = json.loads(bytes(content))
            archive["products"]["definitions"] = []
            content = canonical_bytes(archive)
            values = dict(prepared_bytes=content, content_digest=sha256(content).hexdigest())
        with administrative_archive_edit(connection, target):
            changed = connection.execute(update(target).where(*predicates).values(**values))
            assert changed.rowcount == 1
        with pytest.raises(releases.ReleaseConflict):
            releases.load_release(connection, prepared.release_id)


@pytest.mark.parametrize("scope", ["occurrence", "context"])
def test_current_native_admission_refuses_unimplemented_graph_scope(commit_db_engine, scope):
    with commit_db_engine.begin() as connection:
        *_, prepared = _stage(connection, scope=scope)
        with (
            pytest.raises(
                ExecutionAdmissionError,
                match="unsupported required native constraint scope or pattern",
            ),
            connection.begin_nested(),
        ):
            admit_data_operation_release(connection, prepared)
        definitions = table("sem.data_operation_definition")
        assert not connection.scalar(
            select(definitions.c.operation_id)
            .where(definitions.c.release_id == prepared.release_id)
            .limit(1)
        )


@pytest.mark.parametrize("flag", ["transitive", "symmetric"])
def test_current_native_admission_refuses_scalar_inference_relation(commit_db_engine, flag):
    schema = yaml.safe_load(STORAGE.schema_text)
    schema["slots"] = dict(scalar_relation=dict(range="string", **{flag: True}))
    schema["classes"]["Thing"]["slots"] = ["scalar_relation"]
    with commit_db_engine.begin() as connection:
        *_, prepared = _stage(connection, schema=schema)
        with pytest.raises(
            ExecutionAdmissionError, match="unsupported required native binary inference profile"
        ):
            admit_data_operation_release(connection, prepared)


def test_current_native_admission_accepts_binary_rules_with_subtyped_range(commit_db_engine):
    schema = yaml.safe_load(STORAGE.schema_text)
    schema["slots"] = dict(
        edge=dict(range="Thing", inverse="reverse", transitive=True),
        reverse=dict(range="Thing", symmetric=True),
        broad=dict(range="Thing"),
        narrow=dict(range="Child", is_a="broad"),
    )
    schema["classes"]["Thing"]["slots"] = ["edge", "reverse", "broad", "narrow"]
    schema["classes"]["Child"] = dict(is_a="Thing")
    with commit_db_engine.begin() as connection:
        *_, prepared = _stage(connection, schema=schema)
        assert admit_data_operation_release(connection, prepared)
        connection.execute(
            text("SELECT data.require_execution_release(:r)"), dict(r=prepared.release_id)
        )


@pytest.mark.parametrize("scope", ["shape", "occurrence", "context"])
def test_scope_variants_retain_actual_declared_property_requirements(scope):
    *_, prepared = _prepare(scope=scope)
    sample = next(definition for definition in prepared.definitions if definition.name == "Sample")
    assert {prop.constraint_scope for prop in sample.properties} == {scope}
    assert json.loads(prepared.manifest)["data_operation_model"]


def test_native_constraint_diagnostic_distinguishes_stale_descriptor_from_shape_pattern(
    commit_db_engine,
):
    """Fault-inject only the owned clone; test the SQL guard's diagnostic boundary."""
    from sqlalchemy.exc import DBAPIError

    schema = yaml.safe_load(STORAGE.schema_text)
    schema["classes"]["Sample"]["attributes"]["label"] = {
        "range": "string",
        "required": True,
        "pattern": "^bounded$",
    }
    with commit_db_engine.begin() as connection:
        *_, prepared = _stage(connection, schema=schema)
        admit_data_operation_release(connection, prepared)
        query = text("SELECT data.require_execution_release(:r)")
        connection.execute(query, {"r": prepared.release_id})
        fault = connection.begin_nested()
        try:
            # Deliberately mismatch the installed descriptor while leaving the
            # actual archived sources, class projection and shape pattern intact.
            # Python's outer frozen-catalog check is a different boundary.
            connection.exec_driver_sql("""
                CREATE OR REPLACE FUNCTION sem.data_operation_native_descriptor()
                RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp
                AS $$ SELECT jsonb_build_object('version','data-operation-native-v1',
                    'source_digest',repeat('0',64)) $$
            """)
            with (
                pytest.raises(
                    DBAPIError, match="release was prepared for a different native kernel"
                ),
                connection.begin_nested(),
            ):
                connection.execute(query, {"r": prepared.release_id})
        finally:
            fault.rollback()
        # The genuine current descriptor accepts the same supported shape again.
        connection.execute(query, {"r": prepared.release_id})
