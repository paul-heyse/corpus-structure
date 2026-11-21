"""Independent change categories and archived source facts for real closed inputs."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import read_effective_data_operations
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.source_comparison import compare_data_operation_models
from corpus_structure.semantic.source_interfaces import (
    SOURCE_INTERFACE_ARTIFACT,
    SourceInterfaceProjection,
    read_source_interfaces,
)
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from semantic.data_operation_declaration_support import contract
from semantic.test_data_operation_compilation import operation_source, python_inputs


def compile_source(source):
    return compile_data_operations(python_sources=python_inputs(source))


def facets(comparison):
    return {item.facet for item in comparison.changes}


def test_same_signature_body_change_is_implementation_and_recipe_not_contract():
    before = compile_source(operation_source())
    after = compile_source(operation_source(body="return helper(x) + 1"))
    compared = compare_data_operation_models(before, after)
    assert facets(compared) == {"implementation", "recipe"}
    assert compared.material_comparison == "changed"
    assert not compared.breakages
    assert compared.before_digest != compared.after_digest
    material = {item.facet: item.material for item in compared.changes}
    implementation, recipe = material["implementation"], material["recipe"]
    assert implementation is not None and implementation.path is not None
    assert implementation.source == "captured-implementation"
    assert implementation.path[0] == "graph"
    assert recipe is not None and recipe.source == "compiled-recipe"
    assert recipe.path == ("implementation_slices", 0)


def test_historical_key_without_corresponding_fields_stays_unavailable():
    before = compile_source(operation_source())
    after = compile_source(operation_source(body="return helper(x) + 1"))
    historical = replace(
        before,
        source_interfaces=None,
        identities=tuple(
            replace(identity, key="recipe:" + "a" * 64) if identity.domain == "recipe" else identity
            for identity in before.identities
        ),
    )
    recipe = next(
        change
        for change in compare_data_operation_models(historical, after).changes
        if change.facet == "recipe"
    )
    assert recipe.material is not None and recipe.material.source == "unavailable"
    assert recipe.material.path is None
    assert compare_data_operation_models(historical, after).material_comparison == "uncompared"


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s + "\nunrelated = 9\n",
        lambda s: s.replace("return helper(x)", "return helper( x )  # cosmetic"),
    ],
)
def test_unrelated_and_permitted_cosmetic_changes_do_not_invalidate_semantics(change):
    before = compile_source(operation_source())
    after = compile_source(change(operation_source()))
    assert not compare_data_operation_models(before, after).changes


def test_documentation_is_prepared_and_compared_separately_from_callable_shape():
    before = compile_source(operation_source(body='"""Before prose."""\n    return helper(x)'))
    after = compile_source(operation_source(body='"""After prose."""\n    return helper(x)'))
    assert after.source_interfaces is not None
    projection = SourceInterfaceProjection.model_validate_json(after.source_interfaces)
    documented = projection.operations[0].callables[0]
    assert documented.documentation == "After prose."
    assert documented.sections == ({"kind": "text", "value": "After prose."},)
    assert documented.source_digest == projection.modules[0].source_digest
    compared = compare_data_operation_models(before, after)
    assert "documentation" in facets(compared)
    assert "contract" not in facets(compared)
    # The current executable identity includes the function's runtime docstring.
    assert compared.material_comparison == "changed"


def test_inherited_interface_retains_supplier_exposure_and_structured_parameters():
    metadata = contract(entrypoints=["run"])
    source = (
        '''raise RuntimeError("must not execute")
class Base:
    def run(self, x: int = 2) -> int:
        """Compute value.

        Args:
            x: Independent count.
        """
        return x + 1
class Child(Base):
    pass
'''
        + f"Child.__data_operation__={metadata!r}\n"
    )
    model = compile_source(source)
    assert model.source_interfaces is not None
    projection = SourceInterfaceProjection.model_validate_json(model.source_interfaces)
    callable = projection.operations[0].callables[0]
    assert callable.exposed == "example.Child.run"
    assert callable.declaration == "example.Base.run"
    assert callable.line == 3
    parameters = callable.signature["parameters"]
    assert isinstance(parameters, list)
    argument = parameters[1]
    assert isinstance(argument, dict)
    assert argument["default"] == "2"
    parameter = next(section for section in callable.sections if section["kind"] == "parameters")
    values = parameter["value"]
    assert isinstance(values, list)
    first_parameter = values[0]
    assert isinstance(first_parameter, dict)
    assert first_parameter["name"] == "x"
    assert first_parameter["description"] == "Independent count."
    assert projection.operations[0].metadata["coverage"] == metadata["coverage"]
    assert any(
        origin["declaration"] == "example.Base.run" for origin in projection.operations[0].origins
    )


def test_class_documentation_edit_retains_owner_and_does_not_change_callable_contract():
    metadata = contract(entrypoints=["run"])
    source = (
        '''raise RuntimeError("must not execute")
class Operation:
    """Before operation prose.

    Note:
        Operation policy.
    """
    def run(self, x: int = 2) -> int:
        return x + 1
'''
        + f"Operation.__data_operation__={metadata!r}\n"
    )
    before = compile_source(source)
    after = compile_source(source.replace("Before operation prose.", "After operation prose."))
    assert after.source_interfaces is not None
    projection = SourceInterfaceProjection.model_validate_json(after.source_interfaces)
    operation = projection.operations[0]
    documented = operation.documentation
    assert documented is not None
    assert operation.owner == "python:example.Operation"
    assert documented.exposed == documented.declaration == "example.Operation"
    assert documented.module == "example"
    assert documented.path == projection.modules[0].path
    assert documented.source_digest == projection.modules[0].source_digest
    assert documented.line == 2
    assert documented.origin == "extracted"
    assert documented.documentation == "After operation prose.\n\nNote:\n    Operation policy."
    assert documented.sections == (
        {"kind": "text", "value": "After operation prose."},
        {
            "kind": "admonition",
            "value": {"annotation": "note", "description": "Operation policy."},
            "title": "Note",
        },
    )
    assert operation.callables[0].documentation is None
    comparison = compare_data_operation_models(before, after)
    assert "documentation" in facets(comparison)
    assert "contract" not in facets(comparison)
    assert not comparison.breakages


def test_obsolete_interface_projection_requires_regeneration():
    from pydantic import ValidationError

    model = compile_source(operation_source())
    assert model.source_interfaces is not None
    original = json.loads(model.source_interfaces)
    original["version"] = "data-operation-source-interfaces-v1"
    with pytest.raises(ValidationError, match="version"):
        SourceInterfaceProjection.model_validate_json(json.dumps(original))


def test_missing_archive_projection_stays_unavailable_and_model_content_is_unchanged():
    model = compile_source(operation_source())
    assert "source_interfaces" not in json.loads(model.content)
    assert all(
        "source_interfaces" not in node
        for node in json.loads(model.content)["implementation_slices"]
    )
    assert replace(model, source_interfaces=None).content == model.content
    retained = read_effective_data_operations(model.content)
    assert retained.source_interfaces is None
    assert retained == model
    assert read_source_interfaces(SimpleNamespace(artifacts=())) is None
    compared = compare_data_operation_models(retained, retained)
    assert not compared.changes
    assert any("documentation unavailable" in unknown for unknown in compared.unknowns)
    assert compared.material_comparison == "unchanged"


def test_native_griffe_breakages_are_auxiliary_to_full_contract_comparison():
    before = compile_source(operation_source())
    after = compile_source(operation_source().replace("x: int = 2", "x: int"))
    comparison = compare_data_operation_models(before, after)
    assert "contract" in facets(comparison)
    assert any("required" in item.kind.lower() for item in comparison.breakages)
    assert "domain" not in facets(comparison)


def test_incomplete_source_determinants_remain_unknown_even_when_models_equal():
    model = compile_source(operation_source(body="return getattr(x, 'unknown')()"))
    compared = compare_data_operation_models(model, model)
    assert any("getattr" in unknown or "reflection" in unknown for unknown in compared.unknowns)
    assert not compared.changes
    assert compared.material_comparison == "uncompared"


def test_runtime_custody_change_does_not_change_semantic_recipe():
    model = compile_source(operation_source())
    compared = compare_data_operation_models(
        model, model, before_runtime="runtime:old", after_runtime="runtime:new"
    )
    assert facets(compared) == {"runtime"}
    assert compared.material_comparison == "unchanged"


def test_normal_preparation_archives_projection_and_bound_reader_uses_its_bytes(monkeypatch):
    schema = SourceBundle(
        "m", (SourceArtifact("m", b"id: urn:test\nname: test\nclasses: {Thing: {}}\n"),)
    )
    dependencies = data_operation_dependencies(
        ResolvedDependencies(), python_sources=python_inputs(operation_source())
    )
    prepared = prepare_release(schema, dependencies, PreparationProfile(version="semantic-2"))
    archived = read_source_interfaces(prepared)
    assert archived is not None
    assert archived.operations[0].operation == "urn:test:derive"
    assert json.loads(prepared.manifest)["data_operation_source_interfaces"] == next(
        artifact.digest
        for artifact in prepared.artifacts
        if artifact.kind == SOURCE_INTERFACE_ARTIFACT
    )
    assert sum(artifact.kind == SOURCE_INTERFACE_ARTIFACT for artifact in prepared.artifacts) == 1
    from corpus_structure.semantic.releases import _validate_manifest

    _validate_manifest(schema, dependencies, PreparationProfile(version="semantic-2"), prepared)
    # Bound reads consume the retained projection even if source extraction is unavailable.
    from corpus_structure.semantic import python_operation_sources

    monkeypatch.setattr(
        python_operation_sources,
        "ClosedPythonSources",
        lambda _: pytest.fail("archive read reanalysed source"),
    )
    assert bound_data_operation_model(prepared).source_interfaces == archived.content


def test_added_operation_frames_owned_encoded_json_without_erasing_types():
    before = compile_data_operations()
    after = compile_source(operation_source())
    compared = compare_data_operation_models(before, after)
    added = next(item for item in compared.changes if item.operation == "urn:test:derive")
    assert added.kind == "added"
    assert isinstance(added.after, dict)
    assert added.after["parameters"] == {"json": {}}
    assert added.before is None


def test_mismatched_documentation_projection_cannot_be_attached_to_another_model():
    before = compile_source(operation_source())
    after = compile_source(operation_source(body="return helper(x) + 1"))
    with pytest.raises(ValueError, match="another effective model"):
        compare_data_operation_models(before, after, after_interfaces=before.source_interfaces)


def test_interface_rendering_participates_in_release_custody_not_semantic_recipe():
    model = compile_source(operation_source())
    assert model.source_interfaces is not None
    projection = SourceInterfaceProjection.model_validate_json(model.source_interfaces)
    altered = projection.model_copy(update={"unknowns": ("new documentation interpretation",)})
    assert replace(model, source_interfaces=altered.content).content == model.content
    assert altered.identity != projection.identity


def test_griffe_entrypoints_match_exposed_identity_across_addition_and_reorder():
    from corpus_structure.semantic.data_operation_model import CallableParameter, CallableSurface

    before = compile_source(operation_source())
    original = before.operations[0]
    run = CallableSurface(
        "example.Operation.run",
        "example.Operation.run",
        (CallableParameter("x", "positional or keyword", "int", "2"),),
        "int",
    )
    close = CallableSurface("example.Operation.close", "example.Operation.close", (), "None")
    first = replace(
        before, operations=(replace(original, callable_surfaces=(run,)),), source_interfaces=None
    )
    added = replace(
        before,
        operations=(replace(original, callable_surfaces=(close, run)),),
        source_interfaces=None,
    )
    comparison = compare_data_operation_models(first, added)
    assert not comparison.breakages
    reordered = replace(added, operations=(replace(original, callable_surfaces=(run, close)),))
    assert not compare_data_operation_models(added, reordered).breakages
    from corpus_structure.semantic.source_comparison import _callable_container

    with pytest.raises(ValueError, match="duplicate exposed callable"):
        _callable_container(replace(original, callable_surfaces=(run, run)))


def test_documentation_claim_edit_does_not_masquerade_as_domain_enforcement_change():
    before = compile_source(operation_source())
    after = compile_source(
        operation_source(
            metadata=contract(
                applicability=[
                    {"kind": "documentation", "text": "reworded eligibility description"}
                ],
                invariants=[{"kind": "documentation", "text": "reworded invariant description"}],
            )
        )
    )
    comparison = compare_data_operation_models(before, after)
    assert facets(comparison) == {"documentation"}
    assert not comparison.breakages


@pytest.mark.parametrize("description", ["precision", "coverage", "input_coverage"])
def test_descriptive_precision_and_coverage_are_visible_without_domain_change(description):
    metadata = contract()
    before = compile_source(operation_source(metadata=metadata))
    if description == "precision":
        metadata["precision_description"] = "Documented output spelling, unchanged value semantics."
    elif description == "coverage":
        metadata["coverage"]["description"] = "Reworded examined-population explanation."
    else:
        metadata["roles"][0]["support"]["coverage"]["description"] = (
            "Reworded selected-input explanation."
        )
    after = compile_source(operation_source(metadata=metadata))
    comparison = compare_data_operation_models(before, after)
    assert facets(comparison) == {"documentation"}
    assert not comparison.breakages
    assert before.operations[0].definition == after.operations[0].definition
    assert before.operations[0].recipe == after.operations[0].recipe
