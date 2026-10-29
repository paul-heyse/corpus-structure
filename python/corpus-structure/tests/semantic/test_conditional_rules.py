from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator
from pydantic import MISSING, ConfigDict, Field, ValidationError, create_model

from corpus_structure.semantic import (
    PreparationError,
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.conditional_rules import (
    compile_conditional_rules,
    conditional_model_namespace,
)
from corpus_structure.semantic.prepare import _view, preview_schema

PROFILE = PreparationProfile(version="semantic-2")


def rule():
    return {
        "preconditions": {"slot_conditions": {"status": {"equals_string": "ready"}}},
        "postconditions": {"slot_conditions": {"label": {"required": True}}},
        "elseconditions": {"slot_conditions": {"reason": {"required": True}}},
    }


def schema(rules=None) -> dict[str, Any]:
    return {
        "id": "https://example.org/conditional",
        "name": "conditional",
        "prefixes": {"ex": "https://example.org/", "xsd": "http://www.w3.org/2001/XMLSchema#"},
        "default_prefix": "ex",
        "types": {
            "string": {"base": "str", "uri": "xsd:string"},
            "decimal": {"base": "Decimal", "uri": "xsd:decimal"},
            "date": {"base": "XSDDate", "uri": "xsd:date"},
        },
        "classes": {
            "Thing": {
                "attributes": {
                    "id": {"identifier": True},
                    "status": {"range": "string"},
                    "label": {"range": "string"},
                    "reason": {"range": "string"},
                    "amount": {"range": "decimal"},
                    "when": {"range": "date"},
                },
                "rules": [rule()] if rules is None else rules,
            }
        },
    }


def bundle(data):
    return SourceBundle(
        "conditional", (SourceArtifact("conditional", yaml.safe_dump(data).encode()),)
    )


def prepare(data=None):
    return prepare_release(
        bundle(schema() if data is None else data),
        composed_dependencies(ResolvedDependencies()),
        profile=PROFILE,
    )


def test_native_compiler_and_namespace_without_release_admission():
    fragments = compile_conditional_rules(_view(bundle(schema()), PROFILE))
    assert fragments["Thing"] == {
        "if": {"properties": {"status": {"const": "ready"}}, "required": ["status"]},
        "then": {"properties": {"label": {}}, "required": ["label"]},
        "else": {"properties": {"reason": {}}, "required": ["reason"]},
    }
    model = create_model(
        "DirectRuleBoundary",
        __config__=ConfigDict(strict=True),
        __namespace__=conditional_model_namespace(fragments["Thing"]),
        status=(str, Field(default=MISSING)),
        label=(str, Field(default=MISSING)),
        reason=(str, Field(default=MISSING)),
        amount=(Decimal, Field(default=MISSING)),
        when=(date, Field(default=MISSING)),
    )
    value = model.model_validate(
        {
            "status": "ready",
            "label": "",
            "amount": Decimal("1.0000000000000001"),
            "when": date(2026, 10, 29),
        }
    )
    assert value.model_dump()["amount"] == Decimal("1.0000000000000001")
    assert value.model_dump()["when"] == date(2026, 10, 29)
    assert value.model_fields_set == {"status", "label", "amount", "when"}
    with pytest.raises(ValidationError, match="conditional rule"):
        model.model_validate({"status": "ready"})
    assert model.model_json_schema()["if"] == fragments["Thing"]["if"]


def test_native_aliases_follow_each_inherited_class():
    data = schema()
    data["classes"]["Thing"]["attributes"]["status"]["alias"] = "state"
    data["classes"]["Child"] = {
        "is_a": "Thing",
        "slot_usage": {"status": {"alias": "child_state"}},
    }
    fragments = compile_conditional_rules(_view(bundle(data), PROFILE))
    assert fragments["Thing"]["if"]["properties"] == {"state": {"const": "ready"}}
    assert fragments["Child"]["if"]["properties"] == {"child_state": {"const": "ready"}}


def test_colliding_boundary_aliases_refuse():
    data = schema()
    data["classes"]["Thing"]["attributes"]["label"]["alias"] = "status"
    with pytest.raises(PreparationError, match="aliases must be unique"):
        compile_conditional_rules(_view(bundle(data), PROFILE))


@pytest.mark.parametrize(
    "value,valid",
    [
        ({"id": "a", "status": "ready", "label": "yes"}, True),
        ({"id": "a", "status": "ready"}, False),
        ({"id": "a", "status": "ready", "reason": "no"}, False),
        ({"id": "a", "status": "pending", "reason": "why"}, True),
        ({"id": "a", "status": "pending", "label": "yes"}, False),
        ({"id": "a", "reason": "missing status"}, True),
        ({"id": "a"}, False),
        ({"id": "a", "status": "", "reason": "empty status"}, True),
        ({"id": "a", "status": "ready", "label": ""}, True),
        ({"id": "a", "status": None, "reason": "null"}, False),
        ({"id": "a", "status": "ready", "label": None}, False),
    ],
)
def test_branches_presence_null_and_export_parity(value, valid):
    release = prepare()
    adapter = dict(release._adapters)["Thing"]
    exported = adapter.json_schema()
    assert Draft202012Validator(exported).is_valid(value) is valid
    if valid:
        validated = release.validate_json("Thing", json.dumps(value))
        assert validated.model_dump(exclude_unset=True, by_alias=True) == value
    else:
        with pytest.raises(ValidationError):
            release.validate_json("Thing", json.dumps(value))


def test_exact_python_scalars_and_fields_set_survive_rule_validation():
    release = prepare()
    amount = Decimal("123456789012345678901234567890.01234567890123456789")
    when = date(2026, 10, 29)
    adapter = dict(release._adapters)["Thing"]
    value = adapter.validate_python(
        {"id": "a", "status": "ready", "label": "", "amount": amount, "when": when}
    )
    assert vars(value)["amount"] is amount
    assert vars(value)["when"] is when
    assert value.model_fields_set == {"id", "status", "label", "amount", "when"}
    assert value.model_dump(by_alias=True, exclude_unset=True)["amount"] == amount
    assert "reason" not in value.model_dump(by_alias=True, exclude_unset=True)
    json_value = release.validate_json(
        "Thing",
        json.dumps(
            {"id": "a", "status": "ready", "label": "", "amount": str(amount), "when": str(when)}
        ),
    )
    assert json_value.model_dump()["amount"] == amount
    assert json_value.model_dump()["when"] == when


def test_native_fragment_is_archived_and_reused_in_model_schema():
    release = prepare()
    artifacts = {
        artifact.kind: json.loads(artifact.content)
        for artifact in release.artifacts
        if artifact.kind.endswith(".json")
    }
    native = compile_conditional_rules(_view(bundle(schema()), PROFILE))
    assert artifacts["conditional_rules.json"] == native
    adapter = dict(release._adapters)["Thing"]
    exported = adapter.json_schema()
    assert {key: exported[key] for key in native["Thing"]} == native["Thing"]
    assert artifacts["conditional_rule_options.json"]["include_null"] is False
    assert artifacts["conditional_rule_coverage.json"]["shacl"] == "not_lowered"


def test_native_inheritance_multiple_rules_and_aliases():
    data = schema()
    data["classes"]["Thing"]["attributes"]["status"]["alias"] = "state"
    data["classes"]["Thing"]["attributes"]["label"]["alias"] = "display"
    data["classes"]["Child"] = {
        "is_a": "Thing",
        "rules": [
            {
                "preconditions": {
                    "slot_conditions": {"status": {"equals_string_in": ["ready", "pending"]}}
                },
                "postconditions": {"slot_conditions": {"amount": {"required": True}}},
            }
        ],
    }
    release = prepare(data)
    adapter = dict(release._adapters)["Child"]
    valid = {"id": "a", "state": "ready", "display": "yes", "amount": Decimal("1")}
    assert adapter.validate_python(valid).model_dump()["status"] == "ready"
    with pytest.raises(ValidationError, match="conditional rule"):
        adapter.validate_python({"id": "a", "state": "ready", "amount": Decimal("1")})
    with pytest.raises(ValidationError, match="conditional rule"):
        adapter.validate_python({"id": "a", "state": "ready", "display": "yes"})
    native = json.loads(
        next(a.content for a in release.artifacts if a.kind == "conditional_rules.json")
    )
    assert len(native["Child"]["allOf"]) == 2
    assert "state" in native["Thing"]["if"]["properties"]
    assert "display" in native["Thing"]["then"]["properties"]


def test_explicit_presence_absence_conjunction_and_open_world():
    rules = [
        {
            "preconditions": {
                "slot_conditions": {
                    "status": {"value_presence": "PRESENT"},
                    "reason": {"value_presence": "ABSENT"},
                }
            },
            "postconditions": {"slot_conditions": {"label": {"equals_string_in": ["ok", ""]}}},
            "open_world": True,
        }
    ]
    release = prepare(schema(rules))
    release.validate_json("Thing", '{"id":"a","status":"x"}')
    release.validate_json("Thing", '{"id":"a","status":"x","label":""}')
    release.validate_json("Thing", '{"id":"a","status":"x","reason":"y","label":"other"}')
    with pytest.raises(ValidationError):
        release.validate_json("Thing", '{"id":"a","status":"x","label":"other"}')


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update(bidirectional=True),
        lambda r: r.update(deactivated=False),
        lambda r: r.update(preconditions={}),
        lambda r: r["preconditions"].update(any_of=[{}]),
        lambda r: r["preconditions"]["slot_conditions"].update(status={}),
        lambda r: r["preconditions"]["slot_conditions"].update(status={"equals_string": True}),
        lambda r: r["preconditions"]["slot_conditions"].update(
            status={"equals_string_in": ["yes", False]}
        ),
        lambda r: r["postconditions"]["slot_conditions"].update(label={"range": "string"}),
        lambda r: r["postconditions"]["slot_conditions"].update(label={"minimum_cardinality": 1}),
        lambda r: r["postconditions"]["slot_conditions"].update(
            label={"any_of": [{"equals_string": "x"}]}
        ),
        lambda r: r["postconditions"]["slot_conditions"].update(missing={"required": True}),
        lambda r: r["preconditions"]["slot_conditions"].update(
            status={"value_presence": "ABSENT"}, label={"value_presence": "ABSENT"}
        ),
        lambda r: r["postconditions"]["slot_conditions"].update(label={"required": "true"}),
        lambda r: r["postconditions"]["slot_conditions"].update(
            label={"required": True, "alias": "other"}
        ),
    ],
)
def test_unsupported_rules_refuse_without_erasing_fields(mutate):
    candidate = rule()
    mutate(candidate)
    data = schema([candidate])
    original = deepcopy(data)
    with pytest.raises(PreparationError) as error:
        compile_conditional_rules(_view(bundle(data), PROFILE))
    assert error.value.diagnostics[0].outcome == "unsupported"
    assert data == original


def test_scalar_string_choice_and_multivalued_refusals():
    data = schema()
    data["classes"]["Thing"]["attributes"]["status"]["range"] = "decimal"
    with pytest.raises(PreparationError, match="scalar string"):
        compile_conditional_rules(_view(bundle(data), PROFILE))
    data = schema()
    data["classes"]["Thing"]["attributes"]["status"]["multivalued"] = True
    with pytest.raises(PreparationError, match="multivalued"):
        compile_conditional_rules(_view(bundle(data), PROFILE))


def test_semantic_1_and_preview_keep_refusing_rules():
    source = bundle(schema())
    with pytest.raises(PreparationError):
        prepare_release(source)
    with pytest.raises(PreparationError):
        preview_schema(source)
    data = schema()
    del data["classes"]["Thing"]["rules"]
    baseline = prepare_release(bundle(data))
    baseline.validate_json("Thing", '{"id":"a"}')
    assert all(a.kind != "conditional_rules.json" for a in baseline.artifacts)


def test_native_rule_atoms_preserve_alias_presence_and_branch_scope():
    from corpus_structure.semantic.conditional_rules import compile_native_conditionals

    data = schema()
    data["classes"]["Thing"]["attributes"]["status"]["alias"] = "state"
    view = _view(bundle(data), PROFILE)
    rows = compile_native_conditionals(view, compile_conditional_rules(view), "accepted_value")
    assert len(rows) == 1
    assert rows[0]["scope"] == "accepted_value"
    assert rows[0]["branches"] == {
        "if": [{"property": "status", "presence": "present", "choices": None},
               {"property": "status", "presence": "optional", "choices": ["ready"]}],
        "then": [{"property": "label", "presence": "present", "choices": None}],
        "else": [{"property": "reason", "presence": "present", "choices": None}],
    }
