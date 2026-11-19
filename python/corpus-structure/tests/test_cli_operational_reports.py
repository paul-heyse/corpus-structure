"""Attribution, partial scope and optional code detail retain their owner's standing."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from corpus_structure.cli.observations import Bindings, Observation, ObservationPage
from corpus_structure.cli.operation_observation import operational_observation
from corpus_structure.semantic.code_identity import CodeIdentity, CodeUnknown
from corpus_structure.semantic.code_reuse import explain_code_reuse
from corpus_structure.semantic.serving_code import (
    ServingImplementation,
    serving_code,
    serving_report,
)


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
        result = serving_report({"items": [1], "continuation": "discarded"})
    assert result["continuation"] is None and result["reuse"]["eligible"] is False
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
