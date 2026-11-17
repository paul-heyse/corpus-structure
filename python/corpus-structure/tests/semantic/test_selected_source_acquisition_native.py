"""Native selection preserves a chosen proof without collapsing equal semantic values."""

from dataclasses import replace
from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
from corpus_structure.semantic.data_operation_demands import DemandPlanner, RootSubject, freeze_demand
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, SelectedSourceSetEntry
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.demand_results import read_demand_result
from semantic.test_data_operation_pinned_reuse_native import CONSUMER, PINNED, _complete_ready, _produce, _ready

pytestmark = pytest.mark.parametrize("ddo_kernel", [PINNED], indirect=True, ids=["selected-source-proof"])


def selected(kernel, demand):
    with kernel["engine"].begin() as connection:
        page = read_demand_result(connection, demand["demand_id"], project_id="ddo-test")
    (header,) = page.members()
    return SelectedSourceSetEntry.from_selected_header(header, page.cut)


def register(kernel, source_set, *, inference="selected-source-control"):
    intent = freeze_demand(
        kernel["model"], roots=(RootSubject("focus:A", "source:A", b'{"focus":true}'),),
        targets=(CONSUMER,), source_sets=(source_set,), inference=inference,
        execution_profile="execution:test",
    )
    with kernel["engine"].begin() as connection:
        return DemandPlanner(kernel["model"], DataOperationStorage(connection)).register(
            intent, project="ddo-test", release=kernel["prepared"].release_id, runtime=kernel["runtime"]
        )


def test_native_selected_source_basis_preserves_two_producers_and_refuses_forged_selection(ddo_kernel):
    first_demand, first, first_product = _produce(ddo_kernel, subject="source-subject:B", value=42, inference="first-source-proof")
    second_demand, second, second_product = _produce(ddo_kernel, subject="source-subject:B", value=42, inference="second-source-proof")
    assert first_product == second_product
    assert first["derivation_id"] != second["derivation_id"]
    first_selection, second_selection = selected(ddo_kernel, first_demand), selected(ddo_kernel, second_demand)
    assert first_selection.entry == second_selection.entry
    assert first_selection.proof.output.member_id is None
    keys = []
    for source_selection in (first_selection, second_selection):
        demand = register(ddo_kernel, FrozenSourceSet.from_selected("selected", (source_selection,)))
        _, ready = _ready(ddo_kernel, demand)
        (answer,) = ready
        (member,) = answer.binding_result.roles[0].members
        assert member.support_references == (source_selection.proof.support,)
        assert member.producer_output == source_selection.proof.output
        keys.append(answer.request_key)
    assert keys[0] != keys[1]  # This role deliberately requires episode identity.
    later_cut = selected(ddo_kernel, first_demand)
    assert later_cut.read.cut_id != first_selection.read.cut_id
    _, (same,) = _ready(ddo_kernel, register(ddo_kernel, FrozenSourceSet.from_selected("selected", (later_cut,))))
    assert same.request_key == keys[0]

    # An explicitly unqualified value still sees both real episodes and cannot
    # become a scalar through a body-based or first-visible-proof collapse.
    _, broad = _ready(ddo_kernel, register(ddo_kernel, FrozenSourceSet.unqualified("selected", (first_selection.entry,)), inference="unqualified-proof-control"))
    assert broad == ()
    forged = (
        first_selection.proof.model_copy(update={"support": second_selection.proof.support}),
        first_selection.proof.model_copy(update={"anchor_use_id": second_selection.proof.anchor_use_id}),
        first_selection.proof.model_copy(update={"output": first_selection.proof.output.model_copy(update={"role": "foreign-output"})}),
        first_selection.proof.model_copy(update={"output": first_selection.proof.output.model_copy(update={"position": 1})}),
        first_selection.proof.model_copy(update={"output": first_selection.proof.output.model_copy(update={"multiplicity": 2})}),
    )
    for ordinal, proof in enumerate(forged):
        bad = replace(first_selection, proof=proof)
        with pytest.raises(DBAPIError, match="selected use/output support"):
            register(ddo_kernel, FrozenSourceSet.from_selected("selected", (bad,)), inference="forged-source-" + str(ordinal))

    # Attachment/publication rechecks current trust rather than retaining the
    # authority of a prior successfully acquired selector.
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).revoke_data_support(cast(WireRevokeDataSupportRequest, {
            "project_id": "ddo-test", "original_source": "source:B", "selector_kind": "episode",
            "selector": first["derivation_id"], "reason": "selected-proof-revocation-control",
        }))
    with pytest.raises(DBAPIError, match="trust|revoked|support"):
        register(ddo_kernel, FrozenSourceSet.from_selected("selected", (first_selection,)), inference="revoked-source-control")
    with ddo_kernel["engine"].connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 2
