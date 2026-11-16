"""Finite historical structural fixture projection and native publication metadata.

These functions read explicitly supplied retained inputs and call the shared pure
kernels. They do not select work, own execution, acquire providers or grant authority.
"""

from corpus_structure.core.method import UnitResult
from corpus_structure.core.vocab import ObservationOutcome
from corpus_structure.methods.structural_products import produce_structural_comparison


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
    return UnitResult(
        ref=ref,
        outcome=ObservationOutcome.PRODUCED,
        structural_product=report.model_dump(mode="json"),
    )
