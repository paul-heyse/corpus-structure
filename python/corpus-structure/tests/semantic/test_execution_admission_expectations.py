"""Revision-local expectation resolution, independent of historical native payload health."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from corpus_structure.semantic.execution_admission import (
    ExecutionAdmissionError,
    NativeExpectation,
    _expectations,
    _revision_expectation,
)


def revision(root: Path, name: str, predecessor: str | None, *, frozen: bool = False):
    body = "BEGIN RETURN 'admitted'; END"
    descriptor = {
        "physical_id": "independent-physical-model",
        "views": [{"relation": "data.selected_fact", "query": "SELECT 17 AS value"}],
        "functions": [{"signature": "data.guard_execution_admission()", "body_sha256": "a" * 64}],
    }
    descriptor_body = "SELECT '" + json.dumps(descriptor) + "'::jsonb"
    sql = (
        "CREATE FUNCTION data.execution_contract_descriptor() RETURNS jsonb LANGUAGE sql "
        f"AS $descriptor${descriptor_body}$descriptor$;\n"
        "CREATE FUNCTION data.require_execution_release(text) RETURNS text LANGUAGE plpgsql "
        f"AS $guard${body}$guard$;\n"
    ).encode()
    declaration = f"revision = {name!r}\ndown_revision = {predecessor!r}\n"
    if frozen:
        for kind, filename, payload in (
            ("ADMISSION", name + "_admission.sql", sql),
            ("STATE", name + "_native.json", b'{"objects": []}'),
        ):
            (root / filename).write_bytes(payload)
            declaration += (
                f"NATIVE_{kind}_FILE = {filename!r}\n"
                f"NATIVE_{kind}_SHA256 = {sha256(payload).hexdigest()!r}\n"
            )
    (root / (name + ".py")).write_text(declaration)
    return NativeExpectation(
        (sha256(descriptor_body.encode()).hexdigest(), sha256(body.encode()).hexdigest()),
        "independent-physical-model",
        "a" * 64,
        "SELECT 17 AS value",
        (root / (name + "_native.json"), sha256(b'{"objects": []}').hexdigest()),
        body,
    )


def test_current_and_inherited_expectations_preserve_frozen_meaning(tmp_path):
    revision(tmp_path, "base", None)
    expected = revision(tmp_path, "frozen", "base", frozen=True)
    revision(tmp_path, "child", "frozen")
    assert _revision_expectation(tmp_path, "frozen") == expected
    assert _revision_expectation(tmp_path, "child") == expected
    assert _expectations(tmp_path) == {"frozen": expected, "child": expected}


def test_explicit_revision_never_opens_unrelated_admission_or_state(tmp_path, monkeypatch):
    expected = revision(tmp_path, "selected", None, frozen=True)
    revision(tmp_path, "unrelated", None, frozen=True)
    (tmp_path / "unrelated_admission.sql").write_bytes(b"malformed admission")
    (tmp_path / "unrelated_native.json").write_bytes(b"malformed state")
    read_bytes = Path.read_bytes

    def guarded(path, *args, **kwargs):
        if path.name.startswith("unrelated_"):
            pytest.fail(f"unrelated payload opened: {path.name}")
        return read_bytes(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    assert _revision_expectation(tmp_path, "selected") == expected
    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(ExecutionAdmissionError, match="digest differs"):
        _expectations(tmp_path)


@pytest.mark.parametrize("failure", ["digest", "payload", "unsafe_path", "missing_state"])
def test_selected_artifact_refuses_corruption_and_unsafe_metadata(tmp_path, failure):
    revision(tmp_path, "selected", None, frozen=True)
    declaration = tmp_path / "selected.py"
    if failure in {"digest", "payload"}:
        payload = b"invalid SQL"
        (tmp_path / "selected_admission.sql").write_bytes(payload)
        if failure == "payload":
            text = declaration.read_text()
            lines = [
                f"NATIVE_ADMISSION_SHA256 = {sha256(payload).hexdigest()!r}"
                if line.startswith("NATIVE_ADMISSION_SHA256")
                else line
                for line in text.splitlines()
            ]
            declaration.write_text("\n".join(lines))
    elif failure == "unsafe_path":
        declaration.write_text(
            declaration.read_text().replace("selected_native.json", "../outside.json")
        )
    else:
        (tmp_path / "selected_native.json").unlink()
    with pytest.raises(ExecutionAdmissionError):
        _revision_expectation(tmp_path, "selected")


@pytest.mark.parametrize(
    "failure", ["duplicate", "nonliteral", "predecessor", "incomplete", "duplicate_field"]
)
def test_malformed_revision_metadata_refuses_even_when_unrelated(tmp_path, failure):
    revision(tmp_path, "selected", None, frozen=True)
    malformed = tmp_path / "other.py"
    malformed.write_text(
        {
            "duplicate": "revision='selected'\ndown_revision=None\n",
            "nonliteral": "revision=compute_revision()\ndown_revision=None\n",
            "predecessor": "revision='other'\ndown_revision=17\n",
            "incomplete": "revision='other'\ndown_revision=None\nNATIVE_STATE_FILE='other.json'\n",
            "duplicate_field": "revision='other'\nrevision='again'\ndown_revision=None\n",
        }[failure]
    )
    with pytest.raises(ExecutionAdmissionError):
        _revision_expectation(tmp_path, "selected")


@pytest.mark.parametrize("failure", ["missing", "cycle", "unavailable"])
def test_inheritance_refuses_when_no_expectation_can_be_resolved(tmp_path, failure):
    if failure == "cycle":
        revision(tmp_path, "selected", "other")
        revision(tmp_path, "other", "selected")
    elif failure == "missing":
        revision(tmp_path, "selected", "absent")
    else:
        revision(tmp_path, "selected", None)
    with pytest.raises(ExecutionAdmissionError):
        _revision_expectation(tmp_path, "selected")


def test_selected_payload_and_metadata_caches_follow_file_identity(tmp_path):
    expected = revision(tmp_path, "selected", None, frozen=True)
    assert _revision_expectation(tmp_path, "selected") == expected
    (tmp_path / "selected_admission.sql").write_bytes(b"changed payload")
    with pytest.raises(ExecutionAdmissionError, match="digest differs"):
        _revision_expectation(tmp_path, "selected")
    revision(tmp_path, "selected", None, frozen=True)
    assert _revision_expectation(tmp_path, "selected") == expected
    (tmp_path / "selected.py").write_text("revision='selected'\ndown_revision='absent'\n")
    with pytest.raises(ExecutionAdmissionError, match="predecessor"):
        _revision_expectation(tmp_path, "selected")
