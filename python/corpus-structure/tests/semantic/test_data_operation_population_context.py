"""Population association retains JSON context types within one frozen demand."""

import pytest

from corpus_structure.semantic.data_operation_demands import _population_context_matches


@pytest.mark.parametrize("scope, expected", [(1, True), (1.0, True), (True, False), ("1", False)])
@pytest.mark.parametrize("origin", ["selection", "producer", "source-set"])
def test_population_context_distinguishes_boolean_and_number_with_numeric_value_equality(
    scope, expected, origin,
):
    obligation = {
        "obligation_id": "obligation:one", "operation_id": "operation:aggregate",
        "subject": "subject:one", "original_source": "source:one", "analyzed_scope": {"page": 1},
    }
    context = {**obligation, "analyzed_scope": {"page": scope}}
    source_sets = {}
    if origin == "selection":
        row = {"evidence": {"selection": context}, "members": []}
    elif origin == "producer":
        row = {"evidence": {"producer_context": context}, "members": []}
    else:
        # A remote source is admitted only through the frozen member association.
        row = {
            "evidence": {
                "producer_context": {**context, "original_source": "source:remote"},
                "product_id": "product:remote",
            },
            "members": [{**context, "member_id": "member:one"}],
        }
        source_sets = {"selected": [{
            **obligation, "project_id": "project:one", "product": "product:remote",
            "member": "member:one", "original_source": "source:remote",
        }]}
        row["members"][0]["original_source"] = "source:remote"
    assert _population_context_matches(
        row, obligation, source_set="selected", source_sets=source_sets, project="project:one",
    ) is expected


def test_two_populations_in_one_demand_keep_their_distinct_boolean_and_numeric_roots():
    common = {"subject": "same", "original_source": "same"}
    rows = [{"evidence": {"producer_context": {**common, "analyzed_scope": {"page": value}}}}
            for value in (True, 1)]
    for index, value in enumerate((True, 1)):
        obligation = {**common, "analyzed_scope": {"page": value}}
        assert [position for position, row in enumerate(rows) if _population_context_matches(
            row, obligation, source_set=None, source_sets={}, project="project:one",
        )] == [index]
