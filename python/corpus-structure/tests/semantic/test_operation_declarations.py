"""Independent controls for the declared operation grammar and openness contracts."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Literal

import pytest
import yaml

from corpus_structure.model.compiled import compiled_model, running_model
from corpus_structure.schema.operation_declarations import (
    check_declared_openness,
    check_literal_members,
    vocabulary,
)
from corpus_structure.schema.operation_declarations import (
    declarations as grammar,
)
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.operation_reporting import validation_report
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import (
    PreparationError,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from semantic.data_operation_declaration_support import contract, declarations


def operation(**changes):
    value = contract(**changes)
    value["capabilities"] = {
        **value["capabilities"],
        "preparation": "resource",
        "ownership": "immutable",
    }
    return value


def changed_model(source_name, update):
    sources = dict(running_model().sources)
    document = yaml.safe_load(sources[source_name])
    update(document)
    sources[source_name] = yaml.safe_dump(document).encode()
    return compiled_model(sources)


@pytest.mark.parametrize("field", ["precision", "profile_alias"])
def test_extra_top_level_fields_refuse(field):
    with pytest.raises(PreparationError, match="unsupported fields: " + field):
        compile_data_operations(declarations=declarations(operation(**{field: "extra"})))


def test_nested_record_is_closed_and_located():
    value = operation()
    value["roles"][0]["extra"] = True
    with pytest.raises(PreparationError, match="unsupported fields: extra") as caught:
        compile_data_operations(declarations=declarations(value))
    assert caught.value.diagnostics[0].location.endswith("/roles/0")


def test_closed_profile_refuses_but_descriptive_terms_remain_open():
    with pytest.raises(PreparationError, match="profile"):
        compile_data_operations(declarations=declarations(operation(profile="experimental")))
    value = operation()
    value["capabilities"].update(ownership="experimental-shared", preparation="new-preparation")
    value["capabilities"]["cancellation"] = "arbitrary description without an interpreter"
    model = compile_data_operations(declarations=declarations(value))
    assert [(item.code, item.outcome) for item in model.diagnostics] == [
        ("ownership_unknown_term", "advisory"),
        ("preparation_unknown_term", "advisory"),
    ]
    assert model.operations[0].capabilities.ownership == "experimental-shared"
    assert (
        model.operations[0].capabilities.cancellation
        == "arbitrary description without an interpreter"
    )


def test_declared_form_perturbation_changes_actual_compiler_acceptance():
    changed = changed_model(
        "operation-vocabularies.yaml",
        lambda value: value["enums"]["Form"]["permissible_values"].update(vector={}),
    )
    value = operation()
    value["capabilities"]["forms"] = ["vector"]
    with pytest.raises(PreparationError):
        compile_data_operations(declarations=declarations(value))
    model = compile_data_operations(declarations=declarations(value), declaration_model=changed)
    assert model.operations[0].capabilities.forms == ("vector",)
    with pytest.raises(ValueError, match=r"missing=.*vector"):
        check_literal_members("Form", Literal["scalar", "batch", "stream"], changed)


def test_release_preparation_uses_the_captured_vocabulary():
    changed = changed_model(
        "operation-vocabularies.yaml",
        lambda value: value["enums"]["Ownership"]["permissible_values"].update(captured={}),
    )
    value = operation()
    value["capabilities"]["ownership"] = "captured"
    schema = SourceBundle(
        "test.yaml",
        (SourceArtifact("test.yaml", b"id: https://example.org/test\nname: test\nclasses: {}\n"),),
    )
    original = prepare_release(
        schema, data_operation_dependencies(ResolvedDependencies(), declarations(value))
    )
    prepared = prepare_release(
        schema,
        data_operation_dependencies(
            ResolvedDependencies(), declarations(value), declaration_model=changed
        ),
    )
    assert [item.code for item in original.diagnostics] == ["ownership_unknown_term"]
    assert prepared.diagnostics == ()
    assert prepared.release_id != original.release_id


def test_recommended_validity_warning_has_one_nonrefusing_owner():
    changed = changed_model(
        "operation-declarations.yaml",
        lambda value: value["classes"]["DataOperationDeclaration"]["attributes"][
            "validity_family"
        ].update(recommended=True),
    )
    missing = compile_data_operations(
        declarations=declarations(operation()), declaration_model=changed
    )
    assert [(item.code, item.outcome) for item in missing.diagnostics] == [
        ("validity_undetermined", "advisory")
    ]
    explicit = compile_data_operations(
        declarations=declarations(operation(validity_family=["none"])), declaration_model=changed
    )
    assert explicit.diagnostics == ()
    # The claim rollout remains UDM-05's: current existing declarations are not warned early.
    assert compile_data_operations(declarations=declarations(operation())).diagnostics == ()


def test_preparation_retains_nonrefusing_diagnostics_for_its_report():
    value = operation()
    value["capabilities"]["ownership"] = "experimental-shared"
    schema = SourceBundle(
        "test.yaml",
        (SourceArtifact("test.yaml", b"id: https://example.org/test\nname: test\nclasses: {}\n"),),
    )
    dependencies = data_operation_dependencies(ResolvedDependencies(), declarations(value))
    prepared = prepare_release(schema, dependencies)
    assert [(item.code, item.outcome) for item in prepared.diagnostics] == [
        ("ownership_unknown_term", "advisory")
    ]
    report = validation_report(prepared.diagnostics, prepared=prepared).model_dump(mode="json")
    assert report["complete"] is False
    assert report["observations"][0]["category"] == "unassessed"
    assert report["observations"][0]["code"] == "ownership_unknown_term"


def test_diagnostics_are_not_semantic_model_archive_fields():
    value = operation()
    value["capabilities"]["ownership"] = "experimental-shared"
    model = compile_data_operations(declarations=declarations(value))
    assert model.diagnostics
    assert b'"diagnostics"' not in model.content
    from corpus_structure.semantic.data_operation_model import read_effective_data_operations

    restored = read_effective_data_operations(model.content)
    assert restored.content == model.content
    assert restored.diagnostics == ()


@pytest.mark.parametrize("openness,refuses", [("closed", True), ("pack-extensible", False)])
def test_released_pack_extension_follows_declared_openness(openness, refuses):
    base = {
        "id": "https://example.org/base",
        "name": "base",
        "enums": {
            "Base": {"annotations": {"cs:openness": openness}, "permissible_values": {"known": {}}}
        },
    }
    pack = {
        "id": "https://example.org/pack",
        "name": "pack",
        "imports": ["base"],
        "enums": {"Extended": {"inherits": ["Base"], "permissible_values": {"new": {}}}},
    }
    sources = {"base": yaml.safe_dump(base).encode(), "pack": yaml.safe_dump(pack).encode()}
    bundle = SourceBundle(
        "pack", tuple(SourceArtifact(name, body) for name, body in sources.items())
    )
    if refuses:
        with pytest.raises(PreparationError, match="cannot extend closed vocabulary Base"):
            prepare_release(bundle)
    else:
        prepared = prepare_release(bundle)
        assert {
            member.value
            for item in prepared.vocabularies
            if item.enum == "Extended"
            for member in item.members
        } == {"known", "new"}


@pytest.mark.parametrize(
    "enum_name,slot",
    [
        ("Ownership", {"range": "Ownership"}),
        ("Profile", {"any_of": [{"range": "Profile"}, {"range": "string"}]}),
    ],
)
def test_declared_openness_cannot_disagree_with_range(enum_name, slot):
    model = changed_model(
        "operation-declarations.yaml",
        lambda value: value["classes"].update(Bad={"attributes": {"value": slot}}),
    )
    with pytest.raises(PreparationError, match="vocabulary"):
        check_declared_openness(model.private_view("operation-declarations.yaml"))


def test_projection_reuses_one_validator_and_reports_provisional_members():
    assert grammar() is grammar()
    assert vocabulary("Ownership").openness == "open"
    assert dict(vocabulary("Ownership").statuses)["immutable"] is None
    assert dict(vocabulary("Ownership").statuses)["owned-pdf-build"] == "provisional"


def test_current_complete_python_literals_follow_the_declared_structural_grammar():
    root = Path(__file__).parents[2] / "src/corpus_structure"
    observed = []
    unknown_terms = set()
    for path in root.rglob("*.py"):
        source = path.read_text()
        if "__data_operation__" not in source:
            continue
        for node in ast.walk(ast.parse(source)):
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
                if isinstance(node, ast.AnnAssign)
                else []
            )
            if not any(
                isinstance(target, ast.Name) and target.id.endswith("__data_operation__")
                for target in targets
            ):
                continue
            assert isinstance(node, (ast.Assign, ast.AnnAssign))
            assert node.value is not None
            value = ast.literal_eval(node.value)
            # Abstract and inherited overlays are combined by the independently
            # tested closed Python front end, not complete declaration records.
            if value.get("abstract") or "id" not in value or "role_overrides" in value:
                continue
            observed.append(value["id"])
            unknown_terms.update(
                (item.code, item.message) for item in grammar().validate(value, value["id"])
            )
    assert "text.compose_view/full-native" in observed
    assert "reference.snapshot/declared" in observed
    assert unknown_terms == {
        ("preparation_unknown_term", "open vocabulary term is not assessed: schema")
    }


def test_enum_only_import_does_not_create_physical_tables_or_columns():
    sources = dict(running_model().sources)
    document = yaml.safe_load(sources["physical.yaml"])
    document["imports"].append("operation-vocabularies")
    sources["physical.yaml"] = yaml.safe_dump(document, sort_keys=False).encode()
    ordinary = running_model().physical()
    candidate = compiled_model(sources).physical()
    assert {(name, tuple(table.columns.keys())) for name, table in candidate.tables.items()} == {
        (name, tuple(table.columns.keys())) for name, table in ordinary.tables.items()
    }


def test_pdf_capture_and_native_contract_share_one_outcome_vocabulary():
    from corpus_structure.semantic.pdf_capture import pdf_capture_inputs

    bundle = pdf_capture_inputs(
        SourceBundle("core", (SourceArtifact("core", running_model().sources["core.yaml"]),))
    )
    prepared = prepare_release(bundle)
    outcome = next(item for item in prepared.vocabularies if item.enum == "PdfObservationOutcome")
    assert {member.value for member in outcome.members} == {
        "succeeded",
        "partial",
        "failed",
        "unknown",
        "unsupported",
    }
    assert not any(item.enum == "DdoPdfObservationOutcome" for item in prepared.vocabularies)
    for root, slots in (
        (
            "data-operation-pdf-capture.yaml",
            (("DdoPdfObservedRequest", "outcome"), ("DdoPdfObservedPage", "outcome")),
        ),
        (
            "pdf-products.yaml",
            (("PdfRecognitionObservation", "outcome"), ("PdfProductHealth", "execution_outcome")),
        ),
    ):
        view = (
            compiled_model({source.name: source.content for source in bundle.sources}).view(
                bundle.root
            )
            if root == "data-operation-pdf-capture.yaml"
            else running_model().view(root)
        )
        enum = view.get_enum("PdfObservationOutcome")
        assert enum is not None
        assert set(enum.permissible_values or {}) == {
            "succeeded",
            "partial",
            "failed",
            "unknown",
            "unsupported",
        }
        for name, slot in slots:
            assert view.induced_slot(slot, name).range == "PdfObservationOutcome"
