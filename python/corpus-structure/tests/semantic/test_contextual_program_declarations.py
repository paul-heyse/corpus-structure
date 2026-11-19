"""Contextual producers retain structured programs and explicit family ownership."""

import pytest

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.contextual_admission_native import (
    contextual_admission_native_programs,
)
from corpus_structure.semantic.contextual_definition_native import (
    contextual_definition_native_programs,
)
from corpus_structure.semantic.contextual_linguistics_native import (
    contextual_linguistics_native_programs,
)
from corpus_structure.semantic.contextual_neighborhood import contextual_neighborhood_programs
from corpus_structure.semantic.contextual_scoring_native import contextual_scoring_native_programs
from corpus_structure.semantic.contextual_witness_native import contextual_witness_native_programs
from corpus_structure.semantic.native_objects import INTERNAL_PROGRAM
from corpus_structure.semantic.native_program import NativeRoutine
from corpus_structure.semantic.native_program_registry import ProgramValidity


@pytest.mark.parametrize(
    "produce",
    (
        contextual_admission_native_programs,
        contextual_definition_native_programs,
        contextual_witness_native_programs,
        contextual_linguistics_native_programs,
        contextual_scoring_native_programs,
        contextual_neighborhood_programs,
    ),
)
def test_contextual_producers_keep_typed_programs_without_eager_rendering(produce, monkeypatch):
    def refuse_render(self):
        raise AssertionError("contextual producer rendered before native registry")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    declarations = produce()
    assert declarations
    assert len({item.identity for item in declarations}) == len(declarations)
    for declaration in declarations:
        assert declaration.source == "data-operations:forward"
        assert declaration.owner == role_name("publisher")
        assert declaration.access == INTERNAL_PROGRAM
    roles = {item.identity.name: item.validity for item in declarations if item.validity}
    assert roles == (
        {
            "ddo_require_contextual_completion": (
                ProgramValidity("contextual", "completion_guard"),
            ),
            "ddo_contextual_dependencies_valid": (ProgramValidity("contextual", "validator"),),
        }
        if produce is contextual_admission_native_programs
        else {}
    )


def test_contextual_vector_row_declaration_keeps_table_output_contract():
    rows = next(
        item.routine
        for item in contextual_scoring_native_programs()
        if item.identity.name == "ddo_contextual_vector_rows"
    )
    assert rows.argument_types == ("jsonb", "jsonb")
    assert rows.returns.setof is True
    assert tuple(name for name, _ in rows.table_columns) == (
        "inventory_id",
        "profile_id",
        "target_id",
        "vector",
        "search_text",
        "exact_forms",
    )
    assert rows.strict is True
    assert rows.volatility == "immutable"
