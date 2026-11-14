"""Infrastructure evidence: provider selection persists without claiming provider behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from test_receipts import (
    _failure_projection,
    _receipt_retryable,
    classify,
    classify_receipt,
    main,
    write_unresolved,
)

NODE = "test_case.py::test_case"


def receipt(
    directory: Path, *, mode="ordinary", blocked=False, teardown_failed=False, optional=False
):
    directory.mkdir(exist_ok=True)
    missing = [
        {"name": "asset_a", "reason": "missing first asset"},
        {"name": "asset_b", "reason": "missing second asset"},
    ]
    properties = [("qualification_prerequisites", missing), ("qualification_reason", "both absent")]
    if optional:
        properties.append(("qualification_optional", "outside ordinary scope"))
    reports: list[dict[str, object]] = [{"$report_type": "SessionStart"}]
    for phase in ("setup", "call", "teardown"):
        if blocked and phase == "call":
            continue
        outcome = "skipped" if blocked and phase == "setup" else "passed"
        if phase == "teardown" and teardown_failed:
            outcome = "failed"
        reports.append(
            {
                "$report_type": "TestReport",
                "nodeid": NODE,
                "when": phase,
                "outcome": outcome,
                "user_properties": properties if phase == "setup" and blocked else [],
                "longrepr": "teardown defect"
                if outcome == "failed"
                else "missing assets"
                if outcome == "skipped"
                else None,
            }
        )
    code = int(teardown_failed)
    reports.append({"$report_type": "SessionFinish", "exitstatus": code})
    events = [
        {
            "event": "collection_finish",
            "selected": [NODE],
            "native_required": [],
            "evidence_selection": mode,
            "provider_evidence": [NODE] if mode == "providers" else [],
        },
        {"event": "session_start", "xdist_numprocesses": 0},
        {"event": "logstart", "nodeid": NODE},
        {"event": "logfinish", "nodeid": NODE},
    ]
    for filename, rows in (("reportlog.jsonl", reports), ("events-controller-1.jsonl", events)):
        (directory / filename).write_text("".join(json.dumps(row) + "\n" for row in rows))
    (directory / "pytest.process.json").write_text(json.dumps({"returncode": code}))
    (directory / "invocation.json").write_text(
        json.dumps({"evidence_selection": mode, "python_only": True})
    )
    return directory


@pytest.mark.parametrize(
    "required,observed", [("providers", "ordinary"), ("ordinary", "providers")]
)
def test_other_evidence_mode_cannot_cover_required_identity(tmp_path, required, observed):
    original = receipt(tmp_path / "original", mode=required, blocked=True)
    replacement = receipt(tmp_path / "replacement", mode=observed)
    result = classify([original, replacement], [original])
    assert result["required_unresolved"] == [NODE]
    assert result["coverage"][NODE] == ["blocked", "incomplete"]


def test_missing_provider_collection_cannot_be_replaced_by_ordinary_pass(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    (original / "invocation.json").write_text(json.dumps({"evidence_selection": "providers"}))
    ordinary = receipt(tmp_path / "ordinary")
    result = classify([original, ordinary], required_lanes={"ordinary": [original, ordinary]})
    assert result["missing_lanes"] == ["ordinary"]
    assert result["lane_selections"] == {}


def test_provider_manifest_must_contain_actual_provider_identities(tmp_path):
    directory = receipt(tmp_path, mode="providers")
    events = directory / "events-controller-1.jsonl"
    rows = [json.loads(line) for line in events.read_text().splitlines()]
    rows[0]["provider_evidence"] = []
    events.write_text("".join(json.dumps(row) + "\n" for row in rows))
    result = classify_receipt(directory)
    assert result["status"] == "incomplete"
    assert not result["identity_valid"]
    assert any("without provider evidence" in reason for reason in result["stream_errors"])


def test_legacy_mode_absence_is_ordinary(tmp_path):
    directory = receipt(tmp_path)
    (directory / "invocation.json").write_text("{}")
    events = directory / "events-controller-1.jsonl"
    rows = [json.loads(line) for line in events.read_text().splitlines()]
    rows[0].pop("evidence_selection")
    rows[0].pop("provider_evidence")
    events.write_text("".join(json.dumps(row) + "\n" for row in rows))
    result = classify_receipt(directory)
    assert result["evidence_selection"] == "ordinary"
    assert result["status"] == "passed"


def test_blocked_provider_is_manually_retryable_and_optional_cannot_erase_it(tmp_path):
    result = classify_receipt(receipt(tmp_path, mode="providers", blocked=True, optional=True))
    assert result["status"] == "blocked"
    assert result["nodes"][NODE]["status"] == "blocked"
    assert _receipt_retryable(result)


def test_blocked_projection_preserves_all_reasons_and_separate_failed_teardown(tmp_path):
    directory = receipt(tmp_path, mode="providers", blocked=True, teardown_failed=True)
    result = classify([directory])
    assert result["status"] == "failed"
    projection = _failure_projection(result, 20, None)
    assert [(item["phase"], item["outcome"]) for item in projection["items"]] == [
        ("setup", "blocked"),
        ("teardown", "failed"),
    ]
    assert projection["items"][0]["prerequisites"] == [
        {"name": "asset_a", "reason": "missing first asset"},
        {"name": "asset_b", "reason": "missing second asset"},
    ]
    assert projection["items"][1]["reason"] == "pytest_failure"


def test_provider_recollection_preserves_mode_without_running_body(tmp_path, monkeypatch):
    case = tmp_path / "case"
    case.mkdir()
    (case / "pytest.ini").write_text("[pytest]\nmarkers = shared_cluster_fault: exclusive\n")
    (case / "conftest.py").write_text(
        'from hypothesis import settings\nsettings.register_profile("ci", deadline=None)\n'
    )
    (case / "test_case.py").write_text(
        "import pytest\n@pytest.mark.provider_evidence\n"
        'def test_case():\n    raise AssertionError("recollection must not run bodies")\n'
    )
    monkeypatch.chdir(case)
    required = case / "required.json"
    required.write_text(
        json.dumps(
            {"selected": [NODE], "evidence_selection": "providers", "provider_evidence": [NODE]}
        )
    )
    result = {
        "required": [NODE],
        "required_unresolved": [NODE],
        "receipts": [{"evidence_selection": "providers"}],
    }
    target = tmp_path / "unresolved.txt"
    written = write_unresolved(result, target, required_from=[required], lane="ordinary")
    assert written["evidence_selection"] == "providers"
    collected = classify_receipt(Path(written["validation_receipt"]))
    assert collected["selected"] == [NODE]
    assert collected["evidence_selection"] == "providers"
    assert target.read_text() == NODE + "\n"


def test_supervisor_persists_provider_mode_and_never_starts_rust(tmp_path, monkeypatch, capsys):
    parent = tmp_path / "managed"
    parent.mkdir()
    output = parent / "ordinary"
    monkeypatch.setattr(
        "test_receipts.invocation_context",
        lambda native_host="shared": {"native_host": native_host},
    )

    def run(directory, args, **kwargs):
        assert kwargs["evidence_selection"] == "providers"
        assert kwargs["native_host"] == "shared" and kwargs["python_only"] is True
        invocation = (directory / "invocation.json").read_text()
        receipt(directory, mode="providers", blocked=True)
        (directory / "invocation.json").write_text(invocation)
        return {"returncode": 0}

    monkeypatch.setattr("test_receipts.run_python", run)
    monkeypatch.setattr(
        "test_receipts.run_rust",
        lambda *args, **kwargs: pytest.fail("provider scope is Python-only"),
    )
    assert (
        main(
            [
                "run",
                "--out-dir",
                str(output),
                "--managed-lane",
                "ordinary",
                "--evidence-selection",
                "providers",
            ]
        )
        == 1
    )
    invocation = json.loads((output / "invocation.json").read_text())
    assert invocation["evidence_selection"] == "providers"
    assert invocation["python_only"]
    answer = json.loads(capsys.readouterr().out)
    assert answer["evidence_selection"] == "providers"
    assert answer["status"] == "blocked"


def test_supervisor_refuses_provider_fault_before_creating_workspace(tmp_path):
    output = tmp_path / "fault"
    with pytest.raises(SystemExit) as refused:
        main(
            [
                "run",
                "--out-dir",
                str(output),
                "--managed-lane",
                "fault",
                "--evidence-selection",
                "providers",
            ]
        )
    assert refused.value.code == 2
    assert not output.exists()


def test_collection_receipt_cannot_supply_functional_pass_or_retry(tmp_path):
    directory = receipt(tmp_path)
    invocation = directory / "invocation.json"
    invocation.write_text(
        json.dumps({"evidence_selection": "ordinary", "collection_only": True, "python_only": True})
    )
    result = classify([directory], [directory])
    assert result["status"] == "not_run"
    assert result["required_unresolved"] == [NODE]
    assert result["coverage"][NODE] == ["not_run"]
    assert not _receipt_retryable(result["receipts"][0])
