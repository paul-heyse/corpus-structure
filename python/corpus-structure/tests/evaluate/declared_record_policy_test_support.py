"""Shared authored scenarios and fixtures for declared record policy test support."""

import pytest
from evaluate.declared_record_policy_support import source, training_grade


@pytest.fixture(scope="module")
def fit_basis():
    from semantic.record_policy_support import algorithm

    from corpus_structure.evaluate.declared_record_policy import (
        DdoRecordFitSpecification,
        DdoRecordGradeSelection,
        _fit_feature_value,
    )
    from corpus_structure.semantic.record_policy_authority import DdoRecordPolicyApplicability

    first = training_grade()
    preliminary = _fit_feature_value(
        first, algorithm=algorithm(), assumptions="independent complete frozen source frames"
    )
    feature = preliminary.instance
    assert feature is not None
    second = training_grade(calibration=True, feature=feature, held_out_from=(first.frame_digest,))
    specification = DdoRecordFitSpecification(
        calibration_selection=DdoRecordGradeSelection(
            project_id="project:one",
            demand_id="demand:calibration",
            read_id="read:calibration",
            use_id="use:calibration",
            derivation_id="derivation:calibration",
            product_id="product:calibration",
            expected_cut="cut:calibration",
            cut_canonical_json="retained calibration cut bytes",
            frame_digest=second.frame_digest,
        ),
        feature_selection=DdoRecordGradeSelection(
            project_id="project:one",
            demand_id="demand:grade",
            read_id="read:grade",
            use_id="use:grade",
            derivation_id="derivation:grade",
            product_id="product:grade",
            expected_cut="cut:grade",
            cut_canonical_json="retained native cut bytes",
            frame_digest=first.frame_digest,
        ),
        frozen_feature=feature,
        applicability=DdoRecordPolicyApplicability(
            project_id="project:one",
            sources=(source(900),),
        ),
        family_contract=first.frame.family_contract,
        reading_recipe=first.frame.reading_recipe,
        event_procedure="procedure:whole-reading",
        assumptions="independent complete frozen source frames",
        threshold=0.99,
        threshold_procedure="predeclared-threshold-1",
    )
    return first, second, specification
