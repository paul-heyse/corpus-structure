"""Finite source-local kernels for genuine historical sealed publication fixtures."""

from corpus_structure.core.method import UnitResult
from corpus_structure.core.vocab import ObservationOutcome
from corpus_structure.methods.scoped_relations import (
    discover_relations,
)


def build_scoped_result(
    view,
    cfg,
    ref,
    *,
    annotations=(),
    annotation_errors=(),
    primary_layers=(),
    passages=None,
    annotation_origin_task_id=None,
    qualifier_preflight=None,
):
    from corpus_structure.methods.inline_formula_occurrences import INLINE_FORMULA_QUESTION
    from corpus_structure.methods.table_interpretation import table_policy_operations
    from corpus_structure.semantic.proposals import native_source_frame

    if (ref.unit_id, ref.unit_key) != (view.ref.id, view.ref.key):
        raise ValueError("sealed scoped fixture requires its exact selected source unit")
    if cfg.classification_refs:
        raise ValueError(
            "sealed scoped fixture requires explicit separately prepared model/correspondence output"
        )
    bindings = [
        row
        for row in cfg.work_bindings
        if row.native_content_digest == view.ref.native_product.content_digest
    ]
    if len(bindings) > 1:
        raise ValueError("source has ambiguous parent-work assignment")
    frame = native_source_frame(view, ())
    output = discover_relations(
        frame,
        source_work=bindings[0].source_work if bindings else None,
        annotations=annotations,
        annotation_errors=annotation_errors,
        primary_layers=primary_layers,
        annotation_origin_task_id=annotation_origin_task_id,
        passages=passages,
        formula_seconds=cfg.formula_seconds,
        max_formula_chars=cfg.max_formula_chars,
        predicate_version="6",
        inline_equations_enabled=True,
        witnessed_links_enabled=True,
        ordered_formula_witness=cfg.ordered_formula_witness,
        named_link_version="4",
        qualifier_preflight=qualifier_preflight,
    )
    formula_keys = {
        row["operation_key"]
        for row in output["extra_operations"]
        if row["question"] == INLINE_FORMULA_QUESTION
    }
    table_inputs = tuple(
        row for row in output["contributions"] if row["operation_key"] not in formula_keys
    )
    interpretation = table_policy_operations(
        contributions=table_inputs,
        dependency_ids=tuple(
            sorted(
                {
                    dependency
                    for row in table_inputs
                    for dependency in row["computation_dependencies"]
                }
                | set(output["operation"]["computation_dependencies"])
            )
        ),
        source_revision=frame.native_product.content_digest,
        mode=cfg.interpretation_mode,
        weight_scale=cfg.interpretation_weight_scale,
    )
    return UnitResult(
        ref=ref,
        outcome=ObservationOutcome.PRODUCED
        if output["contributions"]
        else ObservationOutcome.EMPTY,
        contributions=output["contributions"],
        contribution_operations=(output["operation"], *output["extra_operations"], *interpretation),
        parse_detail={
            "formula_syntax": list(output["formula_diagnostics"]),
            "annotation_errors": list(annotation_errors),
        },
        contribution_coordinate_texts=output["coordinates"],
    )


def scoped_relation_result(reader, view, cfg, ref):
    """Read one explicit sealed source, then call the same pure discovery kernels."""
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.m1_annotations import consume_annotations
    from corpus_structure.methods.predicate_contributions import predicate_qualifier_refusal
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import NativeSourcePin

    frame = native_source_frame(view, ())
    if cfg.inputs is not None:
        sources = [source for source in cfg.inputs.sources if source.source_view_id == view.ref.id]
        if len(sources) != 1:
            raise ValueError("original annotations require exactly one selected source reference")
        original = sources[0]
        if (
            original.native_task_id,
            original.native_product_key,
            original.native_content_digest,
            original.projection_digest,
            original.recipe_digest,
        ) != (
            frame.native_product.task_id,
            frame.native_product.product_key,
            frame.native_product.content_digest,
            frame.projection_digest,
            frame.recipe_digest,
        ):
            raise ValueError("original annotation reference differs from current native source")
        retained = reader.structural_source_annotations(
            cfg.inputs, original.identity, AnnotationProfile(cfg.sentences)
        )
        if (
            NativeSourcePin.from_source(retained.source) != NativeSourcePin.from_source(frame)
            or retained.source.text != frame.text
        ):
            raise ValueError("retained annotations differ from current native projection")
        annotations, errors = retained.annotations, retained.errors
        origin = getattr(retained, "annotation_task_id", None)
        passages = tuple(row for row in cfg.inputs.passages if row.source_ref == original.identity)
    else:
        annotations, errors, retained = consume_annotations(
            reader, view, AnnotationProfile(cfg.sentences)
        )
        origin, passages = retained.get("origin_task_id"), None
    primary = (
        reader.characterization_layers(
            tuple(ProductReference(**pin) for pin in cfg.characterization_layers)
        )
        if cfg.characterization_layers
        else {
            pin: report
            for annotation in annotations
            for pin, report in getattr(annotation, "primary_layers", {}).items()
        }
    )
    return build_scoped_result(
        view,
        cfg,
        ref,
        annotations=annotations,
        annotation_errors=errors,
        primary_layers=primary,
        passages=passages,
        annotation_origin_task_id=origin,
        qualifier_preflight=lambda component: predicate_qualifier_refusal(
            reader.prepared, component
        ),
    )
