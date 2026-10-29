"""Independent protocol and placement cases exercise public preparation/validation."""

import json
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from corpus_structure.semantic import (
    PreparationError,
    PreparationProfile,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.statement_types import effective_bindings, statement_definition
from corpus_structure.semantic.types import ResolvedDependencies

from .test_conditional_rules import bundle, schema


def statement_schema() -> dict[str, Any]:
    return {
        "id": "https://example.org/binding",
        "name": "binding",
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "types": {"string": {"base": "str"}, "integer": {"base": "int"}},
        "enums": {"StatementKind": {"permissible_values": {"claim": {}, "proof": {}}}},
        "classes": {
            "SourceStatement": {
                "attributes": {
                    "id": {"identifier": True},
                    "locator": {"required": True},
                    "statement_kind": {"range": "StatementKind"},
                }
            },
            "NarrowStatement": {
                "is_a": "SourceStatement",
                "attributes": {"supports": {"range": "NarrowStatement", "multivalued": True}},
            },
            "AgentStatementBinding": {"attributes": {"statement": {"range": "NarrowStatement"}}},
            "Unrelated": {"attributes": {"id": {"identifier": True}}},
        },
    }


def prepare_statement(data: dict[str, Any]):
    return prepare_release(
        SourceBundle("binding", (SourceArtifact("binding", yaml.safe_dump(data).encode()),))
    )


def test_effective_binding_is_archived_and_reference_positions_preserve_shape():
    prepared = prepare_statement(statement_schema())
    binding = effective_bindings(prepared)
    assert statement_definition(prepared).name == "NarrowStatement"
    assert binding["statement"]["class_iri"] == "https://example.org/NarrowStatement"
    position = next(
        p
        for p in binding["references"]
        if p["class_name"] == "NarrowStatement" and p["property_name"] == "supports"
    )
    assert (position["kind"], position["collection"], position["range"]) == (
        "class",
        "sequence",
        "NarrowStatement",
    )
    row = next(r for r in prepared.registry_rows if r.kind == "effective_bindings")
    assert json.loads(row.body) == binding


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "unrelated",
        "multivalued",
        "identifier",
        "locator_type",
        "locator_optional",
        "kind_range",
    ],
)
def test_malformed_statement_binding_refuses_during_public_preparation(defect):
    data = statement_schema()
    statement = data["classes"]["AgentStatementBinding"]["attributes"]["statement"]
    base = data["classes"]["SourceStatement"]["attributes"]
    if defect == "missing":
        del data["classes"]["AgentStatementBinding"]["attributes"]["statement"]
    elif defect == "unrelated":
        statement["range"] = "Unrelated"
    elif defect == "multivalued":
        statement["multivalued"] = True
    elif defect == "identifier":
        base["id"] = {}
    elif defect == "locator_type":
        base["locator"]["range"] = "integer"
    elif defect == "locator_optional":
        base["locator"]["required"] = False
    else:
        base["statement_kind"]["range"] = "string"
    with pytest.raises(PreparationError, match=r"statement|locator"):
        prepare_statement(data)


def test_accepted_conditions_do_not_reject_submission_and_missing_context_is_structural():
    prepared = prepare_release(
        bundle(schema()),
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2", constraint_scope="accepted_value"),
    )
    raw = {"id": "thing", "status": "ready"}
    assert prepared.validate_python("Thing", raw).model_dump()["status"] == "ready"
    assert dict(prepared._adapters)["Thing"].validate_python(raw).model_dump()["status"] == "ready"
    assert "if" not in prepared.json_schema("Thing")
    with pytest.raises(ValidationError, match="conditional rule"):
        prepared.validate_accepted_python("Thing", raw)
    assert (
        prepared.validate_accepted_python("Thing", {**raw, "label": "accepted"}).model_dump()[
            "label"
        ]
        == "accepted"
    )


def test_accepted_field_constraints_are_enforced_only_at_accepted_entrypoint():
    data = schema()
    data["classes"]["Thing"].pop("rules")
    data["classes"]["Thing"]["attributes"]["amount"].update({"minimum_value": 1, "required": True})
    prepared = prepare_release(
        bundle(data),
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2", constraint_scope="accepted_value"),
    )
    assert prepared.validate_json("Thing", '{"id":"x","amount":"0"}').model_dump()["amount"] == 0
    with pytest.raises(ValidationError, match="below minimum"):
        prepared.validate_accepted_json("Thing", '{"id":"x","amount":"0"}')
    with pytest.raises(ValidationError, match="requires Thing/amount"):
        prepared.validate_accepted_python("Thing", {"id": "x"})


def test_binding_refusal_identifies_its_owner_and_actionable_repair():
    data = statement_schema()
    data["classes"]["AgentStatementBinding"]["attributes"]["statement"]["range"] = "Unrelated"
    with pytest.raises(PreparationError) as raised:
        prepare_statement(data)
    diagnostic = raised.value.diagnostics[0]
    assert diagnostic.contract_id == "source_statement_binding"
    assert diagnostic.location == "AgentStatementBinding/statement"
    assert diagnostic.actual == "'Unrelated'"
    assert diagnostic.consumer and "native_source_guard" in diagnostic.consumer
    assert diagnostic.remedy and "new candidate release" in diagnostic.remedy


def test_property_adapters_reuse_public_boundary_fields():
    release = prepare_statement(statement_schema())
    first = release.property_adapter("NarrowStatement", "supports", item=True)
    assert first is release.property_adapter("NarrowStatement", "supports", item=True)
    assert first.validate_python("statement:target", strict=True) == "statement:target"
