"""Actual empty-database target authoring, frozen Alembic installation and purpose ACLs."""

import json
import shutil
from dataclasses import replace
from hashlib import sha256

import pytest
import yaml
from alembic.script import ScriptDirectory
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, Text, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.cli.schema import _native_candidate_python
from corpus_structure.semantic.alembic_privileges import admit_privileges
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.migrations import (
    ALEMBIC_DIR,
    alembic_config,
    current_revision,
    upgrade,
)
from corpus_structure.semantic.native_authoring import (
    authored_admission_sql,
    load_native_state,
    verify_frozen_catalog,
    verify_rendered_candidate,
)
from corpus_structure.semantic.native_objects import (
    NativeAuthoringError,
    admit_native,
    native_owner,
)
from corpus_structure.semantic.storage_target import acquired_target, verify_target
from corpus_structure.semantic.target_installation import (
    capture_target_installation,
    prepare_target_candidate,
    prepare_target_successor,
)
from corpus_structure.semantic.value_codec import decimal_digit_limit
from native_test_support import principal_engine


@pytest.fixture(scope="module")
def fresh_target_epoch():
    return capture_target_installation(get_metadata())


def application_namespaces(connection):
    return tuple(
        connection.scalars(
            text(
                "SELECT nspname FROM pg_namespace WHERE nspname IN ('meta','sem','data','ops','kb','eval') ORDER BY nspname"
            )
        )
    )


def runtime_temp_privileges(connection):
    return tuple(
        (
            role,
            connection.scalar(
                text("SELECT has_database_privilege(:role,current_database(),'TEMP')"),
                {"role": role},
            ),
        )
        for role in (
            "corpus_sem_writer",
            "corpus_sem_reader",
            "corpus_sem_admitter",
            "corpus_sem_evaluator",
            "corpus_sem_fitter",
        )
    )


def test_actual_target_default_contract(semantic_bare_engine, fresh_target_epoch):
    from corpus_structure.semantic.native_authoring import _declared_physical_catalog

    selected = MetaData()
    for name in ("ops.task", "sem.sql_admission"):
        fresh_target_epoch.metadata.tables[name].to_metadata(selected)
    with semantic_bare_engine.begin() as connection:
        catalog = _declared_physical_catalog(connection, selected)
        assert catalog.defaults == {
            "ops.task": {"invocation_key": "(gen_random_uuid())::text", "trigger": "'{}'::jsonb"},
            "sem.sql_admission": {"input_kind": "'dependency'::text"},
        }
        assert (
            connection.scalar(text("SELECT to_regclass('pg_temp.semantic_candidate_catalog')"))
            is None
        )
        assert not application_namespaces(connection)


def test_actual_physical_row_type_context_restores_existing_data_and_new_tables(
    semantic_bare_engine,
):
    from corpus_structure.semantic.native_authoring import physical_row_type_context

    before = MetaData()
    Table(
        "parent",
        before,
        Column("id", Integer, primary_key=True, autoincrement=False),
        schema="row_type_control",
    )
    desired = MetaData()
    Table(
        "parent",
        desired,
        Column("id", Integer, primary_key=True, autoincrement=False),
        Column("note", Text, server_default=text("'future'")),
        schema="row_type_control",
        info={"read_roles": ()},
    )
    Table(
        "child",
        desired,
        Column("id", Integer, primary_key=True, autoincrement=False),
        Column("parent", Integer, ForeignKey("row_type_control.parent.id")),
        schema="row_type_control",
        info={"read_roles": ()},
    )
    with semantic_bare_engine.begin() as connection:
        connection.exec_driver_sql("CREATE SCHEMA row_type_control")
        connection.exec_driver_sql(
            "GRANT USAGE,CREATE ON SCHEMA row_type_control TO corpus_sem_publisher"
        )
        before.create_all(connection)
        connection.exec_driver_sql(
            "ALTER TABLE row_type_control.parent OWNER TO corpus_sem_publisher"
        )
        connection.exec_driver_sql("INSERT INTO row_type_control.parent VALUES(7)")
        with physical_row_type_context(connection, desired):
            assert connection.execute(
                text("SELECT id,note FROM row_type_control.parent")
            ).one() == (7, None)
            assert (
                connection.scalar(
                    text(
                        "SELECT pg_get_userbyid(relowner) FROM pg_class "
                        "WHERE oid='row_type_control.child'::regclass"
                    )
                )
                == "corpus_sem_publisher"
            )
        assert connection.execute(text("SELECT * FROM row_type_control.parent")).one() == (7,)
        assert connection.scalar(text("SELECT to_regclass('row_type_control.child')")) is None


def register_target_revision(
    location, revision_id, rendered, authoring, candidate, *, predecessor=None
):
    from corpus_structure.semantic.alembic_native import NativeTransitionOp
    from corpus_structure.semantic.alembic_privileges import PrivilegeTransitionOp, operation_record
    from corpus_structure.semantic.identity import canonical_bytes

    state = canonical_bytes(
        {
            "version": 2,
            "predecessor": predecessor,
            "operations": [
                operation_record(item)
                for item in candidate.upgrade_ops.ops
                if isinstance(item, (NativeTransitionOp, PrivilegeTransitionOp))
            ],
            "privileges": list(candidate.privilege_policies),
            "desired": [item.payload() for item in authoring.desired],
        }
    )
    admission = authored_admission_sql(authoring).encode()
    bindings = []
    for kind, suffix, content in (
        ("STATE", "native.json", state),
        ("ADMISSION", "admission.sql", admission),
    ):
        filename = revision_id + "_" + suffix
        (location / "versions" / filename).write_bytes(content)
        bindings.extend(
            (
                f"NATIVE_{kind}_FILE = {filename!r}",
                f"NATIVE_{kind}_SHA256 = {sha256(content).hexdigest()!r}",
            )
        )
    prefix, body = rendered.split("def upgrade():\n", 1)
    directory = ScriptDirectory.from_config(alembic_config(script_location=location))
    revision = directory.generate_revision(
        revision_id,
        "actual current target",
        head=predecessor or "base",
        imports=prefix + "\n" + "\n".join(bindings),
        upgrades=body.lstrip(),
        downgrades="raise RuntimeError('unsupported')",
    )
    assert revision is not None and revision.down_revision == predecessor
    return revision


def install_target_root(engine, epoch, tmp_path):
    with engine.begin() as connection:
        target = acquired_target(connection, purpose="maintenance")
        assert target.database == engine.url.database
        assert not application_namespaces(connection)
        assert current_revision(connection) is None
        before_temp = runtime_temp_privileges(connection)
        candidate, authoring = prepare_target_candidate(connection, epoch, owned_authoring=True)
        assert not authoring.predecessor
        assert not any(item.role_bindings for item in authoring.desired)
        assert not application_namespaces(connection)
        assert runtime_temp_privileges(connection) == before_temp
        assert not connection.scalar(
            text(
                "SELECT EXISTS(SELECT FROM pg_class WHERE relnamespace=pg_my_temp_schema() "
                "AND (starts_with(relname,'cs_archive_') OR starts_with(relname,'ps_pdf_')))"
            )
        )
        assert candidate.upgrade_ops is not None
        rendered = _native_candidate_python(candidate.upgrade_ops)
        admission = authored_admission_sql(authoring)
        verify_rendered_candidate(
            connection,
            rendered,
            authoring,
            candidate.privilege_policies,
            admission,
        )
        assert not application_namespaces(connection)
        assert runtime_temp_privileges(connection) == before_temp

    # Use Alembic's ordinary root template and upgrade lifecycle. The body is
    # exactly the operation-owned renderer already replayed above; there is no
    # hand-authored DDL, forced stamp, or fabricated native catalog/state.
    location = tmp_path / "fresh-target"
    (location / "versions").mkdir(parents=True)
    for filename in ("env.py", "script.py.mako"):
        shutil.copyfile(ALEMBIC_DIR / filename, location / filename)
    revision = register_target_revision(
        location, "target_fresh_control", rendered, authoring, candidate
    )
    with engine.begin() as connection:
        verify_target(connection, target, purpose="maintenance")
        assert upgrade(connection, revision.revision, script_location=location) == [
            {"revision": revision.revision, "direction": "upgrade"},
        ]
        assert current_revision(connection) == revision.revision
        actual = set(
            connection.scalars(
                text(
                    "SELECT n.nspname||'.'||c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname IN ('sem','data','ops','kb','eval') AND c.relkind IN ('r','p')"
                )
            )
        )
        assert actual == set(epoch.metadata.tables)
        assert not {"ops.run", "ops.method", "kb.source_view", "data.fact"} & actual
        admit_native(connection, authoring.desired)
        admit_privileges(connection, candidate.privilege_policies)
        verify_frozen_catalog(connection, admission)
        assert all(not permitted for _, permitted in runtime_temp_privileges(connection))
        with native_owner(connection, "corpus_sem_publisher"):
            connection.exec_driver_sql("CREATE TEMP TABLE target_scratch_control(value integer)")
            connection.exec_driver_sql("DROP TABLE pg_temp.target_scratch_control")
    return target, authoring, candidate, admission, revision, location


def test_actual_fresh_target_authoring_render_replay_install_and_acl(
    semantic_bare_engine,
    native_settings,
    fresh_target_epoch,
    tmp_path,
    monkeypatch,
):
    from corpus_structure.semantic import (
        data_operation_storage,
        migrations,
        native_program_registry,
        native_protocol_authoring,
    )
    from corpus_structure.semantic.execution_admission import (
        ExecutionAdmissionError,
        require_archive_fence,
    )
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.native_revision_compare import compare_native_programs
    from corpus_structure.semantic.target_installation import foundation_programs
    from corpus_structure.serve.demand_export import export_demand_result, verify_demand_export
    from semantic.data_operation_demand_support import attach, claim, publish, retain
    from semantic.data_operation_kernel_support import STORAGE, admit_kernel, prepare_kernel

    engine = semantic_bare_engine
    target, authoring, _, admission, revision, location = install_target_root(
        engine,
        fresh_target_epoch,
        tmp_path,
    )
    frozen = load_native_state(ALEMBIC_DIR / "versions" / "semantic_ddo_pe_n29_native.json")
    current_acl = {
        item.identity: (item.catalog["owner"], item.catalog.get("acl"))
        for item in authoring.desired
    }
    previous_acl = {
        item.identity: (item.catalog["owner"], item.catalog.get("acl")) for item in frozen
    }
    assert {item.name for item in previous_acl.keys() - current_acl.keys()} == {
        "ddo_classify_validity",
        "record_sql_admission",
        "ddo_rich_producing_request",
    }
    assert {item.name for item in current_acl.keys() - previous_acl.keys()} == {
        "ddo_conservative_dependencies_valid",
        "ddo_support_reference_node",
        "ddo_privileged_effect_eligible",
        "ddo_privileged_effect_admitted",
        "ddo_privileged_effect_authorized",
        "ddo_require_completion_effect_authority",
        "ddo_record_grade_require_cut_material",
        "ddo_record_grade_acquire_census_material",
        "admit_data_operation_effect_grants",
        "ddo_rich_producing_request",
        "prove_execution_release",
        "prove_execution_catalog",
        "consume_data_completion_draft",
        "ddo_impl_consume_data_completion_draft",
        "inspect_data_completion_draft",
        "ddo_impl_inspect_data_completion_draft",
        "ddo_impl_register_data_execution_origin",
        "require_execution_binding_facts",
        "ddo_current_validation_identities",
        "ddo_missing_validation_identities",
        "ddo_require_episode_identity",
        "ddo_require_completion_invariants",
        "ddo_require_completion_families",
        "ddo_require_episode_artifact_correspondence",
        "ddo_require_episode_contextual_correspondence",
        "ddo_require_episode_definition_correspondence",
        "ddo_require_episode_operation_event_correspondence",
        "ddo_require_episode_record_fit_correspondence",
        "ddo_require_episode_record_grade_correspondence",
        "ddo_require_episode_rich_correspondence",
        "ddo_require_consuming_episode",
        "ddo_episode_current_valid",
        "ddo_receipt_validation_current",
        "ddo_reconfirm_completion_validity",
        "pdf_spool_material_identity",
        "pdf_spool_request_material",
        "read_pdf_spool_recovery_candidates",
        "register_data_execution_origin",
        "semantic_immutable",
    }
    assert {
        (item.schema, item.relation)
        for item in current_acl.keys() - previous_acl.keys()
        if item.name == "semantic_immutable"
    } == {
        ("ops", "data_draft_consumption"),
        ("ops", "data_execution_origin"),
        ("ops", "data_validity_reconfirmation"),
        ("sem", "data_operation_effect_grant"),
    }
    assert all(
        current_acl[item] == previous_acl[item] for item in current_acl.keys() & previous_acl.keys()
    )
    frozen_n31 = {
        item.identity: item
        for item in load_native_state(ALEMBIC_DIR / "versions" / "semantic_ddo_pe_n31_native.json")
    }
    n36_canonical_json = next(
        item
        for item in load_native_state(ALEMBIC_DIR / "versions" / "semantic_ddo_pe_n36_native.json")
        if item.identity.schema == "data" and item.identity.name == "canonical_json"
    )
    desired = {item.identity: item for item in authoring.desired}
    from corpus_structure.semantic.native_products import literal_json_descriptor

    manifest = native_program_registry.ProgramManifest.from_definitions(authoring.desired)
    descriptor = literal_json_descriptor(admission, "data.execution_contract_descriptor")
    assert descriptor["kernel_identity"] == manifest.kernel_identity
    assert canonical_bytes(descriptor["program_manifest"]) == canonical_bytes(manifest.inventory)
    for program in foundation_programs(
        get_metadata(), decimal_digits=decimal_digit_limit()
    ).programs:
        key = program.declaration.identity
        if key.name == "activate_release":
            assert "data.prove_execution_release" in desired[key].statements[0]
        elif key.name == "require_archive_bytes":
            archive_check = desired[key].statements[0]
            assert "semantic-release-archive-4" in archive_check
            assert "archive generated products differ from release identity" in archive_check
            assert "products_digest" in archive_check
        elif key == n36_canonical_json.identity:
            assert desired[key].statements == n36_canonical_json.statements
        else:
            assert desired[key].statements == frozen_n31[key].statements
        assert current_acl[key] == (
            frozen_n31[key].catalog["owner"],
            frozen_n31[key].catalog.get("acl"),
        )
    # Resolve this genuinely registered immutable root. A reader must not need
    # access to the maintenance-only Alembic table to authenticate its contract.
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", location)
    unchanged = compare_native_programs(fresh_target_epoch, revision.revision)
    assert unchanged is not None and unchanged.unchanged
    assert unchanged.object_count == len(authoring.desired)
    assert unchanged.kernel_identity == manifest.kernel_identity
    changed_program = next(
        item for item in fresh_target_epoch.programs if item.identity.name == "read_demand_result"
    )
    variant = replace(
        fresh_target_epoch,
        programs=tuple(
            replace(item, sql=item.sql + "\n-- fixture changed the exact installed statement")
            if item.identity == changed_program.identity
            else item
            for item in fresh_target_epoch.programs
        ),
    )
    delta = compare_native_programs(variant, revision.revision)
    assert delta is not None and delta.changed == (changed_program.identity,)
    assert not (delta.added or delta.retired or delta.privileges_changed or delta.unchanged)
    admitter = principal_engine(native_settings, "admit", engine.url.database)
    try:
        with admitter.begin() as connection:
            require_archive_fence(connection)

        preparation = prepare_kernel(STORAGE, directory=tmp_path / "recorded-basis")

        def unexpected_generation(*args, **kwargs):
            raise AssertionError("acquisition must use the release's recorded native kernel")

        with monkeypatch.context() as execution:
            execution.setattr(
                native_protocol_authoring, "native_protocol_sources", unexpected_generation
            )
            execution.setattr(native_program_registry, "render_programs", unexpected_generation)
            with engine.begin() as connection:
                kernel = admit_kernel(connection, STORAGE, preparation=preparation)
            with admitter.begin() as connection:
                descriptor = connection.scalar(
                    text("SELECT sem.data_operation_native_descriptor()")
                )
                assert descriptor[
                    "source_digest"
                ] == data_operation_storage.require_data_operation_native(
                    connection, kernel.prepared
                )
                incorrect = replace(
                    kernel.prepared,
                    artifacts=tuple(
                        replace(
                            artifact,
                            content=canonical_bytes(
                                {**json.loads(artifact.content), "native_digest": "0" * 64}
                            ),
                        )
                        if artifact.kind == "data_operation_native_definitions.json"
                        else artifact
                        for artifact in kernel.prepared.artifacts
                    ),
                )
                with pytest.raises(ValueError, match="different native kernel"):
                    data_operation_storage.require_data_operation_native(connection, incorrect)
                assert descriptor[
                    "source_digest"
                ] == data_operation_storage.require_data_operation_native(
                    connection, kernel.prepared
                )
        demand, _, _, attached = attach(kernel)
        fence = claim(kernel, attached)
        publish(kernel, fence, retain(kernel, fence, outputs=(7,)))
        with engine.begin() as connection:
            selected = next(
                item for item in authoring.desired if item.identity.name == "read_demand_result"
            )
            with native_owner(connection, selected.catalog["owner"]):
                connection.exec_driver_sql(
                    "GRANT EXECUTE ON FUNCTION " + selected.identity.qualified + " TO PUBLIC"
                )
        try:
            with (
                admitter.begin() as connection,
                pytest.raises(ExecutionAdmissionError, match="native deployment catalog differs"),
            ):
                require_archive_fence(connection)
        finally:
            with (
                engine.begin() as connection,
                native_owner(connection, selected.catalog["owner"]),
            ):
                connection.exec_driver_sql(
                    "REVOKE EXECUTE ON FUNCTION " + selected.identity.qualified + " FROM PUBLIC"
                )
    finally:
        admitter.dispose()
    with engine.begin() as connection:
        # These historical kernel identities are intentionally absent. If such
        # an identity exists with a forbidden application grant, the same guard
        # must still refuse it. The controlled function has no semantic behavior.
        with connection.begin_nested() as changed:
            connection.exec_driver_sql(
                "CREATE FUNCTION data.validate_state(text,text) RETURNS integer "
                "LANGUAGE sql AS 'SELECT 0'; "
                "REVOKE ALL ON FUNCTION data.validate_state(text,text) FROM PUBLIC; "
                "GRANT EXECUTE ON FUNCTION data.validate_state(text,text) TO corpus_sem_reader"
            )
            with (
                pytest.raises(DBAPIError, match="application private kernel privilege"),
                connection.begin_nested(),
            ):
                verify_frozen_catalog(connection, admission)
            changed.rollback()
        assert (
            connection.scalar(text("SELECT to_regprocedure('data.validate_state(text,text)')"))
            is None
        )
        verify_frozen_catalog(connection, admission)
        assert upgrade(connection, revision.revision, script_location=location) == []
        with pytest.raises(NativeAuthoringError, match="existing application namespaces"):
            prepare_target_candidate(connection, fresh_target_epoch, owned_authoring=True)

        selected = next(
            item for item in authoring.desired if item.identity.name == "read_demand_result"
        )
        with connection.begin_nested() as changed:
            with native_owner(connection, selected.catalog["owner"]):
                connection.exec_driver_sql(
                    "GRANT EXECUTE ON FUNCTION " + selected.identity.qualified + " TO PUBLIC"
                )
            with pytest.raises(NativeAuthoringError):
                admit_native(connection, authoring.desired)
            changed.rollback()
        admit_native(connection, authoring.desired)

    reader = principal_engine(native_settings, "read", engine.url.database)
    try:
        with reader.begin() as connection:
            verify_target(connection, target.model_copy(update={"purpose": "read"}), purpose="read")
            assert (
                connection.scalar(
                    text(
                        "SELECT has_function_privilege(current_user,'ops.read_demand_result(jsonb)','EXECUTE')"
                    )
                )
                is True
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT has_function_privilege(current_user,"
                        "'ops.read_pdf_selected_source_events(text,text,text,text,text,text,text,text,text)','EXECUTE')"
                    )
                )
                is True
            )
            assert (
                connection.scalar(text("SELECT has_schema_privilege(current_user,'ops','CREATE')"))
                is False
            )
            with pytest.raises(DBAPIError) as scratch_denied, connection.begin_nested():
                connection.exec_driver_sql(
                    "CREATE TEMP TABLE runtime_forbidden_scratch(value integer)"
                )
            assert getattr(scratch_denied.value.orig, "sqlstate", None) == "42501"
            with pytest.raises(DBAPIError) as denied, connection.begin_nested():
                connection.exec_driver_sql("SELECT * FROM kb.data_product")
            assert getattr(denied.value.orig, "sqlstate", None) == "42501"
        with monkeypatch.context() as execution, reader.begin() as connection:
            execution.setattr(
                native_protocol_authoring, "native_protocol_sources", unexpected_generation
            )
            execution.setattr(native_program_registry, "render_programs", unexpected_generation)
            destination = tmp_path / "demand-export"
            exported = export_demand_result(
                connection,
                demand["demand_id"],
                project_id="ddo-test",
                destination=destination,
                page_rows=1,
            )
        assert (
            verify_demand_export(destination, manifest_digest=exported["manifest_digest"])[
                "outcome"
            ]
            == "passed"
        )
    finally:
        reader.dispose()


def test_actual_target_successor_uses_registered_state_and_preserves_installation(
    semantic_bare_engine,
    fresh_target_epoch,
    tmp_path,
):
    engine = semantic_bare_engine
    target, root_authoring, _, root_admission, root_revision, location = install_target_root(
        engine,
        fresh_target_epoch,
        tmp_path,
    )
    directory = ScriptDirectory.from_config(alembic_config(script_location=location))
    registered = directory.get_revision(root_revision.revision)
    assert registered is not None
    predecessor = load_native_state(
        location / "versions" / registered.module.NATIVE_STATE_FILE,
        digest=registered.module.NATIVE_STATE_SHA256,
    )
    assert predecessor == root_authoring.desired
    sources = dict(get_metadata().info["physical_sources"])
    declaration = yaml.safe_load(sources["physical.yaml"])
    declaration["classes"]["project"]["attributes"]["native_installation_note"] = {
        "range": "string",
        "annotations": {"ph:server_default_value": "unreviewed"},
    }
    sources["physical.yaml"] = yaml.safe_dump(declaration, sort_keys=False).encode()
    from corpus_structure.schema.physical import compile_physical

    successor = capture_target_installation(
        compile_physical(sources, linkml_types=get_metadata().info["physical_linkml_types"])
    )
    with engine.begin() as connection:
        verify_target(connection, target, purpose="maintenance")
        connection.exec_driver_sql(
            "INSERT INTO data.project(project_id) VALUES('successor-control')"
        )
        selected = next(item for item in predecessor if item.identity.name == "read_demand_result")
        incomplete = tuple(
            item for item in predecessor if item.identity.name != "pdf_identity_frame"
        )
        assert len(incomplete) < len(predecessor)
        with pytest.raises(
            NativeAuthoringError, match="complete frozen native predecessor inventory"
        ):
            prepare_target_successor(
                connection, successor, predecessor=incomplete, owned_authoring=True
            )
        with connection.begin_nested() as changed:
            with native_owner(connection, selected.catalog["owner"]):
                connection.exec_driver_sql(
                    "GRANT EXECUTE ON FUNCTION " + selected.identity.qualified + " TO PUBLIC"
                )
            with pytest.raises(NativeAuthoringError, match="native admission failed"):
                prepare_target_successor(
                    connection, successor, predecessor=predecessor, owned_authoring=True
                )
            changed.rollback()
        candidate, authoring = prepare_target_successor(
            connection,
            successor,
            predecessor=predecessor,
            owned_authoring=True,
        )
        assert authoring.predecessor == predecessor
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.columns WHERE table_schema='data' "
                    "AND table_name='project' AND column_name='native_installation_note'"
                )
            )
            == 0
        )
        verify_frozen_catalog(connection, root_admission)
        assert candidate.upgrade_ops is not None and candidate.upgrade_ops.ops
        rendered = _native_candidate_python(candidate.upgrade_ops)
        admission = authored_admission_sql(authoring)
        verify_rendered_candidate(
            connection, rendered, authoring, candidate.privilege_policies, admission
        )
        verify_frozen_catalog(connection, root_admission)
    revision = register_target_revision(
        location,
        "target_successor_control",
        rendered,
        authoring,
        candidate,
        predecessor=root_revision.revision,
    )
    with engine.begin() as connection:
        verify_target(connection, target, purpose="maintenance")
        assert upgrade(
            connection,
            revision.revision,
            script_location=location,
            expected_predecessor=root_revision.revision,
        ) == [
            {"revision": revision.revision, "direction": "upgrade"},
        ]
        assert connection.execute(
            text("SELECT project_id,generation,native_installation_note FROM data.project")
        ).one() == (
            "successor-control",
            0,
            "unreviewed",
        )
        admit_native(connection, authoring.desired)
        admit_privileges(connection, candidate.privilege_policies)
        verify_frozen_catalog(connection, admission)
        assert current_revision(connection) == revision.revision
        registered = ScriptDirectory.from_config(
            alembic_config(script_location=location)
        ).get_revision(revision.revision)
        assert registered is not None
        current = load_native_state(
            location / "versions" / registered.module.NATIVE_STATE_FILE,
            digest=registered.module.NATIVE_STATE_SHA256,
        )
        unchanged, _ = prepare_target_successor(
            connection, successor, predecessor=current, owned_authoring=True
        )
        assert unchanged.upgrade_ops is not None and unchanged.upgrade_ops.is_empty()
