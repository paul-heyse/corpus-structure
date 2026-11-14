"""Explicit JSON null context stays distinct from an unqualified SQL NULL bind."""

import json
from importlib.resources import files

import pytest
from sqlalchemy import JSON, bindparam, func, literal_column, select

from corpus_structure.semantic.data_operation_json import ContextJSONB, json_context_equal
from corpus_structure.semantic.data_operation_storage import _binding_scope_parameter
from semantic.data_operation_kernel_support import STORAGE


@pytest.mark.db
def test_context_bind_and_comparison_distinguish_json_null_from_sql_null(semantic_bare_engine):
    json_null = literal_column("'null'::jsonb", ContextJSONB())
    sql_null = literal_column("NULL::jsonb", ContextJSONB())
    query = select(
        func.jsonb_typeof(bindparam("explicit", JSON.NULL, type_=ContextJSONB())),
        bindparam("unqualified", None, type_=ContextJSONB()).is_(None),
        json_context_equal(json_null, None),
        json_context_equal(sql_null, None),
        json_null.is_(None),
        sql_null.is_(None),
    )
    with semantic_bare_engine.connect() as connection:
        assert tuple(connection.execute(query).one()) == ("null", True, True, None, False, True)


@pytest.mark.db
@pytest.mark.parametrize("qualified", [False, True])
def test_native_original_scope_predicate_selects_only_the_explicit_json_null_root(
    semantic_bare_engine,
    qualified,
):
    source = files("corpus_structure.semantic").joinpath("sql/data_operations.sql").read_text()
    assert "admission.analyzed_scope IS NOT DISTINCT FROM p_scope" in source
    # Exact native original-source branch predicate, with the production projection
    # parameter binder. These VALUES test context selection, not original admission.
    admission = select(
        literal_column("'null'::jsonb", ContextJSONB()).label("analyzed_scope")
    ).subquery("admission")
    parameter = _binding_scope_parameter(None) if qualified else _binding_scope_parameter()
    query = select(
        admission.c.analyzed_scope.is_not_distinct_from(parameter), func.jsonb_typeof(parameter)
    )
    with semantic_bare_engine.connect() as connection:
        assert tuple(connection.execute(query).one()) == (
            (True, "null") if qualified else (False, None)
        )


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.db
def test_native_demand_retains_json_null_scope_through_product_binding(ddo_kernel):
    from corpus_structure.semantic.data_operation_demands import (
        DemandPlanner,
        RootSubject,
        freeze_demand,
    )
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from semantic.data_operation_demand_support import claim, publish, retain

    intent = freeze_demand(
        ddo_kernel["model"],
        roots=(RootSubject("null:subject", "source:test", b"null"),),
        targets=("urn:ddo-test:sample", "urn:ddo-test:consumer"),
        inference="inference:test",
        execution_profile="execution:test",
    )
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        demand = planner.register(
            intent,
            project="ddo-test",
            release=ddo_kernel["prepared"].release_id,
            runtime=ddo_kernel["runtime"],
        )["demand_id"]
        ready = planner.ready(planner.resume(demand), authorization=b"{}")
        assert len(ready) == 1 and ready[0].operation == "urn:ddo-test:sample"
    sample = ddo_kernel["model"].operation("urn:ddo-test:sample")
    sample_kernel = {**ddo_kernel, "kind": ddo_kernel["identities"][sample.roles[0].kind, "kind"]}
    fence = claim(sample_kernel, json.loads(ready[0].native))
    publish(sample_kernel, fence, retain(sample_kernel, fence, outputs=({"value": 12},)))
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        ready = planner.ready(planner.resume(demand), authorization=b"{}")
        assert len(ready) == 1 and ready[0].operation == "urn:ddo-test:consumer"
        assert ready[0].resolved.subject_context.analyzed_scope == b"null"
        assert ready[0].binding_result.roles[0].members[0].analyzed_scope == b"null"
