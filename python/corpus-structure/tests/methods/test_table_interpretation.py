"""Literal source-choice expectations distinguish real shared coupling from duplicate votes."""

from copy import deepcopy
from typing import Any

import pytest

from corpus_structure.methods.table_interpretation import table_policy_operations
from corpus_structure.semantic.local_interpretation_reports import (
    validate_local_interpretation_report,
)
from corpus_structure.semantic.observations import source_python, source_value


def rows():
    result: list[dict[str, Any]] = [
        dict(contribution_id=key, computation_dependencies=("source",))
        for key in ("cell-a", "cell-b", "band-x", "band-y")
    ]
    for cell in ("cell-a", "cell-b"):
        for band in ("band-x", "band-y"):
            result.append(
                dict(
                    contribution_id=cell + band,
                    semantic_type="structural.scoped_attachment",
                    computation_dependencies=("source",),
                    value=source_value(
                        dict(
                            protocol="scoped-attachment-1",
                            subject_id=cell,
                            target_id=band,
                            relation="header",
                            region="#/tables/1",
                            scope="column1",
                        )
                    ),
                )
            )
    return result


def test_current_source_products_dispatch_once_owned_shared_factor():
    products = rows()
    (op,) = table_policy_operations(
        contributions=products,
        dependency_ids=("source",),
        source_revision="native1",
        mode="coupled",
    )
    report = op["local_interpretation"]
    assert op["operation_version"] == "local-interpretation-2"
    assert report["policy_mode"] == "coupled" and report["coupling_enabled"]
    request = source_python(report["request"])
    result = source_python(report["result"])
    joint = [p for p in request["potentials"] if len(p["scope"]) > 1]
    assert len(joint) == 1
    assert joint[0]["scope"] == ["cell-a", "cell-b"]
    assert result["log_partition"] == pytest.approx(1.791759469228055)
    probabilities = [a["probability"] for a in result["alternatives"]]
    assert sorted(probabilities) == pytest.approx([1 / 6, 1 / 6, 1 / 3, 1 / 3])
    validate_local_interpretation_report(op, products)
    (reversed_op,) = table_policy_operations(
        contributions=list(reversed(products)),
        dependency_ids=("source",),
        source_revision="native1",
        mode="coupled",
    )
    assert reversed_op["operation_key"] == op["operation_key"]
    assert (
        reversed_op["local_interpretation"]["retained_input_digest"]
        == report["retained_input_digest"]
    )
    reversed_result = source_python(reversed_op["local_interpretation"]["result"])
    assert reversed_result["marginals"] == result["marginals"]
    assert reversed_result["alternatives"] == result["alternatives"]


def test_three_modes_preserve_same_source_selection():
    modes = {
        mode: table_policy_operations(
            contributions=rows(), dependency_ids=("source",), source_revision="native1", mode=mode
        )[0]
        for mode in ("feasibility", "independent", "coupled")
    }
    assert {o["local_interpretation"]["policy_mode"] for o in modes.values()} == set(modes)
    assert len({o["local_interpretation"]["retained_input_digest"] for o in modes.values()}) == 1
    for mode in ("feasibility", "independent"):
        assert all(
            a["probability"] == pytest.approx(0.25)
            for a in source_python(modes[mode]["local_interpretation"]["result"])["alternatives"]
        )


def test_absent_endpoint_and_false_mode_refuse():
    with pytest.raises(ValueError, match="endpoint"):
        table_policy_operations(
            contributions=rows()[1:], dependency_ids=("source",), source_revision="native1"
        )
    (op,) = table_policy_operations(
        contributions=rows(), dependency_ids=("source",), source_revision="native1"
    )
    bad = deepcopy(op)
    bad["local_interpretation"]["policy_mode"] = "independent"
    from corpus_structure.semantic.local_interpretation_reports import _digest

    bad["local_interpretation"]["seal"] = _digest(
        {k: v for k, v in bad["local_interpretation"].items() if k != "seal"}
    )
    with pytest.raises(ValueError, match="mode"):
        validate_local_interpretation_report(bad, rows())
