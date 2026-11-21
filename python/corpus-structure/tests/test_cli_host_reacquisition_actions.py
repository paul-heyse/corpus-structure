"""Captured shared-host prerequisites produce guarded, conditional operator actions."""

import json
import shlex
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
import typer

from corpus_structure.cli.app import build_full_app
from corpus_structure.cli.managed import ResultStore
from corpus_structure.cli.observations import ObservationSelection
from corpus_structure.cli.output import CliState
from corpus_structure.cli.result_inspection import NativeInspection, inspect_result
from corpus_structure.semantic.storage_target import StorageTarget

TARGET = StorageTarget(
    database="stage",
    database_oid=123,
    system_identifier="original-cluster",
    host="localhost",
    port=5434,
    purpose="write",
)


@pytest.mark.parametrize("with_target", [True, False])
def test_captured_runtime_prerequisite_has_exact_reacquisition_action(
    tmp_path, monkeypatch, with_target
):
    from corpus_structure.semantic.data_operation_prepared_products import (
        PreparedProductDiagnostic,
        PreparedProductRefusal,
    )
    from corpus_structure.semantic.refusals import semantic_failure_fields

    store = ResultStore(tmp_path / "results")
    with store.operation("demands.execute", account=True) as invocation:
        invocation.bind_observations(
            demand_id="demand:one",
            release_id="release:one",
            runtime_id="runtime:old",
        )
        if with_target:
            invocation.record_target(TARGET, None, None, "release:one")
        context = invocation.directory / "execution-context.json"
        context.write_text("{}")
        invocation.publish("execution_context", context)
        invocation.record_failure(
            "refusal",
            {
                "code": "ExceptionGroup",
                "message": "A deliberately unrelated group message.",
                **semantic_failure_fields(
                    ExceptionGroup(
                        "opaque group",
                        [
                            PreparedProductRefusal(
                                "A deliberately unrelated leaf message.",
                                PreparedProductDiagnostic(
                                    "spacy.distributions_sha256",
                                    "old",
                                    "new",
                                    "shared-host-runtime",
                                ),
                            )
                        ],
                    )
                ),
            },
        )
        invocation.settle("failed")
    monkeypatch.setattr(
        "corpus_structure.cli.execution_context.read_execution_context",
        lambda *args: SimpleNamespace(
            demand_id="demand:one",
            model_dump=lambda **kwargs: {
                "configured_target": {"profile": "deployment"},
                "source_root": "/original source",
            },
        ),
    )
    monkeypatch.setattr(
        "corpus_structure.cli.result_inspection.native_inspection",
        lambda *args: NativeInspection(reason="No current native observation."),
    )
    ctx = typer.Context(typer.main.get_command(build_full_app()), obj=CliState())
    report = inspect_result(ctx, store, invocation.id, ObservationSelection())
    assert report.preparation is not None
    assert report.preparation.expected == "old" and report.preparation.actual == "new"
    action = next(action for action in report.next_actions if action.kind == "reacquire_host")
    assert action.standing == "conditional" and action.runtime_id == "runtime:old"
    assert action.release_id == "release:one" and action.prerequisite == report.preparation
    if with_target:
        assert action.command is not None and action.required_inputs == ()
        arguments = shlex.split(action.command)
        assert arguments[:3] == ["ci", "release", "reacquire-host"]
        assert arguments[arguments.index("--runtime") + 1] == "runtime:old"
        assert arguments[arguments.index("--target") + 1] == "deployment"
        assert (
            StorageTarget.model_validate_json(arguments[arguments.index("--expected-target") + 1])
            == TARGET
        )
    else:
        assert action.command is None and action.required_inputs == ("acquired_target",)


def test_grouped_preparation_does_not_choose_among_distinct_prerequisites():
    from corpus_structure.semantic.data_operation_prepared_products import (
        PreparedProductDiagnostic,
        PreparedProductRefusal,
    )
    from corpus_structure.semantic.refusals import semantic_failure_fields

    first = PreparedProductRefusal(
        "one", PreparedProductDiagnostic("host", "old", "new", "shared-host-runtime")
    )
    second = PreparedProductRefusal(
        "two", PreparedProductDiagnostic("model", "a", "b", "model-resource")
    )
    group = ExceptionGroup("original group", [first, ExceptionGroup("nested", [second])])
    assert "preparation" not in semantic_failure_fields(group)
    assert group.exceptions[0] is first
    equal = ExceptionGroup("repeated", [first, ExceptionGroup("nested", [first])])
    assert semantic_failure_fields(equal)["preparation"]["prerequisite"] == "shared-host-runtime"


@pytest.mark.parametrize("target", ["development", "deployment"])
def test_reacquire_host_refuses_equal_oid_on_another_cluster_before_acquisition(
    cli, monkeypatch, tmp_path, target
):
    from corpus_structure.semantic import (
        native_host_reacquisition,
        releases,
        runtime,
        storage_target,
    )
    from corpus_structure.settings import Settings

    foreign = TARGET.model_copy(update={"system_identifier": "another-cluster", "purpose": "admit"})

    @contextmanager
    def engine(*args, **kwargs):
        class Engine:
            @contextmanager
            def begin(self):
                yield object()

        yield Engine()

    def forbid(*args, **kwargs):
        raise AssertionError("target refusal must precede release loading and host reacquisition")

    def verify(connection, expected, *, purpose):
        assert expected == TARGET and purpose == "admit"
        raise storage_target.StorageTargetError("acquired target differs from original cluster")

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(storage_target, "acquired_target", lambda *args, **kwargs: foreign)
    monkeypatch.setattr(storage_target, "verify_declared_route", lambda *args: None)
    monkeypatch.setattr(storage_target, "verify_target", verify)
    monkeypatch.setattr(releases, "load_release_inputs", forbid)
    monkeypatch.setattr(native_host_reacquisition, "reacquire_shared_host_runtime", forbid)
    result = cli(
        "release",
        "reacquire-host",
        "--release",
        "release:one",
        "--runtime",
        "runtime:old",
        "--database-oid",
        "123",
        "--target",
        target,
        "--expected-target",
        TARGET.model_dump_json(),
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path / "results")},
        settings=lambda: Settings(deployment={"url": "postgresql://operator@localhost:5434/stage"}),
    )
    assert result.exit_code != 0, result.output
    assert json.loads(result.stdout)["error"]["code"] == "StorageTargetError"
