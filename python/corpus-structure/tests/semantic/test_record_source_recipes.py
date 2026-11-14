"""Record preparation identity and scoped implementation isolation before database effects."""

from dataclasses import FrozenInstanceError, replace
from typing import cast

import pytest
from scenario_recipes import scenario_builder

from corpus_structure.semantic import contracts
from corpus_structure.semantic.types import PreparedRelease
from semantic import native_record_fixtures as records


@pytest.fixture
def record_preparations(monkeypatch):
    records._record_preparation_cached.cache_clear()
    compiled = []

    def compiler(bundle, dependencies, profile):
        compiled.append((bundle, dependencies, profile))
        return cast(PreparedRelease, object())

    monkeypatch.setattr(records, "prepare_release", compiler)
    try:
        yield compiled
    finally:
        records._record_preparation_cached.cache_clear()


def test_record_recipe_has_one_builder_and_refuses_unknown_owned_choices():
    recipe = records.RecordSourceRecipe()
    assert scenario_builder(recipe) is records.build_record_recipe
    assert hash(recipe) == hash(records.RecordSourceRecipe())
    with pytest.raises(FrozenInstanceError):
        setattr(recipe, "composition", "reference")  # noqa: B010 - frozen runtime contract
    with pytest.raises(ValueError, match="unknown record composition: invented"):
        records.RecordSourceRecipe(composition="invented")
    with pytest.raises(ValueError, match="unknown record method: invented"):
        records.RecordSourceRecipe(record_method="invented")


def test_record_preparation_projects_only_input_composition_and_methods(record_preparations):
    base = records.RecordSourceRecipe()
    later = replace(
        base,
        sibling_references=("changed published text",),
        include_blank_cell=True,
        record_configuration_hash="different-task-config",
    )
    first = records.prepare_record_source(base.preparation_recipe)
    assert records.prepare_record_source(later.preparation_recipe) is first
    extended = records.prepare_record_source(
        replace(base, additional_methods=("private.contextual",)).preparation_recipe
    )
    characterized = records.prepare_record_source(
        replace(base, composition="characterization").preparation_recipe
    )
    assert extended is not first and characterized is not first and extended is not characterized
    assert len(record_preparations) == 3
    assert first.bundle != characterized.bundle
    assert first.dependencies != extended.dependencies
    assert records.prepare_record_source(base.preparation_recipe) is first


def test_record_preparation_nested_overrides_bypass_reads_and_writes(record_preparations):
    installed = contracts.current_implementation()

    def changed(suffix):
        analysis = tuple(
            replace(item, content=item.content + suffix) if item.name == "libraries.json" else item
            for item in installed.analysis_inputs
        )
        return contracts.ImplementationSnapshot(
            replace(
                installed.execution_inputs,
                implementations=contracts.semantic_implementation_inputs(analysis),
            ),
            analysis,
        )

    outer, inner = changed(b"\n"), changed(b"\n\n")
    recipe = records.RecordSourceRecipe().preparation_recipe
    warm = records.prepare_record_source(recipe)
    before = records._record_preparation_cached.cache_info()

    class LeaveInner(Exception):
        pass

    def libraries(preparation):
        return next(
            item.content
            for item in preparation.dependencies.artifacts
            if item.name == "execution/implementation/libraries.json"
        )

    with contracts.implementation_override(outer):
        first = records.prepare_record_source(recipe)
        second = records.prepare_record_source(recipe)
        assert first is not warm and second is not first
        assert first.profile == warm.profile
        assert libraries(first) == libraries(warm) + b"\n"
        with pytest.raises(LeaveInner), contracts.implementation_override(inner):
            nested = records.prepare_record_source(recipe)
            assert libraries(nested) == libraries(warm) + b"\n\n"
            raise LeaveInner
        assert libraries(records.prepare_record_source(recipe)) == libraries(first)
    assert records._record_preparation_cached.cache_info() == before
    assert records.prepare_record_source(recipe) is warm
    assert len(record_preparations) == 5
