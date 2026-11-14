"""Real child collection controls for provider scope and pre-fixture prerequisites."""

from __future__ import annotations

import json
from pathlib import Path

from test_receipts import _node_status, classify_receipt, run_python

CONFIGURATION = """from hypothesis import settings
settings.register_profile("ci", deadline=None, derandomize=True, database=None)
"""


def child(tmp_path: Path, source: str, *, args=(), conftest=""):
    case = tmp_path / "case"
    case.mkdir()
    (case / "pytest.ini").write_text(
        "[pytest]\naddopts = --strict-markers\nmarkers =\n"
        "    db: synthetic native consumer\n"
        "    shared_cluster_fault: exclusive serial scope\n"
    )
    (case / "test_case.py").write_text(source)
    (case / "conftest.py").write_text(CONFIGURATION + conftest)
    output = tmp_path / "receipt"
    output.mkdir()
    process = run_python(output, ["-n", "0", *args], cwd=case, timeout=45)
    events = [
        json.loads(line)
        for path in output.glob("events-*.jsonl")
        for line in path.read_text().splitlines()
    ]
    return process, output, case, events


SELECTION = """import pytest

def test_controlled():
    pass

@pytest.mark.provider_evidence
def test_provider():
    raise AssertionError("provider must be excluded from ordinary selection")
"""


def test_default_selection_excludes_provider_from_required_collection(tmp_path):
    process, output, _, events = child(tmp_path, SELECTION)
    assert process["returncode"] == 0
    receipt = classify_receipt(output)
    assert receipt["selected"] == ["test_case.py::test_controlled"]
    collection = next(event for event in events if event["event"] == "collection_finish")
    assert collection["evidence_selection"] == "ordinary"
    assert collection["provider_evidence"] == []
    assert receipt["deselected"] == ["test_case.py::test_provider"]


def test_explicit_provider_identity_requires_provider_selection_before_setup(tmp_path):
    process, output, _, _ = child(tmp_path, SELECTION, args=("test_case.py::test_provider",))
    assert process["returncode"] == 4
    assert "ci test --providers-only" in (output / "pytest.stderr").read_text()
    assert any(
        "ci test --providers-only" in reason for reason in classify_receipt(output)["stream_errors"]
    )
    assert not any(
        report.get("when") == "call"
        for node in classify_receipt(output)["nodes"].values()
        for report in node["reports"]
    )


def test_provider_selection_with_no_provider_identity_is_not_run(tmp_path):
    process, output, _, events = child(
        tmp_path,
        "def test_controlled():\n    raise AssertionError('outside provider scope')\n",
        args=("--qualification-evidence", "providers"),
    )
    assert process["returncode"] == 5
    receipt = classify_receipt(output)
    assert receipt["status"] == "not_run"
    assert receipt["selected"] == []
    collection = next(event for event in events if event["event"] == "collection_finish")
    assert collection["evidence_selection"] == "providers"
    assert collection["provider_evidence"] == []


def test_explicit_provider_excluded_by_keyword_is_not_required(tmp_path):
    process, output, _, _ = child(
        tmp_path,
        SELECTION,
        args=("test_case.py::test_provider", "-k", "controlled"),
    )
    assert process["returncode"] == 5
    assert classify_receipt(output)["selected"] == []


def test_provider_selection_refuses_fault_identities(tmp_path):
    process, output, _, _ = child(
        tmp_path,
        "import pytest\n@pytest.mark.shared_cluster_fault\n"
        "@pytest.mark.provider_evidence\ndef test_case():\n    pass\n",
        args=("--qualification-evidence", "providers"),
    )
    assert process["returncode"] == 4
    assert "incompatible with the exclusive fault lane" in (output / "pytest.stderr").read_text()


PREREQUISITES = """import pytest
from pathlib import Path
from test_prerequisites import mark_prerequisites

cache = {}
def missing(name):
    with Path("checks.txt").open("a") as stream:
        stream.write(name + "\\n")
    return "missing " + name

checks = {name: lambda name=name: missing(name) for name in ("first", "second")}
def pytest_collection_finish(session):
    mark_prerequisites(session.items, checks, cache)

@pytest.fixture
def scenario():
    Path("scenario-started").touch()
    raise AssertionError("missing prerequisites must skip before scenario setup")
"""

BLOCKED = """import pytest

@pytest.mark.provider_evidence
@pytest.mark.db
@pytest.mark.prerequisite("second")
@pytest.mark.prerequisite("first")
@pytest.mark.parametrize("case", ["one", "two"])
def test_provider(case, scenario):
    raise AssertionError("missing prerequisites must skip before call")

def test_controlled():
    pass
"""


def test_all_missing_prerequisites_are_preserved_before_any_scenario_fixture(tmp_path):
    process, output, case, events = child(
        tmp_path,
        BLOCKED,
        args=("--qualification-evidence", "providers"),
        conftest=PREREQUISITES,
    )
    assert process["returncode"] == 0
    assert not (case / "scenario-started").exists()
    assert (case / "checks.txt").read_text().splitlines() == ["first", "second"]
    receipt = classify_receipt(output)
    assert receipt["status"] == "blocked"
    assert len(receipt["selected"]) == 2
    expected = [
        {"name": "first", "reason": "missing first"},
        {"name": "second", "reason": "missing second"},
    ]
    for node in receipt["nodes"].values():
        assert node["status"] == "blocked"
        assert node["properties"]["qualification_prerequisites"] == expected
        assert node["reason"] == "first: missing first; second: missing second"
    collection = next(event for event in events if event["event"] == "collection_finish")
    assert collection["provider_evidence"] == collection["selected"]
    assert collection["native_required"] == collection["selected"]
    assert receipt["native_provenance"]["status"] == "no_claim"


def test_evidence_and_keyword_filters_precede_prerequisite_checks(tmp_path):
    process, output, case, _ = child(
        tmp_path,
        BLOCKED,
        args=("--qualification-evidence", "providers", "-k", "controlled"),
        conftest=PREREQUISITES,
    )
    assert process["returncode"] == 5
    assert not (case / "checks.txt").exists()
    assert not (case / "scenario-started").exists()
    assert classify_receipt(output)["selected"] == []


def test_unknown_prerequisite_is_a_collection_error(tmp_path):
    process, output, case, _ = child(
        tmp_path,
        'import pytest\n@pytest.mark.prerequisite("typo")\ndef test_case(scenario):\n    pass\n',
        conftest=PREREQUISITES,
    )
    assert process["returncode"] == 4
    assert "unknown prerequisite 'typo'" in (output / "pytest.stderr").read_text()
    assert not (case / "scenario-started").exists()


def test_aggregate_prerequisites_never_mask_failed_teardown():
    missing = [
        {"name": "first", "reason": "missing first"},
        {"name": "second", "reason": "missing second"},
    ]
    reports = [
        {
            "when": "setup",
            "outcome": "skipped",
            "user_properties": [
                ("qualification_prerequisites", missing),
                ("qualification_reason", "both missing"),
            ],
        },
        {"when": "teardown", "outcome": "failed"},
    ]
    node = _node_status(reports, started=True, finished=True)
    assert node["status"] == "failed"
    assert node["properties"]["qualification_prerequisites"] == missing
