"""Routing tests only: native demand semantics are exercised by native kernel tests."""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest

from corpus_structure.cli import demands
from corpus_structure.semantic.storage_target import StorageTarget


@pytest.fixture
def routing(monkeypatch):
    opened = []
    connection = object()

    class Engine:
        @contextmanager
        def begin(self):
            yield connection

    @contextmanager
    def engine(settings, *, purpose):
        opened.append(purpose)
        yield Engine()

    monkeypatch.setattr(demands, "ENGINE", engine)
    from corpus_structure.orchestrate import native_execution

    monkeypatch.setattr(
        native_execution,
        "read_data_demand",
        lambda conn, demand, **options: {
            "demand_id": demand,
            "project_id": "project:one",
            "release_id": "release:one",
            "runtime_id": "runtime:one",
        },
    )
    monkeypatch.setattr(
        native_execution,
        "acquired_target",
        lambda conn, *, purpose: StorageTarget(
            database="routing-only",
            database_oid=1,
            system_identifier="routing-only",
            host="localhost",
            port=5434,
            purpose=purpose,
        ),
    )
    monkeypatch.setattr(demands, "read_data_demand", native_execution.read_data_demand)
    monkeypatch.setattr(demands, "acquired_target", native_execution.acquired_target)
    return opened, connection


def test_demand_help_has_no_settings_or_database_effects(cli):
    def refuse():
        raise AssertionError("help must not resolve settings")

    for action in (
        (),
        ("create",),
        ("plan",),
        ("read",),
        ("cancel",),
        ("execute",),
        ("retire-draft",),
    ):
        result = cli("demands", *action, "--help", settings=refuse)
        assert result.exit_code == 0, result.output


def test_create_routes_closed_request_to_service_and_records_managed_result(
    cli,
    tmp_path,
    monkeypatch,
    routing,
):
    opened, connection = routing
    request = {
        "project_id": "project:one",
        "release_id": "release:one",
        "runtime_id": "runtime:one",
        "intent": {"model": "frozen:one"},
    }
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request))
    seen = []

    def create(conn, value):
        assert conn is connection
        seen.append(value)
        return {
            "demand_id": "demand:one",
            "release_id": value.release_id,
            "runtime_id": value.runtime_id,
            "continuation": None,
        }

    monkeypatch.setattr(demands, "create_data_demand", create)
    results = tmp_path / "results"
    result = cli(
        "demands",
        "create",
        "--request",
        str(source),
        "--json",
        env={"CORPUS_CI_RESULTS": str(results)},
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert opened == ["write"]
    assert seen[0].intent == request["intent"]
    assert report["native"]["runtime_id"] == "runtime:one"
    manifest = json.loads((results / report["id"] / "manifest.json").read_text())
    assert manifest["outcome"] == "passed"
    assert manifest["operation_account"]["known_effects"] == ["native demand create:demand:one"]
    assert set(manifest["artifacts"]) >= {"request", "native"}


def test_read_routes_complete_native_continuation_without_semantic_defaults(
    cli,
    tmp_path,
    monkeypatch,
    routing,
):
    opened, connection = routing
    pins = {
        "demand_id": "demand:one",
        "read_id": "read:one",
        "after": "obligation:one",
        "selection": {"retained": "meaning"},
        "trust_snapshot": {"scope": 3},
        "view": "frontier",
        "limit": 7,
    }
    source = tmp_path / "continuation.json"
    source.write_text(json.dumps(pins))
    seen = []

    def read(conn, demand, **options):
        assert conn is connection
        seen.append((demand, options))
        return {"demand_id": demand, "read_id": pins["read_id"], "continuation": pins}

    monkeypatch.setattr(demands, "read_data_demand", read)
    result = cli("demands", "read", "demand:one", "--continuation", str(source), "--json")
    assert result.exit_code == 0, result.output
    assert opened == ["read"]
    assert seen == [
        ("demand:one", {"continuation": pins, "limit": None, "max_bytes": None, "view": None})
    ]
    assert json.loads(result.stdout)["continuation"] == pins


def test_read_refuses_duplicate_continuation_pins_before_target_acquisition(cli, tmp_path, routing):
    opened, _ = routing
    source = tmp_path / "continuation.json"
    source.write_bytes(b'{"demand_id":"demand:one","demand_id":"demand:two"}')
    result = cli("demands", "read", "demand:one", "--continuation", str(source), "--json")
    assert result.exit_code != 0
    assert opened == []
    assert "request must be valid JSON" in result.stdout


def test_cancel_routes_original_demand_and_reason_and_retains_shared_status(
    cli,
    tmp_path,
    monkeypatch,
    routing,
):
    opened, connection = routing
    seen = []

    def cancel(conn, demand, *, reason):
        assert conn is connection
        seen.append((demand, reason))
        return {
            "demand_id": demand,
            "state": "cancelled",
            "requests": [
                {"interest": "shared", "physical_retirement": "unconfirmed"},
            ],
        }

    monkeypatch.setattr(demands, "cancel_data_demand", cancel)
    result = cli(
        "demands",
        "cancel",
        "demand:one",
        "--reason",
        "operator stopped",
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path / "results")},
    )
    assert result.exit_code == 0, result.output
    assert opened == ["write"]
    assert seen == [("demand:one", "operator stopped")]
    assert json.loads(result.stdout)["native"]["requests"][0]["interest"] == "shared"


def test_execute_retains_pending_native_fates_and_exact_resume_target(
    cli,
    tmp_path,
    monkeypatch,
    routing,
):
    from corpus_structure.orchestrate.data_operations import DemandAdvance
    from corpus_structure.semantic import data_operation_service
    from corpus_structure.settings import AnalyticsSettings, Settings

    selected = AnalyticsSettings(threads=3, memory_limit="192MB", scratch_path=tmp_path / "spill")
    seen = []
    snapshot = {"demand_id": "demand:one", "state": "open", "uses": [{"fate": "awaiting-inputs"}]}

    def execute(engine, demand, **kwargs):
        seen.append((demand, kwargs["source_root"], kwargs["limit"], kwargs["max_rounds"]))
        assert kwargs["analytics_settings"] == selected
        return DemandAdvance(demand, json.dumps(snapshot).encode(), (), 0)

    monkeypatch.setattr(data_operation_service, "execute_data_demand", execute)
    result = cli(
        "demands",
        "execute",
        "demand:one",
        "--source-root",
        str(tmp_path),
        "--limit",
        "3",
        "--max-rounds",
        "2",
        "--json",
        settings=lambda: Settings(analytics=selected),
        env={"CORPUS_CI_RESULTS": str(tmp_path / "results")},
    )
    assert result.exit_code == 0, result.output
    assert routing[0] == ["write", "admit"]
    assert seen == [("demand:one", tmp_path, 3, 2)]
    native = json.loads(result.stdout)["native"]
    assert native["snapshot"] == snapshot
    assert native["receipt_count"] == 0
    assert native["snapshot_standing"] == "fresh-read"


def test_create_and_report_preserve_exact_native_scope_numbers(cli, tmp_path, monkeypatch, routing):
    from decimal import Decimal

    from corpus_structure.semantic.data_operation_json import json_loads

    number = "0.12345678901234567890123456789"
    source = tmp_path / "request.json"
    source.write_text(
        '{"project_id":"p","release_id":"r","runtime_id":"t",'
        '"intent":{"analyzed_scope":{"fraction":' + number + "}}}"
    )

    def create(conn, request):
        assert request.intent["analyzed_scope"]["fraction"] == Decimal(number)
        return {"demand_id": "demand:exact", **request.intent}

    monkeypatch.setattr(demands, "create_data_demand", create)
    result = cli(
        "demands",
        "create",
        "--request",
        str(source),
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path / "results")},
    )
    assert result.exit_code == 0, result.output
    assert json_loads(result.stdout)["native"]["analyzed_scope"]["fraction"] == Decimal(number)
    assert number in result.stdout and '"' + number + '"' not in result.stdout


def test_execute_keeps_scope_numbers_in_retained_snapshot(cli, tmp_path, monkeypatch, routing):
    from decimal import Decimal

    from corpus_structure.orchestrate.data_operations import DemandAdvance
    from corpus_structure.semantic import data_operation_service
    from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
    from semantic.demand_result_support import demand_result_page

    number = "0.12345678901234567890123456789"
    native_page = demand_result_page()
    native_page["demand_id"] = "demand:exact"
    native_page["obligations"][0]["analyzed_scope"] = {"fraction": Decimal(number)}
    snapshot = json_bytes(native_page)
    monkeypatch.setattr(
        data_operation_service,
        "execute_data_demand",
        lambda *args, **kwargs: DemandAdvance("demand:exact", snapshot, (), 0),
    )
    result = cli(
        "demands",
        "execute",
        "demand:exact",
        "--source-root",
        str(tmp_path),
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path / "results")},
    )
    assert result.exit_code == 0, result.output
    reported = json_loads(result.stdout)["native"]["snapshot"]
    assert reported["obligations"][0]["analyzed_scope"]["fraction"] == Decimal(number)


@pytest.mark.parametrize("invalid", ["missing-root", "missing-demand", "workflow-override"])
def test_run_demand_refuses_incomplete_or_changed_intent_before_acquisition(cli, tmp_path, invalid):
    def refuse_settings():
        raise AssertionError(
            "invalid retained intent must refuse before settings or database access"
        )

    arguments = {
        "missing-root": ("--demand", "demand:exact"),
        "missing-demand": ("--source-root", str(tmp_path)),
        "workflow-override": (
            "--demand",
            "demand:exact",
            "--source-root",
            str(tmp_path),
            "--whole-document",
        ),
    }
    result = cli("run", *arguments[invalid], settings=refuse_settings)
    assert result.exit_code == 2, result.output
    if invalid == "missing-root":
        assert "--source-root" in result.output
    elif invalid == "missing-demand":
        assert "--semantic-release" in result.output and "--runtime" in result.output
    else:
        assert "retained demand owns its original source and workflow choices" in result.output


def test_visual_request_uses_managed_demand_owner_and_explicit_local_actor(
    cli, tmp_path, monkeypatch, routing
):
    from corpus_structure.orchestrate.data_operations import DemandAdvance
    from corpus_structure.semantic import visual_requests

    seen = []

    def execute(engine, demand, *, visual_actor, **execution):
        seen.append((demand, visual_actor, execution))
        return DemandAdvance(demand, b'{"state":"awaiting-external"}', (), 0)

    monkeypatch.setattr(visual_requests, "execute_visual_demand", execute)
    result = cli(
        "source",
        "visual-request",
        "--demand",
        "demand:one",
        "--artifacts",
        str(tmp_path / "weights"),
        "--source-root",
        str(tmp_path),
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path / "results")},
    )
    assert result.exit_code == 0, result.output
    assert routing[0] == ["write", "admit"]
    assert len(seen) == 1 and seen[0][0] == "demand:one"
    assert seen[0][1].artifacts == tmp_path / "weights"
    assert seen[0][2]["source_root"] == tmp_path
    native = json.loads(result.stdout)["native"]
    assert native["snapshot"] == {"state": "awaiting-external"}
    assert native["receipt_count"] == 0


def test_visual_group_keeps_each_actual_demand_and_managed_receipt_without_run_group(
    cli, tmp_path, monkeypatch, routing
):
    from corpus_structure.orchestrate.data_operations import DemandAdvance
    from corpus_structure.semantic import visual_requests

    seen = []

    def execute(engine, demand, **execution):
        seen.append(demand)
        return DemandAdvance(
            demand, json.dumps({"demand_id": demand, "state": "awaiting-external"}).encode(), (), 0
        )

    monkeypatch.setattr(visual_requests, "execute_visual_demand", execute)
    path = tmp_path / "demands.json"
    path.write_text('["demand:first","demand:second"]')
    result = cli(
        "source",
        "visual-group",
        "--demands",
        str(path),
        "--artifacts",
        str(tmp_path / "weights"),
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path / "results")},
    )
    assert result.exit_code == 0, result.output
    assert seen == ["demand:first", "demand:second"]
    reports = json.loads(result.stdout)
    assert len({report["id"] for report in reports}) == 2
    assert [report["native"]["demand_id"] for report in reports] == seen
    assert all("run_id" not in report["native"] for report in reports)


def test_retire_draft_selects_exact_project_target_and_private_namespace(
    cli, tmp_path, monkeypatch, routing
):
    from corpus_structure.semantic import completion_drafts, data_operation_storage

    opened, connection = routing
    seen = []
    identity = "a" * 64

    class Storage:
        def __init__(self, actual):
            assert actual is connection

        def inspect_data_completion_draft(self, payload):
            seen.append(payload)
            return {
                "state": "eligible",
                "reason": "retired",
                "intent_id": "intent:one",
                "receipt_id": "receipt:one",
                "failure_id": "failure:one",
            }

    class Store:
        def retire(self, draft, *, project_id, inspect):
            assert (draft, project_id) == (identity, "project:one")
            result = inspect((draft, project_id))
            return completion_drafts.DraftRetirement(
                draft,
                "retired",
                "native-publication-and-retirement",
                result["intent_id"],
                result["receipt_id"],
                result["failure_id"],
            )

    def writer_schema(actual_connection, release_id):
        assert actual_connection is connection
        assert release_id == "release:writer"
        return b"writer schema"

    def open_store(root, target, max_bytes, *, writer_schema_for_release):
        assert root == tmp_path / "data" / "completion-drafts"
        assert (target.database, target.database_oid, target.purpose) == (
            "routing-only",
            1,
            "write",
        )
        assert max_bytes > 0
        assert writer_schema_for_release("release:writer") == b"writer schema"
        return Store()

    monkeypatch.setattr(data_operation_storage, "DataOperationStorage", Storage)
    monkeypatch.setattr(completion_drafts, "completion_draft_store", open_store)
    monkeypatch.setattr(completion_drafts, "captured_writer_schema", writer_schema)
    env = {
        "CORPUS_CI_RESULTS": str(tmp_path / "results"),
        "CORPUS_PATHS__DATA_DIR": str(tmp_path / "data"),
    }
    result = cli(
        "demands",
        "retire-draft",
        identity,
        "--project",
        "project:one",
        "--target",
        "development",
        "--json",
        env=env,
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert seen == [(identity, "project:one")] and opened == ["write"]
    assert report["native"]["receipt_id"] == "receipt:one"
    manifest = json.loads((tmp_path / "results" / report["id"] / "manifest.json").read_text())
    assert manifest["operation_account"]["known_effects"] == ["private completion draft retired"]
