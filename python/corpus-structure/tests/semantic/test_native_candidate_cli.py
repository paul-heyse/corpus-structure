import json

from corpus_structure.settings import Settings


def test_native_candidate_refuses_runtime_target_and_existing_output_before_connection(
    cli, tmp_path, monkeypatch
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
        "ordinary",
        "--out",
        str(out),
        "--json",
        settings=lambda: settings,
    )
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "SemanticRefusal"
    assert not out.exists()
    out.mkdir()
    (out / "retained").write_text("unchanged")
    result = cli(
        "schema",
        "native-candidate",
        "--authoring-database",
        "disposable",
        "--out",
        str(out),
        "--json",
        settings=lambda: settings,
    )
    assert result.exit_code == 1
    assert (out / "retained").read_text() == "unchanged"


def test_native_candidate_restores_deployment_role_instead_of_authoring_login(monkeypatch):
    from types import SimpleNamespace

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
