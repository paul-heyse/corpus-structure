import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from corpus_structure.settings import Settings


@pytest.mark.parametrize("database", ["", "postgres", "template0", "template1", "cs_template"])
def test_native_candidate_refuses_system_and_template_databases_before_connection(
    cli, tmp_path, monkeypatch, database
):
    from corpus_structure.semantic import runtime

    def unexpected(*args, **kwargs):
        raise AssertionError("a refused authoring request must not acquire database resources")

    monkeypatch.setattr(runtime, "open_runtime_engine", unexpected)
    settings = Settings(
        database={
            "url": "postgresql://runtime@/ordinary",
            "maintenance_url": "postgresql://owner@/",
        }
    )
    out = tmp_path / "candidate"
    result = cli(
        "schema",
        "native-candidate",
        "--authoring-database",
        database,
        "--out",
        str(out),
        "--json",
        settings=lambda: settings,
    )
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "SemanticRefusal"
    assert not out.exists()


def test_native_candidate_refuses_existing_output_before_connection(cli, tmp_path, monkeypatch):
    from corpus_structure.semantic import runtime

    def unexpected(*args, **kwargs):
        raise AssertionError("a refused authoring request must not acquire database resources")

    monkeypatch.setattr(runtime, "open_runtime_engine", unexpected)
    out = tmp_path / "candidate"
    out.mkdir()
    (out / "retained").write_text("unchanged")
    result = cli(
        "schema",
        "native-candidate",
        "--out",
        str(out),
        "--json",
    )
    assert result.exit_code == 1
    assert (out / "retained").read_text() == "unchanged"


@pytest.mark.parametrize("database", [None, "ordinary", "another_persistent_database"])
@pytest.mark.parametrize("fail", [False, True])
def test_native_candidate_recreation_preserves_desired_admission_and_rolls_back(
    cli, tmp_path, monkeypatch, database, fail
):
    from alembic.operations.ops import UpgradeOps
    from sqlalchemy.engine import make_url

    from corpus_structure.semantic import migrations, native_candidate, runtime, storage_target
    from corpus_structure.semantic.alembic_native import NativeTransitionOp
    from corpus_structure.semantic.native_objects import (
        NativeAuthoring,
        NativeIdentity,
        NativeObject,
    )
    from corpus_structure.semantic.refusals import SemanticRefusal

    settings = Settings(
        database={
            "url": "postgresql://runtime@/ordinary?host=/socket&port=5434",
            "maintenance_url": "postgresql://owner@/",
        }
    )
    events = []
    retired, recreated = (
        NativeObject(
            NativeIdentity("view", "data", name),
            "CLI recreation regression",
            (f"CREATE VIEW data.{name} AS SELECT 1 AS value",),
            "{}",
        )
        for name in ("old_fixture", "new_fixture")
    )

    class Connection:
        dialect = SimpleNamespace(
            identifier_preparer=SimpleNamespace(quote=lambda name: '"' + name + '"')
        )

        def begin(self):
            events.append("begin")
            return SimpleNamespace(rollback=lambda: events.append("rollback"))

        def exec_driver_sql(self, statement):
            assert statement == "SELECT current_user"
            return SimpleNamespace(scalar_one=lambda: "owner")

    @contextmanager
    def connection():
        yield Connection()

    @contextmanager
    def engine(selected, application_name, *, purpose):
        assert application_name == "ci-native-candidate"
        assert purpose == "maintenance"
        resolved = make_url(runtime.connection_settings(selected, purpose).database.url)
        assert resolved.username == "owner"
        assert resolved.database == (database or "ordinary")
        assert resolved.query == {"host": "/socket", "port": "5434"}
        events.append("connect")
        yield SimpleNamespace(connect=connection)
        assert events[-1] == "rollback"
        events.append("closed")

    def prepare(conn, *, owned_authoring, predecessor_state, target_metadata, retire, recreate):
        assert owned_authoring is True
        assert predecessor_state is None
        assert events[-1] == "begin"
        assert "data.project" in target_metadata.tables
        assert {item.name for item in retire} == {"old_fixture"}
        assert {item.name for item in recreate} == {"new_fixture"}
        if fail:
            raise SemanticRefusal("candidate refused")
        return SimpleNamespace(
            privilege_policies=(),
            upgrade_ops=UpgradeOps(
                [
                    NativeTransitionOp(retired, None),
                    NativeTransitionOp(recreated, None),
                    NativeTransitionOp(None, recreated),
                ]
            )
        ), NativeAuthoring(
            desired=(recreated,),
            predecessor=(retired, recreated),
            retire=frozenset({retired.identity}),
            recreate=frozenset({recreated.identity}),
        )

    def admission(authoring):
        # Serialization receives the exact normalized authoring result; a
        # temporary recreation must remain desired, never become retirement.
        assert authoring.desired == (recreated,)
        assert authoring.retire == frozenset({retired.identity})
        assert authoring.recreate == frozenset({recreated.identity})
        return "SELECT 1;"

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(storage_target, "verify_declared_route", lambda *_: None)
    monkeypatch.setattr(
        storage_target,
        "acquired_target",
        lambda _, *, purpose: storage_target.StorageTarget(
            database=database or "ordinary",
            database_oid=10,
            system_identifier="1",
            host="/socket",
            port=5434,
            purpose=purpose,
        ),
    )
    monkeypatch.setattr(migrations, "migration_fence", lambda _: None)
    monkeypatch.setattr(migrations, "current_revision", lambda conn: "106")
    monkeypatch.setattr(native_candidate, "prepare_series_candidate", prepare)
    monkeypatch.setattr(native_candidate, "authored_admission_sql", admission)
    out = tmp_path / "candidate"
    intent = tmp_path / "intent.yaml"
    intent.write_text(
        "retire: [{kind: view, schema: data, name: old_fixture}]\n"
        "recreate: [{kind: view, schema: data, name: new_fixture}]\n"
    )
    arguments = [] if database is None else ["--authoring-database", database]
    result = cli(
        "schema",
        "native-candidate",
        *arguments,
        "--intent",
        str(intent),
        "--out",
        str(out),
        "--json",
        settings=lambda: settings,
    )
    assert "resolve native authoring intent" in result.stderr
    assert "rollback-only authoring" in result.stderr
    if fail:
        assert result.exit_code == 1
        assert json.loads(result.stdout)["error"]["code"] == "SemanticRefusal"
        assert not out.exists()
        assert events == ["connect", "begin", "rollback"]
        assert "publish native candidate" not in result.stderr
    else:
        assert result.exit_code == 0, result.output
        report = json.loads(result.stdout)
        assert "publish native candidate" in result.stderr
        assert report["database"] == (database or "ordinary")
        assert report["predecessor"] == "106"
        assert report["native_operations"] == 3
        assert {item.name for item in out.iterdir()} == {
            "native_candidate.py",
            "native_operations.json",
            "native_admission.sql",
        }
        assert events == ["connect", "begin", "rollback", "closed"]
        operations = json.loads((out / "native_operations.json").read_bytes())
        assert [NativeObject.from_payload(item) for item in operations["desired"]] == [recreated]
        restored = [NativeTransitionOp.from_payload(item["payload"]) for item in operations["operations"]]
        assert [(item.before, item.after) for item in restored] == [
            (retired, None),
            (recreated, None),
            (None, recreated),
        ]


def test_explicit_overload_owner_keeps_each_abi_and_its_grants(monkeypatch):
    from corpus_structure.semantic import native_candidate

    calls = []

    def capture(connection, declaration, **facts):
        calls.append((declaration, facts))
        return SimpleNamespace(sql=declaration)

    monkeypatch.setattr(native_candidate, "definition_from_sql", capture)
    sql = """
    CREATE FUNCTION eval.fit(bigint) RETURNS jsonb LANGUAGE sql AS $$ SELECT '{}'::jsonb $$;
    CREATE FUNCTION eval.unrelated(text) RETURNS jsonb LANGUAGE sql AS $$ SELECT '{}'::jsonb $$;
    CREATE FUNCTION eval.fit(bigint,bigint) RETURNS jsonb LANGUAGE sql AS $$ SELECT '{}'::jsonb $$;
    """
    grants = (("corpus_sem_fitter", "EXECUTE", False),)
    actual = native_candidate._task_call_definitions(
        object(), sql, schema="eval", name="fit", source="declared fitting ABI", grants=grants
    )
    assert len(actual) == 2
    assert "eval.fit(bigint)" in actual[0].sql
    assert "eval.fit(bigint,bigint)" in actual[1].sql
    assert all(facts["owner"] == "corpus_sem_publisher" for _, facts in calls)
    assert all(facts["grants"] == grants for _, facts in calls)
    assert all("unrelated" not in definition.sql for definition in actual)
    calls.clear()
    assert (
        native_candidate._task_call_definition(
            object(), sql, schema="eval", name="fit", source="legacy singular ABI", grants=grants
        )
        == actual[0]
    )
    assert len(calls) == 1


def test_current_pdf_payload_owns_new_helpers_without_expanding_historical_selection(monkeypatch):
    from corpus_structure.semantic import native_candidate

    calls = []

    def capture(connection, declaration, **facts):
        calls.append((declaration, facts))
        return SimpleNamespace(sql=declaration, identity=declaration)

    monkeypatch.setattr(native_candidate, "definition_from_sql", capture)
    sql = """
    CREATE FUNCTION ops.require_pdf_stage_owner(bigint) RETURNS text
      LANGUAGE sql AS $$ SELECT 'owned'::text $$;
    CREATE FUNCTION ops.new_pdf_helper(text) RETURNS text LANGUAGE sql AS $$ SELECT $1 $$;
    CREATE FUNCTION ops.pdf_native_record_shape(text) RETURNS boolean
      LANGUAGE sql AS $$ SELECT true $$;
    CREATE FUNCTION ops.pdf_record_context_rows(text) RETURNS text LANGUAGE sql AS $$ SELECT $1 $$;
    CREATE FUNCTION ops.select_source_view(bigint,bigint,bigint) RETURNS void
      LANGUAGE sql AS $$ SELECT NULL::void $$;
    CREATE FUNCTION ops.select_reused_source_views(bigint,bigint) RETURNS void
      LANGUAGE sql AS $$ SELECT NULL::void $$;
    CREATE FUNCTION ops.add_source_task_dependency(bigint,bigint) RETURNS void
      LANGUAGE sql AS $$ SELECT NULL::void $$;
    CREATE FUNCTION ops.validate_measurement_definition() RETURNS trigger
      LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$;
    CREATE FUNCTION eval.unrelated(text) RETURNS text LANGUAGE sql AS $$ SELECT $1 $$;
    REVOKE ALL ON FUNCTION ops.new_pdf_helper(text) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION ops.new_pdf_helper(text) TO corpus_sem_writer;
    """
    current = native_candidate._pdf_payload_definitions(
        object(), sql, source="current PDF owner", current_source=True
    )
    assert len(current) == 2
    assert "require_pdf_stage_owner" in current[0].sql
    assert "new_pdf_helper" in current[1].sql
    assert calls[1][1]["grants"] == (("corpus_sem_writer", "EXECUTE", False),)
    calls.clear()
    old = native_candidate._pdf_payload_definitions(object(), sql, source="frozen0065")
    assert len(old) == 1
    assert "require_pdf_stage_owner" in old[0].sql
