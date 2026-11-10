"""Native model apply acquires the exact authoring target before reviewed file effects."""

import json
from hashlib import sha256

import yaml
from model_change_support import model_checkout as model_checkout

from corpus_structure.schema.model_change import ChangeRequest, prepare_preview
from corpus_structure.schema.model_deployment import deployment_settings
from corpus_structure.settings import Settings


def test_native_apply_reports_actual_authoring_acquisition(
    model_checkout, semantic_application_settings, semantic_db_engine, monkeypatch, cli
):
    from contextlib import contextmanager

    from corpus_structure.cli import recipes
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.schema import model_deployment
    from corpus_structure.semantic.migrations import current_revision
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import acquired_target

    root, location = model_checkout
    configured = Settings(
        database=semantic_application_settings.database.model_dump(),
        deployment={"url": "postgresql://unopened:deployment-secret@localhost:5434/destination"},
        ci_results=root / "results",
    )
    with open_runtime_engine(configured, "ca04-preview", purpose="maintenance") as engine:
        with engine.connect() as conn:
            identity = acquired_target(conn, purpose="maintenance")
            predecessor = current_revision(conn)
    with semantic_db_engine.connect() as conn:
        expected_database, expected_oid = conn.exec_driver_sql(
            "SELECT datname, oid FROM pg_database WHERE datname = current_database()"
        ).one()
    assert predecessor is not None
    physical_path = location / "semantic" / "physical.yaml"
    before = physical_path.read_bytes()
    proposed = yaml.safe_load(before)
    proposed["classes"]["project"]["attributes"]["native_apply_fixture"] = {"range": "string"}
    _, destination = deployment_settings(configured, "deployment")
    preview = prepare_preview(
        root,
        ChangeRequest(
            physical=yaml.safe_dump(proposed),
            native_predecessor=predecessor,
            native_revision="ca04_apply_fixture",
            deployment_profile="deployment",
        ),
        target=model_deployment.target_fingerprint(destination),
        target_profile="deployment",
        authoring_target=model_deployment.target_fingerprint(configured),
        authoring_identity=identity,
    )
    store = ResultStore(root / "results")
    with store.operation("model.preview") as retained:
        path = retained.directory / "preview.json"
        raw = preview.model_dump_json().encode()
        path.write_bytes(raw)
        retained.publish("preview", path)
        retained.settle(sha256=sha256(raw).hexdigest())

    real_fence = model_deployment.predecessor_fence
    acquisitions = []

    @contextmanager
    def fence(source, target, revision, expected):
        assert source is configured
        assert physical_path.read_bytes() == before
        with real_fence(source, target, revision, expected) as actual:
            acquisitions.append(actual)
            assert actual.database == expected_database and actual.database_oid == expected_oid
            assert actual.purpose == "maintenance"
            yield actual
            assert "native_apply_fixture" in physical_path.read_text()

    calls = []

    def settings():
        calls.append(True)
        return configured

    monkeypatch.setattr(model_deployment, "predecessor_fence", fence)
    monkeypatch.setattr(recipes, "checkout", lambda _: root)
    result = cli("model", "change", "apply", retained.id, "--json", settings=settings)
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert calls == [True] and acquisitions == [identity]
    assert report["target_profile"] == "development"
    assert report["acquired_target"]["database"] == expected_database
    assert report["acquired_target"]["database_oid"] == expected_oid
    assert report["operation_account"]["acquired_target"] == report["acquired_target"]
    assert report["selection"]["profile"] == "development"
    assert report["selection"]["standing"] == "configured_unobserved"
    assert report["selection"]["settings_section"] == "database"
    assert report["selection"]["origins"]["database.url"] == "constructor"
    assert "deployment-secret" not in result.stdout
    # A repeated exact apply reuses file bytes, but still acquires its authoring fence.
    monkeypatch.setattr(model_deployment, "predecessor_fence", real_fence)
    human = cli("model", "change", "apply", retained.id, settings=settings)
    assert human.exit_code == 0, human.output
    assert "Current configuration" in human.stdout and "configured, unobserved" in human.stdout
    assert "maintenance" in human.stdout and expected_database in human.stdout
    assert "deployment-secret" not in human.stdout

