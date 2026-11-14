"""Finite historical structural fixture projection and native publication metadata.

These functions read explicitly supplied retained inputs and call the shared pure
kernels. They do not select work, own execution, acquire providers or grant authority.
"""

from corpus_structure.core.method import UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.semantic.operations import OperationDescriptor
from corpus_structure.methods.structural_products import (
    StructuralComparisonConfig, StructuralDossierConfig, ConditionQualificationConfig,
    SEALED_COMPARISON_NAME, SEALED_COMPARISON_VERSION,
    SEALED_CONDITION_NAME, SEALED_CONDITION_VERSION,
    produce_structural_comparison, dossier_root, produce_structural_dossier,
    produce_condition_qualification,
)
from corpus_structure.methods.artifact_identity import (
    ArtifactIdentityConfig, SEALED_ARTIFACT_NAME, SEALED_ARTIFACT_VERSION,
)
from corpus_structure.semantic.structural_products import (
    StructuralProductReport, LocatedDefinitionComponent,
)


def comparison_descriptor():
    return OperationDescriptor(SEALED_COMPARISON_NAME, SEALED_COMPARISON_VERSION,
        "consolidate", "deterministic", TaskUnitType.RUN, StructuralComparisonConfig)


def dossier_descriptor():
    return OperationDescriptor("structure.dossier", "3", "consolidate", "deterministic",
        TaskUnitType.RUN, StructuralDossierConfig)


def condition_descriptor():
    return OperationDescriptor(SEALED_CONDITION_NAME, SEALED_CONDITION_VERSION,
        "resolve", "deterministic", TaskUnitType.RUN, ConditionQualificationConfig)


def artifact_descriptor():
    return OperationDescriptor(SEALED_ARTIFACT_NAME, SEALED_ARTIFACT_VERSION,
        "consolidate", "deterministic", TaskUnitType.RUN, ArtifactIdentityConfig)



def comparison_result(reader, cfg, ref, *, check_active):
    if cfg.inputs is None or cfg.left_reading is None or cfg.right_reading is None:
        raise ValueError("comparison inputs absent")
    check_active()
    reader.validate_structural_inputs(cfg.inputs)
    primary = {}
    for source in cfg.inputs.sources:
        primary.update(
            reader.primary_characterization(
                source.source_view_id, families=("formal.lexical", "formal.threshold")
            )
        )
    report = produce_structural_comparison(
        cfg.inputs,
        left_id=cfg.left_id,
        right_id=cfg.right_id,
        left_reading=cfg.left_reading,
        right_reading=cfg.right_reading,
        left_retained=reader.retained_source_contribution(cfg.left_reading),
        right_retained=reader.retained_source_contribution(cfg.right_reading),
        primary_layers=primary,
        predicate_version="6",
        check_active=check_active,
    )
    return UnitResult(ref=ref, outcome=ObservationOutcome.PRODUCED, structural_product=report.model_dump(mode="json"))


def dossier_result(reader, cfg, ref, *, check_active):
    if cfg.inputs is None or cfg.root_component is None:
        raise ValueError("dossier inputs absent")
    retained = []
    for reference in cfg.predecessors:
        check_active()
        retained.append((reference, reader.retained_structural_report(reference)))
    root = dossier_root(cfg.root_component, retained)
    checked = reader.resolve_definition_component(cfg.root_component)
    if LocatedDefinitionComponent.model_validate(checked) != root:
        raise ValueError("dossier root differs from its native component")
    relationships = {}
    for selection in cfg.comparison_selections:
        reference = selection.relationship_ref
        if reference not in relationships:
            check_active()
            relationships[reference] = reader.retained_relationship_decision(reference)
    contribution_retained = []
    for reference in cfg.contribution_predecessors:
        check_active()
        contribution_retained.append(
            (reference, reader.retained_source_contribution(reference))
        )
    report = produce_structural_dossier(
        cfg.inputs,
        root_component=cfg.root_component,
        root=root,
        retained=tuple(retained),
        relationships=relationships,
        contribution_retained=tuple(contribution_retained),
        comparison_selections=cfg.comparison_selections,
        member_budget=cfg.member_budget,
        policy=cfg.policy,
        check_active=check_active,
    )
    return UnitResult(ref=ref, outcome=ObservationOutcome.PRODUCED, structural_product=report.model_dump(mode="json"))


def condition_result(reader, cfg, ref, *, check_active):
    if cfg.inputs is None or cfg.attachment is None:
        raise ValueError("condition qualification requires complete source and attachment")
    check_active()
    reader.validate_structural_inputs(cfg.inputs)
    if cfg.attachment.release_id != reader.prepared.release_id:
        raise ValueError("condition attachment belongs to another release")
    retained = reader.retained_source_contribution(cfg.attachment)
    report = produce_condition_qualification(
        cfg.inputs, attachment=cfg.attachment, retained=retained
    )
    return UnitResult(ref=ref, outcome=ObservationOutcome.PRODUCED, structural_product=report.model_dump(mode="json", exclude_none=True))


def artifact_result(reader, cfg, ref, *, check_active):
    from corpus_structure.methods.artifact_identity import project_retained_artifact_identity
    from corpus_structure.semantic.product_reference import ProductReference

    if cfg.inputs is None or cfg.policy is None:
        raise ValueError("artifact identity inputs absent")
    primary = reader.characterization_layers(tuple(ProductReference(**pin) for pin in cfg.characterization_layers)) if cfg.characterization_layers else {}
    bindings = {value.native_content_digest for value in cfg.work_bindings}
    frames = {}
    for source in cfg.inputs.sources:
        check_active()
        if source.native_content_digest in bindings:
            frames[source.identity] = reader.structural_source_frame(cfg.inputs, source.identity)
    retained = []
    for reference in sorted(cfg.external_nomination_refs, key=lambda value: value.contribution_id):
        check_active()
        retained.append((reference, reader.retained_source_contribution(reference)))
    report = project_retained_artifact_identity(cfg, frames=frames, primary_layers=primary,
        nomination_inputs=tuple(retained), check_active=check_active)
    return UnitResult(ref=ref, outcome=ObservationOutcome.PRODUCED, structural_product=report.model_dump(mode="json"))
