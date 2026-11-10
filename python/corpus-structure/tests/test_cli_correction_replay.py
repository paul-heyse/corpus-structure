"""Independent replay, disclosure, source custody and shared presentation expectations."""

import json
from hashlib import sha256
from io import StringIO
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from rich.console import Console

from corpus_structure.cli.correction_rendering import render_correction, render_exception
from corpus_structure.cli.diagnostic_artifacts import diagnostic_document, publish_diagnostic
from corpus_structure.cli.managed import ResultStore
from corpus_structure.semantic.correction_detail import capture_json_errors
from corpus_structure.semantic.diagnostic_selection import select_diagnostic
from corpus_structure.semantic.operation_reporting import validation_failure_report
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.types import SourceArtifact


class CapturedFailure(SemanticRefusal):
    def __init__(self):
        super().__init__("supplied invalid input")
        self.validation_capture = capture_json_errors(
            Draft202012Validator(
                {
                    "properties": {"choice": {"anyOf": [{"type": "integer"}, {"type": "boolean"}]}},
                    "required": ["other"],
                }
            ),
            {"choice": "private-input"},
            detail=True,
        )


def retained(tmp_path, *, raw=False):
    store = ResultStore(tmp_path)
    report = validation_failure_report(
        CapturedFailure(),
        detail=True,
        raw_evidence=raw,
        release_id="release:original",
        operation="original.operation",
    )
    source = SourceArtifact("supplied", b"name: supplied\nclasses:\n  Example: {}\n")
    with store.operation("schema.check") as result:
        publish_diagnostic(result, report, sources=(source,), raw_evidence=raw)
        result.settle("failed")
    return store, result, source


def test_replay_preserves_nested_multiplicity_original_binding_and_document(
    cli, tmp_path, monkeypatch
):
    _store, result, source = retained(tmp_path)

    def refuse(*args, **kwargs):
        pytest.fail("replay executed a producer")

    monkeypatch.setattr("corpus_structure.semantic.regeneration.prepare_release", refuse)
    monkeypatch.setattr(
        "corpus_structure.semantic.operation_reporting._validation_presentation", refuse
    )
    env = {"CORPUS_CI_RESULTS": str(tmp_path)}
    document = cli("schema", "diagnostic", result.id, "--json", env=env)
    assert document.exit_code == 0, document.output
    assert json.loads(document.stdout) == json.loads(
        (result.directory / "diagnostic-report.json").read_bytes()
    )
    correction = cli("schema", "diagnostic", result.id, "--view", "correction", "--json", env=env)
    assert correction.exit_code == 0, correction.output
    selected = json.loads(correction.stdout)
    report = selected["report"]
    assert report["release_id"] == "release:original"
    assert report["validation_outcome"] == "nonconformant"
    assert selected["invocation"]["outcome"] == "failed"
    nodes = report["correction_detail"]["nodes"]
    assert [node.get("parent") for node in nodes] == [None, 0, 0, None]
    assert [node["keyword"] for node in nodes] == ["anyOf", "type", "type", "required"]
    assert "private-input" not in correction.stdout
    assert selected["provenance"]["sources"][0]["digest"] == source.digest
    assert selected["provenance"]["sources"][0]["availability"] == "withheld"
    summary = cli("schema", "diagnostic", result.id, "--view", "summary", "--json", env=env)
    assert summary.exit_code == 0, summary.output
    operation_binding = json.loads(summary.stdout)["operation_bindings"]
    assert operation_binding == {
        "standing": "recorded",
        "basis": "captured_observations_only",
        "values": [{"operation": "original.operation", "scope": "boundary"}],
    }
    human = cli("schema", "diagnostic", result.id, env=env)
    assert human.exit_code == 0, human.output
    assert "Original-engine detail" in human.stdout and "original.operation" in human.stdout
    assert "Source contributors · unavailable" in human.stdout


def test_authenticated_source_excerpt_uses_retained_bytes_and_explicit_lines(
    cli, tmp_path, monkeypatch
):
    _store, result, source = retained(tmp_path, raw=True)
    monkeypatch.chdir(tmp_path)
    Path("supplied").write_text("changed checkout data")
    env = {"CORPUS_CI_RESULTS": str(tmp_path)}
    refused = cli("schema", "diagnostic", result.id, "--view", "summary", "--json", env=env)
    assert refused.exit_code == 1 and "raw diagnostic retrieval" in refused.output
    output = cli(
        "schema",
        "diagnostic",
        result.id,
        "--view",
        "correction",
        "--source",
        "supplied",
        "--source-line",
        "2",
        "--source-lines",
        "1",
        "--raw-evidence",
        "--json",
        env=env,
    )
    assert output.exit_code == 0, output.output
    excerpt = json.loads(output.stdout)["source_excerpt"]
    assert excerpt["digest"] == sha256(source.content).hexdigest()
    assert (excerpt["start_line"], excerpt["lines"], excerpt["content"]) == (2, 1, "classes:\n")
    assert "changed checkout" not in output.stdout
    assert excerpt["location_basis"].startswith("explicit source line")


def test_summary_and_omission_are_selected_without_changing_assessment(tmp_path):
    report = validation_failure_report(
        CapturedFailure(), detail=True, release_id="release:original"
    )
    document = diagnostic_document(report)
    selected = select_diagnostic(document, "correction", max_errors=2)
    assert len(selected["report"]["correction_detail"]["nodes"]) == 2
    assert selected["omissions"]
    assert not selected["report"]["presentation"]["render_complete"]
    assert selected["report"]["validation_outcome"] == "nonconformant"
    summary = select_diagnostic(document, "summary")
    assert "observations" not in summary["report"]
    stream = StringIO()
    Console(file=stream, width=32, color_system=None).print(render_correction(selected))
    assert "Omitted" in stream.getvalue() and "anyOf" in stream.getvalue()


def test_publication_or_render_failure_preserves_original_failure(cli, tmp_path, monkeypatch):
    from corpus_structure.cli import correction_rendering, diagnostic_artifacts
    from corpus_structure.semantic import regeneration

    def fail(*args, **kwargs):
        raise ValueError("secondary presentation defect")

    def prepare(*args, **kwargs):
        raise CapturedFailure()

    monkeypatch.setattr(regeneration, "acquire_packs", prepare)
    monkeypatch.setattr(diagnostic_artifacts, "publish_diagnostic", fail)
    monkeypatch.setattr(correction_rendering, "render_correction", fail)
    result = cli(
        "schema",
        "compile",
        "--retain-diagnostics",
        "--correction-detail",
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert result.exit_code == 1, result.output
    assert "Detailed correction unavailable" in result.stderr
    (manifest,) = ResultStore(tmp_path).list(None, 20, None).results
    assert manifest.outcome == "failed" and manifest.settled is not None
    assert "secondary presentation defect" not in result.stderr


def test_owned_grouped_exception_presentation_keeps_notes_and_omissions():
    from corpus_structure.cli.exception_observations import (
        ExceptionFrame,
        ExceptionStack,
        ExceptionTrace,
        OmittedExceptionDetail,
    )

    trace = ExceptionTrace(
        stacks=(
            ExceptionStack(
                exc_type="ExceptionGroup",
                exc_value="group",
                is_group=True,
                exc_notes=("operator note",),
                exceptions=(
                    ExceptionTrace(
                        stacks=(
                            ExceptionStack(
                                exc_type="ValueError",
                                exc_value="child",
                                is_cause=True,
                                frames=(
                                    ExceptionFrame(
                                        filename="producer.py", lineno=7, name="produce"
                                    ),
                                ),
                            ),
                        )
                    ),
                    OmittedExceptionDetail(path="$.children[1]", reason="child bound"),
                ),
            ),
        )
    )
    stream = StringIO()
    Console(file=stream, width=50, color_system=None).print(
        render_exception(trace, invocation="original", stage="stage")
    )
    text = stream.getvalue()
    assert all(
        value in text
        for value in (
            "original",
            "operator note",
            "ValueError",
            "producer.py:7",
            "child bound",
            "cause",
        )
    )
    assert "locals" not in text and "Validation" not in text


def test_failed_compile_retains_once_acquired_source_then_rechecks(cli, tmp_path, monkeypatch):
    import shutil

    import yaml

    from corpus_structure.cli.recipes import checkout
    from corpus_structure.semantic import regeneration

    pack = tmp_path / "domains" / "broken"
    shutil.copytree(checkout() / "domains/toy", pack)
    path = pack / "semantic.yaml"
    original = path.read_bytes()
    invalid = yaml.safe_load(original)
    invalid["slots"]["owns"]["range"] = "MissingTargetClass"
    path.write_text(yaml.safe_dump(invalid))
    diagnosed = path.read_bytes()
    acquired = []
    actual = regeneration.acquire_packs

    def acquire(*args, **kwargs):
        value = actual(*args, **kwargs)
        acquired.append(value[0])
        return value

    monkeypatch.setattr(regeneration, "acquire_packs", acquire)
    env = {"CORPUS_CI_RESULTS": str(tmp_path / "results")}
    failed = cli(
        "schema",
        "compile",
        "--domains",
        str(pack.parent),
        "--domain",
        "broken",
        "--retain-diagnostics",
        "--correction-detail",
        "--raw-evidence",
        "--json",
        env=env,
    )
    assert failed.exit_code == 1, failed.output
    assert len(acquired) == 1
    (manifest,) = ResultStore(tmp_path / "results").list(None, 20, None).results
    assert manifest.outcome == "failed"
    path.write_bytes(original)
    replay = cli(
        "schema",
        "diagnostic",
        manifest.id,
        "--view",
        "correction",
        "--raw-evidence",
        "--source",
        "toy_semantic",
        "--json",
        env=env,
    )
    assert replay.exit_code == 0, replay.output
    selected = json.loads(replay.stdout)
    assert selected["source_excerpt"]["digest"] == sha256(diagnosed).hexdigest()
    assert selected["source_excerpt"]["content"] == "".join(
        diagnosed.decode().splitlines(keepends=True)[:20]
    )
    assert len(acquired) == 1
    rechecked = cli(
        "schema", "check", "--domains", str(pack.parent), "--domain", "broken", "--json", env=env
    )
    assert rechecked.exit_code == 0, rechecked.output
    assert len(acquired) == 2


def test_expired_retained_diagnostic_is_unavailable_without_producer_execution(
    cli, tmp_path, monkeypatch
):
    from corpus_structure.cli import managed

    store, result, _source = retained(tmp_path)
    deadline = result.manifest.expiry() + 1
    # Expiry authorizes the managed owner to collect; reads are valid until collection.
    assert result.id in store.collect(apply=True, now=deadline).removed
    monkeypatch.setattr(managed.time, "time", lambda: deadline)
    output = cli(
        "schema",
        "diagnostic",
        result.id,
        "--view",
        "correction",
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert output.exit_code == 1, output.output
    assert "expired" in output.stdout


def test_oversized_identity_is_omitted_by_ordinal_without_shortening():
    from corpus_structure.semantic.identity import canonical_bytes

    long_name = "exact-field-" + "x" * 5000
    validator = Draft202012Validator({"properties": {long_name: {"type": "integer"}}})
    error = next(validator.iter_errors({long_name: "wrong"}))
    report = validation_failure_report(error, detail=True)
    selected = select_diagnostic(diagnostic_document(report), "correction", max_bytes=2048)
    assert len(canonical_bytes(selected)) <= 2048
    assert selected["report"]["validation_outcome"] == "nonconformant"
    assert selected["report"]["correction_detail"]["nodes"] == []
    assert selected["omissions"][0]["first_omitted_ordinal"] == 0
    assert "exact-field-" not in json.dumps(selected)


def test_unknown_report_decoder_refuses_even_authenticated_publication(cli, tmp_path):
    from corpus_structure.semantic.identity import canonical_bytes

    report = validation_failure_report(CapturedFailure(), detail=True)
    document = diagnostic_document(report)
    document["report"]["report_version"] = 999
    content = canonical_bytes(document)
    with ResultStore(tmp_path).operation("old-diagnostic") as result:
        artifact = result.directory / "diagnostic-report.json"
        artifact.write_bytes(content)
        result.publish("diagnostic-report", artifact)
        result.stage("published", diagnostic_sha256=sha256(content).hexdigest())
    output = cli(
        "schema", "diagnostic", result.id, "--json", env={"CORPUS_CI_RESULTS": str(tmp_path)}
    )
    assert output.exit_code == 1, output.output
    assert "malformed or corrupt" in output.stdout


def test_summary_keeps_multiple_or_unknown_recorded_operation_scopes_honest():
    report = validation_failure_report(CapturedFailure(), detail=True).model_dump(
        mode="json", exclude_none=True
    )
    report["observations"][0].update(operation="first", scope="alpha")
    report["observations"][1].update(operation="second", scope="beta")
    selected = select_diagnostic(dict(version=1, report=report, members=[]), "summary")
    assert selected["operation_bindings"]["standing"] == "multiple"
    assert selected["operation_bindings"]["values"] == [
        {"operation": "first", "scope": "alpha"},
        {"operation": "second", "scope": "beta"},
    ]
    for observation in report["observations"]:
        observation.pop("operation", None)
    unknown = select_diagnostic(dict(version=1, report=report, members=[]), "summary")
    assert unknown["operation_bindings"]["standing"] == "unavailable"
    assert unknown["operation_bindings"]["basis"] == "captured_observations_only"
    assert all(value["operation"] is None for value in unknown["operation_bindings"]["values"])


def test_genuine_shacl_sequence_path_uses_shared_selection_and_literal_render():
    from rdflib import Graph

    from corpus_structure.semantic.ontology import validate_graph
    from corpus_structure.semantic.operation_reporting import graph_validation_report
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import SourceBundle

    prepared = prepare_release(
        SourceBundle(
            "source",
            (
                SourceArtifact(
                    "source",
                    b"id: https://example.test/model\nname: source\n"
                    b"prefixes: {ex: 'https://example.test/'}\n"
                    b"default_prefix: ex\nclasses: {Item: {}}\n",
                ),
            ),
        )
    )
    data = Graph().parse(
        data="""@prefix ex: <https://example.test/> .
ex:item ex:parent ex:parentItem . ex:parentItem ex:value "bad" .""",
        format="turtle",
    )
    shapes = Graph().parse(
        data="""@prefix ex: <https://example.test/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:Shape a sh:NodeShape; sh:targetNode ex:item; sh:property ex:Property .
ex:Property sh:path (ex:parent ex:value); sh:datatype xsd:integer .""",
        format="turtle",
    )
    validation = validate_graph(data, shapes)
    assert validation.conforms is False
    report = graph_validation_report(
        validation,
        prepared=prepared,
        scope="original-qualified-projection",
        detail=True,
        raw_evidence=True,
    )
    selected = select_diagnostic(diagnostic_document(report), "correction", raw_evidence=True)
    body = selected["report"]
    assert body["release_id"] == prepared.release_id
    assert body["validation_outcome"] == "nonconformant"
    assert body["evidence"]["digest"] == sha256(validation.report).hexdigest()
    (node,) = body["correction_detail"]["nodes"]
    assert json.loads(node["path_json"]) == {
        "status": "available",
        "path": {
            "kind": "sequence",
            "members": [
                {"kind": "predicate", "iri": "https://example.test/parent"},
                {"kind": "predicate", "iri": "https://example.test/value"},
            ],
        },
    }
    facts = json.loads(node["rdf_json"])
    assert facts["focus"]["value"] == "https://example.test/item"
    assert facts["source_shape"]["value"] == "https://example.test/Property"
    assert facts["severity"]["value"] == "http://www.w3.org/ns/shacl#Violation"
    assert facts["value"]["kind"] == "literal" and facts["value"]["value"] == "bad"
    assert selected["operation_bindings"]["values"][0]["scope"] == "original-qualified-projection"
    stream = StringIO()
    Console(file=stream, width=100, color_system=None).print(render_correction(selected))
    text = stream.getvalue()
    assert "nonconformant" in text and "sequence" in text and "parent" in text
