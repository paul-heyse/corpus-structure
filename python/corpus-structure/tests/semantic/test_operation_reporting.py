"""Independent report categories, source locations and declared-change expectations."""

from dataclasses import replace
from functools import lru_cache
from typing import Any, cast

import psycopg
import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from jsonschema.exceptions import ValidationError as JsonValidationError
from pydantic import ValidationError

from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.operation_reporting import (
    compare_semantic_releases,
    explain_operation,
    report_schema,
    validation_failure_report,
    validation_report,
)
from corpus_structure.semantic.operation_value_types import NativeResultViolation
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.types import (
    Diagnostic,
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


@lru_cache(maxsize=1)
def report_inputs():
    source = SourceArtifact(
        "m",
        b"""id: https://example.org/report-test
name: report_test
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
 Thing:
  attributes:
   label: {range: string, required: true}
""",
    )
    return (
        SourceBundle("m", (source,)),
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )


@lru_cache(maxsize=1)
def prepared():
    return prepare_release(*report_inputs())


def test_preparation_failure_retains_exact_model_location_and_unknown_coverage():
    value = validation_report(
        (Diagnostic("unsupported_path", "Class.slot", "not assessed", outcome="unsupported"),)
    ).model_dump(mode="json")
    assert not value["complete"]
    item = value["observations"][0]
    assert item["category"] == "unassessed"
    assert item["model_path"] == item["input_path"] == "Class.slot"
    assert item["code"] == "unsupported_path"


def test_nested_pydantic_error_uses_instance_location():
    with pytest.raises(ValidationError) as caught:
        prepared().validate_python("Thing", {"label": 5})
    item = validation_failure_report(caught.value, scope="caller").model_dump(mode="json")[
        "observations"
    ][0]
    assert item["category"] == "invalid_input"
    assert item["input_path"] == "/label"
    assert item["code"] == "string_type"


def test_cli_boundary_preserves_trusted_context_and_original_validation_error(capsys):
    import json

    import typer

    from corpus_structure.cli.failures import failure_boundary

    original = None
    with pytest.raises(typer.Exit), failure_boundary(True) as context:
        context.bind(prepared(), "read_source_view", scope="subject")
        try:
            prepared().validate_python("Thing", {"label": 5})
        except ValidationError as error:
            original = error
            raise
    value = json.loads(capsys.readouterr().out)["error"]["validation"]
    assert isinstance(original, ValidationError)
    assert value["release_id"] == prepared().release_id
    assert value["model_id"] == prepared().execution_model_id
    observation = value["observations"][0]
    assert observation["operation"] == "read_source_view"
    assert observation["input_path"] == "/label"
    assert observation["scope"] == "subject"
    assert value["evidence"]["kind"] == "marker"
    assert "original_report" not in observation or observation["original_report"] is None


def test_mcp_boundary_preserves_invocation_context_without_leaking_between_calls():
    import json

    from fastmcp.exceptions import ToolError

    from corpus_structure.semantic.refusals import located_failure_context, tool_refusals

    @tool_refusals()
    def bound():
        with located_failure_context(prepared(), "read_source_view", scope="subject"):
            prepared().validate_python("Thing", {"label": 5})

    @tool_refusals()
    def unbound():
        prepared().validate_python("Thing", {"label": 5})

    with pytest.raises(ToolError) as caught:
        bound()
    value = json.loads(str(caught.value))["validation"]
    assert isinstance(caught.value.__cause__, ValidationError)
    assert value["release_id"] == prepared().release_id
    assert value["model_id"] == prepared().execution_model_id
    assert value["observations"][0]["operation"] == "read_source_view"
    with pytest.raises(ToolError) as separate:
        unbound()
    other = json.loads(str(separate.value))["validation"]
    assert "release_id" not in other and "model_id" not in other
    assert "operation" not in other["observations"][0]


def test_invalid_json_schema_is_distinct_from_invalid_instance():
    with pytest.raises(SchemaError) as schema_error:
        Draft202012Validator.check_schema({"type": "not_a_type"})
    assert (
        validation_failure_report(schema_error.value).model_dump(mode="json")["observations"][0][
            "category"
        ]
        == "invalid_shape"
    )
    with pytest.raises(JsonValidationError) as instance_error:
        Draft202012Validator({"type": "integer"}).validate("bad")
    assert (
        validation_failure_report(instance_error.value).model_dump(mode="json")["observations"][0][
            "category"
        ]
        == "invalid_input"
    )


def test_validator_execution_error_and_native_constraint_remain_separate():
    execution = validation_failure_report(RuntimeError("validator offline")).model_dump(mode="json")
    assert execution["observations"][0]["category"] == "validator_failure"
    native = validation_failure_report(psycopg.errors.ForeignKeyViolation("original")).model_dump(
        mode="json"
    )
    assert native["observations"][0]["category"] == "state_violation"
    assert native["observations"][0]["code"] == "database_constraint"
    assert native["observations"][0]["native_sqlstate"] == "23503"


def test_native_output_validation_is_not_reported_as_invalid_caller_input():
    from corpus_structure.semantic.operation_value_types import (
        HeldProgress,
        NativeResultViolation,
        native_result_scope,
    )

    raw = {"attempt": "broken", "holder": "h", "packet_hash": "p", "result": {}}
    with (
        pytest.raises(NativeResultViolation) as caught,
        native_result_scope("claim", "ClaimedTask", "held_progress"),
    ):
        HeldProgress.model_validate(raw)
    original = caught.value.original
    assert isinstance(original, ValidationError)
    report = validation_failure_report(caught.value).model_dump(mode="json")
    item = report["observations"][0]
    assert item["category"] == "validator_failure"
    assert item["operation"] == "claim"
    assert item["model_path"] == "ClaimedTask"
    assert item["input_path"] == "/held_progress/attempt"
    assert item["scope"] == "native_result"
    assert (
        validation_failure_report(original).model_dump(mode="json")["observations"][0]["category"]
        == "invalid_input"
    )


def test_static_operation_description_is_unresolved_and_does_not_authorize():
    result = explain_operation(prepared(), "claim").model_dump(mode="json")
    assert result["operation"] == "claim"
    assert result["release_id"] == prepared().release_id
    assert not result["complete"]
    assert any(check["status"] == "unresolved" for check in result["checks"])
    implementation = next(
        check for check in result["checks"] if check["owner"] == "semantic.contracts"
    )
    assert implementation["status"] == "applicable"
    with pytest.raises(SemanticRefusal):
        explain_operation(prepared(), "not_an_operation")


def test_changed_implementation_binding_is_observed_as_unavailable(monkeypatch):
    from corpus_structure.semantic import operation_reporting as reports
    from corpus_structure.semantic.contracts import bound_execution_model

    model = bound_execution_model(prepared())
    operation = model.operation("claim")
    changed = replace(
        model,
        implementations=tuple(
            replace(item, version="unqualified-test-version")
            if item.id == operation.implementation
            else item
            for item in model.implementations
        ),
    )
    monkeypatch.setattr(reports, "bound_execution_model", lambda release: changed)
    report = reports.explain_operation(prepared(), "claim").model_dump(mode="json")
    check = next(item for item in report["checks"] if item["owner"] == "semantic.contracts")
    assert check["status"] == "unavailable"
    assert "effects differ" in check["reason"]
    assert report["complete"] is False


def test_live_subject_family_follows_declared_inputs_and_refuses_unqualified_kinds():
    from corpus_structure.semantic.contracts import bound_execution_model
    from corpus_structure.semantic.operation_reporting import _subject_family
    from corpus_structure.semantic.product_reference import ProductReference

    model = bound_execution_model(prepared())
    derive = model.operation("derive")
    assert _subject_family(derive) == "snapshot"
    assert _subject_family(model.operation("read_native_source")) == "published_document"
    assert _subject_family(model.operation("publish_pdf_region_artifact")) == "published_document"
    assert _subject_family(replace(derive, inputs=("SourceView",))) == "published_document"
    assert _subject_family(replace(derive, inputs=("SnapshotBinding", "SourceView"))) is None
    assert _subject_family(replace(derive, inputs=("PdfProductReference",))) is None
    with pytest.raises(SemanticRefusal, match="no qualified observer"):
        explain_operation(prepared(), "claim", subject=ProductReference(1, "observation", "0" * 64))


def test_declared_class_change_reports_unknown_consumer_closure_not_no_impact():
    before = prepared()
    definition = before.definitions[0]
    prop = replace(definition.properties[0], required=False)
    after = replace(
        before, release_id="release:changed", definitions=(replace(definition, properties=(prop,)),)
    )
    value = compare_semantic_releases(before, after).model_dump(mode="json")
    assert [(r["kind"], r["model_ref"]) for r in value["changes"]] == [("changed", "class:Thing")]
    assert value["changes"][0]["members"] == [
        {
            "kind": "changed",
            "model_path": "class:Thing/properties/label/required",
            "before": {"kind": "boolean", "boolean": True},
            "after": {"kind": "boolean", "boolean": False},
        }
    ]
    assert not value["complete"]
    assert value["unknowns"]
    same = compare_semantic_releases(before, before).model_dump(mode="json")
    assert same["changes"] == []


def test_normalized_member_facts_distinguish_absence_null_and_native_order():
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.operation_reporting import _changed_members, _report_model

    members = _changed_members({}, {"optional": None}, "class:Thing")
    assert members == [
        {
            "kind": "added",
            "model_path": "class:Thing/optional",
            "after": {"kind": "null"},
        }
    ]
    boundary, _digest = _report_model()
    value = boundary.validate_json("AddedSemanticMember", canonical_bytes(members[0]))
    assert value.model_dump(mode="json") == members[0]
    first = [{"name": "a", "nullable": False}, {"name": "b", "nullable": True}]
    reordered = _changed_members(first, list(reversed(first)), "operation:call/parameters")
    assert len(reordered) == 1
    assert reordered[0]["model_path"] == "operation:call/parameters"
    assert reordered[0]["before"]["items"][0]["fields"][0]["value"]["text"] == "a"
    assert reordered[0]["after"]["items"][0]["fields"][0]["value"]["text"] == "b"


@pytest.mark.parametrize("collection", ["parameters", "result_fields", "properties"])
def test_named_collection_membership_preserves_insert_and_remove_positions(collection):
    from corpus_structure.semantic.operation_reporting import _changed_members

    path = "operation:call/" + collection
    first, added = {"name": "a"}, {"name": "b"}
    front = _changed_members([first], [added, first], path)
    back = _changed_members([first], [first, added], path)
    assert front != back
    assert front[0]["model_path"] == back[0]["model_path"] == path

    def names(value):
        return [item["fields"][0]["value"]["text"] for item in value["items"]]

    assert names(front[0]["before"]) == names(back[0]["before"]) == ["a"]
    assert names(front[0]["after"]) == ["b", "a"]
    assert names(back[0]["after"]) == ["a", "b"]
    removed_front = _changed_members([added, first], [first], path)
    removed_back = _changed_members([first, added], [first], path)
    assert removed_front != removed_back
    assert names(removed_front[0]["before"]) == ["b", "a"]
    assert names(removed_back[0]["before"]) == ["a", "b"]
    assert names(removed_front[0]["after"]) == names(removed_back[0]["after"]) == ["a"]


def test_native_diagnostic_retains_owner_binding_without_supplied_prepared_context():
    from corpus_structure.core.db.store import (
        DatabaseCause,
        DatabaseFailure,
        DatabaseOperationFailure,
        record_operation_failure,
    )
    from corpus_structure.semantic.invariant_failures import InvariantFailure, InvariantViolation

    native = DatabaseOperationFailure(
        DatabaseFailure(DatabaseCause.CONSTRAINT, sqlstate="23503"),
        release_id="release:attested",
    )
    error = InvariantViolation(
        InvariantFailure(
            "pdf.published_document_address",
            "published_document_address",
            "publish_pdf_region_artifact",
            "model:attested",
            "relational",
            native,
        )
    )
    report = validation_failure_report(error).model_dump(mode="json")
    assert report["model_id"] == "model:attested"
    assert report["release_id"] == "release:attested"
    assert report["observations"][0]["operation"] == "publish_pdf_region_artifact"
    with pytest.raises(SemanticRefusal, match="model differs"):
        validation_failure_report(error, prepared=prepared())
    raw = psycopg.errors.ForeignKeyViolation("independent native failure")
    record_operation_failure(raw, native)
    observed = validation_failure_report(raw).model_dump(mode="json")
    assert observed["release_id"] == "release:attested"
    with pytest.raises(SemanticRefusal, match="release differs"):
        validation_failure_report(raw, prepared=prepared())


@pytest.mark.parametrize(
    "error",
    [
        SemanticRefusal("unsupported binding"),
        NativeResultViolation("read_native_source", "PublishedRegionRow", "pointer"),
    ],
)
def test_region_observer_does_not_relabel_failed_evaluation_as_missing(monkeypatch, error):
    from sqlalchemy import create_engine

    from corpus_structure.semantic.operation_reporting import (
        PublishedDocumentSubject,
        _document_subject_checks,
    )
    from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
    from corpus_structure.semantic.product_reference import ProductReference

    def fail(self, pointer, region_index):
        raise error

    monkeypatch.setattr(PublishedPdfReader, "region", fail)
    engine = create_engine("sqlite://")
    try:
        with engine.connect() as conn:
            pin = ProductReference(1, "native", "0" * 64)
            reader = PublishedPdfReader(conn, pin, revision={})
            subject = PublishedDocumentSubject(pin, pointer="#/texts/0", region_index=0)
            with pytest.raises(type(error)) as caught:
                _document_subject_checks(prepared(), subject, conn, reader, [])
            assert caught.value is error
    finally:
        engine.dispose()


def test_native_admission_infrastructure_failure_propagates_without_missing_verdict(monkeypatch):
    from sqlalchemy import create_engine

    from corpus_structure.semantic import contracts

    error = psycopg.OperationalError("independent connection failure")

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(contracts, "require_database_operation", fail)
    engine = create_engine("sqlite://")
    try:
        with engine.connect() as conn, pytest.raises(psycopg.OperationalError) as caught:
            explain_operation(prepared(), "claim", connection=conn)
        assert caught.value is error
    finally:
        engine.dispose()


def test_retained_subject_contract_absence_refuses_without_current_schema_fallback(monkeypatch):
    from types import SimpleNamespace

    from sqlalchemy import create_engine

    from corpus_structure.semantic import pdf_contracts
    from corpus_structure.semantic.operation_reporting import parse_operation_subject

    boundary = prepare_release(report_inputs()[0])
    monkeypatch.setattr(
        pdf_contracts, "pdf_context_for_release", lambda *args: SimpleNamespace(boundary=boundary)
    )
    engine = create_engine("sqlite://")
    try:
        with engine.connect() as conn, pytest.raises(SemanticRefusal, match="retained release"):
            parse_operation_subject(prepared(), "read_native_source", b"{}", connection=conn)
    finally:
        engine.dispose()


def test_relationship_lifecycle_and_removed_dependency_edges_reach_declared_consumers(monkeypatch):
    from corpus_structure.semantic import operation_reporting as reports
    from corpus_structure.semantic.contracts import bound_execution_model

    before = prepared()
    after = replace(before, release_id="release:changed-contracts")
    model = bound_execution_model(before)
    operation = next(op for op in model.operations if op.projections)
    projection = next(p for p in model.projections if p.id in operation.projections)
    relationship = model.relationships[0]
    lifecycle = model.lifecycles[0]
    implementation = model.implementations[0]
    concept = replace(model.concepts[0], id=implementation.id, relationships=(relationship.id,))
    input_consumer = replace(
        operation,
        id="declared_input_consumer",
        inputs=(concept.id,),
        projections=(),
        transitions=(),
        applicability=(),
        dependencies=(),
        implementation=None,
    )
    # Deliberately link this independently selected consumer through declared
    # projection and transition edges; the changed side removes those edges.
    projection = replace(projection, relationships=(relationship.id,))
    transition = replace(model.transitions[0], operation=operation.id, lifecycle=lifecycle.id)
    old = replace(
        model,
        operations=(operation, input_consumer),
        concepts=(concept,),
        projections=(projection,),
        transitions=(transition,),
    )
    new = replace(
        old,
        operations=(replace(operation, projections=(), transitions=()), input_consumer),
        projections=(replace(projection, relationships=()),),
        transitions=(),
        implementations=tuple(
            replace(item, version="changed") if item.id == implementation.id else item
            for item in old.implementations
        ),
        relationships=tuple(
            replace(item, multiplicity="changed-independent-expectation")
            if item.id == relationship.id
            else item
            for item in old.relationships
        ),
        lifecycles=tuple(
            replace(item, initial_states=()) if item.id == lifecycle.id else item
            for item in old.lifecycles
        ),
    )
    monkeypatch.setattr(
        reports, "bound_execution_model", lambda release: old if release is before else new
    )
    value = reports.compare_semantic_releases(before, after).model_dump(mode="json")
    changes = {item["model_ref"]: item for item in value["changes"]}
    assert changes["relationship:" + relationship.id]["consumers"] == sorted(
        [
            operation.id,
            input_consumer.id,
        ]
    )
    assert changes["lifecycle:" + lifecycle.id]["consumers"] == [operation.id]
    assert changes["transition:" + transition.id]["consumers"] == [operation.id]
    # A concept and implementation may have the same local ID. A concept input
    # must not become an implementation dependency merely by matching its text.
    assert input_consumer.id not in changes["implementation:" + implementation.id]["consumers"]


def test_report_schema_is_the_real_model_bound_public_shape():
    schema = report_schema("OperationExplanation")
    assert schema["type"] == "object"
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert "checks" in properties
    version = properties["report_version"]
    assert isinstance(version, dict)
    assert type(version["minimum"]) is type(version["maximum"]) is int
    Draft202012Validator.check_schema(schema)
    with pytest.raises(SemanticRefusal):
        report_schema("Unknown")


def test_registration_and_invocation_share_the_captured_schema_source(monkeypatch):
    from corpus_structure.semantic import contracts
    from corpus_structure.semantic import operation_reporting as reports

    registered = reports.report_schema("OperationExplanation")
    sources = reports._report_sources()

    def refuse_reacquisition():
        raise AssertionError("invocation must not silently adopt changed installed schema")

    monkeypatch.setattr(contracts, "trusted_execution_schema", refuse_reacquisition)
    reports._report_model.cache_clear()
    boundary, _digest = reports._report_model()
    assert reports._report_sources() is sources
    assert boundary.json_schema("OperationExplanation", mode="serialization") == registered


def test_graph_shape_execution_and_located_nonconformance_stay_distinct():
    from corpus_structure.semantic.ontology import (
        GraphDiagnostic,
        GraphExecutionError,
        GraphShapeError,
        GraphValidation,
    )
    from corpus_structure.semantic.operation_reporting import graph_validation_report

    for error, category in (
        (GraphShapeError("shape"), "invalid_shape"),
        (GraphExecutionError("engine"), "validator_failure"),
    ):
        value = validation_failure_report(error).model_dump(mode="json")
        assert value["observations"][0]["category"] == category
    graph = GraphValidation(
        False,
        b"retained raw report",
        "nonconformant",
        (
            GraphDiagnostic(
                "urn:item:3", "urn:field", "urn:shape", "urn:constraint", "urn:violation", "missing"
            ),
        ),
    )
    value = graph_validation_report(
        graph, prepared=prepared(), scope="complete supplied closure"
    ).model_dump(mode="json")
    observation = value["observations"][0]
    assert observation["category"] == "state_violation"
    from hashlib import sha256

    assert observation["input_path"] == "graph/focus/" + sha256(b"urn:item:3").hexdigest()
    assert observation["model_path"] == "urn:shape"
    assert value["evidence"]["kind"] == "marker"
    assert len(value["evidence"]["digest"]) == 64


def test_actual_schema_check_reports_retained_located_coverage(cli):
    import json

    checked = cli("schema", "check", "--json")
    assert checked.exit_code == 0, checked.output
    located = json.loads(checked.stdout)["validation"]
    assert located["release_id"] == json.loads(checked.stdout)["release_id"]
    assert located["model_id"] == json.loads(checked.stdout)["execution_model_id"]
    assert not located["complete"]
    assert any(
        item["category"] == "unassessed"
        and item["code"] == "projection_analysis_incomplete"
        and item["model_path"].startswith("projection:")
        for item in located["observations"]
    )


def alias_release(policy=None, *, origins=None, profile="class-iri-aliases-1"):
    import json

    from corpus_structure.semantic.types import PreparedArtifact

    base = prepared()
    iri = base.definitions[0].iri
    artifact = PreparedArtifact(
        "operation/alias-policy.json",
        json.dumps(
            {
                "profile": profile,
                "classes": {
                    iri: {"articles": [], "head_words": {iri: []}, "rewrites": policy or []}
                },
                "origins": {iri: origins or ["original"]},
            }
        ).encode(),
    )
    return replace(
        base, artifacts=(*(a for a in base.artifacts if a.kind != artifact.kind), artifact)
    )


def test_alias_only_impact_retains_class_member_and_actual_consumer_kinds():
    old = alias_release()
    new = alias_release([{"match": "alpha", "replace": "beta"}])
    value = compare_semantic_releases(old, new).model_dump(mode="json")
    changes = [c for c in value["changes"] if c["aspect"] == "alias_normalization"]
    assert len(changes) == 1
    change = changes[0]
    assert change["model_ref"] == "alias_policy:" + old.definitions[0].iri
    assert "implementation:resolve_identity" in change["consumers"]
    assert any(c.startswith("analysis_profile:") for c in change["consumers"])
    assert change["members"][0]["model_path"].endswith("/rewrites")
    assert not value["complete"]


def test_origin_only_alias_impact_does_not_advise_semantic_regeneration():
    from corpus_structure.semantic.operation_reporting import compatibility_advice

    report = compare_semantic_releases(alias_release(), alias_release(origins=["relocated"]))
    value = report.model_dump(mode="json")
    assert [c["aspect"] for c in value["changes"]] == ["alias_origin"]
    assert value["changes"][0]["consumers"] == []
    advice = compatibility_advice(report)
    assert any("provenance" in text for text in advice)
    assert not any(text.startswith("Regenerate") for text in advice)


def test_unknown_alias_profile_is_unassessed_not_an_empty_policy():
    value = compare_semantic_releases(alias_release(), alias_release(profile="unknown")).model_dump(
        mode="json"
    )
    assert not value["complete"]
    assert any("alias policy unassessed" in text for text in value["unknowns"])


def test_alias_rewrite_order_is_a_semantic_change_with_independent_ordered_values():
    rules = [{"match": "a", "replace": "b"}, {"match": "b", "replace": "c"}]
    report = compare_semantic_releases(alias_release(rules), alias_release(rules[::-1]))
    change = next(
        c for c in report.model_dump(mode="json")["changes"] if c["aspect"] == "alias_normalization"
    )
    member = change["members"][0]
    assert member["model_path"].endswith("/classes/rewrites")
    assert member["before"] != member["after"]
    assert member["before"]["items"][0]["fields"][0]["value"]["text"] == "a"
    assert member["after"]["items"][0]["fields"][0]["value"]["text"] == "b"


def test_alias_policy_added_and_removed_class_retains_its_full_identity():
    import json

    from corpus_structure.semantic.types import PreparedArtifact

    old = alias_release()
    iri = old.definitions[0].iri
    empty = PreparedArtifact(
        "operation/alias-policy.json",
        json.dumps(
            {
                "profile": "class-iri-aliases-1",
                "classes": {},
                "origins": {},
            }
        ).encode(),
    )
    removed = replace(
        old,
        artifacts=(
            *(a for a in old.artifacts if a.kind != empty.kind),
            empty,
        ),
    )
    for before, after, expected in ((old, removed, "removed"), (removed, old, "added")):
        report = compare_semantic_releases(before, after).model_dump(mode="json")
        change = next(c for c in report["changes"] if c["aspect"] == "alias_normalization")
        assert change["kind"] == expected
        assert change["model_ref"] == "alias_policy:" + iri


def test_missing_neutral_alias_product_does_not_invent_a_normalization_change():
    original = alias_release()
    neutral = replace(
        original,
        artifacts=tuple(
            a
            for a in original.artifacts
            if a.kind not in {"operation/alias-policy.json", "operation/domain-rules.yaml"}
        ),
    )
    report = compare_semantic_releases(neutral, original).model_dump(mode="json")
    assert not any(c["aspect"] == "alias_normalization" for c in report["changes"])
    assert any(c["aspect"] == "alias_origin" for c in report["changes"])


@pytest.mark.parametrize("legacy", [False, True])
def test_alias_profile_consumers_use_semantic_declarations_with_separate_runtime_custody(
    monkeypatch, legacy
):
    from corpus_structure.semantic import operation_reporting as reports
    from corpus_structure.semantic.contracts import bound_execution_model
    from corpus_structure.semantic.identity import canonical_bytes

    old = alias_release()
    new = alias_release([{"match": "a", "replace": "b"}])
    model = bound_execution_model(old)
    import json

    payload = json.loads(model.content)
    if legacy:
        payload["inputs"]["compiler_version"] = "26"
    without_alignment = replace(
        model,
        content=canonical_bytes(payload),
        implementation_digests=tuple(
            pair
            for pair in model.implementation_digests
            if pair[0] != "alignment/semantic_alignment.py"
        ),
    )
    monkeypatch.setattr(reports, "bound_execution_model", lambda prepared: without_alignment)
    result = reports.compare_semantic_releases(old, new).model_dump(mode="json")
    change = next(c for c in result["changes"] if c["aspect"] == "alias_normalization")
    assert "implementation:resolve_identity" in change["consumers"]
    assert any(c.startswith("analysis_profile:") for c in change["consumers"]) is not legacy
    assert (
        any("alignment implementation custody unavailable" in u for u in result["unknowns"])
        is legacy
    )


def test_runtime_change_is_reported_separately_from_semantic_meaning():
    from corpus_structure.semantic.contracts import analysis_implementation_inputs
    from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding

    prepared = alias_release()
    sources = analysis_implementation_inputs()
    changed_sources = tuple(
        replace(source, content=source.content + b"\n# runtime change\n")
        if source.name == "text/sentences.py"
        else source
        for source in sources
    )
    before = prepare_runtime_binding(prepared, sources)
    after = prepare_runtime_binding(prepared, changed_sources)
    assert before.runtime_id != after.runtime_id
    report = compare_semantic_releases(
        prepared,
        prepared,
        before_runtime=before,
        after_runtime=after,
    ).model_dump(mode="json")
    assert report["changes"] == []
    assert any("Executable runtime changed independently" in value for value in report["unknowns"])


def test_runtime_comparison_refuses_a_relabelled_release():
    from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding

    prepared = alias_release()
    runtime = prepare_runtime_binding(prepared)
    with pytest.raises(ValueError, match="another semantic release"):
        compare_semantic_releases(
            prepared,
            prepared,
            before_runtime=replace(runtime, release_id="another-release"),
        )


def test_runtime_comparison_refuses_unauthenticated_archive():
    from corpus_structure.semantic.runtime_bindings import (
        RuntimeBindingError,
        prepare_runtime_binding,
    )

    prepared = alias_release()
    runtime = prepare_runtime_binding(prepared)
    with pytest.raises(RuntimeBindingError, match="noncanonical or unsupported shape"):
        compare_semantic_releases(
            prepared,
            prepared,
            before_runtime=replace(runtime, archive=runtime.archive + b" "),
            after_runtime=runtime,
        )


def test_semantic_release_change_does_not_imply_executable_runtime_change():
    from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding

    bundle, dependencies, profile = report_inputs()
    before = prepare_release(bundle, dependencies, profile)
    changed_bundle = replace(
        bundle,
        sources=tuple(
            replace(
                source,
                content=source.content + b"\ndescription: distinct report semantic release\n",
            )
            for source in bundle.sources
        ),
    )
    after = prepare_release(changed_bundle, dependencies, profile)
    assert before.release_id != after.release_id
    before_runtime = prepare_runtime_binding(before)
    after_runtime = prepare_runtime_binding(after)
    assert before_runtime.runtime_id != after_runtime.runtime_id
    report = compare_semantic_releases(
        before,
        after,
        before_runtime=before_runtime,
        after_runtime=after_runtime,
    ).model_dump(mode="json")
    assert not any(
        "Executable runtime changed independently" in value for value in report["unknowns"]
    )


def test_retained_dependency_detail_keeps_repeated_occurrences_and_pages(monkeypatch):
    from dataclasses import dataclass
    from types import SimpleNamespace

    from corpus_structure.semantic import projection_analysis_products as products
    from corpus_structure.semantic.operation_reporting import projection_dependency_detail

    @dataclass(frozen=True)
    class Occurrence:
        identity: str
        structural_path: str
        role: str = "value"
        clause: str = "output"
        source_ref: str = "physical:kb.source.id"
        target_ref: str = "projection:test/fields/id"
        output: str = "id"
        relationship: str | None = None
        unknown_reason: str | None = None

    analysis = SimpleNamespace(
        consumers=("read",),
        detail_status="available",
        unknowns=(),
        occurrences=(
            Occurrence("occurrence:second", "/fields/0/right"),
            Occurrence("occurrence:first", "/fields/0/left"),
        ),
    )
    product = SimpleNamespace(
        complete=True, projections=(SimpleNamespace(family="input", analysis=analysis),)
    )
    monkeypatch.setattr(products, "read_projection_analysis", lambda _: product)
    first = projection_dependency_detail(None, limit=1, operation="read")
    assert first["total"] == 2
    assert first["items"][0]["occurrence"]["identity"] == "occurrence:first"
    assert first["next_after"] == 1 and not first["paging_complete"]
    second = projection_dependency_detail(None, after=first["next_after"], limit=1)
    assert second["items"][0]["occurrence"]["identity"] == "occurrence:second"
    assert second["paging_complete"] and second["coverage_complete"]
    assert projection_dependency_detail(None, output="other")["total"] == 0
    assert projection_dependency_detail(None, occurrence="occurrence:first")["total"] == 1
    assert projection_dependency_detail(None, operation="unrelated")["total"] == 0
    with pytest.raises(SemanticRefusal, match="bounds"):
        projection_dependency_detail(None, limit=1001)
    with pytest.raises(SemanticRefusal, match="position"):
        projection_dependency_detail(None, after=3)


def test_archived_detail_unavailable_is_not_empty_or_reanalyzed(monkeypatch):
    from types import SimpleNamespace

    from corpus_structure.semantic import projection_analysis_products as products
    from corpus_structure.semantic.operation_reporting import projection_dependency_detail

    old = SimpleNamespace(
        complete=True,
        projections=(
            SimpleNamespace(
                family="coverage",
                analysis=SimpleNamespace(
                    consumers=("read",), detail_status="unavailable", unknowns=(), occurrences=()
                ),
            ),
        ),
    )
    monkeypatch.setattr(products, "read_projection_analysis", lambda _: old)
    page = projection_dependency_detail(None, output="unknown-output")
    assert page["total"] == 1
    assert page["items"][0]["status"] == "unavailable"
    assert "occurrence" not in page["items"][0]
    assert not page["coverage_complete"]
    monkeypatch.setattr(products, "read_projection_analysis", lambda _: None)
    assert (
        projection_dependency_detail(None)["items"][0]["reason"]
        == "Retained projection analysis unavailable."
    )


def test_report_v2_exposes_typed_optional_dependency_page():
    schema = report_schema("OperationExplanation")
    properties = schema["properties"]
    required = schema["required"]
    assert isinstance(properties, dict) and isinstance(required, list)
    assert properties["report_version"]["minimum"] == 2
    assert properties["report_version"]["maximum"] == 2
    assert "projection_dependencies" in properties
    assert "projection_dependencies" not in required
    definitions = schema["$defs"]
    assert isinstance(definitions, dict)
    occurrence = next(
        value
        for name, value in definitions.items()
        if name.endswith("ProjectionDependencyOccurrence")
    )
    assert set(occurrence["properties"]["role"]["enum"]) == {
        "value",
        "membership",
        "ordering",
        "unknown",
    }


def test_projection_validation_reuses_retained_detail_and_keeps_compact_completeness(monkeypatch):
    from dataclasses import dataclass
    from types import SimpleNamespace

    from corpus_structure.semantic import projection_analysis_products as products
    from corpus_structure.semantic.operation_reporting import projection_validation_report

    @dataclass(frozen=True)
    class Occurrence:
        identity: str
        structural_path: str
        role: str = "value"
        clause: str = "output"
        source_ref: str = "physical:kb.source.id"
        target_ref: str = "projection:test/fields/id"
        output: str = "id"
        relationship: str | None = None
        unknown_reason: str | None = None

    analysis = SimpleNamespace(
        detail_status="available",
        unknowns=(),
        occurrences=(Occurrence("right", "/fields/0/right"), Occurrence("left", "/fields/0/left")),
    )
    product = SimpleNamespace(
        complete=True,
        unknowns=(),
        projections=(SimpleNamespace(family="input", analysis=analysis),),
    )
    context: Any = SimpleNamespace(
        release_id="release:validation", execution_model_id="model:validation"
    )
    monkeypatch.setattr(products, "read_projection_analysis", lambda _: product)
    compact = projection_validation_report(context).model_dump(mode="json")
    assert compact["report_version"] == 5
    assert compact["complete"] is True and compact["observations"] == []
    assert compact.get("projection_dependencies") is None
    first = projection_validation_report(
        context, dependency_detail=True, dependency_family="input", dependency_limit=1
    ).model_dump(mode="json")
    assert first["complete"] is True and first["observations"] == []
    page = first["projection_dependencies"]
    assert page["total"] == 2 and page["next_after"] == 1
    assert page["items"][0]["occurrence"]["identity"] == "left"
    second = projection_validation_report(
        context, dependency_detail=True, dependency_after=1, dependency_limit=1
    ).model_dump(mode="json")["projection_dependencies"]
    assert second["items"][0]["occurrence"]["identity"] == "right"
    assert second["paging_complete"] and second["coverage_complete"]
    selected = projection_validation_report(
        context, dependency_detail=True, dependency_occurrence="right", dependency_output="id"
    ).model_dump(mode="json")["projection_dependencies"]
    assert selected["total"] == 1
    assert selected["items"][0]["occurrence"]["identity"] == "right"
    with pytest.raises(SemanticRefusal, match="bounds"):
        projection_validation_report(context, dependency_detail=True, dependency_limit=1001)
    with pytest.raises(SemanticRefusal, match="position"):
        projection_validation_report(context, dependency_detail=True, dependency_after=3)

    analysis.detail_status = "unavailable"
    analysis.occurrences = ()
    unavailable = projection_validation_report(context, dependency_detail=True).model_dump(
        mode="json"
    )
    assert unavailable["complete"] is True and unavailable["observations"] == []
    assert unavailable["projection_dependencies"]["items"] == [
        {
            "side": "current",
            "family": "input",
            "status": "unavailable",
            "reason": "Archived analysis does not retain occurrence detail.",
        }
    ]
    assert not unavailable["projection_dependencies"]["coverage_complete"]
    monkeypatch.setattr(products, "read_projection_analysis", lambda _: None)
    missing = projection_validation_report(context, dependency_detail=True).model_dump(mode="json")
    assert not missing["complete"]
    assert (
        missing["projection_dependencies"]["items"][0]["reason"]
        == "Retained projection analysis unavailable."
    )


def test_validation_v5_registration_versions_shared_consumers():
    schema = cast(dict[str, Any], report_schema("LocatedValidationReport"))
    assert schema["properties"]["report_version"]["minimum"] == 5
    assert schema["properties"]["report_version"]["maximum"] == 5
    assert "projection_dependencies" in schema["properties"]
    assert "projection_dependencies" not in schema["required"]
    for name, version in (
        ("OperationExplanation", 2),
        ("SemanticImpactReport", 4),
        ("ContractInspection", 3),
    ):
        other = cast(dict[str, Any], report_schema(name))
        assert other["properties"]["report_version"]["minimum"] == version
        assert other["properties"]["report_version"]["maximum"] == version
