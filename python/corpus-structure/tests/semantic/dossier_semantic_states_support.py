"""Shared controlled inputs and builders for dossier semantic states support."""

from corpus_structure.semantic.structural_products import (
    StructuralProductReport,
    definition_component,
)
from semantic.structural_admission_support import definition


def applicability():
    original = definition()
    assert original.definition is not None
    template = original.definition.readings[0]
    readings = []
    for i, outcome in enumerate(
        (
            "applicable_definition",
            "applicable_explanation",
            "mention",
            "example",
            "incompatible",
            "unresolved",
        )
    ):
        meaning = template.component.model_dump(exclude={"component_id"})
        meaning["interpretation"] = (
            "explanation" if outcome == "applicable_explanation" else "definition"
        )
        component = definition_component(**meaning)
        premises = tuple(
            p.model_copy(
                update=dict(
                    state=(
                        "incompatible"
                        if outcome == "incompatible" and p.dimension == "sense"
                        else "unknown"
                        if outcome == "unresolved" and p.dimension == "sense"
                        else "compatible"
                    )
                )
            )
            for p in template.premises
        )
        readings.append(
            template.model_copy(
                update=dict(
                    outcome=outcome,
                    component=component,
                    target_id=component.component_id,
                    premises=premises,
                    component_ref=template.component_ref.model_copy(
                        update=dict(
                            component_id=component.component_id,
                            selected_task_id=i + 1,
                            origin_task_id=i + 1,
                        )
                    ),
                )
            )
        )
    targets = tuple(dict.fromkeys(r.target_id for r in readings))
    return StructuralProductReport.model_validate(
        {
            **original.model_dump(),
            "definition": original.definition.model_copy(
                update=dict(
                    readings=tuple(readings), eligible_targets=targets, candidate_targets=targets
                )
            ),
        }
    )
