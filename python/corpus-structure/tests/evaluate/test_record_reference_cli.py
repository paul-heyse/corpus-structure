"""Controlled CLI mechanics; these connections do not establish native database behavior."""

from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from corpus_structure.cli import eval as evaluation
from corpus_structure.cli import golden
from corpus_structure.cli.failures import failure_boundary
from corpus_structure.evaluate import record_references as records
from corpus_structure.evaluate import semantic
from corpus_structure.evaluate.record_alignment import RecordEvaluationFrame
from corpus_structure.semantic.proposals import ProposalFrame


@pytest.fixture
def reference_connection(monkeypatch):
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.one_or_none.return_value = {
        "id": 4,
        "project_id": "selected",
        "sampling": {"record_protocol": records.PROTOCOL},
    }

    @contextmanager
    def session(ctx, project=None, *, json=False):
        with failure_boundary(json, expected=(semantic.ReferenceError,)):
            yield conn, project or "selected"

    monkeypatch.setattr(golden, "reference_session", session)
    monkeypatch.setattr(evaluation, "reference_session", session)
    monkeypatch.setattr(semantic, "_unit", lambda *a: {"project_id": "selected", "set_id": 4})
    monkeypatch.setattr(records, "_unit", lambda *a: {"project_id": "selected", "set_id": 4})
    return conn


@pytest.fixture
def record_frame():
    return RecordEvaluationFrame(
        unit="source-unit",
        release_id="frozen-release",
        guideline_version="guideline-1",
        reference_policy_version="reference-1",
        prediction_policy_version="prediction-1",
        pin={"source_view_id": 7},
        anchor_ids=frozenset(),
    )


def test_origin_forwards_attested_membership(cli, monkeypatch, tmp_path, reference_connection):
    provenance = tmp_path / "origin.json"
    provenance.write_text('{"attestation":"operator selected common origin"}')
    assign = MagicMock()
    monkeypatch.setattr(records, "assign_origin", assign)
    result = cli(
        "golden",
        "record-origin",
        "--origin-group",
        "origin-1",
        "--partition",
        "development",
        "--source-uri",
        "source:a",
        "--source-uri",
        "source:b",
        "--provenance",
        str(provenance),
        "--json",
    )
    assert result.exit_code == 0, (result.output, result.exception)
    assign.assert_called_once_with(
        reference_connection,
        project_id="selected",
        origin_group="origin-1",
        partition="development",
        source_uris=["source:a", "source:b"],
        provenance={"attestation": "operator selected common origin"},
    )


def create_arguments(tmp_path, record_frame):
    sample = tmp_path / "sample.json"
    sample.write_text(
        json.dumps(
            {
                "unit_keys": ["source-unit"],
                "sampling": {
                    "seed": 42,
                    "strata": {"source-unit": "empty"},
                    "inclusion_probabilities": {"source-unit": 1},
                    "provenance": {"author": "operator"},
                    "cohort": "representative",
                },
                "frames": {"source-unit": records.encode_frame(record_frame)},
                "captured_coordinates": {"source-unit": [{"pointer": "/paragraph/1"}]},
                "context_dependency_digests": {"source-unit": "a" * 64},
            }
        )
    )
    guideline = tmp_path / "guideline.txt"
    guideline.write_text("Exact independent guideline.\n")
    return [
        "golden",
        "record-create",
        "--from-run",
        "8",
        "--source-cut",
        "9",
        "--label",
        "independent",
        "--split",
        "dev",
        "--guideline",
        "guideline-1",
        "--guideline-text",
        str(guideline),
        "--partition",
        "development",
        "--reference-policy",
        "reference-1",
        "--prediction-policy",
        "prediction-1",
        "--sample",
        str(sample),
        "--json",
    ], sample


def test_create_forwards_frozen_inputs(
    cli, monkeypatch, tmp_path, reference_connection, record_frame
):
    arguments, sample = create_arguments(tmp_path, record_frame)
    create = MagicMock(return_value={"set_id": 4})
    monkeypatch.setattr(records, "create_reference_set", create)
    result = cli(*arguments)
    assert result.exit_code == 0, (result.output, result.exception)
    assert json.loads(result.stdout) == {"set_id": 4}
    payload = json.loads(sample.read_text())
    create.assert_called_once_with(
        reference_connection,
        project_id="selected",
        source_run_id=8,
        source_cut_id=9,
        label="independent",
        legacy_split="dev",
        guideline="guideline-1",
        guideline_text="Exact independent guideline.\n",
        partition="development",
        unit_keys=["source-unit"],
        sampling=payload["sampling"],
        frames={"source-unit": record_frame},
        reference_policy_version="reference-1",
        prediction_policy_version="prediction-1",
        captured_coordinates=payload["captured_coordinates"],
        context_dependency_digests=payload["context_dependency_digests"],
    )


@pytest.mark.parametrize("missing", ["unit_keys", "sampling", "frames"])
def test_missing_sample_input_is_refused(
    cli, monkeypatch, tmp_path, reference_connection, record_frame, missing
):
    arguments, sample = create_arguments(tmp_path, record_frame)
    payload = json.loads(sample.read_text())
    del payload[missing]
    sample.write_text(json.dumps(payload))
    create = MagicMock()
    monkeypatch.setattr(records, "create_reference_set", create)
    result = cli(*arguments)
    assert result.exit_code == 1
    assert "sample requires" in json.loads(result.stdout)["error"]["message"]
    create.assert_not_called()


def test_source_cut_is_required_before_opening_session(cli, monkeypatch, tmp_path, record_frame):
    arguments, _ = create_arguments(tmp_path, record_frame)
    index = arguments.index("--source-cut")
    del arguments[index : index + 2]
    opened = MagicMock(side_effect=AssertionError("session opened"))
    monkeypatch.setattr(golden, "reference_session", opened)
    result = cli(*arguments)
    assert result.exit_code == 2
    assert "--source-cut" in result.output
    opened.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sampling", None),
        ("unit_keys", [["source-unit"]]),
        ("captured_coordinates", [1]),
        ("captured_coordinates", {"source-unit": [1]}),
        ("context_dependency_digests", ["digest"]),
        ("context_dependency_digests", {"source-unit": 1}),
        ("frames", [1]),
        ("frames", {"source-unit": None}),
    ],
)
def test_malformed_sample_shape_is_refused_before_service(
    cli, monkeypatch, tmp_path, reference_connection, record_frame, field, value
):
    arguments, sample = create_arguments(tmp_path, record_frame)
    payload = json.loads(sample.read_text())
    payload[field] = value
    sample.write_text(json.dumps(payload))
    create = MagicMock()
    monkeypatch.setattr(records, "create_reference_set", create)
    result = cli(*arguments)
    assert result.exit_code == 1
    error = json.loads(result.stdout)["error"]
    assert error["code"] == "ReferenceError"
    assert field in error["message"]
    create.assert_not_called()


def test_non_object_sampling_probabilities_are_refused_before_service(
    cli, monkeypatch, tmp_path, reference_connection, record_frame
):
    arguments, sample = create_arguments(tmp_path, record_frame)
    payload = json.loads(sample.read_text())
    payload["sampling"]["inclusion_probabilities"] = None
    sample.write_text(json.dumps(payload))
    create = MagicMock()
    monkeypatch.setattr(records, "create_reference_set", create)
    result = cli(*arguments)
    assert result.exit_code == 1
    assert "inclusion_probabilities" in json.loads(result.stdout)["error"]["message"]
    create.assert_not_called()


@pytest.mark.parametrize("invalid_pin", [None, ["source_view_id", 7]])
def test_submit_refuses_non_object_record_pin_before_service(
    cli, monkeypatch, tmp_path, reference_connection, record_frame, invalid_pin
):
    authored, frame = tmp_path / "answer.json", tmp_path / "frame.json"
    authored.write_text("{}")
    value = records.encode_frame(record_frame)
    value["evaluation_frame"]["pin"] = invalid_pin
    frame.write_text(json.dumps(value))
    record = MagicMock()
    monkeypatch.setattr(records, "record_pass", record)
    result = cli(
        "golden",
        "submit",
        "--unit",
        "5",
        "--pass",
        "A",
        "--actor",
        "a",
        "--authored",
        str(authored),
        "--frame",
        str(frame),
        "--json",
    )
    assert result.exit_code == 1
    error = json.loads(result.stdout)["error"]
    assert error["code"] == "ReferenceError"
    assert "pin" in error["message"]
    record.assert_not_called()


@pytest.mark.parametrize("protocol", [records.PROTOCOL, None])
def test_submit_uses_stored_protocol_and_preserves_exact_authored_bytes(
    cli, monkeypatch, tmp_path, reference_connection, record_frame, protocol
):
    reference_connection.execute.return_value.mappings.return_value.one_or_none.return_value = {
        "project_id": "selected",
        "sampling": {"record_protocol": protocol},
    }
    authored = tmp_path / "answer.json"
    # Submitted family labels never select the protocol.
    exact = (
        b'{ "family": "Agent" , "records": [] }\n' if protocol else b'{"family":"source_records"}\n'
    )
    authored.write_bytes(exact)
    frame = tmp_path / "frame.json"
    frame.write_text(
        json.dumps(
            records.encode_frame(record_frame)
            if protocol
            else {"unit_ref": "source-unit", "text": "Independent source", "sentences": []}
        )
    )
    legacy, record = MagicMock(return_value=10), MagicMock(return_value=11)
    monkeypatch.setattr(semantic, "record_pass", legacy)
    monkeypatch.setattr(records, "record_pass", record)
    result = cli(
        "golden",
        "submit",
        "--unit",
        "5",
        "--pass",
        "A",
        "--actor",
        "independent-A",
        "--authored",
        str(authored),
        "--frame",
        str(frame),
        "--json",
    )
    assert result.exit_code == 0, (result.output, result.exception)
    selected, other = (record, legacy) if protocol else (legacy, record)
    selected.assert_called_once()
    other.assert_not_called()
    assert selected.call_args.kwargs["authored"] == exact
    assert selected.call_args.kwargs["frame"] == (
        record_frame if protocol else ProposalFrame("source-unit", "Independent source", ())
    )
    assert json.loads(result.stdout)["pass_id"] == (11 if protocol else 10)


@pytest.mark.parametrize("protocol", [records.PROTOCOL, None])
def test_eval_routes_from_stored_protocol(cli, monkeypatch, reference_connection, protocol):
    reference_connection.execute.return_value.mappings.return_value.one_or_none.return_value = {
        "project_id": "selected",
        "sampling": {"record_protocol": protocol},
    }
    legacy = MagicMock(return_value={"family": "Agent"})
    record = MagicMock(return_value={"family": "source_records"})
    monkeypatch.setattr(semantic, "reference_evaluate", legacy)
    monkeypatch.setattr(records, "reference_evaluate", record)
    result = cli("eval", "run", "--run", "8", "--set-id", "4", "--json")
    assert result.exit_code == 0, (result.output, result.exception)
    selected, other = (record, legacy) if protocol else (legacy, record)
    selected.assert_called_once_with(
        reference_connection, project_id="selected", run_id=8, set_id=4
    )
    other.assert_not_called()


@pytest.mark.parametrize("pass_kind", ["A", "B", "C"])
def test_packet_routes_c_separately_and_preserves_retained_json(
    cli, monkeypatch, reference_connection, pass_kind
):
    author = MagicMock(return_value={"source": "frozen-source"})
    adjudicate = MagicMock(
        return_value={
            "source": {"source": "frozen-source"},
            "adjudication_passes": [10, 11],
            "authors": [{"pass_id": 10, "authored": b'{ "reason": "independent" }\n'}],
            "disagreement": {"pass_a": 10, "pass_b": 11},
        }
    )
    monkeypatch.setattr(records, "author_packet", author)
    monkeypatch.setattr(records, "adjudication_packet", adjudicate)
    result = cli("golden", "record-packet", "--unit", "5", "--pass", pass_kind, "--json")
    assert result.exit_code == 0, (result.output, result.exception)
    if pass_kind == "C":
        author.assert_not_called()
        adjudicate.assert_called_once_with(reference_connection, 5)
        packet = json.loads(result.stdout)
        assert packet["authors"][0]["authored"] == '{ "reason": "independent" }\n'
        assert packet["adjudication_passes"] == [10, 11]
    else:
        author.assert_called_once_with(reference_connection, 5)
        adjudicate.assert_not_called()


@pytest.mark.parametrize("command", ["submit", "packet", "eval"])
def test_wrong_project_never_dispatches(cli, monkeypatch, tmp_path, reference_connection, command):
    reference_connection.execute.return_value.mappings.return_value.one_or_none.return_value = {
        "project_id": "another",
        "sampling": {"record_protocol": records.PROTOCOL},
    }
    dispatch = MagicMock()
    for name in ("record_pass", "author_packet", "adjudication_packet", "reference_evaluate"):
        monkeypatch.setattr(records, name, dispatch)
    monkeypatch.setattr(semantic, "record_pass", dispatch)
    monkeypatch.setattr(semantic, "reference_evaluate", dispatch)
    authored, frame = tmp_path / "answer.json", tmp_path / "frame.json"
    authored.write_text("{}")
    frame.write_text("{}")
    arguments = {
        "submit": [
            "golden",
            "submit",
            "--unit",
            "5",
            "--pass",
            "A",
            "--actor",
            "a",
            "--authored",
            str(authored),
            "--frame",
            str(frame),
        ],
        "packet": ["golden", "record-packet", "--unit", "5", "--pass", "C"],
        "eval": ["eval", "run", "--run", "8", "--set-id", "4"],
    }[command]
    result = cli(*arguments, "--json")
    assert result.exit_code == 1
    assert "another project" in json.loads(result.stdout)["error"]["message"]
    dispatch.assert_not_called()


@pytest.mark.parametrize("protocol", [None, "future-unsupported-protocol"])
def test_packet_refuses_non_record_set(cli, monkeypatch, reference_connection, protocol):
    reference_connection.execute.return_value.mappings.return_value.one_or_none.return_value = {
        "project_id": "selected",
        "sampling": {"record_protocol": protocol},
    }
    packet = MagicMock()
    monkeypatch.setattr(records, "author_packet", packet)
    result = cli("golden", "record-packet", "--unit", "5", "--pass", "A", "--json")
    assert result.exit_code == 1
    assert "protocol" in json.loads(result.stdout)["error"]["message"]
    packet.assert_not_called()
