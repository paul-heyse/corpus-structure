"""Family responsibilities are owned by structured native producers."""

import pytest

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import INTERNAL_PROGRAM
from corpus_structure.semantic.native_program import NativeRoutine
from corpus_structure.semantic.native_program_registry import ProgramValidity
from corpus_structure.semantic.operation_event_native import operation_event_native_programs
from corpus_structure.semantic.record_grade_native import record_grade_native_programs
from corpus_structure.semantic.record_policy_completion_native import (
    record_policy_completion_native_programs,
)
from corpus_structure.semantic.rich_admission_native import rich_admission_native_programs


@pytest.mark.parametrize(
    ("produce", "family", "validator", "guards"),
    (
        (
            lambda model: rich_admission_native_programs(target_metadata=model),
            "rich",
            "ddo_rich_admission_dependencies_valid",
            ("ddo_require_rich_preparation_completion", "ddo_require_rich_admission_completion"),
        ),
        (
            operation_event_native_programs,
            "operation-event",
            "ddo_operation_event_dependencies_valid",
            ("ddo_require_operation_event_completion",),
        ),
        (
            record_policy_completion_native_programs,
            "record-fit",
            "ddo_record_fit_dependencies_valid",
            ("ddo_require_record_fit_completion",),
        ),
        (
            record_grade_native_programs,
            "record-grade",
            "ddo_record_grade_dependencies_valid",
            ("ddo_require_record_grade_completion",),
        ),
    ),
)
def test_family_declarations_own_actual_guards_without_eager_rendering(
    produce, family, validator, guards, monkeypatch
):
    def refuse_render(self):
        raise AssertionError("producer rendered before the registry boundary")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    declarations = produce(get_metadata())
    assert declarations
    marked = {item.identity.name: item.validity for item in declarations if item.validity}
    assert marked == {
        validator: (ProgramValidity(family, "validator"),),
        **{name: (ProgramValidity(family, "completion_guard"),) for name in guards},
    }
    for declaration in declarations:
        assert declaration.source == "data-operations:forward"
        assert declaration.owner == role_name("publisher")
        assert declaration.access == INTERNAL_PROGRAM
    selected = next(item for item in declarations if item.identity.name == validator)
    assert selected.identity.arguments == ("text",)
