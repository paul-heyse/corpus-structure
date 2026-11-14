"""Ordinary source commands preserve operator choices and use native demand custody."""

import json

import pytest

from corpus_structure.cli import demands
from corpus_structure.orchestrate.source_request import NamedScope


@pytest.mark.parametrize(
    "command,workflow", [("run", "phase0"), ("ingest", "capture"), ("regenerate", "phase0")]
)
def test_ordinary_source_flags_reach_native_service_without_graph_or_registry(
    cli, tmp_path, monkeypatch, command, workflow
):
    calls = []
    monkeypatch.setattr(demands, "execute_request", lambda ctx, **values: calls.append(values))
    result = cli(
        command,
        "--source-root",
        str(tmp_path),
        "--project",
        "p",
        "--semantic-release",
        "r",
        "--runtime",
        "t",
        "--domain",
        "toy",
        "--scope",
        "one",
        "--source-membership",
        "direct",
        "--document",
        "book",
        "--target",
        "text.formal_evidence/source-native",
        "--json",
    )
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    request = calls[0]["source_request"]
    assert request.workflow == workflow and request.project_id == "p"
    assert request.release_id == "r" and request.runtime_id == "t"
    assert request.domain == "toy" and request.selection == NamedScope("one")
    assert request.membership == "direct" and request.documents == ("book",)
    assert request.targets == ("text.formal_evidence/source-native",)
    assert calls[0]["source_root"] == tmp_path
    assert "graph" not in calls[0] and "registry_for" not in calls[0]


@pytest.mark.parametrize("command", [("run", "resume"), ("regenerate",)])
def test_recovery_selects_only_exact_native_demand(cli, tmp_path, monkeypatch, command):
    calls = []
    monkeypatch.setattr(demands, "execute_request", lambda ctx, **values: calls.append(values))
    identity = ("demand:one",) if command == ("run", "resume") else ("--demand", "demand:one")
    result = cli(*command, *identity, "--source-root", str(tmp_path), "--project", "p", "--json")
    assert result.exit_code == 0, result.output
    assert calls[0]["demand"] == "demand:one" and calls[0]["project"] == "p"
    assert "resume_run" not in calls[0] and "source_request" not in calls[0]


@pytest.mark.parametrize("action", ["parsers", "interpret"])
def test_parser_and_interpretation_requests_preserve_exact_declared_questions(
    cli, tmp_path, monkeypatch, action
):
    calls = []
    monkeypatch.setattr(demands, "execute_request", lambda ctx, **values: calls.append(values))
    source = tmp_path / "request.json"
    source.write_text(
        json.dumps(
            {
                "project_id": "p",
                "release_id": "r",
                "runtime_id": "t",
                "roots": [
                    {
                        "subject": "source",
                        "original_source": "book",
                        "analyzed_scope": {"start": 3, "end": 9},
                    }
                ],
                "targets": ["text.d1_source/source-native"],
                "execution_profile": "cuda-bfloat16",
                "selections": [
                    {
                        "operation": "text.d1_source/source-native",
                        "parameters": {
                            "family": "source-question",
                            "question": {"text": "Copy the retained numeral."},
                        },
                    }
                ],
            }
        )
    )
    result = cli("run", action, "--request", str(source), "--source-root", str(tmp_path), "--json")
    assert result.exit_code == 0, result.output
    request = calls[0]["request"]
    assert request.roots[0].analyzed_scope == {"start": 3, "end": 9}
    assert request.selections[0].parameters["question"] == {"text": "Copy the retained numeral."}
    assert request.execution_profile == "cuda-bfloat16" and request.runtime_id == "t"
