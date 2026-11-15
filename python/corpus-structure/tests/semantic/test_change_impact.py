"""Independent source-change relevance and actual native selected-currentness cases."""

from dataclasses import replace
from decimal import Decimal

import pytest

from corpus_structure.semantic._data_operation_fates import VisibleFate
from corpus_structure.semantic.change_impact import (
    ChangeImpactRequest,
    PopulationMember,
    RevocationCause,
    SelectionEvidence,
    changed_operations,
    classify_change_impact,
    inspect_change_impact,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from semantic.data_operation_kernel_support import POPULATION, STORAGE
from semantic.declared_scenarios import declared_serving_case as declared_serving_case
from semantic.declared_scenarios import declared_serving_seed as declared_serving_seed
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
    model,
    subject="one",
    *,
    fate: VisibleFate = "fulfilled",
    product="value:one",
    episode="episode:one",
):
    return SelectionEvidence(
        member=PopulationMember(
            operation=model.operations[0].semantic_id,
            subject=subject,
            subject_definition=model.operations[0].subject,
            original_source="source:one",
        ),
        fate=fate,
        derivations=(episode,),
        products=((product, None, "result", 0, 1),),
    )


@pytest.fixture(scope="module")
def impact_models():
    return models()


@pytest.mark.parametrize(
    ("fate", "state", "reason"),
    [
        ("waiting", "awaiting", "target_execution_not_settled"),
        ("attached", "awaiting", "target_execution_not_settled"),
        ("awaiting-discovery", "awaiting", "target_execution_not_settled"),
        ("awaiting-inputs", "awaiting", "target_execution_not_settled"),
        ("awaiting-external", "awaiting", "target_execution_not_settled"),
        ("awaiting-population", "awaiting", "target_execution_not_settled"),
        ("unavailable", "unknown", "native_target_unavailable_cause_unestablished"),
        ("cancelled", "inapplicable", "target_demand_cancelled"),
        ("not-applicable", "inapplicable", "native_target_not_applicable"),
        ("failed", "unknown", "native_target_failed"),
        ("partial", "unknown", "native_target_partial"),
        ("invalid", "unknown", "native_target_invalid"),
        ("unknown", "unknown", "native_target_unknown"),
        ("known-absent", "unknown", "native_target_known_absent"),
        ("closed", "unknown", "native_target_closed"),
    ],
)
def test_nonfulfilled_target_fates_do_not_become_value_or_absence_proof(
    impact_models, fate, state, reason
):
    before, target = impact_models
    current = observation(target, fate=fate)
    (row,) = classify_change_impact(
        before, target, before=(observation(before),), target=(current,), target_observed=True
    )
    assert row.state == state
    assert row.reasons == (reason,)


def test_unknown_protocol_fate_is_rejected_at_observation_boundary(impact_models):
    before, _ = impact_models
    invalid = observation(before).model_dump()
    invalid["fate"] = "unrecognized"
    with pytest.raises(ValueError, match="Input should be"):
        SelectionEvidence.model_validate(invalid)


def test_complete_population_absence_precedes_partial_target_fate(impact_models):
    before, target = impact_models
    old = observation(before)
    (row,) = classify_change_impact(
        before,
        target,
        before=(old,),
        target=(observation(target, fate="partial"),),
        before_population=(old.member,),
        target_population=(),
        population_complete=True,
        target_observed=True,
    )
    assert row.state == "inapplicable"
    assert row.reasons == ("absent_under_complete_target_population",)


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
    fresh = equal.model_copy(update={"derivations": ("episode:independent",)})
    assert (
        classify_change_impact(
            before, target, before=(old,), target=(fresh,), target_observed=True
        )[0].state
        == "substitutable"
    )
    assert classify_change_impact(before, target, before=(old,))[0].state == "unknown"
    proven = old.model_copy(
        update={
            "invalidity_causes": (
                RevocationCause(
                    kind="direct",
                    reference="revocation:one",
                    selector_kind="derivation",
                    selector="episode:one",
                ),
            )
        }
    )
    assert classify_change_impact(before, target, before=(proven,))[0].state == "revoked"
    assert (
        classify_change_impact(
            before, target, before=(proven,), target=(equal,), target_observed=True
        )[0].state
        == "unknown"
    )
    assert (
        classify_change_impact(
            before, target, before=(proven,), target=(fresh,), target_observed=True
        )[0].state
        == "substitutable"
    )


def test_native_admitted_rebound_support_preserves_same_trusted_producer_episode():
    before, target = models()
    original = observation(before, fate="unavailable").model_copy(
        update={
            "support": ("episode:withdrawn-upstream",),
            "invalidity_causes": (
                RevocationCause(
                    kind="upstream",
                    reference="revocation:upstream",
                    selector_kind="derivation",
                    selector="episode:withdrawn-upstream",
                    derivation_id="episode:withdrawn-upstream",
                ),
            ),
        }
    )
    rebound = observation(target).model_copy(update={"support": ("episode:trusted-replacement",)})
    row = classify_change_impact(
        before, target, before=(original,), target=(rebound,), target_observed=True
    )[0]
    assert row.state == "substitutable" and row.witnesses == ("episode:one", "revocation:upstream")


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
        assert first.population_complete
        invented = PopulationMember(
            operation="urn:invented",
            subject="not-in-demand",
            subject_definition="invented-subject",
            original_source="source:invented",
        )
        uncorroborated = inspect_change_impact(
            connection,
            request.model_copy(
                update={
                    "before_population": (invented,),
                    "target_population": (),
                    "population_complete": True,
                }
            ),
            target_prepared=stage.prepared,
        )
        assert all(row.member.subject != "not-in-demand" for row in uncorroborated.items)
        assert any("supplied population differs" in reason for reason in uncorroborated.unknowns)
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


def test_population_context_uses_jsonb_number_meaning_without_bool_or_string_conflation():
    base = PopulationMember(
        operation="op",
        subject="one",
        subject_definition="declared-subject",
        original_source="source",
        analyzed_scope={"index": 1},
    )
    assert base.key == base.model_copy(update={"analyzed_scope": {"index": Decimal("1.00")}}).key
    assert base.key != base.model_copy(update={"subject_definition": "another-subject"}).key
    assert base.key != base.model_copy(update={"analyzed_scope": {"index": True}}).key
    assert base.key != base.model_copy(update={"analyzed_scope": {"index": "1"}}).key


def test_actual_native_revocation_causes_distinguish_producer_and_upstream(declared_serving_case):
    import json
    from typing import cast

    from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    episode = json.loads(stage.source_receipt)["derivation_id"]
    with clone.writer.begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                dict(
                    project_id=stage.project_id,
                    original_source=stage.original_source,
                    selector_kind="derivation",
                    selector=episode,
                    reason="independent revoked producer fixture",
                ),
            )
        )
    request = ChangeImpactRequest(
        project_id=stage.project_id,
        before_demand_id=stage.demand_id,
        target_release_id=stage.prepared.release_id,
        target_demand_id=stage.demand_id,
    )
    with clone.reader.begin() as connection:
        result = inspect_change_impact(connection, request, target_prepared=stage.prepared)
    rows = [row for row in result.items if row.state == "revoked"]
    assert rows
    assert any("direct_derivation_revocation" in row.reasons for row in rows)
    assert any("upstream_derivation_revocation" in row.reasons for row in rows)
    assert all(any(witness.startswith("revocation:") for witness in row.witnesses) for row in rows)


def test_cancelled_target_demand_is_not_reported_as_revoked(declared_serving_case):
    from typing import cast

    from corpus_structure.semantic._data_operation_wire import WireCancelDataDemandRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    with clone.writer.begin() as connection:
        DataOperationStorage(connection).cancel_data_demand(
            cast(
                WireCancelDataDemandRequest,
                dict(
                    demand_id=stage.demand_id,
                    reason="independent requested cancellation",
                ),
            )
        )
    with clone.reader.begin() as connection:
        report = inspect_change_impact(
            connection,
            ChangeImpactRequest(
                project_id=stage.project_id,
                before_demand_id=stage.demand_id,
                target_release_id=stage.prepared.release_id,
                target_demand_id=stage.demand_id,
            ),
            target_prepared=stage.prepared,
        )
    assert all(
        row.state == "inapplicable" and row.reasons == ("target_demand_cancelled",)
        for row in report.items
    )


def _executed_change_recipe():
    from semantic.data_operation_declaration_support import source_declaration
    from semantic.data_operation_kernel_support import EXECUTION

    producer = source_declaration()
    producer.update(
        id="urn:change:producer", parameters={"value": {"value_type": "integer", "default": 7}}
    )
    producer["roles"][0].update(collection="scalar", maximum=1, kind="primitive:integer")
    producer["capabilities"]["cancellation"] = "call-boundary"
    consumer = source_declaration()
    consumer.update(id="urn:change:consumer", dependencies=[producer["id"]])
    consumer["roles"][0].update(collection="scalar", maximum=1, kind="primitive:integer")
    consumer["roles"].insert(
        0,
        dict(
            name="item",
            parameter="item",
            kind="primitive:integer",
            direction="input",
            minimum=1,
            maximum=1,
            collection="scalar",
            presence="required",
            support=dict(
                provenance="value_substitution",
                source="same-original",
                coverage="selected-scope",
                identity_requirements=[],
            ),
        ),
    )
    consumer["binding"] = dict(operator="scan", roles=["item"])
    consumer["capabilities"]["cancellation"] = "call-boundary"
    source = (
        "def helper(value: int) -> int:\n    return value\n"
        "def producer(*, value: int = 7) -> int:\n    return helper(value)\n"
        f"producer__data_operation__ = {producer!r}\n"
        "def consumer(item: int) -> int:\n    return item * 2\n"
        f"consumer__data_operation__ = {consumer!r}\n"
    ).encode()
    return replace(
        EXECUTION,
        name="source-change-cutoff",
        python_sources=(("ddo_execution_fixture", "ddo_execution_fixture.py", source),),
    )


@pytest.mark.parametrize("ddo_kernel", [_executed_change_recipe()], indirect=True)
def test_changed_python_helper_executes_new_recipe_and_equal_output_cuts_off_consumer(
    ddo_kernel, tmp_path, monkeypatch
):
    from corpus_structure.semantic.change_impact import resume_changed_demand
    from corpus_structure.semantic.data_operation_demands import (
        DemandPlanner,
        RootSubject,
        freeze_demand,
    )
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from semantic.data_operation_kernel_support import admit_kernel, prepare_kernel

    old = ddo_kernel
    module, filename, content = old.recipe.python_sources[0]
    target_directory = tmp_path / "target"
    target_directory.mkdir()
    new_recipe = replace(
        old.recipe,
        name="source-change-cutoff-new",
        project_id=None,
        python_sources=(
            (module, filename, content.replace(b"return value\n", b"return value + 0\n")),
        ),
    )
    preparation = prepare_kernel(new_recipe, directory=target_directory)
    with old.engine.begin() as connection:
        target = admit_kernel(connection, new_recipe, preparation=preparation)

    def register(kernel):
        intent = freeze_demand(
            kernel.model,
            roots=(RootSubject("one", "source:one", b"{}"),),
            targets=("urn:change:consumer",),
            inference="exact-source-change",
            execution_profile="execution:test",
        )
        with old.engine.begin() as connection:
            return DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
                intent,
                project="execution",
                release=kernel.prepared.release_id,
                runtime=kernel.runtime,
            )["demand_id"]

    import sys

    monkeypatch.delitem(sys.modules, module, raising=False)
    monkeypatch.syspath_prepend(str(old.preparation.directory))
    original_demand = register(old)
    first = resume_changed_demand(
        old.engine,
        original_demand,
        project_id="execution",
        source_root=old.preparation.directory,
        database_capacity=6,
    )
    assert first.receipt_count == 2
    target_demand = register(target)
    request = ChangeImpactRequest(
        project_id="execution",
        before_demand_id=original_demand,
        target_release_id=target.prepared.release_id,
        target_demand_id=target_demand,
    )
    with old.engine.begin() as connection:
        waiting = inspect_change_impact(connection, request, target_prepared=target.prepared)
    assert any(row.state == "awaiting" for row in waiting.items)
    assert changed_operations(old.model, target.model)[0] == {"urn:change:producer"}
    monkeypatch.syspath_prepend(str(target_directory))
    monkeypatch.delitem(sys.modules, module)
    changed = resume_changed_demand(
        old.engine,
        target_demand,
        project_id="execution",
        source_root=target_directory,
        database_capacity=6,
    )
    assert changed.receipt_count == 1
    with old.engine.begin() as connection:
        final = inspect_change_impact(connection, request, target_prepared=target.prepared)
    assert all(row.state == "substitutable" for row in final.items)
    consumer = next(row for row in final.items if row.member.operation == "urn:change:consumer")
    assert len(consumer.witnesses) == 1  # Original consumer episode is genuinely reused.
    producer = next(row for row in final.items if row.member.operation == "urn:change:producer")
    assert len(producer.witnesses) == 2  # New source execution, equal semantic output.


def test_real_changed_helper_recipe_preserves_downstream_recipe():
    from semantic.data_operation_kernel_support import prepare_kernel

    recipe = _executed_change_recipe()
    module, filename, content = recipe.python_sources[0]
    target = replace(
        recipe,
        name="pure-source-change",
        python_sources=(
            (module, filename, content.replace(b"return value\n", b"return value + 0\n")),
        ),
    )
    before, after = prepare_kernel(recipe), prepare_kernel(target)
    assert changed_operations(before.model, after.model)[0] == {"urn:change:producer"}


@pytest.mark.parametrize("ddo_kernel", [POPULATION], indirect=True, ids=["population"])
def test_native_population_closure_requires_each_frozen_producer_context(ddo_kernel):
    import json
    from typing import cast

    from corpus_structure.semantic._data_operation_wire import (
        WireCloseDataPopulationRequest,
        WireExpandDataObligationRequest,
        WireRetainDataCompletionIntentRequest,
    )
    from corpus_structure.semantic.change_impact import _acquire
    from corpus_structure.semantic.data_operation_demands import DemandPlanner, RootSubject
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from semantic.data_operation_binding_support import discover
    from semantic.data_operation_demand_support import claim, publish

    demand, _, _ = discover(
        ddo_kernel,
        values=(),
        additional_roots=(RootSubject("doc:two", "source:test", b'{"page":2}'),),
    )

    def acquire():
        with ddo_kernel["engine"].begin() as connection:
            return _acquire(
                connection,
                demand["demand_id"],
                project="ddo-test",
                scope={},
                read_id=None,
                expected_cut=None,
                max_bytes=8388608,
            )

    assert acquire()[3] is False
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        planner.storage.expand_data_obligation(
            cast(
                WireExpandDataObligationRequest,
                dict(
                    demand_id=demand["demand_id"],
                    operation_id="urn:discover",
                    subject="doc:two",
                    original_source="source:test",
                    analyzed_scope={"page": 2},
                    parameters={},
                ),
            )
        )
        ready = planner.ready(planner.resume(demand["demand_id"]), authorization=b"{}")
        second = next(
            row for row in ready if row.operation == "urn:discover" and row.subject == "doc:two"
        )
    fence = claim(ddo_kernel, json.loads(second.native))
    kind = ddo_kernel["identities"][
        next(k.semantic_id for k in ddo_kernel["model"].kinds if k.name == "Population"), "kind"
    ]

    with ddo_kernel["engine"].begin() as connection:
        intent = DataOperationStorage(connection).retain_data_completion_intent(
            cast(
                WireRetainDataCompletionIntentRequest,
                dict(
                    **fence,
                    runtime_id=ddo_kernel["runtime"],
                    completion=dict(
                        outcome="success",
                        implementation_revision="native-test-source-v1",
                        inputs=[],
                        support=[],
                        outputs=[
                            dict(
                                role="result",
                                position=0,
                                multiplicity=1,
                                product=dict(
                                    kind_contract=kind,
                                    body=semantic_value({"complete": True, "members": []}),
                                    members=[],
                                ),
                            )
                        ],
                    ),
                ),
            )
        )
    receipt = publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        snapshot = planner.__class__(ddo_kernel["model"], storage).resume(demand["demand_id"])
        use = next(
            row for row in snapshot["uses"] if row["derivation_id"] == receipt["derivation_id"]
        )
        storage.close_data_population(
            cast(
                WireCloseDataPopulationRequest,
                dict(
                    demand_id=demand["demand_id"],
                    name="all-items",
                    product_id=use["products"][0]["product_id"],
                    derivation_id=receipt["derivation_id"],
                    member_role="result",
                ),
            )
        )
    assert acquire()[3] is True


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_rebound_selected_support_attributes_new_upstream_revocation(ddo_kernel):
    from typing import cast

    from sqlalchemy import text

    from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
    from corpus_structure.semantic.change_impact import _acquire
    from corpus_structure.semantic.data_operation_demands import DemandPlanner
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from semantic.test_data_operation_storage import (
        test_native_planner_rebinds_equal_support_or_replaces_invalid_retained_generation,
    )

    test_native_planner_rebinds_equal_support_or_replaces_invalid_retained_generation(
        ddo_kernel, False
    )
    with ddo_kernel["engine"].begin() as connection:
        demand = connection.scalar(
            text("SELECT id FROM ops.data_demand ORDER BY created_at LIMIT 1")
        )
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand)
        consumer = next(
            row
            for row in snapshot["obligations"]
            if row["operation_id"] == "urn:ddo-test:value-consumer"
        )
        selected = next(
            row for row in snapshot["uses"] if row["obligation_id"] == consumer["obligation_id"]
        )
        support = cast(dict, selected["selection"])["support"]
        replacement = next(row["derivation_id"] for row in support if row.get("derivation_id"))
        episode = selected["derivation_id"]
        first = _acquire(
            connection,
            demand,
            project="ddo-test",
            scope={},
            read_id=None,
            expected_cut=None,
            max_bytes=8388608,
        )
        observed = next(
            row for row in first[1] if row.member.operation == "urn:ddo-test:value-consumer"
        )
        assert observed.fate == "fulfilled" and observed.derivations == (episode,)
        assert observed.invalidity_causes == ()
        result = classify_change_impact(
            ddo_kernel["model"],
            ddo_kernel["model"],
            before=(observed,),
            target=(observed,),
            target_observed=True,
        )
        assert result[0].state == "substitutable"
        revoked = planner.storage.revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                dict(
                    project_id="ddo-test",
                    original_source="source:test",
                    selector_kind="derivation",
                    selector=replacement,
                    reason="rebound current support withdrawn",
                ),
            )
        )
    with ddo_kernel["engine"].begin() as connection:
        after = _acquire(
            connection,
            demand,
            project="ddo-test",
            scope={},
            read_id=None,
            expected_cut=None,
            max_bytes=8388608,
        )
    current = next(row for row in after[1] if row.member.operation == "urn:ddo-test:value-consumer")
    assert current.fate == "unavailable"
    assert {(row.kind, row.selector, row.reference) for row in current.invalidity_causes} == {
        ("upstream", replacement, revoked["revocation_id"])
    }
    assert all(
        row.support_path[0] == "use:" + selected["use_id"] for row in current.invalidity_causes
    )
