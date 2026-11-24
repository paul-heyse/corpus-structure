"""Native selection preserves a chosen proof without collapsing equal semantic values."""

import json
from dataclasses import replace
from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_source_sets import (
    FrozenSourceSet,
    SelectedSourceSetEntry,
)
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.demand_results import read_demand_result
from semantic.population_completion_support import complete_ready
from semantic.test_data_operation_pinned_reuse_native import (
    CONSUMER,
    PINNED,
    _produce,
    _ready,
)

SOURCE_PROOF_CASE = pytest.mark.parametrize(
    "ddo_kernel", [PINNED], indirect=True, ids=["selected-source-proof"]
)


@pytest.fixture
def ddo_kernel(request, commit_db_engine, tmp_path):
    from semantic.data_operation_kernel_support import admit_kernel, prepare_kernel

    recipe = request.param
    preparation = prepare_kernel(recipe, directory=tmp_path / "source-acquisition-kernel")
    with commit_db_engine.begin() as connection:
        return admit_kernel(connection, recipe, engine=commit_db_engine, preparation=preparation)


def selected(kernel, demand, *, member_id=None):
    with kernel["engine"].begin() as connection:
        page = read_demand_result(connection, demand["demand_id"], project_id="ddo-test")
    (header,) = tuple(header for header in page.members() if header["member_id"] == member_id)
    return SelectedSourceSetEntry.from_selected_header(header, page.cut)


def register(kernel, source_set, *, inference="selected-source-control"):
    intent = freeze_demand(
        kernel["model"],
        roots=(RootSubject("focus:A", "source:A", b'{"focus":true}'),),
        targets=(CONSUMER,),
        source_sets=(source_set,) if isinstance(source_set, FrozenSourceSet) else source_set,
        inference=inference,
        execution_profile="execution:test",
    )
    with kernel["engine"].begin() as connection:
        return DemandPlanner(kernel["model"], DataOperationStorage(connection)).register(
            intent,
            project="ddo-test",
            release=kernel["prepared"].release_id,
            runtime=kernel["runtime"],
        )


@SOURCE_PROOF_CASE
def test_native_selected_source_basis_preserves_two_producers_and_refuses_forged_selection(
    ddo_kernel,
):
    first_demand, first, first_product = _produce(
        ddo_kernel, subject="source-subject:B", value=42, inference="first-source-proof"
    )
    second_demand, second, second_product = _produce(
        ddo_kernel, subject="source-subject:B", value=42, inference="second-source-proof"
    )
    assert first_product == second_product
    assert first["derivation_id"] != second["derivation_id"]
    first_selection, second_selection = (
        selected(ddo_kernel, first_demand),
        selected(ddo_kernel, second_demand),
    )
    assert first_selection.entry == second_selection.entry
    assert first_selection.proof.output.member_id is None
    with ddo_kernel["engine"].connect() as connection:
        # The value use is valid under its own support without its historical episode.
        # The exact output proof must independently reach and validate that episode.
        validity = connection.execute(
            text(
                "SELECT closure.kind, closure.id, closure.valid FROM ops.data_demand_read boundary "
                "CROSS JOIN LATERAL ops.ddo_valid_closure(ARRAY[:use]::text[], "
                "'{}'::text[], boundary, '{}'::text[]) AS closure WHERE boundary.id=:read"
            ),
            {"use": first_selection.proof.anchor_use_id, "read": first_selection.read.read_id},
        ).all()
    assert ("use", first_selection.proof.anchor_use_id, True) in validity
    assert all(
        (kind, identity) != ("episode", first["derivation_id"]) for kind, identity, _ in validity
    )
    keys = []
    for source_selection in (first_selection, second_selection):
        demand = register(
            ddo_kernel, FrozenSourceSet.from_selected("selected", (source_selection,))
        )
        _, ready = _ready(ddo_kernel, demand)
        (answer,) = ready
        (member,) = answer.binding_result.roles[0].members
        assert member.support_references == (source_selection.proof.support,)
        assert member.producer_output == source_selection.proof.output
        keys.append(json.loads(answer.native)["request_id"])
    assert keys[0] != keys[1]  # This role deliberately requires episode identity.
    later_cut = selected(ddo_kernel, first_demand)
    assert later_cut.read.cut_id != first_selection.read.cut_id
    _, (same,) = _ready(
        ddo_kernel, register(ddo_kernel, FrozenSourceSet.from_selected("selected", (later_cut,)))
    )
    assert json.loads(same.native)["request_id"] == keys[0]

    # An explicitly unqualified value still sees both real episodes and cannot
    # become a scalar through a body-based or first-visible-proof collapse.
    _, broad = _ready(
        ddo_kernel,
        register(
            ddo_kernel,
            FrozenSourceSet.unqualified("selected", (first_selection.entry,)),
            inference="unqualified-proof-control",
        ),
    )
    assert broad == ()
    forged = (
        first_selection.proof.model_copy(update={"support": second_selection.proof.support}),
        first_selection.proof.model_copy(
            update={"anchor_use_id": second_selection.proof.anchor_use_id}
        ),
        first_selection.proof.model_copy(
            update={
                "output": first_selection.proof.output.model_copy(update={"role": "foreign-output"})
            }
        ),
        first_selection.proof.model_copy(
            update={"output": first_selection.proof.output.model_copy(update={"position": 1})}
        ),
        first_selection.proof.model_copy(
            update={"output": first_selection.proof.output.model_copy(update={"multiplicity": 2})}
        ),
    )
    for ordinal, proof in enumerate(forged):
        bad = replace(first_selection, proof=proof)
        with pytest.raises(DBAPIError, match="selected use/output support"):
            register(
                ddo_kernel,
                FrozenSourceSet.from_selected("selected", (bad,)),
                inference="forged-source-" + str(ordinal),
            )

    # Attachment/publication rechecks current trust rather than retaining the
    # authority of a prior successfully acquired selector.
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": "ddo-test",
                    "original_source": "source:B",
                    "selector_kind": "derivation",
                    "selector": first["derivation_id"],
                    "reason": "selected-proof-revocation-control",
                },
            )
        )
    with pytest.raises(DBAPIError, match=r"trust|revoked|support"):
        register(
            ddo_kernel,
            FrozenSourceSet.from_selected("selected", (first_selection,)),
            inference="revoked-source-control",
        )
    with ddo_kernel["engine"].connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 2


@SOURCE_PROOF_CASE
def test_native_source_acquisition_distinguishes_anchor_from_actual_producing_use(ddo_kernel):
    from corpus_structure.semantic.data_operation_source_sets import selected_source_entries
    from corpus_structure.semantic.demand_results import acquired_selected_relations
    from corpus_structure.semantic.selected_support import SelectedReadReference
    from semantic.test_data_operation_pinned_reuse_native import PRODUCER

    source_demand, source_receipt, _ = _produce(
        ddo_kernel, subject="source-subject:B", value=42, inference="source-anchor-control"
    )
    source = selected(ddo_kernel, source_demand)
    consumer = register(ddo_kernel, FrozenSourceSet.from_selected("selected", (source,)))
    _, (ready,) = _ready(ddo_kernel, consumer)
    complete_ready(ddo_kernel, ready, value=43)
    anchor = selected(ddo_kernel, consumer)
    with (
        ddo_kernel["engine"].begin() as connection,
        acquired_selected_relations(
            connection,
            consumer["demand_id"],
            project_id="ddo-test",
            scope={},
            capture_frontier=True,
        ) as (cut, index),
    ):
        (ancestor,) = selected_source_entries(
            index,
            cut,
            product_id=source.entry.product,
            member_id=None,
            anchor_use_id=anchor.proof.support.admission_use_id,
            support=source.proof.support,
        )
    assert ancestor.proof.anchor_use_id != ancestor.proof.support.admission_use_id
    _, (dependent,) = _ready(
        ddo_kernel,
        register(
            ddo_kernel,
            FrozenSourceSet.from_selected("selected", (ancestor,)),
            inference="ancestor-source-control",
        ),
    )
    assert dependent.binding_result.roles[0].members[0].support_references == (
        source.proof.support,
    )

    # Another native admission can reuse the SAME episode. Its use node is not
    # reachable from the original anchor and cannot substitute for that support.
    extra_intent = freeze_demand(
        ddo_kernel["model"],
        roots=(
            RootSubject("source-subject:B", "source:B", b'{"page":1}'),
            RootSubject("another-source-subject", "source:B", b'{"page":1}'),
        ),
        targets=(PRODUCER,),
        inference="source-anchor-control",
        execution_profile="execution:test",
    )
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        other_demand = planner.register(
            extra_intent,
            project="ddo-test",
            release=ddo_kernel["prepared"].release_id,
            runtime=ddo_kernel["runtime"],
        )
    _ready(ddo_kernel, other_demand)
    unrelated = selected(ddo_kernel, other_demand)
    assert unrelated.proof.support.derivation_id == source_receipt["derivation_id"]
    assert unrelated.proof.support.admission_use_id != source.proof.support.admission_use_id
    # Acquire AFTER that unrelated use exists, so refusal proves use reachability
    # rather than only the old cut's visibility fence.
    visible_source = selected(ddo_kernel, source_demand)
    forged = replace(
        visible_source,
        proof=visible_source.proof.model_copy(
            update={
                "support": unrelated.proof.support,
            }
        ),
    )
    with pytest.raises(DBAPIError, match="selected use/output support"):
        register(
            ddo_kernel,
            FrozenSourceSet.from_selected("selected", (forged,)),
            inference="unreachable-use-control",
        )

    # Self-consistent caller bytes still must equal the actual native cut.
    from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
    from corpus_structure.semantic.demand_results import CutSelection

    fake_record = wire_json_loads(visible_source.read.cut_canonical_json)
    fake_record["runtime_id"] = "runtime:foreign"
    fake_read = SelectedReadReference.from_cut(CutSelection(json_bytes(fake_record)))
    forged_cut = replace(visible_source, read=fake_read)
    with pytest.raises(DBAPIError, match="native retained cut bytes"):
        register(
            ddo_kernel,
            FrozenSourceSet.from_selected("selected", (forged_cut,)),
            inference="forged-cut-control",
        )

    # Exercise the public native acquisition entrypoint under an actual denied
    # purpose; this is an authorization refusal, not a mocked provider outcome.
    intent = freeze_demand(
        ddo_kernel["model"],
        roots=(RootSubject("focus:A", "source:A", b'{"focus":true}'),),
        targets=(CONSUMER,),
        source_sets=(FrozenSourceSet.from_selected("selected", (source,)),),
        inference="reader-purpose-refusal",
        execution_profile="execution:test",
    )
    with ddo_kernel["engine"].begin() as connection:
        connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_reader")
        with pytest.raises(DBAPIError) as refused, connection.begin_nested():
            DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection)).register(
                intent,
                project="ddo-test",
                release=ddo_kernel["prepared"].release_id,
                runtime=ddo_kernel["runtime"],
            )
        assert getattr(refused.value.orig, "sqlstate", None) == "42501"


def _two_role_slot_recipe():
    from copy import deepcopy

    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.test_data_operation_pinned_reuse_native import PRODUCER

    assert PINNED.declaration_content is not None
    declarations = json.loads(PINNED.declaration_content)
    producer = next(op for op in declarations["operations"] if op["id"] == PRODUCER)
    producer["roles"][0].update(maximum=2, collection="bag")
    consumer = next(op for op in declarations["operations"] if op["id"] == CONSUMER)
    original = next(role for role in consumer["roles"] if role["direction"] == "input")
    roles = [role for role in consumer["roles"] if role["direction"] == "output"]
    for name in ("left", "right"):
        role = deepcopy(original)
        role["name"] = name
        role["support"]["coverage"]["role"] = name
        role["support"]["source_set"] = name
        roles.append(role)
    consumer["roles"] = roles
    consumer["binding"] = {
        "operator": "all",
        "children": [{"operator": "scan", "roles": [name]} for name in ("left", "right")],
    }
    return replace(
        PINNED,
        name="selected-source-two-role-emitting-slots",
        declaration_content=canonical_bytes(declarations),
    )


TWO_ROLE_SLOTS = _two_role_slot_recipe()


@pytest.mark.parametrize("ddo_kernel", [TWO_ROLE_SLOTS], indirect=True, ids=["two-emitting-slots"])
def test_native_source_proof_selection_is_role_local_and_preserves_original_reuse_basis(ddo_kernel):
    from corpus_structure.semantic.selected_support import SelectedReadReference
    from semantic.data_operation_demand_support import attach, claim, publish, retain

    demand, _, _, attached = attach(
        ddo_kernel,
        subject="source-subject:B",
        original_source="source:B",
        inference="two-source-slots",
    )
    fence = claim(ddo_kernel, attached)
    receipt = publish(ddo_kernel, fence, retain(ddo_kernel, fence, outputs=(42, 42)))
    with ddo_kernel["engine"].begin() as connection:
        page = read_demand_result(connection, demand["demand_id"], project_id="ddo-test")
    read = SelectedReadReference.from_cut(page.cut)
    headers = sorted(page.members(), key=lambda row: row["position"])
    assert len(headers) == 2
    assert headers[0]["product_id"] == headers[1]["product_id"]
    assert {header["derivation_id"] for header in headers} == {receipt["derivation_id"]}
    first, second = (
        SelectedSourceSetEntry.from_selected_header(header, read) for header in headers
    )
    frozen = (
        FrozenSourceSet.from_selected("left", (first,)),
        FrozenSourceSet.from_selected("right", (second,)),
    )
    consumer = register(ddo_kernel, frozen, inference="same-semantic-request")
    _, (ready,) = _ready(ddo_kernel, consumer)
    positions = {}
    for role in ready.binding_result.roles:
        output = role.members[0].producer_output
        assert output is not None
        positions[role.role] = output.position
    assert positions == {"left": 0, "right": 1}
    original_request = json.loads(ready.native)["request_id"]
    original_binding = json.loads(ready.native)["binding"]
    complete_ready(ddo_kernel, ready, value=99)
    swapped = register(
        ddo_kernel,
        (
            FrozenSourceSet.from_selected("left", (second,)),
            FrozenSourceSet.from_selected("right", (first,)),
        ),
        inference="same-semantic-request",
    )
    _, executable = _ready(ddo_kernel, swapped)
    assert executable == ()  # A new proof choice admits reuse, not new inference.
    with ddo_kernel["engine"].begin() as connection:
        page = read_demand_result(connection, swapped["demand_id"], project_id="ddo-test")
        (use,) = [use for use in page.record["uses"] if use["fate"] == "fulfilled"]
        assert use["request_id"] == original_request
        assert {
            item["role"]: item["producer_output"]["position"] for item in use["selection"]["inputs"]
        } == {"left": 1, "right": 0}
        retained_binding = connection.scalar(
            text("SELECT binding FROM ops.data_request WHERE id=:id"), {"id": original_request}
        )
        assert isinstance(retained_binding, dict)
        assert {
            key: value for key, value in retained_binding.items() if key != "execution_profile"
        } == original_binding


def _member_source_recipe():
    from copy import deepcopy

    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.data_operation_kernel_support import POPULATION

    assert POPULATION.declaration_content is not None
    declarations = json.loads(POPULATION.declaration_content)
    whole = declarations["operations"][0]
    whole.update(id="urn:source-whole", profile="derivation")
    member = deepcopy(whole)
    member["id"] = "urn:source-member"
    member["roles"][0]["kind"] = "Sample"
    consumer = declarations["operations"][1]
    consumer.update(
        id=CONSUMER, dependencies=[], potential_dependencies=[whole["id"], member["id"]]
    )
    role = next(role for role in consumer["roles"] if role["direction"] == "input")
    role.update(maximum=1, collection="scalar", subject_target="source-set")
    role.pop("subject_field")
    role["support"].update(source="frozen-source-set", source_set="selected")
    consumer["binding"] = {"operator": "scan", "roles": [role["name"]]}
    declarations["operations"] = [whole, member, consumer]
    return replace(
        POPULATION,
        name="selected-source-whole-and-explicit-member",
        declaration_content=canonical_bytes(declarations),
    )


MEMBER_SOURCES = _member_source_recipe()


@pytest.mark.parametrize(
    "ddo_kernel", [MEMBER_SOURCES], indirect=True, ids=["whole-and-member-output"]
)
def test_native_source_acquisition_preserves_emitting_member_distinction(ddo_kernel):
    from corpus_structure.semantic.data_operation_values import semantic_value
    from semantic.data_operation_demand_support import attach, claim, publish, retain

    def contract(name):
        kind = next(kind for kind in ddo_kernel["model"].kinds if kind.name == name)
        return ddo_kernel["identities"][kind.semantic_id, "kind"]

    packet = dict(
        member_id="m15",
        kind_contract=contract("Sample"),
        context=dict(
            subject="member:one",
            subject_definition="original-occurrence",
            original_source="source:B",
            analyzed_scope={"page": 1},
        ),
        body={"value": 15, "document_subject": "source-subject:B"},
    )
    choices = []
    for operation, output_member in (("urn:source-whole", None), ("urn:source-member", "m15")):
        demand, _, _, attached = attach(
            ddo_kernel,
            operation=operation,
            subject="source-subject:B",
            original_source="source:B",
            inference="member-emission-control",
        )
        fence = claim(ddo_kernel, attached)

        def completion(value, selected_member=output_member):
            output = {
                "role": "result",
                "position": 0,
                "multiplicity": 1,
                "product": {
                    "kind_contract": contract("Population"),
                    "body": semantic_value({"complete": True, "members": [packet]}),
                    "members": [{**packet, "body": semantic_value(packet["body"])}],
                },
            }
            if selected_member is not None:
                output["member_id"] = selected_member
            value["outputs"] = [output]

        publish(ddo_kernel, fence, retain(ddo_kernel, fence, outputs=(), mutate=completion))
        choices.append(selected(ddo_kernel, demand, member_id="m15"))
    whole, member = choices
    assert whole.entry == member.entry
    assert whole.proof.output.member_id is None
    assert member.proof.output.member_id == "m15"
    for number, choice in enumerate(choices):
        _, (ready,) = _ready(
            ddo_kernel,
            register(
                ddo_kernel,
                FrozenSourceSet.from_selected("selected", (choice,)),
                inference="member-binding-" + str(number),
            ),
        )
        (actual,) = ready.binding_result.roles[0].members
        assert actual.member == "m15" and actual.producer_output == choice.proof.output

    # The pre-existing whole-output helper remains a whole-output contract.
    with ddo_kernel["engine"].begin() as connection:
        connection.execute(
            text("SELECT ops.ddo_require_selected_output(:d,:r,:u,:p,:e)"),
            {
                "d": whole.read.demand_id,
                "r": whole.read.read_id,
                "u": whole.proof.anchor_use_id,
                "p": whole.entry.product,
                "e": whole.proof.support.derivation_id,
            },
        )
    with (
        ddo_kernel["engine"].begin() as connection,
        pytest.raises(DBAPIError, match="selected support"),
        connection.begin_nested(),
    ):
        connection.execute(
            text("SELECT ops.ddo_require_selected_output(:d,:r,:u,:p,:e)"),
            {
                "d": member.read.demand_id,
                "r": member.read.read_id,
                "u": member.proof.anchor_use_id,
                "p": member.entry.product,
                "e": member.proof.support.derivation_id,
            },
        )
    for number, (choice, wrong_member) in enumerate(((whole, "m15"), (member, None))):
        forged = replace(
            choice,
            proof=choice.proof.model_copy(
                update={
                    "output": choice.proof.output.model_copy(update={"member_id": wrong_member}),
                }
            ),
        )
        with pytest.raises(DBAPIError, match="selected use/output support"):
            register(
                ddo_kernel,
                FrozenSourceSet.from_selected("selected", (forged,)),
                inference="forged-output-member-" + str(number),
            )
