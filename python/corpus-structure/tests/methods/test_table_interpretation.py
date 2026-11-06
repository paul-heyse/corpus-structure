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
    operations = table_policy_operations(
        contributions=products,
        dependency_ids=("source",),
        source_revision="native1",
        mode="coupled",
    )
    assert len(operations) == 2
    op = operations[0]
    report = op["local_interpretation"]
    assert op["operation_version"] == "local-interpretation-2"
    assert report["policy_mode"] == "coupled" and report["coupling_enabled"]
    request = source_python(report["request"])
    result = source_python(report["result"])
    joint = [p for p in request["potentials"] if len(p["scope"]) > 1]
    assert len(joint) == 1
    assert joint[0]["scope"] == ["cell-aband-x", "cell-bband-x"]
    assert {c["key"] for d in request["decisions"] for c in d["candidates"]} == {
        "applies",
        "does_not_apply",
    }
    assert result["log_partition"] == pytest.approx(1.791759469228055)
    probabilities = [a["probability"] for a in result["alternatives"]]
    assert sorted(probabilities) == pytest.approx([1 / 6, 1 / 6, 1 / 3, 1 / 3])
    validate_local_interpretation_report(op, products)
    reversed_op = table_policy_operations(
        contributions=list(reversed(products)),
        dependency_ids=("source",),
        source_revision="native1",
        mode="coupled",
    )[0]
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
        )
        for mode in ("feasibility", "independent", "coupled")
    }
    assert {o[0]["local_interpretation"]["policy_mode"] for o in modes.values()} == set(modes)
    for band in range(2):
        digests = {o[band]["local_interpretation"]["retained_input_digest"] for o in modes.values()}
        assert len(digests) == 1
    for mode in ("feasibility", "independent"):
        for op in modes[mode]:
            report = op["local_interpretation"]
            result = source_python(report["result"])
            assert report["outcome"] == "completed" and op["outcome"] == "succeeded"
            assert len(result["alternatives"]) == 4
            assert source_python(report["request"])["feasibility_control"] == (
                mode == "feasibility"
            )
        assert all(
            a["probability"] == pytest.approx(0.25)
            for op in modes[mode]
            for a in source_python(op["local_interpretation"]["result"])["alternatives"]
        )


def test_absent_endpoint_and_false_mode_refuse():
    with pytest.raises(ValueError, match="endpoint"):
        table_policy_operations(
            contributions=rows()[1:], dependency_ids=("source",), source_revision="native1"
        )
    op = table_policy_operations(
        contributions=rows(), dependency_ids=("source",), source_revision="native1"
    )[0]
    bad = deepcopy(op)
    bad["local_interpretation"]["policy_mode"] = "independent"
    from corpus_structure.semantic.local_interpretation_reports import _digest

    bad["local_interpretation"]["seal"] = _digest(
        {k: v for k, v in bad["local_interpretation"].items() if k != "seal"}
    )
    with pytest.raises(ValueError, match="mode"):
        validate_local_interpretation_report(bad, rows())


def test_weighted_joint_cannot_be_resealed_as_uniform_feasibility():
    from corpus_structure.semantic.local_interpretation_reports import _digest

    operations = table_policy_operations(
        contributions=rows(), dependency_ids=("source",), source_revision="native1"
    )
    assert len(operations) == 2
    op = operations[0]
    report = op["local_interpretation"]
    request = source_python(report["request"])
    request["feasibility_control"] = True
    report["request"] = source_value(request)
    report["request_digest"] = _digest(report["request"])
    report["policy_mode"] = "feasibility"
    report["coupling_enabled"] = False
    report["seal"] = _digest({key: value for key, value in report.items() if key != "seal"})
    with pytest.raises(ValueError, match="feasibility control"):
        validate_local_interpretation_report(op, rows())


@pytest.mark.parametrize("relation", ["header", "note"])
def test_multiple_bands_may_coapply_or_not_apply_without_competition(relation):
    products = rows()
    for row in products:
        if "value" in row:
            value = source_python(row["value"])
            value["relation"] = relation
            row["value"] = source_value(value)
    operations = table_policy_operations(
        contributions=products, dependency_ids=("source",), source_revision="native1"
    )
    assert len(operations) == 2
    # Parent/child headers and multiple notes remain separate applicability
    # questions. Each supports all included, all excluded, and partial states.
    for op in operations:
        result = source_python(op["local_interpretation"]["result"])
        assignments = {
            tuple(c["candidate"] for c in alternative["choices"])
            for alternative in result["alternatives"]
        }
        assert assignments == {
            ("applies", "applies"),
            ("applies", "does_not_apply"),
            ("does_not_apply", "applies"),
            ("does_not_apply", "does_not_apply"),
        }


def test_large_band_retains_all_edges_without_constructing_exponential_support():
    products: list[dict[str, Any]] = [
        dict(contribution_id="band", computation_dependencies=("source",))
    ]
    for i in range(17):
        subject = "cell-" + str(i)
        products.extend(
            (
                dict(contribution_id=subject, computation_dependencies=("source",)),
                dict(
                    contribution_id="edge-" + str(i),
                    semantic_type="structural.scoped_attachment",
                    computation_dependencies=("source",),
                    value=source_value(
                        dict(
                            protocol="scoped-attachment-1",
                            subject_id=subject,
                            target_id="band",
                            relation="header",
                            region="#/tables/1",
                            scope="column1",
                        )
                    ),
                ),
            )
        )
    (op,) = table_policy_operations(
        contributions=products, dependency_ids=("source",), source_revision="native1"
    )
    report = op["local_interpretation"]
    assert op["outcome"] == "not_run"
    assert report["policy_version"] == "shared-table-band-2"
    assert "17" in report["reason"] and "16" in report["reason"]
    assert report["probability_standing"] == "not_computed"
    assert len(report["contribution_ids"]) == 35
    assert "result" not in report and "request" not in report
    validate_local_interpretation_report(op, products)
