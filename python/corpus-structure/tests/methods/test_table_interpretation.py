"""Literal scoped choices distinguish a real shared source factor from duplicate votes."""

from copy import deepcopy
from math import sqrt
from threading import Event
from typing import Any

import pytest

from corpus_structure.methods.table_interpretation import table_policy_operations
from corpus_structure.semantic.local_interpretation_reports import (
    _digest,
    validate_local_interpretation_report,
)
from corpus_structure.semantic.observations import source_python, source_value

TABLE = "#/tables/1"


def participant(identity, role, row_extent, column_extent):
    return dict(
        contribution_id=identity,
        computation_dependencies=("source",),
        value=source_value(
            dict(
                role=role,
                region=TABLE,
                text=identity,
                start_row_offset_idx=row_extent[0],
                end_row_offset_idx=row_extent[1],
                start_col_offset_idx=column_extent[0],
                end_col_offset_idx=column_extent[1],
            )
        ),
    )


def attachment(cell, band, relation="header", basis="native_geometry"):
    return dict(
        contribution_id=cell + band,
        semantic_type="structural.scoped_attachment",
        computation_dependencies=("source", cell, band),
        value=source_value(
            dict(
                protocol="scoped-attachment-1",
                subject_id=cell,
                target_id=band,
                relation=relation,
                region=TABLE,
                scope=TABLE,
                basis=basis,
            )
        ),
    )


def rows():
    return [
        participant("cell-a", "cell", (2, 3), (1, 2)),
        participant("cell-b", "cell", (2, 3), (2, 3)),
        participant("band-x", "header", (0, 1), (1, 3)),
        participant("band-y", "header", (0, 1), (3, 5)),
        *(attachment(c, b) for c in ("cell-a", "cell-b") for b in ("band-x", "band-y")),
    ]


def run(products=None, **kwargs):
    return table_policy_operations(
        contributions=rows() if products is None else products,
        dependency_ids=("source",),
        source_revision="native1",
        **kwargs,
    )


def extract(op):
    report = op["local_interpretation"]
    return report, source_python(report["request"]), source_python(report["result"])


def test_source_conditioned_shared_factor_and_mask_are_owned_by_exact_evidence():
    products = rows()
    (op,) = run(products, mode="coupled")
    report, request, result = extract(op)
    assert op["operation_version"] == "local-interpretation-2"
    assert report["policy_version"] == "shared-table-band-3"
    assert report["policy_mode"] == "coupled" and report["coupling_enabled"]
    (joint,) = [p for p in request["potentials"] if len(p["scope"]) > 1]
    assert joint["scope"] == [d["key"] for d in request["decisions"]]
    assert joint["dependency_ids"][0] == "band-x"
    assert [m["allowed"] for m in request["constraints"]] == [[True, True, False]] * 2
    assert {c["kind"] for d in request["decisions"] for c in d["candidates"]} == {
        "resolved",
        "unresolved",
    }
    assert result["search"]["positive_states"] == 4
    probabilities = [a["probability"] for a in result["alternatives"]]
    assert sorted(probabilities) == pytest.approx([0.2, 0.2, 0.2, 0.4])
    for alternative in result["alternatives"]:
        assert all(not c["candidate"].endswith("band-y") for c in alternative["choices"])
    assert result["event_probabilities"] == [
        {"event": "any-header", "probability": pytest.approx(0.8)}
    ]
    validate_local_interpretation_report(op, products)
    (reversed_op,) = run(list(reversed(products)), mode="coupled")
    assert reversed_op["operation_key"] == op["operation_key"]
    reversed_report, reversed_request, reversed_result = extract(reversed_op)
    assert reversed_report["retained_input_digest"] == report["retained_input_digest"]
    assert reversed_request == request
    assert reversed_result["marginals"] == result["marginals"]
    assert reversed_result["alternatives"] == result["alternatives"]


def test_three_arms_and_sensitivity_use_identical_support_and_count_overlap_once():
    outcomes = {}
    for mode, scale, expected in (
        ("feasibility", 1.0, 3 / 4),
        ("independent", 1.0, 1 - (1 + sqrt(2)) ** -2),
        ("coupled", 0.5, (2 + sqrt(2)) / (3 + sqrt(2))),
        ("coupled", 1.0, 4 / 5),
        ("coupled", 2.0, 6 / 7),
    ):
        (op,) = run(mode=mode, weight_scale=scale)
        report, request, result = extract(op)
        assert report["outcome"] == "completed"
        assert report["policy_mode"] == mode
        assert result["event_probabilities"][0]["probability"] == pytest.approx(expected)
        outcomes[mode, scale] = report, request
    first_report, first_request = outcomes["feasibility", 1.0]
    for report, request in outcomes.values():
        assert report["retained_input_digest"] == first_report["retained_input_digest"]
        for field in ("decisions", "constraints", "events", "selection"):
            assert request[field] == first_request[field]
    assert len({r["request_digest"] for r, _ in outcomes.values()}) == len(outcomes)


def test_absent_endpoint_and_false_mode_refuse():
    with pytest.raises(ValueError, match="endpoint"):
        run(rows()[1:])
    (op,) = run()
    bad = deepcopy(op)
    bad["local_interpretation"]["policy_mode"] = "independent"
    bad["local_interpretation"]["seal"] = _digest(
        {k: v for k, v in bad["local_interpretation"].items() if k != "seal"}
    )
    with pytest.raises(ValueError, match="mode"):
        validate_local_interpretation_report(bad, rows())


def test_weighted_joint_cannot_be_resealed_as_uniform_feasibility():
    (op,) = run()
    report, request, _ = extract(op)
    request["feasibility_control"] = True
    report["request"] = source_value(request)
    report["request_digest"] = _digest(report["request"])
    report["policy_mode"] = "feasibility"
    report["coupling_enabled"] = False
    report["seal"] = _digest({key: value for key, value in report.items() if key != "seal"})
    with pytest.raises(ValueError, match="feasibility control"):
        validate_local_interpretation_report(op, rows())


def test_parent_child_header_levels_and_multi_target_notes_can_coapply():
    products = [
        participant("cell-a", "cell", (2, 3), (1, 2)),
        participant("band", "header", (0, 1), (1, 3)),
        participant("measure", "header", (1, 2), (1, 2)),
        participant("note-one", "note", (0, 1), (1, 3)),
        participant("note-two", "note", (0, 1), (1, 3)),
        attachment("cell-a", "band"),
        attachment("cell-a", "measure"),
        attachment("cell-a", "note-one", "note", "matched_cue"),
        attachment("cell-a", "note-two", "note", "matched_cue"),
    ]
    (op,) = run(products, mode="coupled")
    _, request, result = extract(op)
    assert len(request["decisions"]) == 4
    assert not request["constraints"]
    assert result["search"]["positive_states"] == 36
    best = result["alternatives"][0]["choices"]
    assert {c["candidate"] for c in best} == {
        "cell-aband",
        "cell-ameasure",
        "cell-anote-one",
        "cell-anote-two",
    }


def test_large_band_retains_all_edges_without_constructing_exponential_support():
    products: list[dict[str, Any]] = [participant("band", "header", (0, 1), (0, 17))]
    for i in range(17):
        subject = "cell-" + str(i)
        products.extend(
            (
                participant(subject, "cell", (2, 3), (i, i + 1)),
                attachment(subject, "band"),
            )
        )
    (op,) = run(products)
    report = op["local_interpretation"]
    assert op["outcome"] == "not_run"
    assert report["policy_version"] == "shared-table-band-3"
    assert "17" in report["reason"] and "16" in report["reason"]
    assert report["probability_standing"] == "not_computed"
    assert len(report["contribution_ids"]) == 35
    assert "result" not in report and "request" not in report
    validate_local_interpretation_report(op, products)


def test_cancelled_policy_retains_no_probabilities():
    cancellation = Event()
    cancellation.set()
    (op,) = run(cancellation=cancellation)
    report, _, result = extract(op)
    assert report["outcome"] == "cancelled"
    assert result["marginals"] == result["event_probabilities"] == result["alternatives"] == []
