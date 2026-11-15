"""Native effect reads require a current scoped selection and producing episode."""

from typing import cast

import pytest
from psycopg.errors import CheckViolation, InsufficientPrivilege
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.demand_results import read_demand_result
from semantic.declared_scenarios import declared_serving_case as declared_serving_case
from semantic.declared_scenarios import declared_serving_seed as declared_serving_seed

_PROOF = text("SELECT ops.ddo_require_selected_output(:demand,:read,:use,:product,:derivation)")


def _selected(clone, *, scope=None):
    stage = clone.stage.agent
    with clone.reader.begin() as connection:
        page = read_demand_result(
            connection,
            stage.demand_id,
            project_id=stage.project_id,
            scope=scope,
        )
    uses = [use for use in page.record["uses"] if use["fate"] == "fulfilled" and use["products"]]
    if not uses:
        return page, None
    use = uses[0]
    return page, dict(
        demand=stage.demand_id,
        read=page.cut.record["read_id"],
        use=use["use_id"],
        product=use["products"][0]["product_id"],
        derivation=use["derivation_id"],
    )


def test_current_whole_output_is_proved_but_private_helper_has_no_reader_grant(
    declared_serving_case,
):
    clone = declared_serving_case
    _, selected = _selected(clone)
    assert selected is not None
    with clone.admin.begin() as connection:
        connection.execute(_PROOF, selected)
    with pytest.raises(DBAPIError) as refusal, clone.reader.begin() as connection:
        connection.execute(_PROOF, selected)
    assert isinstance(refusal.value.orig, InsufficientPrivilege)
    assert refusal.value.orig.sqlstate == "42501"


@pytest.mark.parametrize("field", ["use", "product", "derivation"])
def test_invented_selection_or_producing_identity_cannot_open_an_effect(
    declared_serving_case, field
):
    clone = declared_serving_case
    _, selected = _selected(clone)
    assert selected is not None
    with pytest.raises(DBAPIError) as refusal, clone.admin.begin() as connection:
        connection.execute(_PROOF, {**selected, field: "invented:" + field})
    assert isinstance(refusal.value.orig, CheckViolation)
    assert refusal.value.orig.sqlstate == "23514"


def test_existing_product_is_not_available_through_an_unrelated_read_scope(declared_serving_case):
    clone = declared_serving_case
    _, selected = _selected(clone)
    narrowed, empty = _selected(clone, scope={"subject": "not-examined-by-this-cut"})
    assert selected is not None and empty is None
    with pytest.raises(DBAPIError) as refusal, clone.admin.begin() as connection:
        connection.execute(_PROOF, {**selected, "read": narrowed.cut.record["read_id"]})
    assert isinstance(refusal.value.orig, CheckViolation)
    assert refusal.value.orig.sqlstate == "23514"


def test_prior_selected_receipt_does_not_bypass_current_revocation(declared_serving_case):
    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    _, selected = _selected(clone)
    assert selected is not None
    with clone.writer.begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                dict(
                    project_id=stage.project_id,
                    original_source=stage.original_source,
                    selector_kind="derivation",
                    selector=selected["derivation"],
                    reason="independently revoked selected effect episode",
                ),
            )
        )
    with pytest.raises(DBAPIError), clone.admin.begin() as connection:
        connection.execute(_PROOF, selected)
