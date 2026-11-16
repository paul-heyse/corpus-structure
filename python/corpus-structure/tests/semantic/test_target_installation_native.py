"""Actual empty-database target authoring, frozen Alembic installation and purpose ACLs."""

import shutil

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.cli.schema import _native_candidate_python
from corpus_structure.semantic.alembic_privileges import admit_privileges
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.migrations import (
    TARGET_ALEMBIC_DIR,
    alembic_config,
    current_revision,
    upgrade,
)
from corpus_structure.semantic.native_candidate import (
    authored_admission_sql,
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
)
from native_test_support import principal_engine


@pytest.fixture(scope="module")
def fresh_target_epoch():
    return capture_target_installation(
        dict(metadata.info["physical_sources"]),
        linkml_types=metadata.info["physical_linkml_types"],
    )


def application_namespaces(connection):
    return tuple(
        connection.scalars(
            text(
                "SELECT nspname FROM pg_namespace WHERE nspname IN ('meta','sem','data','ops','kb','eval') ORDER BY nspname"
            )
        )
    )


def runtime_temp_privileges(connection):
    from corpus_structure.semantic.alembic_privileges import PURPOSE_ROLES

    return tuple(
        (
            role,
            connection.scalar(
                text("SELECT has_database_privilege(:role,current_database(),'TEMP')"),
                {"role": role},
            ),
        )
        for role in PURPOSE_ROLES
    )


def test_actual_target_default_contract(semantic_bare_engine, fresh_target_epoch):
    from corpus_structure.semantic.native_candidate import _declared_physical_catalog

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


def test_actual_fresh_target_authoring_render_replay_install_and_acl(
    semantic_bare_engine,
    native_settings,
    fresh_target_epoch,
    tmp_path,
):
    engine = semantic_bare_engine
    epoch = fresh_target_epoch
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
        rendered = _native_candidate_python(candidate.upgrade_ops, "")
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
        shutil.copyfile(TARGET_ALEMBIC_DIR / filename, location / filename)
    prefix, body = rendered.split("def upgrade():\n", 1)
    directory = ScriptDirectory.from_config(alembic_config(script_location=location))
    revision = directory.generate_revision(
        "target_fresh_control",
        "actual fresh target",
        head="base",
        imports=prefix,
        upgrades=body.lstrip(),
        downgrades="raise RuntimeError('unsupported')",
    )
    assert revision is not None and revision.down_revision is None
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
            prepare_target_candidate(connection, epoch, owned_authoring=True)

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
    finally:
        reader.dispose()
