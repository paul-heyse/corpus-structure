"""Attribution, partial scope and optional code detail retain their owner's standing."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest

from corpus_structure.cli.observations import Bindings, Observation, ObservationPage
from corpus_structure.cli.operation_observation import operational_observation
from corpus_structure.semantic.code_identity import CodeIdentity, CodeUnknown
from corpus_structure.semantic.code_reuse import explain_code_reuse
from corpus_structure.semantic.serving_code import (
    ServingImplementation,
    serving_code,
    serving_report,
)


@pytest.mark.parametrize(
    ("descriptor", "standing"),
    [
        (None, "unavailable"),
        ({"version": "other"}, "unavailable"),
        ({"version": "data-operation-native-v1", "source_digest": "expected"}, "matching"),
        ({"version": "data-operation-native-v1", "source_digest": "different"}, "mismatch"),
    ],
)
def test_native_kernel_observation_only_reads_descriptor(descriptor, standing):
    from corpus_structure.semantic.data_operation_storage import observe_native_kernel

    class Connection:
        def scalar(self, statement):
            assert str(statement) == "SELECT sem.data_operation_native_descriptor()"
            return descriptor

    observed = observe_native_kernel(
        cast(Any, Connection()), cast(Any, SimpleNamespace(native_kernel_digest="expected"))
    )
    assert observed.standing == standing
    assert observed.expected_digest == "expected"


@pytest.mark.parametrize("standing", ["matching", "mismatch", "unavailable"])
def test_inspection_current_kernel_keeps_resume_prerequisites(standing, tmp_path, monkeypatch):
    import typer

    from corpus_structure.cli.app import build_full_app
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.cli.observations import ObservationSelection
    from corpus_structure.cli.output import CliState
    from corpus_structure.cli.result_inspection import NativeInspection, inspect_result
    from corpus_structure.semantic.data_operation_storage import NativeKernelObservation

    store = ResultStore(tmp_path / "results")
    with store.operation("run") as invocation:
        path = invocation.directory / "execution-context.json"
        path.write_text("{}")
        invocation.publish("execution_context", path)
    monkeypatch.setattr(
        "corpus_structure.cli.execution_context.read_execution_context",
        lambda *args: SimpleNamespace(
            demand_id="demand:one",
            model_dump=lambda **kwargs: {
                "configured_target": {"profile": "development"},
                "source_root": "/actual source",
            },
        ),
    )
    monkeypatch.setattr(
        "corpus_structure.cli.result_inspection.native_inspection",
        lambda *args: NativeInspection(
            kernel=NativeKernelObservation(
                standing=standing,
                expected_digest="expected",
                observed_digest="different" if standing == "mismatch" else "expected",
            )
        ),
    )
    ctx = typer.Context(typer.main.get_command(build_full_app()), obj=CliState())
    report = inspect_result(ctx, store, invocation.id, ObservationSelection())
    kinds = {action.kind for action in report.next_actions}
    if standing == "mismatch":
        assert "resume_result" not in kinds
        successor = next(
            action for action in report.next_actions if action.kind == "successor_admission"
        )
        assert successor.standing == "observed" and successor.command is None
        assert "reviewed_successor_release" in successor.required_inputs
    else:
        resume = next(action for action in report.next_actions if action.kind == "resume_result")
        assert resume.standing == "conditional"
        assert resume.reason is not None
        assert "Current execution admission" in resume.reason


def test_recovery_actions_keep_owner_observations_and_guard_fresh_query_target(
    tmp_path, monkeypatch
):
    import json
    import shlex

    import typer

    from corpus_structure.cli.app import build_full_app
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.cli.observations import ObservationSelection
    from corpus_structure.cli.output import CliState
    from corpus_structure.cli.result_inspection import NativeInspection, inspect_result
    from corpus_structure.semantic.storage_target import StorageTarget

    target = StorageTarget(
        database="captured",
        database_oid=21,
        system_identifier="cluster:one",
        host="localhost",
        port=5434,
        purpose="read",
    )
    store = ResultStore(tmp_path / "results")
    with store.operation("controlled", observations=True) as invocation:
        invocation.bind_observations(demand_id="demand:one", project="project with spaces")
        invocation.stage("selected", native_source_root="/actual source")
    bindings = Bindings(invocation_id=invocation.id, demand_id="demand:one")
    refusal = Observation(
        sequence=1,
        producer_sequence=1,
        timestamp="2026-11-21T00:00:00Z",
        kind="event",
        producer="executor",
        bindings=bindings,
        message="native_demand.prepared_acquisition_refused",
        fields={"prerequisite": "model-resource", "expected": "first", "actual": "second"},
    )
    recovery = refusal.model_copy(
        update={
            "sequence": 2,
            "producer_sequence": 2,
            "message": "native_demand.recovery_selected",
            "fields": {
                "recovery_action": "reconcile",
                "observation_scope": "checked committed claim",
            },
        }
    )
    native = NativeInspection(
        availability="available",
        expected_target=target.model_dump(mode="json"),
        demand={
            "demand_id": "demand:one",
            "project_id": "project with spaces",
            "read_id": "old-read",
            "continuation": {"native_only": True},
        },
        retained_read={
            "demand_id": "demand:one",
            "read_id": "old-read",
            "scope": {"operation_id": "selected-operation"},
            "view": "frontier",
            "limit": 7,
            "max_bytes": 1048576,
        },
    )
    monkeypatch.setattr(
        "corpus_structure.cli.result_inspection.native_inspection", lambda *args: native
    )
    ctx = typer.Context(typer.main.get_command(build_full_app()), obj=CliState())
    report = inspect_result(
        ctx,
        store,
        invocation.id,
        ObservationSelection(limit=7),
        page=ObservationPage(result=invocation.id, rows=[refusal, recovery]),
    )
    assert report.preparation_refusal == refusal
    assert report.recovery_observation == recovery
    resume = next(action for action in report.next_actions if action.kind == "resume_demand")
    assert resume.standing == "conditional"
    action = next(action for action in report.next_actions if action.kind == "query")
    assert action.read_scope == "fresh_current"
    assert action.expected_target == target
    assert action.query is not None and action.query.cursor is None
    assert action.command is not None
    args = shlex.split(action.command)
    assert args[:3] == ["ci", "query", "operations"]
    assert args[args.index("--project") + 1] == "project with spaces"
    assert args[args.index("--limit") + 1] == "7"
    assert StorageTarget.model_validate_json(args[args.index("--expected-target") + 1]) == target
    assert "--cursor" not in args
    replay = next(action for action in report.next_actions if action.kind == "replay_native_read")
    assert replay.read_scope == "retained_frontier" and replay.standing == "conditional"
    assert replay.query is None and replay.retained_read == native.retained_read
    assert replay.command is not None
    args = shlex.split(replay.command)
    assert args[:4] == ["ci", "demands", "read", "demand:one"]
    assert args[args.index("--project") + 1] == "project with spaces"
    assert json.loads(args[args.index("--continuation-json") + 1]) == native.retained_read
    assert StorageTarget.model_validate_json(args[args.index("--expected-target") + 1]) == target
    assert all(action.kind != "native_status" for action in report.next_actions)


def test_query_target_handoff_is_verified_before_read(cli, monkeypatch):
    import json
    from contextlib import contextmanager

    from corpus_structure.cli import selected_results
    from corpus_structure.semantic import runtime, storage_target

    target = storage_target.StorageTarget(
        database="captured",
        database_oid=21,
        system_identifier="cluster:one",
        host="localhost",
        port=5434,
        purpose="read",
    )
    connection = object()
    calls = []

    @contextmanager
    def engine(*args, **kwargs):
        class Engine:
            @contextmanager
            def begin(self):
                yield connection

        yield Engine()

    def verify(conn, expected, *, purpose):
        assert conn is connection and expected == target and purpose == "read"
        calls.append("verified")

    def query(conn, request):
        assert calls == ["verified"]
        assert request.project_id == "project:one" and request.demand_id == "demand:one"
        return {"items": [], "continuation": None}

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(storage_target, "verify_target", verify)
    monkeypatch.setattr(selected_results, "serve_demand_query", query)
    args = (
        "query",
        "operations",
        "--demand",
        "demand:one",
        "--project",
        "project:one",
        "--expected-target",
        target.model_dump_json(),
        "--json",
    )
    result = cli(*args)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["items"] == []

    def refuse(*args, **kwargs):
        raise storage_target.StorageTargetError("different PostgreSQL target")

    monkeypatch.setattr(storage_target, "verify_target", refuse)
    result = cli(*args)
    assert result.exit_code != 0
    assert "different PostgreSQL target" in result.stdout


def test_retained_native_handoff_keeps_read_scope_and_verifies_target(cli, monkeypatch):
    import json
    from contextlib import contextmanager

    from corpus_structure.cli import demands
    from corpus_structure.semantic.storage_target import StorageTarget, StorageTargetError

    target = StorageTarget(
        database="captured",
        database_oid=21,
        system_identifier="cluster:one",
        host="localhost",
        port=5434,
        purpose="read",
    )
    retained_read = {
        "demand_id": "demand:one",
        "read_id": "read:captured",
        "scope": {"operation_id": "selected-operation"},
        "view": "frontier",
        "limit": 7,
        "max_bytes": 65536,
    }
    connection = object()
    events = []

    @contextmanager
    def engine(settings, *, purpose):
        assert purpose == "read"

        class Engine:
            @contextmanager
            def begin(self):
                yield connection

        yield Engine()

    def verify(conn, expected, *, purpose):
        assert conn is connection and expected == target and purpose == "read"
        events.append("verified")

    def read(conn, demand, *, continuation, **kwargs):
        assert conn is connection and demand == "demand:one"
        assert events[-1] == "verified" and continuation == retained_read
        assert all(value is None for value in kwargs.values())
        events.append("read")
        return {"project_id": "project with spaces", "read_id": "read:captured"}

    monkeypatch.setattr(demands, "ENGINE", engine)
    monkeypatch.setattr(demands, "verify_target", verify)
    monkeypatch.setattr(demands, "read_data_demand", read)
    args = (
        "demands",
        "read",
        "demand:one",
        "--expected-target",
        target.model_dump_json(),
        "--continuation-json",
        json.dumps(retained_read),
        "--json",
    )
    result = cli(*args, "--project", "project with spaces")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["read_id"] == "read:captured"
    wrong_project = cli(*args, "--project", "different project")
    assert wrong_project.exit_code != 0
    assert "demand belongs to another project" in wrong_project.stdout

    def refuse(*args, **kwargs):
        raise StorageTargetError("different PostgreSQL target")

    monkeypatch.setattr(demands, "verify_target", refuse)
    wrong_target = cli(*args)
    assert wrong_target.exit_code != 0
    assert "different PostgreSQL target" in wrong_target.stdout
    assert events == ["verified", "read", "verified", "read"]


def test_deployment_inspection_preserves_candidate_target_and_settled_effects(tmp_path):
    import shlex

    import typer

    from corpus_structure.cli.app import build_full_app
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.cli.observations import ObservationSelection
    from corpus_structure.cli.output import CliState
    from corpus_structure.cli.result_inspection import inspect_result
    from corpus_structure.semantic.storage_target import StorageTarget

    target = StorageTarget(
        database="stage",
        database_oid=21,
        system_identifier="cluster:one",
        host="localhost",
        port=5434,
        purpose="maintenance",
    )
    store = ResultStore(tmp_path / "results")
    with store.operation(
        "model.deploy", scope={"candidate": "captured-candidate"}, account=True
    ) as invocation:
        invocation.record_deployment_checkpoint(target, "N45", "N46", "release:one", "migration")
        invocation.settle("interrupted")
    ctx = typer.Context(typer.main.get_command(build_full_app()), obj=CliState())
    report = inspect_result(ctx, store, invocation.id, ObservationSelection())
    assert report.deployment is not None
    assert report.deployment.settled_effects == ("migration",)
    assert report.deployment.acquired_target == target
    action = next(action for action in report.next_actions if action.kind == "resume_deployment")
    assert action.command is not None
    assert shlex.split(action.command) == ["ci", "model", "change", "deploy", "captured-candidate"]
    assert action.standing == "conditional" and action.expected_target == target


def event(phase, *, age=0):
    return Observation(
        sequence=1,
        timestamp=(datetime.now(UTC) - timedelta(seconds=age)).isoformat(),
        kind="provider_activity",
        message="provider owner observation",
        producer="provider:one",
        producer_sequence=1,
        assurance="provider_reported",
        fields={"operational_phase": phase},
        bindings=Bindings(provider_invocation="provider:one"),
    )


def test_ready_does_not_claim_inference_and_partial_counts_have_units():
    page = ObservationPage(result="result:one", rows=[event("ready")], coverage="continued")
    native = SimpleNamespace(
        availability="available",
        demand={
            "read_id": "read:one",
            "obligations": [{"id": "one"}],
            "uses": [{"id": "two"}],
            "continuation": {"after": "one"},
        },
    )
    report = operational_observation(page, native, running=True)
    phases = {item.phase: item for item in report.phases}
    assert phases["ready"].standing == "observed"
    assert phases["inference_completed"].standing == "unknown"
    assert phases["publication"].standing == "unknown"
    assert {(item.value, item.unit, item.read_id, item.complete) for item in report.counts} == {
        (1, "obligations", "read:one", False),
        (1, "uses", "read:one", False),
    }


def test_old_structured_observation_is_stale_and_missing_native_stays_unknown():
    page = ObservationPage(
        result="result:one", rows=[event("inference_submitted", age=60)], coverage="continued"
    )
    native = SimpleNamespace(availability="unavailable", demand=None)
    report = operational_observation(page, native, running=True)
    assert (
        next(item for item in report.phases if item.phase == "inference_submitted").standing
        == "stale"
    )
    assert report.counts == ()


def test_local_explanation_uses_same_capture_and_compact_projection():
    code = CodeIdentity(
        ("example.entry",), (), (), (CodeUnknown("example.dep", 7, "opaque call"),), b"{}"
    )
    implementation = ServingImplementation("a" * 64, code)
    with explain_code_reuse() as explanations, serving_code(implementation):
        result = serving_report({"items": [1], "continuation": "next-page"})
    assert result["continuation"] == "next-page"
    assert result["reuse"]["eligible"] is False
    assert result["reuse"]["unknowns"] == [
        {"module": "example.dep", "line": 7, "reason": "opaque call"}
    ]
    assert len(explanations) == 1
    (explanation,) = explanations
    assert explanation.entry_point == "example.entry" and explanation.eligible is False
    assert (
        explanation.facts[0].standing == "unresolved" and explanation.facts[0].dependency_path == ()
    )
    assert explanation.facts[0].line == 7
    assert explanation.outcome == "withheld"


def test_query_explain_reuse_is_opt_in_and_uses_the_executed_owner(cli, monkeypatch):
    import json
    from contextlib import contextmanager

    from corpus_structure.cli import selected_results
    from corpus_structure.semantic import runtime

    @contextmanager
    def engine(*args, **kwargs):
        class Engine:
            @contextmanager
            def begin(self):
                yield object()

        yield Engine()

    code = CodeIdentity(
        ("actual.entry",), (), (), (CodeUnknown("actual.dep", 11, "unresolved runtime"),), b"{}"
    )

    def query(connection, request):
        with serving_code(ServingImplementation("a" * 64, code)):
            return serving_report({"items": [], "continuation": None})

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(selected_results, "serve_demand_query", query)
    ordinary = cli("query", "members", "--demand", "demand:one", "--project", "p", "--json")
    assert ordinary.exit_code == 0, ordinary.output
    assert "reuse_explanation" not in json.loads(ordinary.stdout)
    explained = cli(
        "query", "members", "--demand", "demand:one", "--project", "p", "--explain-reuse", "--json"
    )
    assert explained.exit_code == 0, explained.output
    body = json.loads(explained.stdout)
    (report,) = body["reuse_explanation"]["reports"]
    assert body["reuse_explanation"]["availability"] == "available"
    assert report["entry_point"] == "actual.entry" and report["facts"][0]["module"] == "actual.dep"


def test_selected_page_delivers_implementation_identity_without_live_code_custody():
    import base64
    import json

    from corpus_structure.intervene.demand_read_tools import SelectedResult
    from corpus_structure.intervene.mcp_results import bounded_structured_result
    from corpus_structure.semantic.data_operation_json import (
        JsonBoundaryError,
        finite_result_record,
    )
    from corpus_structure.semantic.page_envelope import PageEnvelope
    from corpus_structure.semantic.selected_pages import byte_bounded_page

    code = CodeIdentity(("actual.entry",), (), (), (), b"{}")
    implementation = ServingImplementation("a" * 64, code)
    presentation = PageEnvelope(
        header={"implementation": implementation, "cut_id": "cut:one"},
        cursor_basis={
            "version": "demand-query-v2",
            "implementation": implementation,
            "selection": "selected",
            "request": {"demand_id": "demand:one", "view": "products"},
            "cut": "cut:one",
        },
    )
    page = byte_bounded_page(
        [{"member_id": "one"}, {"member_id": "two"}],
        offset=0,
        limit=1,
        max_bytes=65536,
        presentation=presentation,
    )
    assert type(page["implementation"]) is str
    assert page["implementation"] == "a" * 64
    assert presentation.header["implementation"] is implementation
    assert implementation.code is code
    assert json.loads(base64.b64decode(page["continuation"], altchars=b"-_", validate=True)) == {
        **presentation.cursor_basis,
        "ordinal": 1,
    }
    delivered = finite_result_record(page)
    mcp = bounded_structured_result(SelectedResult(cut_id="cut:one", result=delivered), 65536)
    assert mcp.structured_content is not None
    assert mcp.structured_content["result"]["implementation"] == "a" * 64

    class OtherString(str):
        pass

    with pytest.raises(JsonBoundaryError, match="unsupported structured result value"):
        finite_result_record({"implementation": OtherString("unowned")})


def test_installed_query_handles_implementation_projection_and_delivery_refusal(cli, monkeypatch):
    import json
    from contextlib import contextmanager

    from corpus_structure.cli import selected_results
    from corpus_structure.semantic import runtime
    from corpus_structure.semantic.page_envelope import PageEnvelope
    from corpus_structure.semantic.selected_pages import byte_bounded_page

    @contextmanager
    def engine(*args, **kwargs):
        class Engine:
            @contextmanager
            def begin(self):
                yield object()

        yield Engine()

    implementation = ServingImplementation(
        "a" * 64, CodeIdentity(("actual.entry",), (), (), (), b"{}")
    )

    def query(connection, request):
        return byte_bounded_page(
            [{"member_id": "one"}],
            offset=0,
            limit=1,
            max_bytes=65536,
            presentation=PageEnvelope(
                header={"implementation": implementation},
                cursor_basis={"implementation": implementation},
            ),
        )

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(selected_results, "serve_demand_query", query)
    args = ("query", "members", "--demand", "demand:one", "--project", "project:one", "--json")
    result = cli(*args)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["implementation"] == "a" * 64

    monkeypatch.setattr(selected_results, "serve_demand_query", lambda *args: {"invalid": object()})
    refused = cli(*args)
    assert refused.exit_code != 0
    assert json.loads(refused.stdout)["error"]["code"] == "JsonBoundaryError"


def test_native_candidate_explanation_is_retained_for_managed_inspection(
    cli, monkeypatch, tmp_path
):
    import json

    from corpus_structure.semantic import metadata, native_revision_compare, target_installation
    from corpus_structure.semantic.code_reuse import record_code_reuse

    code = CodeIdentity(
        ("generator.entry",),
        (),
        (),
        (CodeUnknown("generator.dep", 19, "unresolved contract"),),
        b"{}",
    )
    monkeypatch.setattr(metadata, "get_metadata", lambda: object())
    monkeypatch.setattr(target_installation, "capture_target_installation", lambda value: object())

    def compare(installation, predecessor):
        record_code_reuse(
            code, entry_point="generator.entry", tier="native-programs", outcome="withheld"
        )
        return SimpleNamespace(
            unchanged=True, head_revision=predecessor, object_count=12, kernel_identity="kernel:one"
        )

    monkeypatch.setattr(native_revision_compare, "compare_native_programs", compare)
    response = cli(
        "schema",
        "native-candidate",
        "--expected-predecessor",
        "semantic_ddo_pe_n35",
        "--explain-reuse",
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert response.exit_code == 0, response.output
    native = json.loads(response.stdout)
    assert native["outcome"] == "no_native_change"
    assert native["reuse_explanation"]["reports"][0]["entry_point"] == "generator.entry"
    inspected = cli(
        "results",
        "inspect",
        native["result_id"],
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert inspected.exit_code == 0, inspected.output
    report = json.loads(inspected.stdout)
    assert report["reuse_explanation"] == native["reuse_explanation"]
    assert report["native"]["availability"] == "unavailable"
