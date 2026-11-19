"""The preview binds canonical inputs and resumes exact interrupted writes."""

import json
import subprocess
from contextlib import nullcontext
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
import yaml
from model_change_support import model_checkout as model_checkout
from typer.testing import CliRunner

from corpus_structure.schema import preparation
from corpus_structure.schema.declarations import ModelError
from corpus_structure.schema.model_change import (
    ChangePreview,
    ChangeRequest,
    LogicalSourceEdit,
    apply_preview,
    prepare_preview,
)
from corpus_structure.schema.model_deployment import (
    Candidate,
    deploy_candidate,
    deployment_settings,
)
from corpus_structure.schema.model_discovery import locate_consumers
from corpus_structure.settings import Settings


def test_unknown_legacy_change_fields_refuse(model_checkout):
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Extra inputs"):
        ChangeRequest.model_validate({"core": "legacy"})


def test_logical_model_change_compares_captures_without_revision(model_checkout):
    root, location = model_checkout
    path = location / "semantic" / "core.yaml"
    original = yaml.safe_load(path.read_bytes())
    original["enums"]["StatementKind"]["permissible_values"]["new_statement"] = {}
    relative = path.relative_to(root).as_posix()
    preview = prepare_preview(
        root,
        ChangeRequest(
            logical_sources=(
                LogicalSourceEdit(path=relative, content=yaml.safe_dump(original, sort_keys=False)),
            )
        ),
    )
    assert preview.effects.native is False
    assert preview.model_comparison is not None
    assert [
        (item.source, item.element, item.kind) for item in preview.model_comparison.changes
    ] == [("core.yaml", "enums/StatementKind/permissible_values/new_statement", "added")]
    assert all("revisions.yaml" not in item for item in preview.inputs)


def test_preview_retains_generated_decimal_guard_change(model_checkout):
    root, location = model_checkout
    path = location / "semantic" / "value-codec.yaml"
    candidate = path.read_text().replace("16384", "16385")
    preview = prepare_preview(
        root,
        ChangeRequest(
            logical_sources=(
                LogicalSourceEdit(path=path.relative_to(root).as_posix(), content=candidate),
            )
        ),
    )
    assert preview.sql_explanation is not None
    decimal = next(
        change
        for change in preview.sql_explanation.changes
        if json.loads(change.identity)["name"] == "decimal_canonical"
    )
    assert decimal.before is not None and decimal.after is not None
    assert "16384" in decimal.before.text and "16385" in decimal.after.text


def test_release_candidate_must_match_the_reviewed_release(model_checkout):
    from corpus_structure.semantic.types import PreparedArtifact, PreparedRelease

    root, _ = model_checkout
    artifacts = (
        PreparedArtifact("required.json", b'{"meaning":"reviewed"}'),
        PreparedArtifact("another.json", b"{}"),
    )
    prepared = PreparedRelease("reviewed", b"manifest", (), (), (), (), artifacts, (), (), ())
    preview = prepare_preview(
        root,
        ChangeRequest(deployment=True, packs=("fixture",)),
        target="target",
        local_release="reviewed",
        release_manifest_sha256=sha256(prepared.manifest).hexdigest(),
        release_artifacts_sha256=prepared.artifacts_sha256,
    )
    with pytest.raises(ModelError, match="differs from the reviewed preview"):
        Candidate.from_preview(preview, None, replace(prepared, release_id="different"), {})
    with pytest.raises(ModelError, match="artifacts differ from the reviewed preview"):
        Candidate.from_preview(
            preview,
            None,
            replace(prepared, artifacts=(replace(artifacts[0], content=b"changed"), artifacts[1])),
            {},
        )
    accepted = Candidate.from_preview(
        preview, None, replace(prepared, artifacts=tuple(reversed(artifacts))), {}
    )
    assert accepted.release == "reviewed"
    assert accepted.release_artifacts_sha256 == prepared.artifacts_sha256
    from corpus_structure.schema.model_change import compilation_fingerprint
    from corpus_structure.schema.model_deployment import check_candidate_files

    with pytest.raises(ModelError, match="lacks complete preparation custody"):
        check_candidate_files(root, accepted)
    request = ChangeRequest()
    reusable = accepted.model_copy(
        update={
            "preparation_request": request,
            "preparation_fingerprint": compilation_fingerprint(root, request),
            "files": {},
        }
    )
    check_candidate_files(root, reusable)
    helper = root / preparation.PACKAGE_PATH / "semantic/changed_preparation.py"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text("CHANGED = True\n")
    with pytest.raises(ModelError, match="compilation inputs changed"):
        check_candidate_files(root, reusable)
    older = ChangePreview.model_validate_json(
        preview.model_dump_json(exclude={"release_artifacts_sha256"})
    )
    with pytest.raises(ModelError, match="lacks exact release product digests"):
        Candidate.from_preview(older, None, prepared, {})


def test_explicit_postgresql_route_refuses_ambient_routing(monkeypatch):
    from corpus_structure.semantic.storage_target import StorageTargetError, assert_explicit_route

    settings = Settings(database={"url": "postgresql://host.example:5434/approved"})
    monkeypatch.delenv("PGSERVICE", raising=False)
    monkeypatch.setenv("PGHOSTADDR", "192.0.2.3")
    with pytest.raises(StorageTargetError, match="ambient libpq routing"):
        assert_explicit_route(settings)
    pinned = Settings(
        database={"url": "postgresql://host.example:5434/approved?hostaddr=192.0.2.4"}
    )
    assert assert_explicit_route(pinned)["hostaddr"] == "192.0.2.4"
    monkeypatch.setenv("PGSERVICE", "other-deployment")
    with pytest.raises(StorageTargetError, match="ambient libpq routing"):
        assert_explicit_route(pinned)


def test_structural_discovery_qualifies_coordinates_without_claiming_binding(model_checkout):
    root, _ = model_checkout
    source = root / "python/corpus-structure/src"
    generated = source / "_model"
    generated.mkdir(parents=True, exist_ok=True)
    (source / "scope.py").write_bytes(
        "import other as witness\r\ndef test():\r\n    witness = 1\r\n"
        "    return 'é', witness\r\n".encode()
    )
    (source / "invalid.py").write_bytes(b"return witness\n")
    (generated / "excluded.py").write_bytes(b"witness = 1\n")
    subprocess.run(["git", "-C", str(root), "add", str(source)], check=True)
    report = locate_consumers(
        root,
        "head",
        {"witness"},
        comparison={
            "changes": [
                {"model_ref": "projection:witness", "consumers": ["reader"]},
            ],
            "unknowns": ["detached binding unassessed"],
        },
    )
    assert report["compile"]["python/corpus-structure/src/invalid.py"] == {
        "outcome": "failed",
        "line": 1,
    }
    witness = next(hit for hit in report["candidates"] if hit["line"] == 4)
    assert witness["utf8_column"] == len("    return 'é', ".encode())
    assert witness["source"] == "witness"
    assert witness["lexical_status"] == "qualified"
    assert witness["qualified_names"] == [{"name": "test.<locals>.witness", "origin": "LOCAL"}]
    assert report["excluded_generated"] == ["python/corpus-structure/src/_model/excluded.py"]
    assert report["semantic_coverage"]["consumers"] == {"projection:witness": ["reader"]}
    assert report["semantic_coverage"]["unknowns"] == ["detached binding unassessed"]
    assert report["backend"] == "ast-grep-py"
    assert report["coverage"] == "complete-syntax-examination"


def test_deployment_preview_binds_separate_authoring_and_destination(model_checkout, monkeypatch):
    from corpus_structure.cli import recipes, schema
    from corpus_structure.cli.app import build_full_app

    app = build_full_app()
    from corpus_structure.cli.output import CliState
    from corpus_structure.schema import model_change, model_deployment
    from corpus_structure.semantic import migrations
    from corpus_structure.semantic.storage_target import StorageTarget

    root, location = model_checkout
    (root / "domains").symlink_to(
        Path(preparation.__file__).resolve().parents[5] / "domains", target_is_directory=True
    )
    migrations_dir = root / preparation.PACKAGE_PATH.parents[1] / migrations.ALEMBIC_DIR.name
    versions = migrations_dir / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    (versions / "before.py").write_text('revision = "before"\ndown_revision = None\n')
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", migrations_dir)
    # The routing fixture has no installed native catalog. Generated-statement
    # comparison is exercised against captured models by the preview controls.
    monkeypatch.setattr(model_change, "preview_native_delta", lambda *_args, **_kwargs: None)
    settings = Settings(
        database={"url": "postgresql://dev:private@localhost/development"},
        deployment={"url": "postgresql://prod:secret@localhost/approved-destination"},
    )
    changed_development = settings.model_copy(
        update={
            "database": settings.database.model_copy(update={"url": "postgresql:///other-source"}),
        }
    )
    assert settings.deployment is not None
    changed_destination = settings.model_copy(
        update={
            "deployment": settings.deployment.model_copy(
                update={"url": "postgresql:///other-target"}
            ),
        }
    )
    development = model_deployment.target_fingerprint(settings)
    profile, destination = deployment_settings(settings)
    destination_id = model_deployment.target_fingerprint(destination)
    assert profile == "deployment"
    assert deployment_settings(settings, "development") == ("development", settings)
    assert deployment_settings(Settings(deployment=None))[0] == "development"
    with pytest.raises(ModelError, match="profile is not configured"):
        deployment_settings(Settings(deployment=None), "deployment")

    monkeypatch.setenv("CORPUS_CI_RESULTS", str(root / "results"))
    monkeypatch.setattr(recipes, "checkout", lambda _: root)
    checked = []
    source_identity = StorageTarget(
        database="development",
        database_oid=10,
        system_identifier="1",
        host="socket",
        port=5434,
        purpose="maintenance",
    )
    destination_identity = source_identity.model_copy(
        update={"database": "approved-destination", "database_oid": 20}
    )

    def capture_authoring_base(source, target, predecessor):
        checked.append((source.database.url, target, predecessor))
        return (
            source_identity
            if source.database.url == settings.database.url
            else destination_identity,
            None,
        )

    monkeypatch.setattr(model_deployment, "capture_authoring_base", capture_authoring_base)
    monkeypatch.setattr(model_deployment, "capture_target", lambda *_, **__: destination_identity)
    monkeypatch.setattr(
        model_deployment, "predecessor_fence", lambda *_: nullcontext(source_identity)
    )

    def author(
        source,
        _database,
        *,
        expected_predecessor,
        expected_target,
        native_base,
        target_metadata,
        logical_sources,
        reviewed_delta,
        retire,
        recreate,
        data_steps,
    ):
        assert source.database.url == settings.database.url
        assert expected_predecessor == "before"
        assert expected_target == source_identity
        assert native_base is None and reviewed_delta is None
        assert target_metadata.tables["data.project"].c.reviewed_fixture.nullable
        assert b"SourceValue:" in logical_sources["observations.yaml"]
        assert {item.name for item in retire} == {"retired_fixture"}
        assert {item.name for item in recreate} == {"recreated_fixture"}
        assert [step.name for step in data_steps] == ["ddo_n1_relower"]
        return schema.NativeCandidateResult(
            database="development",
            predecessor="before",
            output="",
            native_operations=0,
            ordinary_operations=0,
            products=[],
        ), {
            "native_candidate.py": b"def upgrade():\n    pass\n",
            "native_operations.json": b'{"version":1,"predecessor":"before","desired":[]}',
            "native_admission.sql": b"-- fixture\n",
        }

    monkeypatch.setattr(schema, "author_native_candidate", author)
    runner = CliRunner()

    def run(args, source, **kwargs):
        source = source.model_copy(update={"ci_results": root / "results"})
        return runner.invoke(
            app,
            ["model", "change", *args, "--json"],
            obj=CliState(settings_factory=lambda: source),
            **kwargs,
        )

    physical_path = location / "semantic" / "physical.yaml"
    before = physical_path.read_bytes()
    proposed = yaml.safe_load(before)
    proposed["classes"]["project"]["attributes"]["reviewed_fixture"] = {"range": "string"}
    staged = run(
        ["preview", "-"],
        settings,
        input=yaml.safe_dump(
            {
                "deployment": True,
                "native_predecessor": "before",
                "native_revision": "after",
                "data_steps": [{"name": "ddo_n1_relower", "parameters": {}}],
                "physical": yaml.safe_dump(proposed),
                "retire": [{"kind": "function", "schema": "data", "name": "retired_fixture"}],
                "recreate": [{"kind": "function", "schema": "data", "name": "recreated_fixture"}],
            }
        ),
    )
    assert staged.exit_code == 0, staged.output
    preview = json.loads(staged.stdout)
    assert preview["target_profile"] == "deployment"
    assert preview["selection"]["profile"] == "deployment"
    assert preview["selection"]["standing"] == "configured_unobserved"
    assert preview["acquired_target"] == destination_identity.model_dump(mode="json")
    assert checked == [
        (settings.database.url, development, "before"),
        (settings.deployment.url, destination_id, "before"),
    ]
    assert physical_path.read_bytes() == before
    assert run(["candidate", preview["result_id"]], settings).exit_code == 1
    applied = run(["apply", preview["result_id"]], settings)
    assert applied.exit_code == 0, applied.output
    applied_report = json.loads(applied.stdout)
    assert applied_report["target_profile"] == "development"
    assert applied_report["acquired_target"] == source_identity.model_dump(mode="json")
    assert (
        applied_report["operation_account"]["acquired_target"] == applied_report["acquired_target"]
    )
    assert applied_report["selection"]["profile"] == "development"
    assert applied_report["selection"]["settings_section"] == "database"
    assert applied_report["selection"]["standing"] == "configured_unobserved"
    assert applied_report["selection"]["observed_binding"] is None
    assert applied_report["selection"]["target_parameter_source"] == "unknown"
    assert applied_report["selection"]["origins"]["database.url"] == "constructor"
    assert "development" in applied_report["selection"]["resources"]["database.url"]
    assert "private" not in applied.stdout and "secret" not in applied.stdout
    assert "reviewed_fixture" in physical_path.read_text()

    # A real normalization failure must retain declaration custody through the
    # managed candidate boundary, without disclosing SQL or the server's prose.
    from types import SimpleNamespace
    from typing import cast

    from psycopg.errors import UndefinedFunction
    from sqlalchemy import Connection
    from sqlalchemy.exc import ProgrammingError

    from corpus_structure.semantic import native_objects

    definition = native_objects.NativeDefinition(
        native_objects.NativeIdentity("function", "ops", "authoring_probe"),
        "CREATE OR REPLACE FUNCTION ops.authoring_probe() RETURNS integer "
        "LANGUAGE sql AS $$ SELECT ops.missing('PRIVATE_SQL') $$",
        "fixture/native-functions.sql",
        owner="publisher",
    )
    original = ProgrammingError(
        definition.sql, {"value": "PRIVATE_PARAMETER"}, UndefinedFunction("PRIVATE_NATIVE_MESSAGE")
    )
    events, failures = [], []

    def dependency_rows(statement):
        # This single isolated definition has no installed dependencies. Preserve
        # the real ordering path before exercising the failing CREATE statement.
        query = str(statement)
        if "CURRENT_USER" in query:
            return SimpleNamespace(scalar_one=lambda: "owner")
        assert "native_scope" in query and "pg_depend" in query
        return ()

    connection = SimpleNamespace(
        execute=dependency_rows,
        scalar=lambda statement: "none" if "current_setting" in str(statement) else "owner",
        begin_nested=lambda: SimpleNamespace(rollback=lambda: events.append("rollback")),
    )

    def execute(_connection, statement):
        if statement.startswith("CREATE"):
            events.append("create")
            raise original
        assert statement == native_objects.native_role_sql("publisher")
        events.append("set owner")

    def refuse_author(*_args, **_kwargs):
        try:
            native_objects.prepare_native_authoring(
                cast(Connection, connection), (definition,), owned_authoring=True
            )
        except native_objects.NativeAuthoringError as error:
            failures.append(error)
            raise

    with monkeypatch.context() as broken_native:
        broken_native.setattr(native_objects, "observe_native", lambda *_args, **_kwargs: None)
        broken_native.setattr(native_objects, "execute_native_sql", execute)
        broken_native.setattr(schema, "author_native_candidate", refuse_author)
        failed = run(["candidate", preview["result_id"]], settings, catch_exceptions=False)
    assert failed.exit_code == 1, failed.output
    diagnostic = json.loads(failed.stdout)
    assert diagnostic["error"]["code"] == "NativeAuthoringError"
    message = diagnostic["error"]["message"]
    assert all(
        fragment in message
        for fragment in (
            "install statement 1",
            "function ops.authoring_probe()",
            "SQLSTATE 42883",
            "fixture/native-functions.sql",
        )
    )
    assert diagnostic["operation_account"]["failure"]["message"] == message
    assert events == ["rollback", "set owner", "create", "rollback"]
    assert len(failures) == 1 and failures[0].__cause__ is original
    inspected = runner.invoke(
        app,
        ["results", "inspect", diagnostic["invocation_id"], "--view", "observations", "--json"],
        obj=CliState(
            settings_factory=lambda: settings.model_copy(update={"ci_results": root / "results"})
        ),
    )
    assert inspected.exit_code == 0, inspected.output
    observations = json.loads(inspected.stdout)["observations"]["rows"]
    assert any(row["message"] == message for row in observations)
    for private in ("PRIVATE_SQL", "PRIVATE_PARAMETER", "PRIVATE_NATIVE_MESSAGE"):
        assert private not in failed.output + inspected.output

    refused = run(["candidate", preview["result_id"]], changed_development)
    assert refused.exit_code != 0
    assert "development authoring target differs" in refused.output
    authored = run(["candidate", preview["result_id"]], changed_destination)
    assert authored.exit_code == 0, authored.output
    authored_id = json.loads(authored.stdout)["result_id"]
    binding = Candidate.model_validate_json(
        (root / "results" / authored_id / "deployment.json").read_bytes()
    )
    assert binding.release == preview["release"]
    assert binding.release_manifest_sha256 is None
    assert binding.release_artifacts_sha256 is None
    assert binding.target_profile == "deployment"
    assert binding.target == destination_id
    assert binding.authoring_target == development
    assert binding.target_identity == destination_identity
    with pytest.raises(ModelError, match="deployment target differs"):
        deploy_candidate(root, changed_destination, binding, (), report=lambda _: None)
    registered = run(["register", authored_id], settings)
    assert registered.exit_code == 0, registered.output
    assert migrations.head_revision() == "after"
    assert (versions / "after.py").read_bytes() == (
        root / "results" / authored_id / "migration.py"
    ).read_bytes()
    assert run(["register", authored_id], settings).exit_code == 0
    extra = versions / "after_changed.py"
    marker = root / "executed"
    extra.write_text(
        f'revision = "after"\nfrom pathlib import Path\nPath({str(marker)!r}).touch()\n'
    )
    with pytest.raises(ModelError, match="different migration wrapper"):
        model_deployment._verify_installed_revision(root, binding)
    assert not marker.exists()
    extra.unlink()
    (versions / "after_admission.sql").write_bytes(b"changed")
    refused = run(["register", authored_id], settings)
    assert refused.exit_code == 1
    assert "migration file already has different content" in refused.output


def test_non_native_apply_does_not_acquire_a_target(model_checkout, monkeypatch, cli):
    from corpus_structure.cli import recipes
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.schema import model_deployment

    root, _ = model_checkout
    preview = prepare_preview(root, ChangeRequest())
    store = ResultStore(root / "results")
    with store.operation("model.preview") as retained:
        path = retained.directory / "preview.json"
        raw = preview.model_dump_json().encode()
        path.write_bytes(raw)
        retained.publish("preview", path)
        retained.settle(sha256=sha256(raw).hexdigest())

    def forbidden(*args, **kwargs):
        pytest.fail("non-native apply acquired a target")

    monkeypatch.setattr(model_deployment, "predecessor_fence", forbidden)
    monkeypatch.setattr(recipes, "checkout", lambda _: root)
    result = cli(
        "model",
        "change",
        "apply",
        retained.id,
        "--json",
        settings=lambda: Settings(ci_results=store.root),
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["target_profile"] is report["acquired_target"] is report["selection"] is None


def test_exact_patch_resumes_and_refuses_changed_file(model_checkout):
    root, location = model_checkout
    paths = tuple(
        location / "semantic" / name for name in ("core.yaml", "operation-vocabularies.yaml")
    )
    declarations = tuple(
        LogicalSourceEdit(
            path=path.relative_to(root).as_posix(),
            content=path.read_text() + "\n# reviewed source change\n",
        )
        for path in paths
    )
    preview = prepare_preview(root, ChangeRequest(logical_sources=declarations))
    assert len(preview.files) == 2

    def interrupt(_: str) -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        apply_preview(root, preview, report=interrupt)
    assert paths[0].read_text() == declarations[0].content
    assert paths[1].read_text() != declarations[1].content
    paths[1].write_text("concurrent edit\n")
    with pytest.raises(ModelError, match="stale model input"):
        apply_preview(root, preview)
    assert paths[1].read_text() == "concurrent edit\n"
    subprocess.run(["git", "-C", str(root), "restore", "--", declarations[1].path], check=True)
    assert len(apply_preview(root, preview)) == 2
    assert paths[1].read_text() == declarations[1].content


def test_compilation_fingerprint_tracks_implementation_membership_and_owned_outputs(model_checkout):
    from corpus_structure.schema.model_change import compilation_fingerprint

    root, _ = model_checkout
    request = ChangeRequest()
    baseline = compilation_fingerprint(root, request)
    package = root / preparation.PACKAGE_PATH
    helper = package / "semantic" / "new_compiler_helper.py"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text("LIMIT = 3\n")
    changed = compilation_fingerprint(root, request)
    assert changed != baseline
    helper.unlink()
    assert compilation_fingerprint(root, request) == baseline
    # This exact output belongs to the canonical generator. Its authored model
    # remains in the fingerprint, while apply's generated bytes are checked by
    # the preview/candidate file effects.
    output = package / "semantic" / "_typed_columns.py"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("generated = 'first'\n")
    assert compilation_fingerprint(root, request) == baseline
    output.write_text("generated = 'second'\n")
    assert compilation_fingerprint(root, request) == baseline


def test_compilation_fingerprint_keeps_captured_generated_source_bytes(model_checkout, monkeypatch):
    from types import SimpleNamespace

    from corpus_structure.schema.model_change import compilation_fingerprint
    from corpus_structure.semantic import data_operation_preparation
    from corpus_structure.semantic.types import (
        PreparationProfile,
        ResolvedDependencies,
        SourceArtifact,
        SourceBundle,
    )

    root, _ = model_checkout
    relative = (preparation.PACKAGE_PATH / "core/vocab.py").as_posix()
    output = root / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("generated = 'first'\n")

    selected = [relative]

    def acquire(*args, **kwargs):
        proposed = kwargs.get("proposed") or {}
        content = proposed.get(relative, output.read_bytes())
        return SimpleNamespace(
            bundle=SourceBundle("captured", (SourceArtifact("captured", content),)),
            dependencies=ResolvedDependencies(),
            profile=PreparationProfile(),
            files=tuple(
                (name, proposed.get(name, (root / name).read_bytes())) for name in selected
            ),
        )

    monkeypatch.setattr(data_operation_preparation, "acquire_data_operation_inputs", acquire)
    request = ChangeRequest(data_operations="inputs.yaml")
    before = compilation_fingerprint(root, request)
    after = b"generated = 'second'\n"
    reviewed = compilation_fingerprint(root, request, proposed={relative: after})
    output.write_bytes(after)
    assert compilation_fingerprint(root, request) == reviewed != before
    extra = "added-source.py"
    (root / extra).write_bytes(after)
    selected.append(extra)
    assert compilation_fingerprint(root, request) != reviewed
    selected.pop()
    assert compilation_fingerprint(root, request) == reviewed
