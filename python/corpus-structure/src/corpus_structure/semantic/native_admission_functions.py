"""Native function catalog correspondence for captured release admission."""

from sqlalchemy import Boolean, Text, and_, case, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, OID

from .alembic_privileges import DEFAULT_READ_ROLES
from .native_catalog import language, pg, procedure
from .native_program import core_variable
from .native_sql_body import admission_body_comparison


def _normalized_function_checks(item, procedure, owner):
    """Generate normalized function and complete ACL correspondence expressions."""
    from sqlalchemy import Boolean, Text, case, cast, func, or_, select
    from sqlalchemy.dialects.postgresql import JSONB, REAL, aggregate_order_by

    from .native_catalog import _CatalogType, acl_rows

    p = procedure.c
    empty = cast(literal("[]", Text()), JSONB())
    config = func.unnest(p.proconfig).table_valued("value").render_derived("configuration")
    sorted_config = (
        select(
            func.coalesce(func.jsonb_agg(aggregate_order_by(config.c.value, config.c.value)), empty)
        )
        .select_from(config)
        .correlate(procedure)
        .scalar_subquery()
    )
    configuration = case(
        (item.bool_op("?")("result_definition"), sorted_config),
        else_=func.coalesce(func.to_jsonb(p.proconfig), empty),
    )
    rows = (
        acl_rows(p.proacl, literal("f"), p.proowner).correlate(procedure).subquery("observed_acl")
    )
    observed_acl = (
        select(
            func.coalesce(
                func.jsonb_agg(aggregate_order_by(func.jsonb_build_array(*rows.c), *rows.c)), empty
            )
        )
        .select_from(rows)
        .correlate(procedure)
        .scalar_subquery()
    )
    entries = (
        func.jsonb_array_elements(item["catalog_acl"]).table_valued("value").render_derived("entry")
    )
    entry = cast(entries.c.value, JSONB())
    grantee = case(
        (entry[0].astext == "$migration_owner", cast(owner, Text())), else_=entry[0].astext
    )
    privilege = entry[1].astext
    bound_acl = (
        select(
            grantee.label("grantee"),
            privilege.label("privilege"),
            func.bool_or(cast(entry[2].astext, Boolean())).label("grantable"),
        )
        .select_from(entries)
        .group_by(grantee, privilege)
        .subquery("bound_acl")
    )
    expected_acl = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(func.jsonb_build_array(*bound_acl.c), *bound_acl.c)
                ),
                empty,
            )
        )
        .select_from(bound_acl)
        .scalar_subquery()
    )
    checks = (
        ("result_definition", func.pg_get_function_result(p.oid)),
        ("argument_definition", func.pg_get_function_arguments(p.oid)),
        ("argument_defaults", func.pg_get_expr(p.proargdefaults, 0)),
        ("support", cast(cast(p.prosupport, _CatalogType("regproc")), Text())),
    )
    return configuration, or_(
        *(
            and_(item.bool_op("?")(name), observed.is_distinct_from(item[name].astext))
            for name, observed in checks
        ),
        *(
            and_(
                item.bool_op("?")(name), observed.is_distinct_from(cast(item[name].astext, REAL()))
            )
            for name, observed in (("cost", p.procost), ("rows", p.prorows))
        ),
        and_(item.bool_op("?")("catalog_acl"), observed_acl.is_distinct_from(expected_acl)),
    )


def function_catalog_checks():
    from .native_admission_release import _catalog_failure, _diagnostic, _json_items

    expected = core_variable("expected", JSONB())
    owner = core_variable("owner_name", Text())
    items = _json_items(expected["functions"], "item")
    item = items.c.value
    observed = procedure.alias("p")
    columns = observed.c
    lang = language.alias("l")
    acl = (
        pg.aclexplode(func.coalesce(columns.proacl, pg.acldefault("f", columns.proowner)))
        .table_valued(column("grantee", OID()), column("privilege_type", Text()))
        .alias("acl")
    )
    configuration, normalized = _normalized_function_checks(item, observed, owner)
    signature = item["signature"].astext
    relation = items.outerjoin(observed, columns.oid == pg.to_regprocedure(signature)).outerjoin(
        lang, lang.c.oid == columns.prolang
    )
    return _catalog_failure(
        select(item)
        .select_from(relation)
        .where(
            or_(
                columns.oid.is_(None),
                admission_body_comparison(item, observed),
                *(
                    columns[column].is_distinct_from(cast(item[field].astext, Boolean()))
                    for column, field in (
                        ("prosecdef", "security"),
                        ("proisstrict", "strict"),
                        ("proleakproof", "leakproof"),
                        ("proretset", "setof"),
                    )
                ),
                cast(columns.provolatile, Text()).is_distinct_from(item["volatility"].astext),
                cast(columns.proparallel, Text()).is_distinct_from(item["parallel"].astext),
                lang.c.lanname.is_distinct_from(item["language"].astext),
                columns.prorettype.is_distinct_from(pg.to_regtype(item["result"].astext)),
                configuration.is_distinct_from(item["config"]),
                pg.pg_get_userbyid(columns.proowner).is_distinct_from(
                    case(
                        (item["owner"].astext == "$migration_owner", owner),
                        else_=item["owner"].astext,
                    )
                ),
                *(
                    pg.has_function_privilege(role, columns.oid, "EXECUTE").is_distinct_from(
                        item["execute_roles"].has_key(role)
                    )
                    for role in DEFAULT_READ_ROLES
                ),
                select(1)
                .select_from(acl)
                .where(acl.c.grantee == 0, acl.c.privilege_type == "EXECUTE")
                .correlate(observed)
                .exists(),
                normalized,
            )
        )
        .order_by(signature),
        _diagnostic("native execution kernel differs: %s", "signature"),
    )
