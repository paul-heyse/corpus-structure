"""Compile read acquisition, trust epochs, visibility, and source admission."""

from pglast import ast, enums
from sqlalchemy import Boolean, Text, and_, cast, column, exists, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, array

from .native_program import (
    Assign,
    Block,
    CatchCheckViolation,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    PerformQuery,
    Raise,
    Return,
    SelectInto,
    call,
    column_type,
    core_variable,
    function,
    pg_type,
    sql_function,
    variable,
)
from .native_program import literal as pg_literal


def read_boundary_native_sql(target) -> str:
    reads = target.tables["ops.data_demand_read"]
    retained = target.tables["ops.data_demand_read_scope"]
    trust = target.tables["ops.data_trust_scope"]
    admissions = target.tables["ops.original_source_admission"]
    revocations = target.tables["ops.data_revocation"]
    boundary = core_variable("boundary", Text())
    project = core_variable("project", Text())
    ordinary_only = core_variable("ordinary_only", Boolean())
    snapshot = core_variable("snapshot", JSONB())
    epoch = core_variable("epoch", trust.c.epoch.type)
    census = core_variable("census", Text())

    def read_field(name):
        return core_variable("boundary", reads.c[name].type, name)

    def retained_field(name):
        return core_variable("retained", retained.c[name].type, name)

    def admission_field(name):
        return core_variable("admission", admissions.c[name].type, name)

    def sql(name, parameters, body, *, strict=False, definer=True):
        return sql_function(
            "ops",
            name,
            parameters=parameters,
            returns=pg_type("bool"),
            body=body,
            volatility="stable",
            strict=strict,
            security_definer=definer,
            search_path=("pg_catalog", "pg_temp"),
        )

    def procedure(name, parameters, body, *, returns="jsonb", volatility=None):
        return function(
            "ops",
            name,
            parameters=parameters,
            returns=pg_type(returns),
            body=body,
            volatility=volatility,
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
        )

    boundary_parameter = Parameter("boundary", pg_type("ops", "data_demand_read"))
    guarded_parameters = (
        boundary_parameter,
        Parameter("project", pg_type("text")),
        Parameter("ordinary_only", pg_type("bool"), pg_literal(False)),
    )
    present = sql(
        "ddo_read_acquisition_present",
        (boundary_parameter,),
        select(
            and_(
                read_field("id").is_not(None),
                read_field("kernel_digest") == "__DDO_SOURCE_DIGEST__",
                *(
                    read_field(name).is_not(None)
                    for name in ("access_universes", "grade_census_eligible", "fit_census_eligible")
                ),
                exists(
                    select(1).select_from(retained).where(retained.c.read_id == read_field("id"))
                ),
            )
        ),
    )
    epochs = procedure(
        "ddo_require_read_epochs",
        guarded_parameters,
        Block(
            (
                If(
                    ~func.coalesce(
                        func.ops.ddo_read_acquisition_present(boundary, type_=Boolean()), False
                    ),
                    (Raise("read requires reacquisition under current native kernel", "23514"),),
                ),
                ForQuery(
                    ("retained",),
                    select(retained)
                    .where(
                        retained.c.read_id == read_field("id"), ~ordinary_only | retained.c.ordinary
                    )
                    .order_by(retained.c.scope),
                    (
                        SelectInto(
                            select(trust.c.epoch)
                            .where(
                                trust.c.scope == retained_field("scope"),
                                trust.c.project_id == project,
                            )
                            .with_for_update(read=True),
                            ("epoch",),
                            strict=True,
                        ),
                        If(
                            epoch != retained_field("epoch"),
                            (Raise("read trust changed; reacquire demand read", "23514"),),
                        ),
                        Assign(
                            "snapshot",
                            snapshot.concat(
                                func.jsonb_build_object(retained_field("scope"), epoch)
                            ),
                        ),
                    ),
                ),
                Return(snapshot),
            ),
            (
                Local("retained", retained),
                Local("epoch", column_type(trust.c.epoch)),
                Local("snapshot", pg_type("jsonb"), cast(literal("{}"), JSONB())),
            ),
        ),
    )
    universes = (
        func.jsonb_array_elements(read_field("access_universes"))
        .table_valued(column("value", JSONB()))
        .render_derived(name="access_universe")
    )
    current = procedure(
        "ddo_require_read_current",
        guarded_parameters,
        Block(
            (
                Assign(
                    "snapshot", func.ops.ddo_require_read_epochs(boundary, project, ordinary_only)
                ),
                PerformQuery(
                    select(
                        func.ops.ddo_authorize(
                            universes.c.value.op("#>>", return_type=Text())(array([], type_=Text()))
                        )
                    )
                ),
                Return(snapshot),
            ),
            (Local("snapshot", pg_type("jsonb")),),
        ),
    )
    eligible = procedure(
        "ddo_read_census_eligible",
        (
            Parameter("d", pg_type("ops", "data_demand")),
            boundary_parameter,
            Parameter("census", pg_type("text")),
        ),
        Block(
            (
                CatchCheckViolation(
                    (
                        If(
                            census == "grade",
                            (
                                Perform(
                                    func.ops.ddo_record_grade_require_finite_census(
                                        core_variable("d", Text()), boundary
                                    )
                                ),
                            ),
                            (
                                If(
                                    census == "fit",
                                    (
                                        Perform(
                                            func.ops.ddo_record_fit_require_finite_cut(
                                                core_variable("d", Text()), boundary
                                            )
                                        ),
                                    ),
                                    (Raise("unknown census property", "P0001"),),
                                ),
                            ),
                        ),
                        Return(pg_literal(True)),
                    ),
                    (Return(pg_literal(False)),),
                ),
            )
        ),
        returns="bool",
        volatility="stable",
    )

    def op(symbol, left, right):
        return ast.A_Expr(
            kind=enums.A_Expr_Kind.AEXPR_OP,
            name=(ast.String(sval=symbol),),
            lexpr=left,
            rexpr=right,
        )

    visible_expression = ast.BoolExpr(
        boolop=enums.BoolExprType.AND_EXPR,
        args=(
            op("<=", variable("created_at"), variable("boundary", "frontier_at")),
            ast.BoolExpr(
                boolop=enums.BoolExprType.OR_EXPR,
                args=(
                    op("=", variable("created_xid"), variable("boundary", "owner_xid")),
                    call(
                        "pg_catalog",
                        "pg_visible_in_snapshot",
                        ast.TypeCast(
                            arg=variable("created_xid"), typeName=pg_type("pg_catalog", "xid8")
                        ),
                        ast.TypeCast(
                            arg=variable("boundary", "read_snapshot"),
                            typeName=pg_type("pg_catalog", "pg_snapshot"),
                        ),
                    ),
                ),
            ),
        ),
    )
    visible = sql(
        "ddo_read_visible",
        (
            Parameter("created_at", column_type(reads.c.frontier_at)),
            Parameter("created_xid", column_type(reads.c.owner_xid)),
            boundary_parameter,
        ),
        ast.SelectStmt(targetList=(ast.ResTarget(val=visible_expression),)),
        strict=True,
        definer=False,
    )
    revoked = exists(
        select(1)
        .select_from(revocations)
        .where(
            revocations.c.scope
            == func.ops.ddo_scope(
                admission_field("project_id"), admission_field("original_source")
            ),
            or_(
                *(
                    and_(
                        revocations.c.selector_kind == selector,
                        revocations.c.selector == admission_field(field),
                    )
                    for selector, field in (
                        ("original-admission", "id"),
                        ("original-source", "source_reference"),
                        ("product", "product_id"),
                    )
                )
            ),
        )
    )
    valid = sql(
        "ddo_original_admission_valid",
        (
            Parameter("admission", pg_type("ops", "original_source_admission")),
            Parameter("boundary", pg_type("ops", "data_demand_read"), pg_literal(None)),
        ),
        select(
            and_(
                admission_field("id").is_not(None),
                or_(
                    read_field("id").is_(None),
                    func.ops.ddo_read_visible(
                        admission_field("created_at"),
                        admission_field("created_xid"),
                        boundary,
                        type_=Boolean(),
                    ),
                ),
                ~revoked,
            )
        ),
    )
    return ";\n".join((present, epochs, current, eligible, visible, valid)) + ";\n"
