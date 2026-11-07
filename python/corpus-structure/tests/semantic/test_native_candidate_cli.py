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
def test_native_candidate_uses_maintenance_and_rolls_back(
    cli, tmp_path, monkeypatch, database, fail
):
    from alembic.operations.ops import UpgradeOps
    from sqlalchemy.engine import make_url

    from corpus_structure.semantic import migrations, native_candidate, runtime, storage_target
    from corpus_structure.semantic.refusals import SemanticRefusal

    settings = Settings(
        database={
            "url": "postgresql://runtime@/ordinary?host=/socket&port=5434",
            "maintenance_url": "postgresql://owner@/",
        }
    )
    events = []

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
        return SimpleNamespace(upgrade_ops=UpgradeOps([])), SimpleNamespace(desired=())

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
    monkeypatch.setattr(native_candidate, "series_native_definitions", lambda conn: ())
    monkeypatch.setattr(native_candidate, "candidate_admission_sql", lambda *a, **kw: "SELECT 1;")
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
    if fail:
        assert result.exit_code == 1
        assert json.loads(result.stdout)["error"]["code"] == "SemanticRefusal"
        assert not out.exists()
        assert events == ["connect", "begin", "rollback"]
    else:
        assert result.exit_code == 0, result.output
        report = json.loads(result.stdout)
        assert report["database"] == (database or "ordinary")
        assert report["predecessor"] == "106"
        assert {item.name for item in out.iterdir()} == {
            "native_candidate.py",
            "native_operations.json",
            "native_admission.sql",
        }
        assert events == ["connect", "begin", "rollback", "closed"]


def test_native_candidate_restores_deployment_role_instead_of_authoring_login(monkeypatch):
    from alembic import op
    from alembic.operations.ops import ExecuteSQLOp, UpgradeOps

    from corpus_structure.cli.schema import _native_candidate_python

    statements = []
    connection = SimpleNamespace(
        exec_driver_sql=lambda sql: SimpleNamespace(scalar_one=lambda: "deployment_owner"),
        dialect=SimpleNamespace(
            identifier_preparer=SimpleNamespace(quote=lambda name: '"' + name + '"')
        ),
    )
    monkeypatch.setattr(op, "get_bind", lambda: connection)
    monkeypatch.setattr(op, "execute", statements.append)
    source = _native_candidate_python(
        UpgradeOps(
            [
                ExecuteSQLOp("SET LOCAL ROLE corpus_sem_publisher"),
                ExecuteSQLOp("SET LOCAL ROLE authoring_owner"),
            ]
        ),
        "SET LOCAL ROLE authoring_owner",
    )
    namespace = {}
    exec(compile(source, "candidate.py", "exec"), namespace)
    namespace["upgrade"]()
    assert statements == [
        "SET LOCAL ROLE corpus_sem_publisher",
        'SET LOCAL ROLE "deployment_owner"',
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
