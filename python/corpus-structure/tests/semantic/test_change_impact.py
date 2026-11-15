"""Independent source-change relevance and actual native selected-currentness cases."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.change_impact import (
    ChangeImpactRequest,
    PopulationMember,
    SelectionEvidence,
    changed_operations,
    classify_change_impact,
    inspect_change_impact,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from semantic.serving_scenarios import declared_serving_case as declared_serving_case
from semantic.serving_scenarios import declared_serving_seed as declared_serving_seed
from semantic.test_data_operation_compilation import operation_source, python_inputs


def models():
    before = compile_data_operations(python_sources=python_inputs(operation_source()))
    target = compile_data_operations(
        python_sources=python_inputs(
            operation_source().replace("return x + GLOBAL", "return x - GLOBAL")
        )
    )
    return before, target


def observation(
    model, subject="one", *, fate="fulfilled", product="value:one", episode="episode:one"
):
    return SelectionEvidence(
        member=PopulationMember(
            operation=model.operations[0].semantic_id, subject=subject, original_source="source:one"
        ),
        fate=fate,
        derivations=(episode,),
        products=((product, None, "result", 0, 1),),
    )


def test_helper_change_is_potential_while_unrelated_source_has_no_affected_roots():
    before, target = models()
    name = before.operations[0].semantic_id
    assert changed_operations(before, target)[0] == {name}
    (row,) = classify_change_impact(before, target, before=(observation(before),))
    assert row.state == "potential" and row.changed_roots == (name,)
    unrelated = compile_data_operations(
        python_sources=python_inputs(operation_source(extra="def other(): return 88\n"))
    )
    assert changed_operations(before, unrelated) == (set(), {})


def test_both_dependency_sides_preserve_removed_consumer_edge_and_finite_cycle():
    before, target = models()
    root = before.operations[0]
    consumer = replace(root, semantic_id="consumer", dependencies=(root.semantic_id,))
    old = replace(before, operations=(root, consumer))
    new = replace(target, operations=(*target.operations, replace(consumer, dependencies=())))
    assert changed_operations(old, new)[1]["consumer"] == {root.semantic_id, "consumer"}


def test_native_target_admission_and_equal_value_establish_cutoff_without_same_episode():
    before, target = models()
    old, new = observation(before), observation(target, episode="episode:new")
    (equal,) = classify_change_impact(
        before, target, before=(old,), target=(new,), target_observed=True
    )
    assert equal.state == "substitutable"
    changed = new.model_copy(update={"products": (("value:other", None, "result", 0, 1),)})
    (different,) = classify_change_impact(
        before, target, before=(old,), target=(changed,), target_observed=True
    )
    assert different.state == "stale"
    waiting = new.model_copy(update={"fate": "waiting"})
    assert (
        classify_change_impact(
            before, target, before=(old,), target=(waiting,), target_observed=True
        )[0].state
        == "awaiting"
    )


def test_unavailable_producer_cannot_be_rehabilitated_by_equal_bytes_or_same_episode():
    before, target = models()
    old = observation(before, fate="unavailable")
    equal = observation(target)
    assert (
        classify_change_impact(
            before, target, before=(old,), target=(equal,), target_observed=True
        )[0].state
        == "unknown"
    )
    fresh = equal.model_copy(update={"derivations": ("episode:independent",)})
    assert (
        classify_change_impact(
            before, target, before=(old,), target=(fresh,), target_observed=True
        )[0].state
        == "substitutable"
    )
    assert classify_change_impact(before, target, before=(old,))[0].state == "revoked"


def test_complete_populations_find_never_derived_addition_and_removed_subject():
    before, target = models()
    old, added = observation(before).member, observation(target, "new").member
    rows = classify_change_impact(
        before,
        target,
        before=(),
        before_population=(old,),
        target_population=(added,),
        population_complete=True,
    )
    actual = {row.member.subject: row.state for row in rows}
    assert actual == {"one": "inapplicable", "new": "awaiting"}
    incomplete = classify_change_impact(
        before, target, before=(), before_population=(old,), population_complete=False
    )
    assert incomplete[0].state == "potential"


def test_subject_scope_and_operation_population_duplicates_refuse():
    before, target = models()
    old = observation(before)
    scoped = old.model_copy(
        update={"member": old.member.model_copy(update={"analyzed_scope": {"page": 2}})}
    )
    assert len(classify_change_impact(before, target, before=(old, scoped))) == 2
    with pytest.raises(ValueError, match="repeat"):
        classify_change_impact(before, target, before=(old, old))


def test_actual_native_currentness_pins_target_and_continuation(declared_serving_case):
    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    request = ChangeImpactRequest(
        project_id=stage.project_id,
        before_demand_id=stage.demand_id,
        target_demand_id=stage.demand_id,
        target_release_id=stage.prepared.release_id,
        limit=1,
    )
    with clone.reader.begin() as connection:
        first = inspect_change_impact(connection, request, target_prepared=stage.prepared)
        assert first.items[0].state == "substitutable"
        if first.continuation is not None:
            second = inspect_change_impact(
                connection,
                request.model_copy(update={"cursor": first.continuation}),
                target_prepared=stage.prepared,
            )
            assert second.comparison_id == first.comparison_id
            assert second.items[0].member != first.items[0].member
            with pytest.raises(ValueError, match=r"comparison|scope"):
                inspect_change_impact(
                    connection,
                    request.model_copy(
                        update={"cursor": first.continuation, "scope": {"subject": "other"}}
                    ),
                    target_prepared=stage.prepared,
                )
        assert first.before_cut["project_id"] == stage.project_id
        with pytest.raises(ValueError, match="project"):
            inspect_change_impact(
                connection,
                request.model_copy(update={"project_id": "wrong"}),
                target_prepared=stage.prepared,
            )
