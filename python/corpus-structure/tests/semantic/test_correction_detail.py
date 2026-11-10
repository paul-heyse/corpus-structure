"""Independent error trees, safe messages, paths and custody failure expectations."""

import json
from types import SimpleNamespace
from typing import cast

import pytest
from jsonschema import Draft202012Validator
from rdflib import RDF, BNode, Graph, Literal, Namespace
from rdflib.namespace import SH, XSD

from corpus_structure.semantic.correction_detail import (
    JsonErrorCapture,
    capture_json_errors,
    error_detail,
    graph_detail,
    shacl_path,
)
from corpus_structure.semantic.types import PreparedRelease


class CapturedFailure(ValueError):
    def __init__(self, message: str, capture: JsonErrorCapture):
        super().__init__(message)
        self.validation_capture = capture


def test_capture_single_iteration_preserves_union_causes_and_safe_values():
    schema = dict(
        type="object",
        properties={
            "secret": {"anyOf": [{"type": "integer"}, {"enum": ["accepted"]}]},
            "n": {"type": "integer"},
        },
    )
    capture = capture_json_errors(
        Draft202012Validator(schema), {"secret": "private-token", "n": "bad"}, detail=True
    )
    error = CapturedFailure("private-token", capture)
    detail, evidence = error_detail(error)
    assert detail["inventory_complete"]
    assert len(detail["nodes"]) == 4
    assert [n["parent"] for n in detail["nodes"]] == [None, 0, 0, None]
    assert detail["nodes"][1]["input_path"] == [{"kind": "field", "field": "secret"}]
    assert "private-token" not in json.dumps([detail, evidence])
    assert evidence["kind"] == "marker"
    raw, engine = error_detail(error, raw_evidence=True)
    assert "private-token" in json.dumps(raw)
    assert engine["kind"] == "inline" and engine["sensitivity"] == "raw"


def test_same_path_keyword_causes_keep_multiplicity_and_limit_coverage():
    validator = Draft202012Validator({"anyOf": [{"type": "integer"}, {"type": "boolean"}]})
    capture = capture_json_errors(validator, "x", detail=True)
    error = CapturedFailure("", capture)
    detail, _ = error_detail(error)
    assert [n["keyword"] for n in detail["nodes"]] == ["anyOf", "type", "type"]
    limited, _ = error_detail(error, max_errors=2)
    assert limited["inventory_complete"] and not limited["render_complete"]
    assert (
        capture_json_errors(
            Draft202012Validator({"items": {"type": "integer"}}), ["a", "b"], max_errors=1
        ).examined_count
        == 2
    )


def test_admitted_shacl_path_structure_and_cycle_refusal():
    from rdflib.collection import Collection

    n = Namespace("https://example.org/")
    graph, head, inverse = Graph(), BNode(), BNode()
    graph.add((inverse, SH.inversePath, n.p))
    Collection(graph, head, [n.q, inverse])
    assert shacl_path(graph, head) == {
        "status": "available",
        "path": {
            "kind": "sequence",
            "members": [
                {"kind": "predicate", "iri": str(n.q)},
                {"kind": "inverse", "member": {"kind": "predicate", "iri": str(n.p)}},
            ],
        },
    }
    graph.add((head, RDF.rest, head))
    assert shacl_path(graph, head)["status"] == "unsupported"
    unsupported = BNode()
    assert shacl_path(graph, unsupported)["status"] == "unsupported"


def test_graph_detail_typed_values_nested_result_and_raw_policy():
    graph, root, child = Graph(), BNode(), BNode()
    for node in (root, child):
        graph.add((node, RDF.type, SH.ValidationResult))
    graph.add((root, SH.detail, child))
    graph.add((root, SH.value, Literal("private", datatype=XSD.string)))
    graph.add((child, SH.detail, root))
    validation = SimpleNamespace(report=graph.serialize(format="nt").encode(), conforms=False)
    detail, evidence = graph_detail(validation)
    assert not detail["render_complete"]
    assert "private" not in json.dumps([detail, evidence])
    _, evidence = graph_detail(validation, raw_evidence=True)
    assert evidence["content"].encode() == validation.report


def test_payload_mapping_keeps_actual_errors_without_rerun():
    from corpus_structure.semantic.pdf_records import NativeMappingError, NativeSchemaMapping

    schema = {"type": "array", "items": {"type": "integer"}}
    mapping = NativeSchemaMapping(b"{}", schema, Draft202012Validator(schema), {})
    with pytest.raises(NativeMappingError) as caught:
        mapping.validate(["bad", "also bad"], detail=True)
    assert caught.value.validation_capture is not None
    assert len(caught.value.validation_capture.errors) == 2
    detail, _ = error_detail(caught.value)
    assert detail["nodes"][1]["input_path"] == [{"kind": "index", "index": 1}]


def test_retained_diagnostic_original_binding_and_byte_tampering(tmp_path):
    from corpus_structure.cli.diagnostic_artifacts import publish_diagnostic, read_diagnostic
    from corpus_structure.cli.managed import ResultError, ResultStore
    from corpus_structure.semantic.operation_reporting import validation_failure_report

    store = ResultStore(tmp_path / "results")
    error = next(Draft202012Validator({"type": "integer"}).iter_errors("private-token"))
    report = validation_failure_report(error, detail=True, release_id="release:original")
    with store.operation("test") as invocation:
        published = publish_diagnostic(invocation, report)
    assert published.model_dump(mode="json")["evidence"]["result_id"] == invocation.id
    restored = read_diagnostic(store, invocation.id)
    assert restored["report"]["release_id"] == "release:original"
    assert "private-token" not in json.dumps(restored)
    artifact = invocation.directory / "diagnostic-report.json"
    artifact.write_bytes(artifact.read_bytes().replace(b"release:original", b"release:tampered"))
    with pytest.raises(ResultError, match="digest"):
        read_diagnostic(store, invocation.id)


def test_retained_raw_requires_explicit_retrieval_opt_in(tmp_path):
    from corpus_structure.cli.diagnostic_artifacts import publish_diagnostic, read_diagnostic
    from corpus_structure.cli.managed import ResultError, ResultStore
    from corpus_structure.semantic.operation_reporting import validation_failure_report

    store = ResultStore(tmp_path / "results")
    error = next(Draft202012Validator({"type": "integer"}).iter_errors("private-token"))
    with store.operation("test") as invocation:
        publish_diagnostic(
            invocation, validation_failure_report(error, detail=True, raw_evidence=True)
        )
    with pytest.raises(ResultError, match="raw diagnostic retrieval"):
        read_diagnostic(store, invocation.id)
    assert "private-token" in json.dumps(read_diagnostic(store, invocation.id, raw_evidence=True))


def test_graph_input_iri_withheld_and_combined_budget():
    from rdflib import URIRef

    graph, result = Graph(), BNode()
    graph.add((result, RDF.type, SH.ValidationResult))
    secret = URIRef("https://example.org/secret?token=private-token")
    graph.add((result, SH.focusNode, secret))
    graph.add((result, SH.value, secret))
    validation = SimpleNamespace(report=graph.serialize(format="nt").encode(), conforms=False)
    detail, evidence = graph_detail(validation, max_bytes=1024)
    assert "private-token" not in json.dumps([detail, evidence])
    assert json.loads(detail["nodes"][0]["rdf_json"])["value"]["kind"] == "iri"
    assert json.loads(detail["nodes"][0]["rdf_json"])["value"]["withheld"]
    detail, evidence = graph_detail(validation, raw_evidence=True, max_bytes=1024)
    from corpus_structure.semantic.identity import canonical_bytes

    assert len(canonical_bytes(dict(correction_detail=detail, evidence=evidence))) <= 1024


@pytest.mark.parametrize(
    "options", [{"max_errors": 0}, {"max_errors": True}, {"max_depth": 17}, {"max_bytes": 1023}]
)
def test_graph_limits_are_validated_before_report_parse(options):
    with pytest.raises(ValueError):
        graph_detail(SimpleNamespace(report=b"not RDF", conforms=False), **options)


def test_cli_retention_preserves_failed_outcome_and_safe_outer_message(tmp_path):
    from typer.testing import CliRunner

    from corpus_structure.cli.app import app
    from corpus_structure.cli.diagnostic_artifacts import read_diagnostic
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.cli.output import CliState
    from corpus_structure.settings import Settings

    root = tmp_path / "results"
    result = CliRunner().invoke(
        app,
        [
            "schema",
            "compile",
            "--domain",
            "../outside",
            "--retain-diagnostics",
            "--correction-detail",
            "--json",
        ],
        obj=CliState(settings_factory=lambda: Settings(ci_results=root)),
    )
    assert result.exit_code == 1, result.output
    invocations = list(root.iterdir())
    invocation = next(p for p in invocations if p.is_dir())
    store = ResultStore(root)
    manifest = store.show(invocation.name)
    assert manifest.outcome == "failed"
    assert read_diagnostic(store, invocation.name)["report"]["complete"] is False


def test_safe_failure_envelope_does_not_reintroduce_wrapper_input():
    from corpus_structure.semantic.pdf_records import NativeMappingError
    from corpus_structure.semantic.refusals import semantic_refusal_report

    capture = capture_json_errors(
        Draft202012Validator({"type": "integer"}), "private-token", detail=True
    )
    error = NativeMappingError("#", "private-token", capture=capture)
    assert "private-token" not in json.dumps(semantic_refusal_report(error))


def test_raw_marker_still_requires_opt_in_when_raw_values_are_in_detail(tmp_path):
    from rdflib import URIRef

    from corpus_structure.cli.diagnostic_artifacts import publish_diagnostic, read_diagnostic
    from corpus_structure.cli.managed import ResultError, ResultStore
    from corpus_structure.semantic.ontology import GraphValidation
    from corpus_structure.semantic.operation_reporting import graph_validation_report

    graph, node = Graph(), BNode()
    graph.add((node, RDF.type, SH.ValidationResult))
    graph.add((node, SH.value, Literal("private-token")))
    graph.add((URIRef("urn:padding"), URIRef("urn:value"), Literal("x" * 2000)))
    validation = GraphValidation(False, graph.serialize(format="nt").encode(), "nonconformant")
    report = graph_validation_report(
        validation,
        prepared=cast(
            PreparedRelease, SimpleNamespace(release_id="release:original", execution_model_id=None)
        ),
        scope="supplied",
        detail=True,
        raw_evidence=True,
        max_bytes=1024,
    )
    assert report.model_dump(mode="json")["evidence"]["kind"] == "marker"
    store = ResultStore(tmp_path / "results")
    with store.operation("test") as invocation:
        publish_diagnostic(invocation, report)
    with pytest.raises(ResultError, match="raw diagnostic retrieval"):
        read_diagnostic(store, invocation.id)
    assert "private-token" in json.dumps(read_diagnostic(store, invocation.id, raw_evidence=True))


@pytest.mark.parametrize("raw", [False, True])
def test_preparation_diagnostics_share_safe_direct_retained_and_envelope_policy(tmp_path, raw):
    from corpus_structure.cli.diagnostic_artifacts import publish_diagnostic, read_diagnostic
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.semantic.operation_reporting import validation_failure_report
    from corpus_structure.semantic.refusals import FailureContext, safe_failure_message
    from corpus_structure.semantic.types import Diagnostic, PreparationError

    secret = "sentinel-private-value"
    error = PreparationError(
        (Diagnostic("invalid_type", "field/path", secret, actual=secret, expected=secret),)
    )
    report = validation_failure_report(error, detail=True, raw_evidence=raw)
    assert (secret in report.model_dump_json()) is raw
    assert (secret in safe_failure_message(error, context=FailureContext(raw_evidence=raw))) is raw
    store = ResultStore(tmp_path / "results")
    with store.operation("test") as invocation:
        publish_diagnostic(invocation, report)
    observed = read_diagnostic(store, invocation.id, raw_evidence=raw)
    assert (secret in json.dumps(observed)) is raw
    from corpus_structure.semantic.correction_detail import preparation_diagnostic

    assert (
        secret in json.dumps(preparation_diagnostic(error.diagnostics[0], raw_evidence=raw))
    ) is raw


@pytest.mark.parametrize("kind", ["GraphShapeError", "GraphExecutionError"])
def test_graph_engine_exception_messages_require_raw_opt_in(kind):
    from corpus_structure.semantic import ontology
    from corpus_structure.semantic.refusals import FailureContext, semantic_refusal_report

    error = getattr(ontology, kind)("input-secret-sentinel")
    safe = semantic_refusal_report(error)
    assert "input-secret-sentinel" not in json.dumps(safe)
    assert safe["validation"]["evidence"]["sensitivity"] == "safe"
    raw = semantic_refusal_report(error, context=FailureContext(raw_evidence=True))
    assert raw["message"] == "input-secret-sentinel"
