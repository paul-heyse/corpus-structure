"""Independent error trees, safe messages, paths and custody failure expectations."""

import json
from types import SimpleNamespace
from typing import Never, cast

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


def _unexpected_scalar_write(*args) -> Never:
    raise AssertionError("Invalid input must fail before writing scalar values.")


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
            "missing-valid-pack",
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
        max_bytes=2048,
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
    assert secret not in safe_failure_message(error, context=FailureContext(raw_evidence=raw))
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
    assert "input-secret-sentinel" not in raw["message"]
    assert "input-secret-sentinel" in json.dumps(raw["validation"])


@pytest.mark.parametrize("detail", [False, True])
@pytest.mark.parametrize("raw", [False, True])
def test_whole_presentation_budget_keeps_nonconformance(detail, raw):
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.operation_reporting import validation_failure_report

    error = next(Draft202012Validator({"type": "integer"}).iter_errors("s" * 16384))
    report = validation_failure_report(
        error, detail=detail, raw_evidence=raw, max_errors=1, max_bytes=1024
    ).model_dump(mode="json", exclude_none=True)
    assert len(canonical_bytes(report)) <= 1024
    assert report["validation_outcome"] == "nonconformant"
    assert len(report["observations"]) <= 1
    if raw:
        assert not report["presentation"]["render_complete"]


def test_pydantic_observations_share_count_bound_in_compact_and_detail():
    from pydantic import TypeAdapter, ValidationError

    from corpus_structure.semantic.operation_reporting import validation_failure_report

    with pytest.raises(ValidationError) as caught:
        TypeAdapter(list[int]).validate_python(["invalid"] * 20)
    for detail in (False, True):
        value = validation_failure_report(caught.value, detail=detail, max_errors=1).model_dump(
            mode="json"
        )
        assert len(value["observations"]) == 1
        assert value["presentation"]["examined_count"] == 20
        assert value["presentation"]["inventory_complete"]
        assert not value["presentation"]["render_complete"]
        assert value["validation_outcome"] == "nonconformant"


def test_native_finite_wrapper_retains_typed_numeric_location():
    from corpus_structure.semantic.operation_reporting import validation_failure_report
    from corpus_structure.semantic.pdf_records import NativeMappingError, NativeSchemaMapping

    mapping = NativeSchemaMapping(b"{}", {}, Draft202012Validator({}), {})
    with pytest.raises(NativeMappingError) as caught:
        mapping.validate({"items": [float("inf")]}, detail=True)
    value = validation_failure_report(caught.value, detail=True).model_dump(mode="json")
    assert value["observations"][0]["code"] == "native_number_nonfinite"
    assert value["observations"][0]["input_path"] == "#/items/0"
    assert value["correction_detail"]["nodes"][0]["input_path"] == [
        {"kind": "field", "field": "items"},
        {"kind": "index", "index": 0},
    ]
    assert value["validation_outcome"] == "nonconformant"


def test_wrapper_reference_profile_preserves_schema_and_input_locations():
    from corpus_structure.semantic.correction_detail import InputPath
    from corpus_structure.semantic.operation_reporting import validation_failure_report
    from corpus_structure.semantic.pdf_records import NativeMappingError, NativeSchemaMapping

    mapping = NativeSchemaMapping(b"{}", {}, Draft202012Validator({}), {})
    with pytest.raises(NativeMappingError) as caught:
        mapping.resolve({"$ref": "urn:unsupported"}, {}, InputPath(("0", 0)))
    report = validation_failure_report(caught.value, detail=True).model_dump(mode="json")
    assert report["validation_outcome"] == "unassessed"
    assert report["observations"][0]["model_path"] == "urn:unsupported"
    assert report["observations"][0]["input_path"] == "#/0/0"
    assert report["correction_detail"]["nodes"][0]["input_path"] == [
        {"kind": "field", "field": "0"},
        {"kind": "index", "index": 0},
    ]


def test_byte_selection_keeps_observation_and_node_roots_coupled():
    from corpus_structure.semantic.operation_reporting import validation_failure_report

    capture = capture_json_errors(
        Draft202012Validator({"properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}}),
        {"a": "s" * 16384, "b": "small"},
        detail=True,
    )
    report = validation_failure_report(
        CapturedFailure("", capture), detail=True, raw_evidence=True, max_bytes=2048
    ).model_dump(mode="json")
    roots = [node for node in report["correction_detail"]["nodes"] if "parent" not in node]
    assert len(roots) == len(report["observations"])
    assert report["validation_outcome"] == "nonconformant"
    assert not report["presentation"]["render_complete"]


def test_compact_json_capture_keeps_actual_inventory_coverage():
    from corpus_structure.semantic.operation_reporting import validation_failure_report

    capture = capture_json_errors(
        Draft202012Validator({"items": {"type": "integer"}}),
        ["first", "second", "third"],
        detail=False,
    )
    value = validation_failure_report(CapturedFailure("", capture)).model_dump(mode="json")
    assert len(value["observations"]) == 1
    assert "correction_detail" not in value
    assert value["presentation"]["examined_count"] == 2
    assert value["presentation"]["inventory_complete"] is False
    assert value["validation_outcome"] == "nonconformant"


def test_native_lowering_reference_profile_retains_actual_nested_traversal():
    from corpus_structure.semantic.operation_reporting import validation_failure_report
    from corpus_structure.semantic.pdf_records import (
        NativeMappingError,
        NativeSchemaMapping,
        iter_native_records,
    )

    schema = {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"$ref": "#/definitions/Item"}}},
        "definitions": {"Item": {"type": "integer"}},
    }
    mapping = NativeSchemaMapping(b"{}", schema, Draft202012Validator(schema), {})
    with pytest.raises(NativeMappingError) as caught:
        list(
            iter_native_records(
                {"items": [1]},
                product_id="product",
                revision_id="revision",
                release_id="release:example",
                source_digest="a" * 64,
                record_id_for=lambda path, kind: "record",
                write_scalar=_unexpected_scalar_write,
                mapping=mapping,
            )
        )
    value = validation_failure_report(caught.value, detail=True).model_dump(mode="json")
    assert value["validation_outcome"] == "unassessed"
    assert value["observations"][0]["input_path"] == "#/items/0"
    assert value["observations"][0]["model_path"] == "#/definitions/Item"
    assert value["correction_detail"]["nodes"][0]["input_path"] == [
        {"kind": "field", "field": "items"},
        {"kind": "index", "index": 0},
    ]


def test_subrecord_finite_path_keeps_native_locator_separate():
    from corpus_structure.semantic.operation_reporting import validation_failure_report
    from corpus_structure.semantic.pdf_records import (
        NativeMappingError,
        NativeSchemaMapping,
        iter_native_records,
    )

    schema = {"$defs": {"Item": {"type": "object", "properties": {"x": {"type": "number"}}}}}
    mapping = NativeSchemaMapping(b"{}", schema, Draft202012Validator(schema), {})
    with pytest.raises(NativeMappingError) as caught:
        list(
            iter_native_records(
                {"x": float("inf")},
                product_id="product",
                revision_id="revision",
                release_id="release:example",
                source_digest="a" * 64,
                record_id_for=lambda path, kind: "record",
                write_scalar=_unexpected_scalar_write,
                mapping=mapping,
                native_type="Item",
                native_address="#/texts/12",
            )
        )
    value = validation_failure_report(caught.value, detail=True).model_dump(mode="json")
    assert value["observations"][0]["input_path"] == "#/x"
    assert value["observations"][0]["record_locator"] == "#/texts/12"
    assert value["correction_detail"]["nodes"][0]["input_path"] == [{"kind": "field", "field": "x"}]


@pytest.mark.parametrize(
    "value,kind,code",
    [
        (1.0, "integer", "payload_scalar_type"),
        (float("inf"), "number", "payload_number_nonfinite"),
        (2**63, "integer", "payload_integer_range"),
    ],
)
def test_payload_numeric_diagnostics_preserve_strict_kind_and_finite_meanings(value, kind, code):
    from corpus_structure.semantic.correction_detail import InputPath
    from corpus_structure.semantic.operation_reporting import validation_failure_report
    from corpus_structure.semantic.pdf_payloads import PayloadContractError, _to_arrow

    with pytest.raises(PayloadContractError) as caught:
        _to_arrow(value, {"type": kind}, {}, InputPath(("n",)))
    report = validation_failure_report(caught.value, detail=True).model_dump(mode="json")
    assert report["validation_outcome"] == "nonconformant"
    assert report["observations"][0]["code"] == code
    assert report["observations"][0]["input_path"] == "#/n"


@pytest.mark.parametrize("detail", [False, True])
@pytest.mark.parametrize("raw", [False, True])
@pytest.mark.parametrize("nested", [False, True])
def test_presentation_uses_one_typed_normalization_and_logarithmic_prefix_probes(
    monkeypatch, detail, raw, nested
):
    import math

    from corpus_structure.semantic import operation_reporting as reports
    from corpus_structure.semantic.identity import canonical_bytes

    # A single root with many causes exercises the hidden-node compact case.
    if nested:
        schema = {"anyOf": [{"type": "integer", "title": str(index)} for index in range(200)]}
        instance = '雪\\"' * 500
    else:
        schema = {"type": "array", "items": {"type": "integer"}}
        instance = ['雪\\"' * 30] * 200
    capture = capture_json_errors(
        Draft202012Validator(schema), instance, detail=True, max_errors=1000
    )
    error = CapturedFailure("", capture)
    reports._report_model()
    original_report, original_bytes = reports._report, reports.canonical_bytes
    validations, probes = [], []

    def report(name, data):
        validations.append(name)
        return original_report(name, data)

    def encoded(value):
        if isinstance(value, dict) and "validation_outcome" in value and "report_version" in value:
            probes.append(value)
        return original_bytes(value)

    monkeypatch.setattr(reports, "_report", report)
    monkeypatch.setattr(reports, "canonical_bytes", encoded)
    result = reports.validation_failure_report(
        error, detail=detail, raw_evidence=raw, max_errors=1000, max_bytes=2048
    )
    value = result.model_dump(mode="json", exclude_none=True)
    assert validations == ["LocatedValidationReport"]
    count = (201 if detail else 1) if nested else 200
    assert len(probes) <= math.ceil(math.log2(max(1, count))) + 5
    assert len(canonical_bytes(value)) <= 2048
    assert value["validation_outcome"] == "nonconformant"
    assert value["complete"] is True
    assert value["presentation"]["inventory_complete"] is True
    if raw or detail:
        assert value["presentation"]["render_complete"] is False
    if detail:
        nodes = value["correction_detail"]["nodes"]
        ordinals = {node["ordinal"] for node in nodes}
        assert all(node.get("parent") is None or node["parent"] in ordinals for node in nodes)
        assert len(value["observations"]) == sum(node.get("parent") is None for node in nodes)
    else:
        assert "correction_detail" not in value
    # The returned typed projection has exactly the trusted boundary's emitted
    # defaults, null omission, empty lists and multibyte/escaped encoding.
    normalized = original_report(
        "LocatedValidationReport",
        {
            key: item
            for key, item in value.items()
            if key not in {"report_version", "report_schema_digest"}
        },
    )
    assert canonical_bytes(value) == canonical_bytes(
        normalized.model_dump(mode="json", exclude_none=True)
    )
    assert result.model_dump(mode="json") == normalized.model_dump(mode="json")


@pytest.mark.parametrize("raw", [False, True])
@pytest.mark.parametrize("detail", [False, True])
@pytest.mark.parametrize("limit", [1, 100])
def test_graph_observation_locations_follow_selected_result_identity(raw, detail, limit):
    from hashlib import sha256

    from rdflib import URIRef

    from corpus_structure.semantic.ontology import GraphDiagnostic, GraphValidation
    from corpus_structure.semantic.operation_reporting import graph_validation_report

    graph = Graph()
    for index, name in enumerate(("a", "b"), 1):
        result = URIRef("urn:result/" + name)
        graph.add((result, RDF.type, SH.ValidationResult))
        graph.add((result, SH.focusNode, URIRef(f"urn:source/record{index}")))
        graph.add((result, SH.sourceShape, URIRef(f"urn:shape/{index}")))
        graph.add((result, SH.resultPath, URIRef(f"urn:field/{index}")))
        graph.add((result, SH.resultSeverity, SH.Violation))
        graph.add((result, SH.resultMessage, Literal(f"private-value-{index}")))
    # Diagnostics use a different order: location matching must follow actual
    # selected RDF result identity rather than zip/count-based association.
    diagnostics = tuple(
        GraphDiagnostic(
            f"urn:source/record{index}",
            f"urn:field/{index}",
            f"urn:shape/{index}",
            None,
            str(SH.Violation),
            f"private-value-{index}",
        )
        for index in (2, 1)
    )
    validation = GraphValidation(
        False, graph.serialize(format="nt").encode(), "nonconformant", diagnostics
    )
    report = graph_validation_report(
        validation,
        prepared=cast(
            PreparedRelease, SimpleNamespace(release_id="release:original", execution_model_id=None)
        ),
        scope="realization@7/qualified-projection",
        detail=detail,
        raw_evidence=raw,
        max_errors=limit,
    ).model_dump(mode="json")
    assert len(report["observations"]) == min(limit, 2)
    for index, observation in enumerate(report["observations"], 1):
        focus = f"urn:source/record{index}"
        expected_path = focus if raw else "graph/focus/" + sha256(focus.encode()).hexdigest()
        assert observation["input_path"] == expected_path
        assert observation["model_path"] == f"urn:shape/{index}"
        assert observation["scope"] == "realization@7/qualified-projection"
        facts = json.loads(observation["actual"])
        assert facts["source_shape"]["value"] == f"urn:shape/{index}"
        assert (f"private-value-{index}" in observation["message"]) is raw
    assert report["validation_outcome"] == "nonconformant"
