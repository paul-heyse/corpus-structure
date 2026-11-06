"""Independent membership, scaling and in-sample scope controls."""

from typing import Literal

import pytest
from pydantic import ValidationError

from corpus_structure.evaluate.operation_fitting import (
    OperationEventAlgorithm,
    OperationEventFrame,
    OperationEventObservation,
    fit_operation_event,
    score_operation_event,
)


def frame(
    judgments: tuple[Literal["supported", "unsupported", "ambiguous", "unassessed"], ...] = (
        "unsupported",
        "unsupported",
        "supported",
        "supported",
    ),
):
    observations = tuple(
        OperationEventObservation(
            event_id=str(i),
            contribution_id="c" + str(i),
            source_ref="same-book",
            features=(float(i), 10.0),
            judgment=j,
        )
        for i, j in enumerate(judgments)
    )
    return OperationEventFrame(
        event_version="defined-by-correct-1",
        producer_version="2",
        rubric_digest="a" * 64,
        reference_digest="b" * 64,
        corpus_id="gs120",
        feature_names=("rank", "constant"),
        event_ids=tuple(o.event_id for o in observations),
        observations=observations,
    )


def test_one_shared_source_fits_and_reports_in_sample_with_prior():
    result = fit_operation_event(frame())
    assert result.status == "fitted" and result.origin_requirement == "none"
    assert result.assessment_mode == "in_sample_development"
    assert result.parameters is not None
    assert result.parameters.means == (1.5, 10.0)
    assert result.parameters.scales[0] == pytest.approx(1.118033988749895)
    assert result.parameters.scales[1] == 1.0
    assert result.positive == result.negative == 2
    assert result.fitted_brier is not None and result.prior_brier is not None
    assert result.fitted_brier < result.prior_brier
    assert [p.prior_probability for p in result.predictions] == [0.5] * 4
    first, last = (
        result.predictions[0].fitted_probability,
        result.predictions[-1].fitted_probability,
    )
    assert first is not None and last is not None
    assert first < 0.5 < last
    for observation, prediction in zip(frame().observations, result.predictions, strict=True):
        assert score_operation_event(
            result.parameters,
            observation.features,
            corpus_id="gs120",
            event_version="defined-by-correct-1",
            producer_version="2",
        ) == pytest.approx(prediction.fitted_probability)
    runtime = result.parameters.model_dump(mode="json")
    assert "observations" not in runtime and "judgment" not in str(runtime)
    assert result == fit_operation_event(frame())


def test_unknown_labels_are_not_fabricated_negatives():
    result = fit_operation_event(frame(("supported", "unassessed", "ambiguous", "supported")))
    assert result.status == "unavailable" and result.parameters is None
    assert result.labeled == 2 and result.negative == 0
    assert len(result.predictions) == 4
    assert all(p.prior_probability == 1 for p in result.predictions)
    assert all(p.fitted_probability is None for p in result.predictions)


def test_empty_binary_labels_leave_frame_visible():
    value = frame(("ambiguous", "unassessed"))
    result = fit_operation_event(value)
    assert result.status == "unavailable" and result.observations == 2 and result.labeled == 0
    assert result.predictions == () and result.frame_digest


@pytest.mark.parametrize(
    "change",
    [
        dict(event_ids=("foreign",)),
        dict(feature_names=("x", "x")),
        dict(
            observations=(
                OperationEventObservation(
                    event_id="0",
                    contribution_id="c",
                    source_ref="s",
                    features=(1,),
                    judgment="supported",
                ),
            ),
            event_ids=("0",),
        ),
    ],
)
def test_malformed_membership_or_feature_contract_refuses(change):
    with pytest.raises(ValidationError):
        OperationEventFrame.model_validate({**frame().model_dump(mode="python"), **change})


def test_unconverged_fit_does_not_export_parameters():
    result = fit_operation_event(frame(), OperationEventAlgorithm(max_iterations=1))
    assert result.status == "failed" and result.parameters is None and result.warnings
    assert all(p.fitted_probability is None for p in result.predictions)


def test_runtime_score_refuses_other_corpus_and_event():
    result = fit_operation_event(frame())
    assert result.parameters is not None
    with pytest.raises(ValueError, match="applicability"):
        score_operation_event(
            result.parameters,
            (1.0, 10.0),
            corpus_id="another-book",
            event_version="defined-by-correct-1",
            producer_version="2",
        )
