"""Actual selected-index support matching; controlled rows confer no native authority."""

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.refusal_types import RichQueryRefused
from corpus_structure.semantic.selected_contribution_input import actual_graph_inputs
from corpus_structure.semantic.selected_graph_budget import SelectedGraphBudgetExceeded
from corpus_structure.semantic.value_codec import decimal_digit_limit
from semantic.test_rich_query_delivery import CUT


def append(index, relation, key, value):
    index.append(json_bytes(dict(relation=relation, key=relation + "/" + key, record=value)))


@pytest.mark.parametrize("disclosure", ["matching", "other-use", "other-episode", "absent"])
def test_selected_products_respect_explicit_authority_disclosure_without_hiding_missing_episodes(
    tmp_path, disclosure
):
    from types import SimpleNamespace
    from typing import cast

    from corpus_structure.semantic.selected_contribution_input import SelectedContributionScope
    from semantic.test_authority_leaf import disclosure as authority_disclosure

    leaf, _ = authority_disclosure()
    index = SelectedRecordIndex(tmp_path / "authority.sqlite")
    try:
        index.append_page(
            {
                **CUT,
                "obligations": [],
                "original_source_admissions": [],
                "uses": [dict(use_id="use:one", derivation_id="issuer:one", fate="fulfilled")],
            }
        )
        if disclosure == "other-use":
            leaf["use_id"] = "use:other"
        elif disclosure == "other-episode":
            leaf["derivation_id"] = "issuer:other"
        if disclosure != "absent":
            append(index, "ops.data_authority_leaf", "authority", leaf)
        # The model and body are deliberately unavailable: an authority leaf must
        # not require or reconstruct its protected episode to skip ordinary roots.
        controlled = cast(SelectedContributionScope, SimpleNamespace(index=index))
        if disclosure == "matching":
            assert list(SelectedContributionScope.products(controlled)) == []
        else:
            with pytest.raises(KeyError):
                list(SelectedContributionScope.products(controlled))
    finally:
        index.close()


def request(index, inputs, support):
    append(
        index,
        "ops.data_derivation",
        "root-episode",
        dict(id="root-episode", request_id="root-request"),
    )
    append(
        index,
        "ops.data_request",
        "root-request",
        dict(id="root-request"),
    )

    index.append_page(
        {**CUT, "obligations": [], "original_source_admissions": [], "uses": [
            dict(use_id="root-use", derivation_id="root-episode", fate="fulfilled",
                 selection=dict(
                     inputs=[{**row, "position": row.get("position") or 0,
                              "multiplicity": 1, "producer_output": None,
                              "support_derivation_ids": []} for row in inputs],
                     support=[{**row, "position": row.get("position") or 0} for row in support],
                     parameters=semantic_value({}), request_inputs=semantic_value({}),
                     inference="controlled", execution_profile="controlled",
                     populations=[], read_id="read:controlled"))
        ]}
    )


def product(index, identifier, kind="kind:ordinary", body=None):
    append(
        index,
        "kb.data_product",
        identifier,
        dict(
            id=identifier,
            kind_contract=kind,
            canonical_body=semantic_value({"value": "actual"} if body is None else body),
        ),
    )


def test_unpositioned_support_population_resolves_only_actual_product_member_edges(tmp_path):
    index = SelectedRecordIndex(tmp_path / "scope.sqlite")
    try:
        inputs = [
            dict(role="sources", position=None, product_id="A", member_id=None),
            dict(role="sources", position=None, product_id="B", member_id="member:B"),
        ]
        supports = [
            dict(
                role="sources",
                position=None,
                kind="computation",
                derivation_id="producer:" + name,
                admission_use_id="use:" + name,
            )
            for name in ("A", "B")
        ]
        request(index, inputs, supports)
        product(index, "A")
        product(index, "B")
        append(
            index,
            "kb.data_product_member",
            "B/member:B",
            dict(product_id="B", member_id="member:B", kind_contract="kind:actual-child"),
        )
        for name in ("A", "B"):
            append(
                index,
                "ops.data_derivation_output",
                name,
                dict(derivation_id="producer:" + name, product_id=name, member_id=None),
            )
        refs, wholes = actual_graph_inputs(
            index,
            "root-episode",
            use_id="root-use",
            cut=CutSelection(json_bytes(CUT)),
            max_support_edges=100,
            decimal_fixed_point_digits=decimal_digit_limit(),
        )
        by_product = {item.product_id: item for item in refs}
        assert {item.derivation_id for item in by_product["A"].support_references} == {"producer:A"}
        assert {item.derivation_id for item in by_product["B"].support_references} == {"producer:B"}
        assert (
            by_product["B"].member_id == "member:B"
            and by_product["B"].kind_contract == "kind:actual-child"
        )
        assert [item.reference.product_id for item in wholes] == ["A"]
        with pytest.raises(SelectedGraphBudgetExceeded, match="examined-edge"):
            actual_graph_inputs(
                index,
                "root-episode",
                use_id="root-use",
                cut=CutSelection(json_bytes(CUT)),
                max_support_edges=1,
                decimal_fixed_point_digits=decimal_digit_limit(),
            )
    finally:
        index.close()


def test_authored_policy_keeps_distinct_original_admission_support(tmp_path):
    index = SelectedRecordIndex(tmp_path / "scope.sqlite")
    try:
        request(
            index,
            [dict(role="policy", position=None, product_id="authored-policy", member_id=None)],
            [
                dict(
                    role="policy",
                    position=None,
                    kind="authored",
                    admission_id="admission:policy",
                    source_reference="authored:policy",
                )
            ],
        )
        product(index, "authored-policy")
        append(
            index,
            "ops.original_source_admission",
            "admission:policy",
            dict(
                id="admission:policy",
                product_id="authored-policy",
                source_reference="authored:policy",
            ),
        )
        refs, _ = actual_graph_inputs(
            index,
            "root-episode",
            use_id="root-use",
            cut=CutSelection(json_bytes(CUT)),
            max_support_edges=100,
            decimal_fixed_point_digits=decimal_digit_limit(),
        )
        assert refs[0].support_references[0].kind == "authored"
        assert refs[0].support_references[0].admission_id == "admission:policy"
    finally:
        index.close()


@pytest.mark.parametrize(
    "defect",
    [None, "unavailable", "other-issuer", "protected-kind", "other-use", "parallel-valid-use"],
)
def test_actual_bounded_authority_leaf_is_not_reconstructed_as_hidden_edges(tmp_path, defect):
    from semantic.test_authority_leaf import disclosure

    leaf, contracts = disclosure()
    index = SelectedRecordIndex(tmp_path / "scope.sqlite")
    try:
        request(
            index,
            [
                dict(
                    role="policy_authorizations",
                    position=None,
                    product_id=leaf["product_id"],
                    member_id=None,
                )
            ],
            [
                dict(
                    role="policy_authorizations",
                    position=None,
                    kind="computation",
                    derivation_id=leaf["derivation_id"],
                    admission_use_id=leaf["use_id"],
                )
            ],
        )
        for identifier, value in contracts["products"].items():
            append(index, "kb.data_product", identifier, dict(id=identifier, **value))
        if defect == "protected-kind":
            contracts["kinds"][leaf["kind_contract"]] = dict(
                kind="urn:protected:labels", universe="evaluator"
            )
        for contract, value in contracts["kinds"].items():
            append(index, "sem.data_kind_contract", contract, dict(kind_contract=contract, **value))
        if defect == "unavailable":
            leaf["standing"] = "unavailable"
        elif defect == "other-issuer":
            leaf["issuer_operation"] = "unrelated.hidden-input"
        elif defect == "other-use":
            leaf["use_id"] = "different-use"
        append(index, "ops.data_authority_leaf", "authority", leaf)
        if defect == "parallel-valid-use":
            append(
                index,
                "ops.data_authority_leaf",
                "another-authority",
                {**leaf, "use_id": "use:another"},
            )
        if defect not in {None, "parallel-valid-use"}:
            with pytest.raises(RichQueryRefused, match="bounded authority"):
                actual_graph_inputs(
                    index,
                    "root-episode",
                    use_id="root-use",
                    cut=CutSelection(json_bytes(CUT)),
                    max_support_edges=100,
                    decimal_fixed_point_digits=decimal_digit_limit(),
                )
        else:
            refs, wholes = actual_graph_inputs(
                index,
                "root-episode",
                use_id="root-use",
                cut=CutSelection(json_bytes(CUT)),
                max_support_edges=100,
                decimal_fixed_point_digits=decimal_digit_limit(),
            )
            assert (
                len(refs) == 1
                and refs[0].support_references[0].derivation_id == leaf["derivation_id"]
            )
            assert len(wholes) == 1 and "judgment_basis_digest" in wholes[0].value
            assert list(index.rows("ops.data_derivation_output")) == []
            assert [row["id"] for row in index.rows("ops.data_request")] == ["root-request"]
    finally:
        index.close()


def test_acquired_support_can_be_sealed_while_retaining_exact_indexed_rows(tmp_path):
    from sqlalchemy.exc import OperationalError

    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex

    index = SelectedRecordIndex(tmp_path / "selected.sqlite")
    try:
        first = {
            "key": "episode:first",
            "relation": "ops.data_derivation",
            "record": {"id": "first"},
        }
        index.append(json_bytes(first))
        index.freeze()
        assert list(index.rows("ops.data_derivation")) == [{"id": "first"}]
        assert index.mapping("ops.data_derivation", ("id",))["first"] == {"id": "first"}
        with pytest.raises(OperationalError, match="readonly"):
            index.append(json_bytes({**first, "key": "episode:second", "record": {"id": "second"}}))
    finally:
        index.close()


def test_consumed_use_selection_keeps_same_derivation_uses_separate(tmp_path):
    from corpus_structure.semantic.selected_contribution_input import selected_use_selection

    index = SelectedRecordIndex(tmp_path / "uses.sqlite")
    try:
        request(index, [], [])
        index.append_page({
            **CUT, "obligations": [], "original_source_admissions": [],
            "uses": [dict(use_id="other-use", derivation_id="root-episode", fate="fulfilled",
                          selection={"inputs_watermark": "another-selected-basis"})],
        })
        assert selected_use_selection(index, "root-use", "root-episode")["inputs"] == []
        assert selected_use_selection(index, "other-use", "root-episode") == {
            "inputs_watermark": "another-selected-basis"
        }
        with pytest.raises(ValueError, match="exact fulfilled use"):
            selected_use_selection(index, "absent", "root-episode")
        with pytest.raises(ValueError, match="another derivation"):
            selected_use_selection(index, "root-use", "another-episode")
        assert "binding" not in index.mapping("ops.data_request", ("id",))["root-request"]
    finally:
        index.close()
