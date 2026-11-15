"""The shared read boundary rejects ambiguous and mismatched captured projections."""

from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.native_definition_projection import read_native_definition_projection


def test_native_projection_preserves_actual_timezone_aware_datetime_meaning():
    from datetime import UTC, datetime

    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.data_operation_storage import kind_meaning_schema
    from corpus_structure.semantic.data_operation_wire import validate_wire_schema
    from corpus_structure.semantic.types import ResolvedDependencies

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
        identities=(
            SimpleNamespace(owner="primitive:string", domain="kind", key="kind:string"),
        ),
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
                "families": [],
                "universe": "ordinary",
            }
        ] if operations else [],
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


def test_native_operation_requires_its_exact_checked_subject():
    operation = {
        "operation_id": "inspect",
        "subject_definition": "selected-source",
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
    model, prepared = _captured(operations=[operation])
    model.operations = (
        SimpleNamespace(
            semantic_id="inspect",
            subject="selected-source",
            replicate_policy="deterministic-single-result",
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
            semantic_id="inspect", subject="project", replicate_policy="deterministic-single-result"
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
        ),
    )
    with pytest.raises(ValueError, match="unsupported native operation replicate policy"):
        read_native_definition_projection(prepared, model=model)
