"""Installed native answer paging over exact current characterization outputs."""

from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.demand_results import read_selected_answer
from semantic.characterization_native_support import (
    characterization_source as characterization_source,
)
from semantic.characterization_native_support import (
    current_characterization_recipe as current_characterization_recipe,
)
from semantic.characterization_native_support import operation_product, operation_use

FORMAL = "text.formal_evidence/source-native"
CONSTRUCTION = "text.constructions/source-native"


def test_native_filtered_outputs_seek_within_one_obligation(characterization_source):
    source = characterization_source
    demand, _, snapshot = source.run(CONSTRUCTION)
    product = operation_product(snapshot, FORMAL)
    use = operation_use(snapshot, FORMAL)
    body = decode_semantic_value(product["body"])
    expected = {
        member["member_id"]: member["body"]
        for member in body["members"]
        if member["body"]["record_type"] == "occurrence"
    }
    assert len(expected) > 1
    selected, after, read_id, cut = [], None, None, None
    with source.reader.begin() as connection:
        for ordinal, member_id in enumerate(sorted(expected)):
            answer = read_selected_answer(
                connection,
                "read_selected_outputs",
                demand,
                project_id=source.factory.project_id,
                read_id=read_id,
                scope={"operation_id": FORMAL, "product_ids": [product["product_id"]]},
                after=after,
                product_id=product["product_id"],
                record_type="occurrence",
                body=True,
                limit=1,
                max_bytes=8 * 1024**2,
            )
            if cut is None:
                cut = answer["cut"]
                read_id = cut["read_id"]
            assert answer["cut"] == cut
            (row,) = answer["rows"]
            assert row["member_id"] == member_id
            assert row["use_id"] == use["use_id"]
            assert row["derivation_id"] == use["derivation_id"]
            assert row["product_id"] == product["product_id"]
            assert decode_semantic_value(row["meaning_body"]) == expected[member_id]
            selected.append(row["member_id"])
            after = answer["answer_after"]
            assert after == (
                [
                    use["obligation_id"],
                    use["use_id"],
                    product["role"],
                    product["position"],
                    product["product_id"],
                    member_id,
                ]
                if ordinal + 1 < len(expected)
                else None
            )
        empty = read_selected_answer(
            connection,
            "read_selected_outputs",
            demand,
            project_id=source.factory.project_id,
            scope={"operation_id": FORMAL},
            product_id="not-selected",
            body=True,
        )
        assert empty["rows"] == [] and empty["answer_after"] is None
        construction = operation_use(snapshot, CONSTRUCTION)
        facts = read_selected_answer(
            connection,
            "read_selected_derivation_facts",
            demand,
            project_id=source.factory.project_id,
            scope={"operation_id": CONSTRUCTION},
            use_id=construction["use_id"],
            derivation_id=construction["derivation_id"],
        )
        expected_inputs = {
            (row["role"], row["product_id"], row.get("member_id"), row["multiplicity"])
            for row in construction["selection"]["inputs"]
        }
        actual_inputs = {
            (row["role"], row["product_id"], row["member_id"], row["multiplicity"])
            for row in facts["rows"]
        }
        assert actual_inputs == expected_inputs
        assert any(
            reference["derivation_id"] == use["derivation_id"]
            and reference["admission_use_id"] == use["use_id"]
            for row in facts["rows"]
            if row["product_id"] == product["product_id"]
            for reference in row["support"]
        )
    assert selected == sorted(expected)
