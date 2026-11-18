"""Independent PostgreSQL controls for read boundaries; dependencies are explicit controls."""

import json
from datetime import timedelta

import pytest
from pglast import ast
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.data_read_boundary_native import read_boundary_native_sql
from corpus_structure.semantic.metadata import metadata, table
from corpus_structure.semantic.prepared_sql import prepare_sql


@pytest.fixture
def read_boundary_control(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA ops")
    for name in (
        "data_demand",
        "data_demand_read",
        "data_demand_read_scope",
        "data_trust_scope",
        "original_source_admission",
        "data_revocation",
    ):
        connection.execute(CreateTable(table("ops." + name), include_foreign_key_constraints=[]))
    # These controls isolate boundary admission, rather than qualify universe
    # authorization, scope hashing, or the census domain providers themselves.
    connection.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_scope(project text,source text) RETURNS text LANGUAGE sql IMMUTABLE AS $$SELECT project||':'||coalesce(source,'<project>')$$"
    )
    connection.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_authorize(universe text) RETURNS void LANGUAGE plpgsql AS $$BEGIN IF universe='forbidden' THEN RAISE EXCEPTION 'universe refused' USING ERRCODE='42501'; END IF; END$$"
    )
    for name in ("ddo_record_grade_require_finite_census", "ddo_record_fit_require_finite_cut"):
        connection.exec_driver_sql(
            "CREATE FUNCTION ops."
            + name
            + "(d ops.data_demand,boundary ops.data_demand_read) RETURNS void LANGUAGE plpgsql STABLE AS $$BEGIN IF d.id='infinite' THEN RAISE EXCEPTION 'not finite' USING ERRCODE='23514'; ELSIF d.id='forbidden' THEN RAISE EXCEPTION 'census refused' USING ERRCODE='42501'; END IF; END$$"
        )
    prepared = prepare_sql(
        read_boundary_native_sql(metadata).replace("__DDO_SOURCE_DIGEST__", "kernel:control"),
        source="read-boundary-control",
    )
    for index, _ in enumerate(prepared.statements):
        connection.exec_driver_sql(
            prepared.excerpt(index), execution_options={"no_parameters": True}
        )
    now, snapshot, xid = connection.execute(
        text("SELECT clock_timestamp(),pg_current_snapshot()::text,pg_current_xact_id()::text")
    ).one()
    boundary = dict(
        id="read:one",
        demand_id="demand:one",
        frontier_at=now.isoformat(),
        read_snapshot=snapshot,
        owner_xid=xid,
        kernel_digest="kernel:control",
        access_universes=["accepted"],
        public_disclosure=False,
        grade_census_eligible=False,
        fit_census_eligible=True,
    )
    connection.execute(
        table("ops.data_demand_read_scope").insert(),
        [
            dict(read_id="read:one", scope="a", epoch=2, ordinary=True, domain=False),
            dict(read_id="read:one", scope="b", epoch=3, ordinary=False, domain=True),
        ],
    )
    connection.execute(
        table("ops.data_trust_scope").insert(),
        [
            dict(scope="a", project_id="project", epoch=2),
            dict(scope="b", project_id="project", epoch=3),
        ],
    )
    yield connection, boundary, now, xid


def _call(connection, name, boundary, *, project="project", ordinary=None):
    args = "jsonb_populate_record(NULL::ops.data_demand_read,CAST(:boundary AS jsonb))"
    params = dict(boundary=json.dumps(boundary), project=project, ordinary=ordinary)
    if name in {"ddo_require_read_epochs", "ddo_require_read_current"}:
        args += ",:project"
        if ordinary is not None:
            args += ",:ordinary"
    return connection.scalar(text("SELECT ops." + name + "(" + args + ")"), params)


def test_read_acquisition_requires_current_complete_facts_and_retained_scope(read_boundary_control):
    connection, boundary, _, _ = read_boundary_control
    assert _call(connection, "ddo_read_acquisition_present", boundary) is True
    for field, bad_value in (
        ("id", None),
        ("kernel_digest", "old"),
        ("access_universes", None),
        ("public_disclosure", None),
        ("grade_census_eligible", None),
        ("fit_census_eligible", None),
    ):
        altered = {**boundary, field: bad_value}
        assert _call(connection, "ddo_read_acquisition_present", altered) is False
    connection.execute(table("ops.data_demand_read_scope").delete())
    assert _call(connection, "ddo_read_acquisition_present", boundary) is False
    with (
        pytest.raises(DBAPIError, match="reacquisition under current native kernel"),
        connection.begin_nested(),
    ):
        _call(connection, "ddo_require_read_epochs", boundary)


def test_read_epoch_default_ordinary_filter_project_and_epoch_fences(read_boundary_control):
    connection, boundary, _, _ = read_boundary_control
    assert _call(connection, "ddo_require_read_epochs", boundary) == {"a": 2, "b": 3}
    assert _call(connection, "ddo_require_read_epochs", boundary, ordinary=True) == {"a": 2}
    connection.execute(
        table("ops.data_trust_scope")
        .update()
        .where(table("ops.data_trust_scope").c.scope == "b")
        .values(epoch=4)
    )
    assert _call(connection, "ddo_require_read_epochs", boundary, ordinary=True) == {"a": 2}
    with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
        _call(connection, "ddo_require_read_epochs", boundary)
    assert getattr(refusal.value.orig, "sqlstate", None) == "23514"
    assert "read trust changed" in str(refusal.value)
    with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
        _call(connection, "ddo_require_read_epochs", boundary, project="other")
    assert getattr(refusal.value.orig, "sqlstate", None) == "P0002"


def test_read_current_reauthorizes_each_use_and_checks_epochs_first(read_boundary_control):
    connection, boundary, _, _ = read_boundary_control
    assert _call(connection, "ddo_require_read_current", boundary) == {"a": 2, "b": 3}
    boundary["access_universes"] = ["accepted", "forbidden"]
    # Authenticated internal custody/currentness does not disclose the protected
    # data. Presentation still requires live caller authority for every universe.
    assert _call(connection, "ddo_require_read_epochs", boundary) == {"a": 2, "b": 3}
    with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
        _call(connection, "ddo_require_read_current", boundary)
    assert getattr(refusal.value.orig, "sqlstate", None) == "42501"
    connection.execute(table("ops.data_trust_scope").update().values(epoch=9))
    with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
        _call(connection, "ddo_require_read_current", boundary)
    assert getattr(refusal.value.orig, "sqlstate", None) == "23514"


@pytest.mark.parametrize("census", ["grade", "fit"])
def test_census_translates_only_check_violation(read_boundary_control, census):
    connection, boundary, _, _ = read_boundary_control
    query = text(
        "SELECT ops.ddo_read_census_eligible(jsonb_populate_record(NULL::ops.data_demand,CAST(:demand AS jsonb)),jsonb_populate_record(NULL::ops.data_demand_read,CAST(:boundary AS jsonb)),:census)"
    )
    params = dict(boundary=json.dumps(boundary), census=census)
    for identity, expected in (("finite", True), ("infinite", False)):
        assert (
            connection.scalar(query, {**params, "demand": json.dumps(dict(id=identity))})
            is expected
        )
    for identity, selected_census, state in (
        ("forbidden", census, "42501"),
        ("finite", "unknown", "P0001"),
    ):
        with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
            connection.execute(
                query,
                {**params, "demand": json.dumps(dict(id=identity)), "census": selected_census},
            )
        assert getattr(refusal.value.orig, "sqlstate", None) == state


def test_visibility_and_original_admission_revocation_selectors(read_boundary_control):
    connection, boundary, now, xid = read_boundary_control
    visible = text(
        "SELECT ops.ddo_read_visible(:created_at,:xid,jsonb_populate_record(NULL::ops.data_demand_read,CAST(:boundary AS jsonb)))"
    )
    assert (
        connection.scalar(visible, dict(created_at=now, xid=xid, boundary=json.dumps(boundary)))
        is True
    )
    assert (
        connection.scalar(
            visible,
            dict(created_at=now + timedelta(seconds=1), xid=xid, boundary=json.dumps(boundary)),
        )
        is False
    )
    assert (
        connection.scalar(visible, dict(created_at=None, xid=xid, boundary=json.dumps(boundary)))
        is None
    )
    other_owner = {**boundary, "owner_xid": "other"}
    # The current transaction can be visible to its own snapshot independently of owner_xid.
    # An xid beyond xmax independently establishes the invisible, non-owner branch.
    unseen_xid = str(int(boundary["read_snapshot"].split(":")[1]) + 100)
    assert (
        connection.scalar(
            visible, dict(created_at=now, xid=unseen_xid, boundary=json.dumps(other_owner))
        )
        is False
    )
    assert (
        connection.scalar(visible, dict(created_at=now, xid="3", boundary=json.dumps(other_owner)))
        is True
    )
    admission = dict(
        id="admission:one",
        project_id="project",
        original_source="source",
        product_id="product:one",
        source_reference="source:one",
        created_at=now.isoformat(),
        created_xid=xid,
    )
    arguments = (
        "jsonb_populate_record(NULL::ops.original_source_admission,CAST(:admission AS jsonb))"
    )
    query = text(
        "SELECT ops.ddo_original_admission_valid("
        + arguments
        + ",jsonb_populate_record(NULL::ops.data_demand_read,CAST(:boundary AS jsonb)))"
    )
    default_query = text("SELECT ops.ddo_original_admission_valid(" + arguments + ")")
    params = dict(admission=json.dumps(admission), boundary=json.dumps(boundary))
    assert connection.scalar(default_query, params) is True
    assert connection.scalar(query, params) is True
    future = dict(admission, created_at=(now + timedelta(seconds=1)).isoformat())
    assert connection.scalar(query, {**params, "admission": json.dumps(future)}) is False
    assert connection.scalar(default_query, {**params, "admission": json.dumps(future)}) is True
    for selector, identity in (
        ("original-admission", "admission:one"),
        ("original-source", "source:one"),
        ("product", "product:one"),
    ):
        with connection.begin_nested() as transaction:
            revocations = table("ops.data_revocation")
            connection.execute(
                revocations.insert(),
                dict(
                    id="revocation:one",
                    scope="other:source",
                    epoch=1,
                    selector_kind=selector,
                    selector=identity,
                    reason="control",
                    created_at=now,
                ),
            )
            assert connection.scalar(query, params) is True
            connection.execute(revocations.update().values(scope="project:source"))
            assert connection.scalar(query, params) is False
            transaction.rollback()


def test_program_boundary_declarations_keep_defaults_security_and_order():
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql

    sources = native_protocol_sources()
    source_map = {item.name: item.content for item in sources}
    assert {"native/data-read-boundary.sql", "native/data-read-boundary.py"} <= source_map.keys()
    sql = native_sql(sources)
    assert "__DDO_READ_BOUNDARY_PROGRAMS__" not in sql
    assert sql.index("FUNCTION ops.ddo_read_acquisition_present(") < sql.index(
        "FUNCTION ops.ddo_validity_edges("
    )
    prepared = prepare_sql(read_boundary_native_sql(metadata), source="read-boundary-declarations")
    functions = {
        raw.stmt.funcname[-1].sval: raw.stmt
        for raw in prepared.statements
        if isinstance(raw.stmt, ast.CreateFunctionStmt) and raw.stmt.funcname
    }
    assert len(functions) == 6
    for name, statement in functions.items():
        options = {item.defname: item.arg for item in statement.options or ()}
        assert bool(options.get("security")) is (name != "ddo_read_visible")
        if name in {
            "ddo_require_read_current",
            "ddo_require_read_epochs",
            "ddo_original_admission_valid",
        }:
            assert statement.parameters and statement.parameters[-1].defexpr is not None
