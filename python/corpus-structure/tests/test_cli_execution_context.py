"""Exact operator recovery uses captured physical choices before preparation."""

import json
from contextlib import contextmanager
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from corpus_structure.cli import demands
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.storage_target import StorageTarget
from corpus_structure.settings import Settings

REQUEST = {
    "project_id": "project:one",
    "release_id": "release:one",
    "runtime_id": "runtime:one",
    "documents": ["document:one"],
    "targets": ["source.pdf/capture"],
}
TARGET = StorageTarget(
    database="captured",
    database_oid=123,
    system_identifier="cluster:one",
    host="localhost",
    port=5434,
    purpose="write",
)


def snapshot():
    return {
        "demand_id": "demand:one",
        "project_id": "project:one",
        "release_id": "release:one",
        "runtime_id": "runtime:one",
    }


@pytest.fixture
def request_file(tmp_path):
    path = tmp_path / "request.json"
    path.write_text(json.dumps(REQUEST))
    return path


def context_from(results):
    folders = [path for path in results.iterdir() if path.is_dir() and len(path.name) == 32]
    assert len(folders) == 1
    return folders[0], json.loads((folders[0] / "execution-context.json").read_text())


def test_passive_preview_retains_explicit_values_without_registration_or_providers(
    cli, monkeypatch, tmp_path, request_file
):
    def refuse(*args, **kwargs):
        raise AssertionError("passive preview reached native acquisition")

    monkeypatch.setattr(demands, "ENGINE", refuse)
    policy = tmp_path / "policy.json"
    policy.write_text('{"max_owned_bytes":17179869184,"workers":3}')
    results = tmp_path / "results"
    invocation = cli(
        "run",
        "preview",
        "--request",
        str(request_file),
        "--source-root",
        str(tmp_path),
        "--execution-policy",
        str(policy),
        "--json",
        env={"CORPUS_CI_RESULTS": str(results)},
    )
    assert invocation.exit_code == 0, invocation.output
    report = json.loads(invocation.stdout)
    assert report["standing"] == "passive" and report["effects"] == []
    assert report["native_availability"] == "unobserved"
    assert report["context"]["source_request"]["documents"] == ["document:one"]
    assert report["context"]["execution_policy"]["max_owned_bytes"] == 17179869184
    assert report["context"]["policy_origins"]["workers"] == "explicit execution policy"
    assert not results.exists()


def test_preparation_failure_retains_recoverable_request_and_policy(
    cli, monkeypatch, tmp_path, request_file
):
    @contextmanager
    def fail(settings, *, purpose):
        raise OSError("preparation unavailable")
        yield

    monkeypatch.setattr(demands, "ENGINE", fail)
    results = tmp_path / "results"
    invocation = cli(
        "run",
        "--request",
        str(request_file),
        "--source-root",
        str(tmp_path),
        "--json",
        env={"CORPUS_CI_RESULTS": str(results)},
    )
    assert invocation.exit_code != 0
    folder, account = context_from(results)
    assert account["source_request"]["release_id"] == "release:one"
    assert account["execution_policy"]["max_owned_bytes"] == 2 * 1024**3
    manifest = json.loads((folder / "manifest.json").read_text())
    assert manifest["outcome"] == "failed"
    assert manifest["artifacts"]["execution_context"] == "execution-context.json"


def test_managed_resume_keeps_policy_after_file_and_defaults_change(
    cli, monkeypatch, tmp_path, request_file
):
    from corpus_structure.orchestrate import native_execution

    @contextmanager
    def engine(settings, *, purpose):
        yield object()

    monkeypatch.setattr(demands, "ENGINE", engine)
    seen = []

    def execute(*args, **kwargs):
        seen.append(kwargs)
        kwargs["registered"](snapshot(), TARGET, kwargs["request"])
        return SimpleNamespace(
            demand_id="demand:one",
            snapshot=json_bytes(snapshot()),
            snapshot_standing="current",
            receipt_count=0,
            receipts_truncated=False,
            receipts=(),
        )

    monkeypatch.setattr(native_execution, "execute_native_intent", execute)
    results = tmp_path / "results"
    policy = tmp_path / "policy.json"
    policy.write_text('{"max_owned_bytes":17179869184,"workers":3}')
    initial = cli(
        "run",
        "--request",
        str(request_file),
        "--source-root",
        str(tmp_path),
        "--execution-policy",
        str(policy),
        "--json",
        env={"CORPUS_CI_RESULTS": str(results)},
    )
    assert initial.exit_code == 0, initial.output
    predecessor = json.loads(initial.stdout)["id"]
    policy.write_text('{"max_owned_bytes":34359738368,"workers":7}')
    changed = Settings()
    settings = changed.model_copy(update={"ci_results": results})
    resumed = cli("run", "resume", "--result", predecessor, "--json", settings=lambda: settings)
    assert resumed.exit_code == 0, resumed.output
    second = json.loads(resumed.stdout)["id"]
    account = json.loads((results / second / "execution-context.json").read_text())
    assert account["predecessor_result"] == predecessor
    assert account["demand_id"] == "demand:one" and account["source_request"] is None
    assert seen[1]["demand"] == "demand:one" and seen[1]["source_request"] is None
    assert seen[1]["expected_target"] == TARGET
    assert asdict(seen[1]["methods"].execution_policy)["max_owned_bytes"] == 17179869184
    assert asdict(seen[1]["methods"].execution_policy)["workers"] == 3
    override = cli(
        "run",
        "resume",
        "--result",
        second,
        "--execution-policy",
        str(policy),
        "--json",
        settings=lambda: settings,
    )
    assert override.exit_code == 0, override.output
    third = json.loads(override.stdout)["id"]
    account = json.loads((results / third / "execution-context.json").read_text())
    assert account["predecessor_result"] == second and account["overrides"] == [
        "max_owned_bytes",
        "workers",
    ]
    assert account["execution_policy"]["workers"] == 7


def test_resume_requires_one_unambiguous_identity(cli):
    invocation = cli("run", "resume", "demand:one", "--result", "a" * 32, "--json")
    assert invocation.exit_code != 0
    assert "select the native demand argument or --result" in invocation.output


def test_missing_old_context_names_required_inputs(cli, tmp_path):
    from corpus_structure.cli.managed import ResultStore

    store = ResultStore(tmp_path)
    with store.operation("run") as old:
        old.settle("failed")
    invocation = cli(
        "run", "resume", "--result", old.id, "--json", env={"CORPUS_CI_RESULTS": str(tmp_path)}
    )
    assert invocation.exit_code != 0
    assert "explicit source root and execution policy" in invocation.stdout


def test_recovery_wrong_configured_target_refuses_before_acquisition(
    cli, monkeypatch, tmp_path, request_file
):
    @contextmanager
    def fail(settings, *, purpose):
        raise OSError("before registration")
        yield

    monkeypatch.setattr(demands, "ENGINE", fail)
    results = tmp_path / "results"
    original = cli(
        "run",
        "--request",
        str(request_file),
        "--source-root",
        str(tmp_path),
        "--json",
        env={"CORPUS_CI_RESULTS": str(results)},
    )
    assert original.exit_code != 0
    folder, _ = context_from(results)
    defaults = Settings()
    moved = defaults.model_copy(
        update={
            "ci_results": results,
            "database": defaults.database.model_copy(
                update={
                    "url": "postgresql://corpus_sem_writer@/different?host=/var/run/postgresql&port=5434"
                }
            ),
        }
    )

    def unexpected(*args, **kwargs):
        raise AssertionError("wrong target must refuse before opening an engine")

    monkeypatch.setattr(demands, "ENGINE", unexpected)
    resumed = cli("run", "resume", "--result", folder.name, "--json", settings=lambda: moved)
    assert resumed.exit_code != 0
    assert "configured recovery route differs" in resumed.stdout
    assert len([item for item in results.iterdir() if item.is_dir() and len(item.name) == 32]) == 1


def test_recovery_context_preserves_exact_fractional_numbers(tmp_path):
    from decimal import Decimal

    from corpus_structure.cli.execution_context import (
        ExecutionRecoveryAccount,
        read_execution_context,
        retain_execution_context,
    )
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.cli.target import ConfiguredSelection
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import NativeDemandRequest
    from corpus_structure.settings import AnalyticsSettings

    exact = Decimal("0.123456789012345678901234567890123456789")
    request = NativeDemandRequest.model_validate(
        {
            "project_id": "p",
            "release_id": "r",
            "runtime_id": "runtime",
            "execution_profile": "source-native",
            "roots": [
                {
                    "subject": "source",
                    "original_source": "doc",
                    "analyzed_scope": {"fraction": exact},
                }
            ],
            "targets": ["source.pdf/capture"],
            "selections": [
                {
                    "operation": "source.pdf/capture",
                    "parameters": {"fraction": exact, "text": "0.123"},
                }
            ],
        }
    )
    account = ExecutionRecoveryAccount(
        observed_at="2026-11-19T00:00:00Z",
        action="run",
        native_request=request,
        source_root=tmp_path,
        execution_policy=CharacterizationExecutionPolicy(),
        policy_origins={},
        analytics_settings=AnalyticsSettings(),
        configured_target=ConfiguredSelection(
            profile="development",
            target_parameter_source="default",
            settings_section="database",
            resources={},
            origins={},
        ),
    )
    store = ResultStore(tmp_path / "results")
    with store.operation("run") as invocation:
        retain_execution_context(invocation, account)
    recovered = read_execution_context(store, invocation.id)
    assert recovered.native_request is not None
    assert recovered.native_request.roots[0].analyzed_scope["fraction"] == exact
    assert recovered.native_request.selections[0].parameters == {"fraction": exact, "text": "0.123"}
    raw = json_loads(store.read_artifact(invocation.id, "execution_context"))
    assert raw["native_request"]["roots"][0]["analyzed_scope"]["fraction"] == exact
    assert isinstance(raw["native_request"]["selections"][0]["parameters"]["fraction"], Decimal)
