"""The shared read boundary rejects ambiguous and mismatched captured projections."""

from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.native_definition_projection import read_native_definition_projection


@pytest.mark.parametrize(
    ("namespace", "authored"),
    [
        ("https://corpus-structure.dev/domains/statistics/terminology/", True),
        ("urn:unrelated:", False),
    ],
)
def test_native_projection_keeps_exact_authored_judgments_without_computational_roles(
    namespace, authored
):
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_storage import (
        data_operation_definition_projection,
    )
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact, SourceBundle

    declaration = f"""id: urn:authored-judgment-projection
name: judgments
prefixes: {{j: '{namespace}'}}
default_prefix: j
default_range: string
types:
  string: {{base: str}}
classes:
  DdoAuthoredMeasurementJudgment:
    attributes:
      basis: {{required: true}}
  DdoAuthoredTerminologyJudgment:
    attributes:
      term: {{required: true}}
  UnusedAuthoredFact:
    attributes:
      fact: {{required: true}}
""".encode()
    prepared = prepare_release(
        SourceBundle("judgments", (SourceArtifact("judgments", declaration),)),
        data_operation_dependencies(ResolvedDependencies()),
    )
    model = bound_data_operation_model(prepared)
    assert not model.operations
    projection = read_native_definition_projection(
        SimpleNamespace(
            artifacts=(
                SimpleNamespace(
                    kind="data_operation_native_definitions.json",
                    content=data_operation_definition_projection(
                        prepared, model, native_digest="native-source-contract"
                    ),
                ),
            )
        ),
        model=model,
    )
    expected = {
        f"{namespace}DdoAuthoredMeasurementJudgment",
        f"{namespace}DdoAuthoredTerminologyJudgment",
    }
    assert {row["kind"] for row in projection["kinds"]} == (expected if authored else set())
    assert all(row["universe"] == "ordinary" for row in projection["kinds"])


def test_native_projection_preserves_actual_timezone_aware_datetime_meaning():
    from datetime import UTC, datetime

    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_storage import kind_meaning_schema
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.data_operation_wire import validate_wire_schema
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact, SourceBundle

    declaration = b"""id: urn:projection-event
name: event
prefixes: {e: 'urn:projection-event:'}
default_prefix: e
types:
  datetime: {base: datetime}
classes:
  Event:
    attributes:
      at: {range: datetime, required: true}
"""
    prepared = prepare_release(
        SourceBundle("event", (SourceArtifact("event", declaration),)),
        data_operation_dependencies(ResolvedDependencies()),
    )
    model = bound_data_operation_model(prepared)
    kind = next(kind for kind in model.kinds if kind.category == "class" and kind.name == "Event")
    schema = kind_meaning_schema(
        kind, model.kinds, prepared.index.definitions, prepared.enum_members
    )
    actual = prepared.validate_json("Event", b'{"at":"2030-01-02T03:04:05+02:00"}').model_dump(
        mode="python"
    )["at"]
    assert actual == datetime(2030, 1, 2, 1, 4, 5, tzinfo=UTC)
    validate_wire_schema(schema, semantic_value({"at": actual}))
    with pytest.raises(ValueError):
        validate_wire_schema(schema, semantic_value({"at": "2030-01-02T03:04:05+02:00"}))
    with pytest.raises(ValueError):
        prepared.validate_json("Event", b'{"at":"2030-01-02T03:04:05"}')


def test_tagged_nominal_projection_is_stable_with_an_unrelated_integer_property():
    from pydantic import TypeAdapter

    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_storage import kind_meaning_schema
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.data_operation_version import MODEL_VERSION
    from corpus_structure.semantic.data_operation_wire import validate_wire_schema
    from corpus_structure.semantic.data_product_reference import SemanticPartitionReference
    from corpus_structure.semantic.nominal_schema_kinds import nominal_schema_kinds
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact, SourceBundle

    definition = b"""id: urn:stable-visual
name: visual
prefixes: {v: 'urn:stable-visual:'}
default_prefix: v
types:
  integer: {base: int}
  PageNumber: {base: int}
classes:
  Visual:
    attributes:
      width: {range: integer, required: true}
      page: {range: PageNumber, required: true}
"""
    bundle = SourceBundle("visual", (SourceArtifact("visual", definition),))
    captured = SourceArtifact(
        "unrelated/nominal-kinds.json",
        json_bytes(
            {
                "version": MODEL_VERSION,
                "kinds": nominal_schema_kinds(
                    TypeAdapter(SemanticPartitionReference).json_schema(),
                    namespace="urn:unrelated:",
                    root_name="UnrelatedReference",
                ),
            }
        ),
    )

    def projection(declarations):
        prepared = prepare_release(
            bundle, data_operation_dependencies(ResolvedDependencies(), declarations)
        )
        model = bound_data_operation_model(prepared)
        owner = prepared.index.definitions["Visual"].iri
        kind = next(kind for kind in model.kinds if kind.semantic_id == owner)
        identity = next(
            item.key for item in model.identities if item.owner == owner and item.domain == "kind"
        )
        meaning = kind_meaning_schema(
            kind, model.kinds, prepared.index.definitions, prepared.enum_members
        )
        return identity, meaning

    first = projection(())
    assert projection((captured,)) == first
    _, schema = first
    validate_wire_schema(schema, semantic_value({"width": 612, "page": 1}))
    with pytest.raises(ValueError):
        validate_wire_schema(schema, semantic_value({"width": "612", "page": 1}))
    with pytest.raises(ValueError):
        validate_wire_schema(schema, semantic_value({"width": 612}))
    with pytest.raises(ValueError):
        validate_wire_schema(schema, semantic_value({"width": 612, "page": 1, "unknown": 4}))


def test_captured_json_meaning_selects_the_recursive_tag_before_validating_its_payload():
    from corpus_structure.semantic.data_operation_storage import kind_meaning_schema
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.data_operation_wire import validate_wire_schema

    kind = SimpleNamespace(
        semantic_id="primitive:json", category="primitive", name="json", facts=b"{}"
    )
    schema = kind_meaning_schema(kind, (kind,), {}, lambda _: ())

    def nested(value):
        for _ in range(16):
            value = ["mapping", [["item", ["sequence", [value]]]]]
        return value

    validate_wire_schema(schema, nested(semantic_value(51)))
    with pytest.raises(ValueError):
        validate_wire_schema(schema, nested(["integer", []]))
    with pytest.raises(ValueError):
        validate_wire_schema(schema, ["sequence", [], "unexpected"])


def _captured(**changes):
    operations = changes.get("operations", [])
    coverage = {
        "binding": "controlled-binding",
        "selection": {"json": {}},
        "result_selection": {"json": {}},
        "result_owners": [],
        "description": "Controlled unused result owner",
    }
    for operation in operations:
        operation["support_contract"]["coverage"] = coverage
    model = SimpleNamespace(
        content=json_bytes(
            {
                "operations": [
                    {"semantic_id": operation["operation_id"], "coverage": coverage}
                    for operation in operations
                ]
            }
        ),
        operations=(),
        rules=(),
        identities=(SimpleNamespace(owner="primitive:string", domain="kind", key="kind:string"),),
        subject_definition=lambda _: SimpleNamespace(identifier_kind="primitive:string"),
    )
    record = {
        "model_digest": sha256(model.content).hexdigest(),
        "native_digest": "native-source-contract",
        "kinds": [
            {
                "kind_contract": "kind:string",
                "kind": "primitive:string",
                "body_schema": {"type": "string"},
                "meaning_schema": {"type": "string"},
                "member_schema": {"not": {}},
                "member_contracts": [],
                "universe": "ordinary",
            }
        ]
        if operations
        else [],
        "operations": [],
        **changes,
    }
    artifact = SimpleNamespace(
        kind="data_operation_native_definitions.json", content=json_bytes(record)
    )
    return model, SimpleNamespace(artifacts=(artifact,))


def test_exact_model_binding_returns_typed_projection():
    model, prepared = _captured()
    assert read_native_definition_projection(prepared, model=model) == {
        "model_digest": sha256(model.content).hexdigest(),
        "native_digest": "native-source-contract",
        "kinds": [],
        "operations": [],
    }


@pytest.mark.parametrize("count", [0, 2])
def test_artifact_must_be_unique(count):
    model, prepared = _captured()
    prepared.artifacts = prepared.artifacts * count
    with pytest.raises(ValueError, match="exactly one"):
        read_native_definition_projection(prepared, model=model)


def test_projection_cannot_be_used_with_another_model():
    model, prepared = _captured(model_digest="another model")
    with pytest.raises(ValueError, match="another effective model"):
        read_native_definition_projection(prepared, model=model)


def test_unknown_projection_fields_are_not_silently_discarded():
    model, prepared = _captured(unknown_policy="must not disappear")
    with pytest.raises(ValueError, match="Extra inputs"):
        read_native_definition_projection(prepared, model=model)


def test_native_rule_catalog_cannot_rebind_a_checked_rule():
    rule = {
        "id": "bounded-span",
        "kind": "SpanCollection",
        "kind_contract": "kind:span-collection",
        "collection": "blocks",
        "fingerprint": "rule:expected",
        "scope": "partition",
        "form": "span_within",
        "checker": "admission",
        "checker_operation": None,
        "checker_callable": None,
        "checker_determinant": "native-data-rule-v1:span_within",
        "parameters": {
            "start": "start",
            "end": "end",
            "limit": "extent",
            "coordinates": "relative",
        },
        "reads": [{"side": "source", "path": "start", "groups": []}],
    }
    model, prepared = _captured(rules=[rule])
    model.rules = (SimpleNamespace(record=rule),)
    assert read_native_definition_projection(prepared, model=model)["rules"] == [rule]
    model.rules = (SimpleNamespace(record={**rule, "fingerprint": "rule:other"}),)
    with pytest.raises(ValueError, match="rule catalog differs"):
        read_native_definition_projection(prepared, model=model)


def test_variant_is_explicit_kind_metadata_not_an_iri_convention():
    from corpus_structure.semantic.native_definition_projection import definition_variant_contract

    model = SimpleNamespace(
        kinds=(
            SimpleNamespace(
                semantic_id="unrelated-name",
                facts=json_bytes({"policies": {"cs:definition_variant": "location"}}),
            ),
        )
    )
    projection = {"kinds": [{"kind": "unrelated-name", "kind_contract": "exact-kind"}]}
    assert definition_variant_contract(model, projection, "location") == "exact-kind"
    assert definition_variant_contract(model, projection, "components") is None


def test_ambiguous_variant_metadata_refuses_instead_of_selecting_first():
    from corpus_structure.semantic.native_definition_projection import definition_variant_contract

    model = SimpleNamespace(
        kinds=tuple(
            SimpleNamespace(
                semantic_id=name,
                facts=json_bytes({"json_schema": {"x-ddo-definition-variant": "components"}}),
            )
            for name in ("first", "second")
        )
    )
    with pytest.raises(ValueError, match="ambiguous"):
        definition_variant_contract(model, {"kinds": []}, "components")


def test_actual_components_schema_owns_its_public_variant():
    from corpus_structure.semantic.structural_products import DeclaredDefinitionComponentsReport

    assert (
        DeclaredDefinitionComponentsReport.model_json_schema()["x-ddo-definition-variant"]
        == "components"
    )


def test_components_subtypes_refine_the_single_variant_owner():
    from corpus_structure.semantic.structural_products import (
        DeclaredLearnedDefinitionComponentsReport,
        DeclaredNamedDefinitionComponentsReport,
        DeclaredSyntaxDefinitionComponentsReport,
    )

    for subtype in (
        DeclaredLearnedDefinitionComponentsReport,
        DeclaredNamedDefinitionComponentsReport,
        DeclaredSyntaxDefinitionComponentsReport,
    ):
        assert "x-ddo-definition-variant" not in subtype.model_json_schema()


def test_native_operation_requires_its_exact_checked_subject():
    operation = {
        "operation_id": "inspect",
        "subject_definition": "selected-source",
        "recipe": "recipe",
        "profile": "derivation",
        "validity_families": [],
        "validity_conservative": False,
        "binding": {},
        "definition": "definition",
        "eligibility": "eligibility",
        "implementation_revision": "implementation",
        "input_roles": [],
        "output_roles": [],
        "support_contract": {"replicate_policy": "deterministic-single-result"},
    }
    model, prepared = _captured(operations=[operation])
    model.operations = (
        SimpleNamespace(
            semantic_id="inspect",
            subject="selected-source",
            replicate_policy="deterministic-single-result",
            roles=(),
            validity=SimpleNamespace(families=(), conservative=False),
        ),
    )
    assert (
        read_native_definition_projection(prepared, model=model)["operations"][0][
            "subject_definition"
        ]
        == "selected-source"
    )
    model.operations = (
        SimpleNamespace(
            semantic_id="inspect",
            subject="project",
            replicate_policy="deterministic-single-result",
            roles=(),
            validity=SimpleNamespace(families=(), conservative=False),
        ),
    )
    with pytest.raises(ValueError, match="checked effective model"):
        read_native_definition_projection(prepared, model=model)


def test_native_operation_missing_subject_is_an_invalid_current_projection():
    model, prepared = _captured(
        operations=[
            {
                "operation_id": "inspect",
                "recipe": "recipe",
                "profile": "derivation",
                "binding": {},
                "definition": "definition",
                "eligibility": "eligibility",
                "implementation_revision": "implementation",
                "input_roles": [],
                "output_roles": [],
                "support_contract": {"replicate_policy": "deterministic-single-result"},
            }
        ]
    )
    with pytest.raises(ValueError, match="subject_definition"):
        read_native_definition_projection(prepared, model=model)


def test_linkml_variant_is_checked_at_its_class_owner():
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.native_definition_projection import definition_variant_contract
    from corpus_structure.semantic.types import PreparationError, SourceArtifact, SourceBundle

    source = b"""id: urn:variant-test
name: variant_test
prefixes: {ex: 'urn:variant-test:'}
default_prefix: ex
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
 Location:
  annotations: {cs:definition_variant: location}
  attributes:
   label: {range: string}
"""

    def compile_source(content):
        return compile_data_operations(
            SourceBundle("variant_test", (SourceArtifact("variant_test", content),))
        )

    model = compile_source(source)
    assert (
        definition_variant_contract(
            model,
            {"kinds": [{"kind": "urn:variant-test:Location", "kind_contract": "checked-location"}]},
            "location",
        )
        == "checked-location"
    )
    with pytest.raises(PreparationError, match="unsupported definition variant"):
        compile_source(source.replace(b"variant: location", b"variant: arbitrary"))
    with pytest.raises(PreparationError, match="native kind policies belong to classes"):
        compile_source(
            source.replace(b"  annotations: {cs:definition_variant: location}\n", b"").replace(
                b"{range: string}",
                b"{range: string, annotations: {cs:definition_variant: location}}",
            )
        )


def test_native_operation_policy_must_be_closed_and_match_checked_model():
    operation = {
        "operation_id": "inspect",
        "subject_definition": "selected-source",
        "recipe": "recipe",
        "profile": "derivation",
        "validity_families": [],
        "validity_conservative": False,
        "binding": {},
        "definition": "definition",
        "eligibility": "eligibility",
        "implementation_revision": "implementation",
        "input_roles": [],
        "output_roles": [],
        "support_contract": {"replicate_policy": "retained-observation-single-result"},
    }
    model, prepared = _captured(operations=[operation])
    model.operations = (
        SimpleNamespace(
            semantic_id="inspect",
            subject="selected-source",
            replicate_policy="retained-observation-single-result",
            roles=(),
            validity=SimpleNamespace(families=(), conservative=False),
        ),
    )
    assert (
        read_native_definition_projection(prepared, model=model)["operations"][0][
            "support_contract"
        ]["replicate_policy"]
        == "retained-observation-single-result"
    )
    operation["support_contract"]["replicate_policy"] = "invented"
    model, prepared = _captured(operations=[operation])
    model.operations = (
        SimpleNamespace(
            semantic_id="inspect",
            subject="selected-source",
            replicate_policy="retained-observation-single-result",
            roles=(),
            validity=SimpleNamespace(families=(), conservative=False),
        ),
    )
    with pytest.raises(ValueError, match="unsupported native operation replicate policy"):
        read_native_definition_projection(prepared, model=model)
