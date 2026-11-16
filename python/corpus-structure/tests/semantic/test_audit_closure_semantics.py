"""Independent expectations for released subsets, projections and source attribution."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.identity import claim_source_item
from corpus_structure.semantic.refusals import (
    SemanticOperationRefusal,
    SemanticReason,
    semantic_failure_fields,
)
from corpus_structure.semantic.rule_views import project_rule_value
from corpus_structure.semantic.unicode_identity import identity_casefold
from semantic.proposals_support import batch, prepared


def test_source_subset_is_narrower_than_storage_and_generated_boundary():
    release = prepared()
    assert release.source_establishments() == {"stated", "agent_asserted"}
    assert release.enum_members("Establishment") == {"stated", "agent_asserted", "derived"}
    from corpus_structure.semantic.identity import canonical_bytes

    raw = batch()
    release.validate_json("AgentAuthoredBatch", canonical_bytes(raw))
    raw["claims"][0]["establishment"] = "derived"
    with pytest.raises(ValidationError) as refused:
        release.validate_json("AgentAuthoredBatch", canonical_bytes(raw))
    assert any(error["loc"] == ("claims", 0, "establishment") for error in refused.value.errors())


def test_expression_projection_keeps_declared_enum_and_expression_form():
    release = prepared()
    expression = {
        "kind": "expression",
        "form": "formula",
        "language": "latex",
        "expression": "x = y",
    }
    view = project_rule_value(release, "Value", expression)
    assert (view.value_kind, view.declared_range, view.expression_form) == (
        "expression",
        "Value",
        "formula",
    )
    assert view.defined_symbol == "x" and view.reading_status == "unavailable"
    enum = project_rule_value(release, "StatementRole", {"kind": "text", "text": "premise"})
    assert enum.enum_id == "StatementRole" and enum.v == "premise"
    assert enum.declared_range == "StatementRole"
    assert (
        project_rule_value(
            release, "Value", {"kind": "missing", "reason": "unknown"}
        ).reading_status
        == "missing"
    )
    assert project_rule_value(release, "Value", None) is None


def test_reason_identity_does_not_depend_on_human_wording():
    reason = SemanticReason(
        "missing_operands", "scientific_policy", "release:test", ("occ:1",), detail="operand absent"
    )
    first, second = (
        SemanticOperationRefusal(reason),
        SemanticOperationRefusal(replace(reason, detail="no operand")),
    )
    assert first.reason == second.reason == "missing_operands"
    assert semantic_failure_fields(first)["semantic_reason"]["references"] == ("occ:1",)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Straße", "strasse"),
        ("\u03a3\u03c2\u03c3", "\u03c3\u03c3\u03c3"),
        ("\u0130I\u0131", "i\u0307i\u0131"),
        ("ﬃ", "ffi"),
        ("É", "é"),
        ("E\u0301", "e\u0301"),
    ],
)
def test_default_casefold_has_no_implicit_normalization(text, expected):
    assert identity_casefold(text) == expected


@pytest.mark.parametrize("value", ["a\0b", "\ud800"])
def test_identity_refuses_strings_outside_the_qualified_database_domain(value):
    with pytest.raises(SemanticOperationRefusal, match="unsupported interpretation"):
        identity_casefold(value)


def test_ordinary_addresses_keep_their_own_mechanical_abi():
    assert [claim_source_item(i) for i in (0, 9, 12)] == ["claims/0", "claims/9", "claims/12"]
    with pytest.raises(ValueError):
        claim_source_item(True)


def test_renamed_display_properties_follow_authored_order():
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release

    raw = b"""id: https://example.org/display
name: display
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types: {string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}}
classes:
  Thing:
    attributes:
      id: {identifier: true}
      caption: {annotations: {cs:role: display, cs:display_order: 2}}
      alternate_names: {multivalued: true, annotations: {cs:role: display, cs:display_order: 3}}
"""
    release = prepare_release(SourceBundle("display", (SourceArtifact("display", raw),)))
    assert [prop.name for prop in release.display_properties("Thing")] == [
        "caption",
        "alternate_names",
    ]
    assert [prop.name for prop in release.display_properties("https://example.org/Thing")] == [
        "caption",
        "alternate_names",
    ]


def test_logical_reading_dimensions_are_owned_by_the_archived_rule_schema():
    from corpus_structure.semantic.rule_views import Reading, ValueView
    from semantic.scientific_rule_views_support import language

    lang = language()
    rule = lang.compile("reading", 'claim.value&.parse == "ok"')
    assert rule.evaluate(
        {"claim": SimpleNamespace(value=ValueView("text", None, "x", None, "text", Reading("ok")))}
    )
    with pytest.raises(ValidationError):
        rule.evaluate(
            {
                "claim": SimpleNamespace(
                    value=ValueView("text", None, "x", None, "text", Reading("invented"))
                )
            }
        )


def test_persisted_scientific_reason_is_typed_and_original_abi_stays_readable():
    import json

    from corpus_structure.semantic.scientific_evidence import scientific_assessment_reason
    from corpus_structure.semantic.scientific_evidence_schema import (
        parse_scientific_assessment_reason,
    )

    reason = SemanticReason(
        "incompatible_bindings",
        "scientific_policy",
        "release:test",
        ("occ:a", "occ:b"),
        detail="bindings differ",
    )
    serialized = scientific_assessment_reason(
        None, detail="undecided", context={}, semantic_reason=reason
    )
    opened = parse_scientific_assessment_reason(serialized)
    assert opened is not None
    assert opened.abi == "scientific-assessment-evidence-2"
    assert opened.semantic_reason == reason
    original = json.loads(serialized)
    original["abi"] = "scientific-assessment-evidence-1"
    original.pop("semantic_reason")
    historical = parse_scientific_assessment_reason(json.dumps(original))
    assert historical is not None and historical.semantic_reason is None
    original["semantic_reason"] = json.loads(serialized)["semantic_reason"]
    with pytest.raises(ValidationError, match="original scientific evidence ABI"):
        parse_scientific_assessment_reason(json.dumps(original))


def test_projection_keeps_missing_and_unsupported_reading_meaning_separate():
    release = prepared()
    missing = project_rule_value(release, "Value", {"kind": "missing", "reason": "explicit_null"})
    assert missing.missing_reason == "explicit_null" and missing.reading_status == "missing"
    unsupported = project_rule_value(
        release,
        "Value",
        {"kind": "expression", "form": "formula", "language": "python", "expression": "x = y"},
    )
    assert unsupported.expression_content == "x = y" and unsupported.expression_language == "python"
    assert unsupported.reading_status == "unsupported" and unsupported.defined_symbol is None


def test_rule_scalar_enum_and_complete_qualification_projection_share_binding_meaning():
    from semantic.scientific_rule_views_support import language

    release = prepared()
    projected = project_rule_value(release, "StatementRole", "premise")
    lang = language()
    rule = lang.compile(
        "enum_metadata",
        'claim.qualification_values["role"].enum_id == "StatementRole" and '
        'claim.qualification_values["role"].declared_range == "StatementRole"',
    )
    assert rule.evaluate({"claim": SimpleNamespace(qualification_values={"role": projected})})


def test_folding_requirement_comes_from_prepared_identity_qualification_and_class_bindings():
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.types import RegistryRow
    from corpus_structure.semantic.unicode_identity import requires_unicode_identity

    release = prepared()
    assert not requires_unicode_identity(release)
    definition = next(d for d in release.definitions if d.name == "Person")
    label_bound = replace(
        release,
        registry_rows=(
            *release.registry_rows,
            RegistryRow(
                "operation_class",
                "Person",
                canonical_bytes({"class": "Person", "cs:case": "casefold"}),
            ),
        ),
    )
    assert requires_unicode_identity(label_bound)
    keyed = replace(
        definition,
        identity_groups=(("name",),),
        properties=tuple(
            replace(prop, case_policy="casefold") if prop.name == "name" else prop
            for prop in definition.properties
        ),
    )
    assert requires_unicode_identity(
        replace(
            release, definitions=tuple(keyed if d == definition else d for d in release.definitions)
        )
    )


@pytest.mark.parametrize(
    "code",
    [
        "missing_operands",
        "unsupported_interpretation",
        "incompatible_bindings",
        "preparation_failed",
    ],
)
def test_cli_and_mcp_render_the_same_owned_semantic_reason(code):
    import json

    import typer
    from fastmcp.exceptions import ToolError
    from typer.testing import CliRunner

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.refusals import located_failure_context, tool_refusals

    release = prepared()
    reason = SemanticReason(
        code, "evaluate", release.release_id, ("occ:source",), detail="human wording can change"
    )

    @tool_refusals()
    def invoke():
        with located_failure_context(release, "evaluate"):
            raise SemanticOperationRefusal(reason)

    with pytest.raises(ToolError) as error:
        invoke()
    tool = json.loads(str(error.value))
    assert tool["code"] == code
    assert tool["semantic_reason"]["operation"] == "evaluate"
    assert tool["semantic_reason"]["release_id"] == release.release_id
    assert tool["semantic_reason"]["references"] == ["occ:source"]
    application = typer.Typer()

    @application.command()
    def command():
        with failure_boundary(True) as context:
            context.bind(release, "evaluate")
            raise SemanticOperationRefusal(reason)

    result = CliRunner().invoke(application, [])
    assert result.exit_code == 1
    cli = json.loads(result.stdout)["error"]
    assert cli["code"] == code and cli["semantic_reason"] == tool["semantic_reason"]


def test_new_expression_form_spelling_uses_released_symbol_behavior():
    from pathlib import Path

    import yaml

    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.rule_views import binding_symbols

    core = yaml.safe_load(
        (Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml").read_bytes()
    )
    core["enums"]["ExpressionForm"]["permissible_values"]["assignment"] = {
        "in_subset": ["symbol_definition", "binding_symbol_expression"]
    }
    release = prepare_release(
        SourceBundle(
            "semantic_core", (SourceArtifact("semantic_core", yaml.safe_dump(core).encode()),)
        )
    )
    definition = {
        "kind": "expression",
        "form": "assignment",
        "language": "latex",
        "expression": "x = y",
    }
    validated = release.validate_json("Value", canonical_bytes(definition))
    projected = project_rule_value(release, "Value", validated)
    assert projected.expression_form == "assignment" and projected.defined_symbol == "x"
    symbol = {**definition, "expression": "x"}
    assert binding_symbols(release, "Value", (symbol,)) == {"x"}
