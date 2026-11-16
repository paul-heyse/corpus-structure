"""Explicit retained semantic pins reuse facts, never another demand's work policy."""

import json
from dataclasses import replace
from typing import cast as typing_cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import (
    WireCancelDataDemandRequest,
    WireRevokeDataSupportRequest,
)
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, SourceSetEntry
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_product_reference import DataProductReference
from corpus_structure.semantic.identity import canonical_bytes
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import STORAGE
from semantic.test_data_operation_population_native import _complete_ready

PRODUCER = "urn:ddo-test:source"
CONSUMER = "urn:explicit-retained-consumer"
PLANNING_DEPENDENCY = "urn:unrelated-planning-dependency"


def _recipe(*, ordinary_dependency=False):
    assert STORAGE.declaration_content is not None
    declarations = json.loads(STORAGE.declaration_content)
    producer = next(op for op in declarations["operations"] if op["id"] == PRODUCER)
    consumer = json.loads(json.dumps(producer))
    consumer.update(id=CONSUMER, potential_dependencies=[PRODUCER])
    consumer["roles"].insert(
        0,
        {
            "name": "items",
            "kind": "integer",
            "direction": "input",
            "minimum": 1,
            "maximum": 1,
            "collection": "scalar",
            "presence": "alternative",
            "alternatives": [PRODUCER],
            "selected": PRODUCER,
            "subject_target": "source-set",
            "support": {
                "provenance": "exact",
                "source": "frozen-source-set",
                "source_set": "selected",
                "coverage": {"role": "items", "description": "exact-retained-product"},
                "identity_requirements": ["episode"],
            },
        },
    )
    consumer["binding"] = {"operator": "scan", "roles": ["items"]}
    if ordinary_dependency:
        unrelated = json.loads(json.dumps(producer))
        unrelated["id"] = PLANNING_DEPENDENCY
        declarations["operations"].append(unrelated)
        consumer["dependencies"] = [unrelated["id"]]
        consumer["potential_dependencies"].append(unrelated["id"])
    declarations["operations"].append(consumer)
    return replace(
        STORAGE,
        name="explicit-retained-source-pins" + ("-with-dependency" if ordinary_dependency else ""),
        declaration_content=canonical_bytes(declarations),
    )


PINNED = _recipe()
PINNED_WITH_DEPENDENCY = _recipe(ordinary_dependency=True)


def _episode_set_recipe():
    assert PINNED.declaration_content is not None
    declarations = json.loads(PINNED.declaration_content)
    consumer = next(item for item in declarations["operations"] if item["id"] == CONSUMER)
    role = next(item for item in consumer["roles"] if item["name"] == "items")
    role.update(collection="set", presence="required", maximum=None)
    role.pop("alternatives")
    role.pop("selected")
    consumer["binding"] = {"operator": "collection", "roles": ["items"], "collection": "set"}
    return replace(PINNED, name="exact-per-input-producing-episodes", declaration_content=canonical_bytes(declarations))


PINNED_EPISODES = _episode_set_recipe()


def _produce(kernel, *, subject, value, inference="inference:test"):
    demand, _, _, attached = attach(kernel, subject=subject, original_source="source:B", inference=inference)
    fence = claim(kernel, attached)
    receipt = publish(kernel, fence, retain(kernel, fence, outputs=(value,)))
    with kernel["engine"].connect() as connection:
        product = connection.scalar(
            text("SELECT product_id FROM ops.data_derivation_output WHERE derivation_id=:episode"),
            {"episode": receipt["derivation_id"]},
        )
    return demand, receipt, product


def _register(kernel, entry, inference="focus-comparison", *, expected_roots=(CONSUMER,)):
    intent = freeze_demand(
        kernel["model"],
        roots=(RootSubject("focus:A", "source:A", b'{"focus":true}'),),
        targets=(CONSUMER,),
        source_sets=(FrozenSourceSet("selected", (entry,)),),
        inference=inference,
        execution_profile="execution:test",
    )
    assert intent.record["root_operations"] == list(expected_roots)
    with kernel["engine"].begin() as connection:
        return DemandPlanner(kernel["model"], DataOperationStorage(connection)).register(
            intent,
            project="ddo-test",
            release=kernel["prepared"].release_id,
            runtime=kernel["runtime"],
        )


def _ready(kernel, demand):
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
        return snapshot, planner.ready(snapshot, authorization=b"{}")


@pytest.mark.parametrize("ddo_kernel", [PINNED], indirect=True, ids=["pinned-retained"])
def test_native_explicit_retained_pin_crosses_demands_without_hidden_production(ddo_kernel):
    source_demand, original, product = _produce(ddo_kernel, subject="source-subject:B", value=42)
    _, _sibling, sibling_product = _produce(ddo_kernel, subject="source-subject:sibling", value=99)
    context = SubjectContext(
        "ddo-test",
        "source-subject:B",
        "source:B",
        b'{"page":1}',
        subject_definition="original-occurrence",
    )
    entry = SourceSetEntry.from_semantic_source(DataProductReference(product), context=context)
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).cancel_data_demand(
            typing_cast(
                WireCancelDataDemandRequest,
                {"demand_id": source_demand["demand_id"], "reason": "finished source workflow"},
            )
        )
    demand = _register(ddo_kernel, entry)
    snapshot, ready = _ready(ddo_kernel, demand)
    (answer,) = ready
    (actual,) = answer.binding_result.roles[0].members
    assert (actual.product, actual.subject, actual.original_source) == (
        product,
        context.subject,
        context.original_source,
    )
    assert actual.product != sibling_product and actual.support_episodes == (
        original["derivation_id"],
    )
    with ddo_kernel["engine"].connect() as connection:
        obligations = connection.execute(
            text(
                "SELECT operation_id,subject,original_source FROM ops.data_obligation WHERE demand_id=:demand"
            ),
            {"demand": demand["demand_id"]},
        ).all()
        assert obligations == [(CONSUMER, "focus:A", "source:A")]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 2
    # A caller-provided context does not establish another source occurrence.
    wrong_entry = SourceSetEntry.from_semantic_source(
        DataProductReference(product), context=replace(context, subject="forged-context")
    )
    _, wrong = _ready(ddo_kernel, _register(ddo_kernel, wrong_entry, "wrong-context"))
    assert wrong == ()
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            typing_cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": "ddo-test",
                    "original_source": "source:B",
                    "selector_kind": "product",
                    "selector": product,
                    "reason": "the exact retained source was withdrawn",
                },
            )
        )
    _, untrusted = _ready(ddo_kernel, _register(ddo_kernel, entry, "revoked-source"))
    assert untrusted == ()
    with (
        ddo_kernel["engine"].begin() as connection,
        pytest.raises(DBAPIError, match="trust snapshot changed"),
        connection.begin_nested(),
    ):
        connection.execute(
            text(
                "SELECT * FROM ops.data_binding_rows(:demand,:operation,CAST(:trust AS jsonb),:read,:subject,:source,CAST(:scope AS jsonb))"
            ),
            {
                "demand": demand["demand_id"],
                "operation": CONSUMER,
                "trust": json.dumps(snapshot["trust_snapshot"]),
                "read": snapshot["read_id"],
                "subject": "focus:A",
                "source": json.dumps("source:A"),
                "scope": '{"focus":true}',
            },
        )
    with pytest.raises(DBAPIError, match=r"support|revoked"):
        _complete_ready(ddo_kernel, answer)
    with ddo_kernel["engine"].connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 2


@pytest.mark.parametrize(
    "ddo_kernel", [PINNED_WITH_DEPENDENCY], indirect=True, ids=["independent-pinned-producer"]
)
def test_explicit_input_producer_is_independent_of_other_planning_dependencies(ddo_kernel):
    from corpus_structure.semantic.data_product_reference import DataProductMemberReference

    _, original, product = _produce(ddo_kernel, subject="source-subject:B", value=42)
    _, _, sibling = _produce(ddo_kernel, subject="source-subject:sibling", value=99)
    context = SubjectContext(
        "ddo-test",
        "source-subject:B",
        "source:B",
        b'{"page":1}',
        subject_definition="original-occurrence",
    )
    reference = DataProductReference(product)
    entry = SourceSetEntry.from_semantic_source(reference, context=context)

    def register(selected, inference="independent-input"):
        return _register(
            ddo_kernel, selected, inference, expected_roots=(CONSUMER, PLANNING_DEPENDENCY)
        )

    snapshot, ready = _ready(ddo_kernel, register(entry))
    assert PRODUCER not in {row["operation_id"] for row in snapshot["obligations"]}
    (answer,) = [item for item in ready if item.operation == CONSUMER]
    (actual,) = answer.binding_result.roles[0].members
    assert actual.product == product and actual.product != sibling
    assert actual.support_episodes == (original["derivation_id"],)
    for wrong_entry, inference in (
        (
            SourceSetEntry.from_semantic_source(
                reference, context=replace(context, subject="forged-context")
            ),
            "wrong-header",
        ),
        (
            SourceSetEntry.from_semantic_source(
                DataProductMemberReference(reference, "missing-member"), context=context
            ),
            "wrong-member",
        ),
    ):
        _, refused = _ready(ddo_kernel, register(wrong_entry, inference))
        assert CONSUMER not in {item.operation for item in refused}
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            typing_cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": "ddo-test",
                    "original_source": "source:B",
                    "selector_kind": "product",
                    "selector": product,
                    "reason": "the exact pinned source is no longer available",
                },
            )
        )
    _, refused = _ready(ddo_kernel, register(entry, "revoked-independent-pin"))
    assert CONSUMER not in {item.operation for item in refused}


@pytest.mark.parametrize("ddo_kernel", [PINNED_EPISODES], indirect=True, ids=["same-value-independent-episodes"])
def test_same_native_value_and_position_keep_each_exact_selected_producing_episode(ddo_kernel):
    from copy import deepcopy

    _, first, product = _produce(ddo_kernel, subject="source-subject:B", value=42, inference="first-genuine-observation")
    _, second, same_product = _produce(ddo_kernel, subject="source-subject:B", value=42, inference="second-genuine-observation")
    _, foreign, foreign_product = _produce(ddo_kernel, subject="source-subject:foreign", value=42, inference="genuine-foreign-context")
    assert foreign_product != product
    assert product == same_product
    episodes = {first["derivation_id"], second["derivation_id"]}
    assert len(episodes) == 2
    context = SubjectContext("ddo-test", "source-subject:B", "source:B", b'{"page":1}', subject_definition="original-occurrence")
    entry = SourceSetEntry.from_semantic_source(DataProductReference(product), context=context)
    _, (ready,) = _ready(ddo_kernel, _register(ddo_kernel, entry, "exact-producing-episode-set"))
    (role,) = ready.binding_result.roles
    assert len(role.members) == 2
    assert {(member.product, member.member, member.position, member.multiplicity) for member in role.members} == {(product, None, 0, 1)}
    assert {member.support_episodes for member in role.members} == {(episode,) for episode in episodes}
    binding = json.loads(ready.binding)
    assert {item["support_derivation_ids"][0] for item in binding["inputs"]} == episodes
    with ddo_kernel["engine"].connect() as connection:
        for item in binding["inputs"]:
            selected = connection.scalar(text("SELECT ops.ddo_input_support_episodes(CAST(:binding AS jsonb),CAST(:input AS jsonb))"), {"binding": json.dumps(binding), "input": json.dumps(item)})
            assert selected == item["support_derivation_ids"]

        # Native CPU-basis reconstruction must use the same exact per-input set,
        # rather than unioning equal-value siblings. This asserts no execution.
        basis = connection.scalar(text("SELECT ops.ddo_cpu_input_basis(request) FROM ops.data_request request WHERE id=:request"), {"request": json.loads(ready.native)["request_id"]})
        from corpus_structure.semantic.data_operation_cpu_basis import cpu_basis_values, cpu_input_basis_from_roles
        assert isinstance(basis, list)
        grouped_roles, _ = cpu_basis_values(basis, scalar_roles=(), set_roles=("items",))
        from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
        observed_episodes = set()
        for item in grouped_roles["items"]:
            assert len(item.support) == 1
            reference = item.support[0]
            assert isinstance(reference, ComputationalSupportReference)
            observed_episodes.add(reference.derivation_id)
        assert observed_episodes == episodes
        assert ready.resolved.subject_context is not None
        assert basis == cpu_input_basis_from_roles(ddo_kernel["identities"][CONSUMER, "recipe"],
            ready.resolved.subject_context, ready.resolved.roles, {"items": (42, 42)},
            parameters=ready.resolved.parameters, replicate=ready.resolved.replicate)

    def counts(connection):
        return tuple(connection.scalar(text("SELECT count(*) FROM " + table)) for table in (
            "ops.data_request", "ops.task", "ops.data_completion_intent", "ops.data_derivation", "kb.data_product"))

    with ddo_kernel["engine"].begin() as connection:
        before = counts(connection)
        for mutation in ("missing", "unknown", "sibling", "foreign"):
            changed = deepcopy(binding)
            target = changed["inputs"][0]
            if mutation == "missing":
                target.pop("support_derivation_ids")
            elif mutation == "unknown":
                target["support_derivation_ids"] = ["derivation:never-produced"]
            elif mutation == "sibling":
                target["support_derivation_ids"] = changed["inputs"][1]["support_derivation_ids"]
            else:
                target["support_derivation_ids"] = [foreign["derivation_id"]]
                changed["support"].append(dict(kind="computation", derivation_id=foreign["derivation_id"], role=target["role"], position=target["position"]))
            with pytest.raises(DBAPIError, match="wire|support|native manifest member"), connection.begin_nested():
                connection.execute(text("SELECT ops.attach_data_request(CAST(:payload AS jsonb))"), {"payload": json.dumps(dict(
                    obligation_id=ready.obligation, request_meaning=json.loads(ready.request),
                    request_key=json.loads(ready.native)["request_id"], binding=changed, replicate=None))})
            assert counts(connection) == before
    from corpus_structure.semantic.data_operation_identity import CollectionValue, OptionalValue, canonical_identity, decode_semantic_value, semantic_value
    meaning = decode_semantic_value(json.loads(ready.request)[3])
    original_members = meaning["inputs"]["items"]["value"].value.members
    merged = dict(original_members[0], support_episodes=tuple(sorted(episodes)))
    meaning["inputs"]["items"]["value"] = OptionalValue("present", CollectionValue("set", (merged,)))
    grouped = deepcopy(binding)
    grouped["inputs"] = [dict(binding["inputs"][0], support_derivation_ids=sorted(episodes))]
    grouped["request_inputs"] = semantic_value(meaning["inputs"])
    grouped_key = canonical_identity("semantic-request", meaning)
    with ddo_kernel["engine"].begin() as connection:
        before = counts(connection)
        with pytest.raises(DBAPIError, match="support set has no exact native binding row"), connection.begin_nested():
            connection.execute(text("SELECT ops.attach_data_request(CAST(:payload AS jsonb))"), {"payload": json.dumps(dict(
                obligation_id=ready.obligation, request_meaning=json.loads(grouped_key.canonical_input), request_key=grouped_key.key,
                binding=grouped, replicate=None))})
        assert counts(connection) == before
    receipt = _complete_ready(ddo_kernel, ready)
    with ddo_kernel["engine"].connect() as connection:
        retained = connection.execute(text("SELECT support_derivation_id FROM ops.data_derivation_support WHERE derivation_id=:episode ORDER BY support_derivation_id"), {"episode": receipt["derivation_id"]}).scalars().all()
        inputs = connection.execute(text("SELECT product_id,position FROM ops.data_derivation_input WHERE derivation_id=:episode ORDER BY position"), {"episode": receipt["derivation_id"]}).all()
    assert set(retained) == episodes and len(retained) == 2
    assert inputs == [(product, 0), (product, 1)]
