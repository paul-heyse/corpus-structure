"""Current physical/native admission descriptors and exact enforcing guards."""

from dataclasses import dataclass

from sqlalchemy import MetaData

from .native_products import NativeAuthoringProvenance


@dataclass(frozen=True)
class PhysicalCatalogExpectations:
    indexes: tuple[dict[str, str], ...]
    generated: dict[str, dict[str, str]]
    defaults: dict[str, dict[str, str]]


def _admission_descriptor(admission):
    from .native_products import literal_json_descriptor

    return literal_json_descriptor(admission, "data.execution_contract_descriptor")


def recorded_authoring_provenance(admission: str) -> NativeAuthoringProvenance:
    """Read only the two authoring fields from an explicit immutable revision witness."""
    descriptor = _admission_descriptor(admission)
    model_id, inputs = descriptor["model_id"], descriptor["inputs"]
    if not isinstance(model_id, str) or not isinstance(inputs, list):
        raise ValueError("native authoring witness has malformed provenance")
    if any(
        not isinstance(item, dict)
        or set(item) != {"name", "sha256"}
        or not isinstance(item["name"], str)
        or not isinstance(item["sha256"], str)
        for item in inputs
    ):
        raise ValueError("native authoring witness has malformed input provenance")
    return NativeAuthoringProvenance(
        model_id, tuple((item["name"], item["sha256"]) for item in inputs)
    )


def catalog_checks(body: str) -> str:
    """Reuse the immutable guard's catalog checks without its release reads or writes."""
    boundaries = (
        (
            " IF NOT EXISTS(SELECT FROM sem.physical_contract ",
            " IF EXISTS(SELECT FROM sem.release archived CROSS JOIN LATERAL",
        ),
        (
            " SELECT item.value INTO spec FROM jsonb_array_elements(expected->'functions')",
            " IF NOT EXISTS(SELECT FROM sem.deployment_admission ",
        ),
    )
    checks = []
    for first, following in boundaries:
        if body.count(first) != 1 or body.count(following) != 1:
            raise ValueError("frozen native guard does not identify its catalog checks")
        start, end = body.index(first), body.index(following)
        if end <= start:
            raise ValueError("frozen native guard has invalid catalog check boundaries")
        checks.append(body[start:end])
    return "\n".join(checks)


def _normalized_function_checks(item, procedure, owner):
    """Generate normalized function and complete ACL correspondence expressions."""
    from sqlalchemy import Boolean, Text, and_, case, cast, func, literal, or_, select
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


def _normalized_function_sql():
    from sqlalchemy import Text
    from sqlalchemy.dialects.postgresql import JSONB

    from .native_catalog import procedure, render
    from .native_program import core_variable

    configuration, predicate = _normalized_function_checks(
        core_variable("item", JSONB(), "value"),
        procedure.alias("p"),
        core_variable("owner_name", Text()),
    )
    return render(configuration), render(predicate)


def _descriptor_sql(descriptor):
    from pglast import ast, enums
    from pglast.stream import RawStream
    from sqlalchemy import Text, cast, literal, select
    from sqlalchemy.dialects.postgresql import JSONB

    from .identity import canonical_bytes
    from .native_program import pg_type, sql_function

    role = ast.VariableSetStmt(
        kind=enums.VariableSetKind.VAR_SET_VALUE,
        name="role",
        is_local=True,
        args=(ast.A_Const(val=ast.String(sval="corpus_sem_publisher")),),
    )
    definition = sql_function(
        "data",
        "execution_contract_descriptor",
        parameters=(),
        returns=pg_type("jsonb"),
        body=select(cast(literal(canonical_bytes(descriptor).decode(), Text()), JSONB())),
        volatility="immutable",
        search_path=("pg_catalog", "pg_temp"),
    )
    return RawStream()(role) + ";\n" + definition + ";\n"


def native_admission_sql(
    sql,
    inputs,
    *,
    base_descriptor: dict,
    target_metadata: MetaData,
    native_objects=(),
    physical_catalog: PhysicalCatalogExpectations | None = None,
):
    from copy import deepcopy
    from hashlib import sha256

    from .native_products import admission_kernel, current_admission_fields

    descriptor = deepcopy(base_descriptor)
    if {item["relation"] for item in descriptor["tables"]} != set(target_metadata.tables):
        raise ValueError("native descriptor requires the exact current physical table declaration")
    descriptor.update(current_admission_fields(inputs, target_metadata=target_metadata))
    descriptor["views"].extend(
        dict(
            relation=native.identity.schema + "." + native.identity.name,
            query=native.catalog["query"],
        )
        for native in native_objects
        if native.identity.kind == "view"
    )
    descriptor["readers"].extend(
        dict(
            relation=native.identity.schema + "." + native.identity.name,
            roles=sorted(
                role
                for role, privilege, _ in native.catalog["acl"]
                if privilege == "SELECT" and role != native.catalog["owner"]
            ),
        )
        for native in native_objects
        if native.identity.kind == "view"
    )
    owned_relations = (
        set(target_metadata.tables)
        | {
            item.identity.schema + "." + item.identity.name
            for item in native_objects
            if item.identity.kind == "view"
        }
        | {item["relation"] for item in descriptor["views"]}
    )
    descriptor["readers"] = [
        item for item in descriptor["readers"] if item["relation"] in owned_relations
    ]
    owned_indexes = {
        (relation.schema + "." if relation.schema else "") + str(index.name)
        for relation in target_metadata.tables.values()
        for index in relation.indexes
    }
    descriptor["indexes"] = (
        list(physical_catalog.indexes)
        if physical_catalog is not None
        else [item for item in descriptor["indexes"] if item["index"] in owned_indexes]
    )
    descriptor["checks"] = [
        item for item in descriptor["checks"] if item["relation"] in target_metadata.tables
    ]
    from pglast import ast

    from .native_function_signatures import function_signature
    from .native_inventory import update_function_inventory
    from .prepared_sql import prepare_sql

    functions = {item["signature"]: item for item in descriptor["functions"]}
    update_function_inventory(functions, sql)
    required_signature = "data.require_execution_release(text)"
    for native in native_objects:
        if native.identity.kind != "function":
            continue
        signature = native.identity.qualified
        declared = [
            function_signature(raw.stmt)
            for statement in native.statements
            for raw in prepare_sql(statement, source=native.source).statements
            if isinstance(raw.stmt, ast.CreateFunctionStmt)
        ]
        if len(declared) != 1 or declared[0] not in functions:
            raise ValueError(
                f"normalized native function is absent from source inventory: {signature}"
            )
        source_signature = declared[0]
        if source_signature != signature:
            if signature in functions:
                raise ValueError(f"ambiguous canonical native identity: {signature}")
            functions[signature] = functions.pop(source_signature)
            functions[signature]["signature"] = signature
        catalog = native.catalog
        if native.catalog_version == 2:
            from .native_sql_body import SQL_STANDARD_PROFILE

            if catalog.get("body_profile") != SQL_STANDARD_PROFILE:
                raise ValueError("unsupported normalized SQL-standard native profile")
            functions[signature].update(
                body_kind=catalog["body_kind"],
                body_profile=catalog["body_profile"],
                server_major=catalog["server_major"],
                dependencies=catalog["dependencies"],
                body_sha256=sha256(catalog["body"].encode()).hexdigest(),
            )
        functions[signature].update(
            owner=catalog["owner"],
            # Managed objects declare their complete ACL. CREATE OR REPLACE
            # inventory alone retains predecessor grants that normalization
            # deliberately removed; both admission checks must describe the
            # same current privilege boundary.
            execute_roles=sorted(
                grantee
                for grantee, privilege, _ in catalog["acl"]
                if privilege == "EXECUTE" and grantee != catalog["owner"]
            ),
            result=catalog["result_type"],
            result_definition=catalog["result"],
            argument_definition=catalog["arguments"],
            catalog_acl=catalog["acl"],
            config=catalog["config"],
            argument_defaults=catalog["defaults"],
            cost=catalog["cost"],
            rows=catalog["rows"],
            support=catalog["support"],
        )
    descriptor["functions"] = sorted(functions.values(), key=lambda item: item["signature"])
    tables = {item["relation"]: item for item in descriptor["tables"]}
    from .native_products import relation_descriptor

    # Existing admitted relations evolve from the same current physical model as
    # explicitly added relations. Frozen predecessor columns are not current authority.
    tables = {
        name: relation_descriptor(target_metadata.tables[name])
        for name in tables
        if name in target_metadata.tables
    }
    # Removed stored relations cannot retain trigger or table admission authority.
    # Current views are separately owned NativeObjects, never stored-table metadata.
    descriptor["triggers"] = [
        trigger
        for trigger in descriptor["triggers"]
        if trigger["relation"] in target_metadata.tables
    ]
    # New append-only guards are declared managed objects, rather than inherited
    # accidentally from a live authoring catalog. Protect them at execution too.
    from pglast import ast, parse_sql

    for native in native_objects:
        if native.identity.kind != "trigger" or native.identity.name != "semantic_immutable":
            continue
        statement = parse_sql(native.catalog["definition"])[0].stmt
        if (
            not isinstance(statement, ast.CreateTrigStmt)
            or statement.row
            or statement.timing != 2
            or statement.events != 56
            or statement.args
            or statement.columns
            or statement.whenClause is not None
            or tuple(part.sval for part in statement.funcname or ())
            != ("sem", "refuse_immutable_mutation")
        ):
            raise ValueError("unsupported managed immutable guard shape")
        relation = native.identity.schema + "." + native.identity.relation
        tables[relation] = relation_descriptor(target_metadata.tables[relation])
        descriptor["triggers"] = [
            item
            for item in descriptor["triggers"]
            if (item["relation"], item["name"]) != (relation, native.identity.name)
        ]
        descriptor["triggers"].append(
            dict(
                relation=relation,
                name=native.identity.name,
                function="sem.refuse_immutable_mutation()",
                type=58,
                columns=[],
                when=None,
                args="",
                deferrable=False,
                deferred=False,
            )
        )
    descriptor["triggers"] = sorted(
        descriptor["triggers"], key=lambda item: (item["relation"], item["name"])
    )
    if physical_catalog is not None:
        for name, table in tables.items():
            generated = physical_catalog.generated.get(name, {})
            defaults = physical_catalog.defaults.get(name, {})
            for column in table["columns"]:
                if column["generated"]:
                    column["default"] = generated[column["name"]]
                elif column["default"] is not None:
                    column["default"] = defaults[column["name"]]
    descriptor["tables"] = sorted(tables.values(), key=lambda item: item["relation"])
    from .alembic_privileges import admission_comparison_sql, desired_policies

    descriptor["privileges"] = list(desired_policies(target_metadata, native_objects))
    for policy in descriptor["privileges"]:
        if policy["kind"] != "schema":
            continue
        roles = {row[0] for row in policy["acl"] if row[1] == "USAGE"}
        for function in functions.values():
            if function["signature"].split(".", 1)[0] == policy["name"]:
                roles.update(
                    role for role in function.get("execute_roles", ()) if role.startswith("corpus_")
                )
        for reader in descriptor.get("readers", ()):
            if reader["relation"].split(".", 1)[0] == policy["name"]:
                roles.update(reader["roles"])
        policy["acl"] = sorted(
            [(role, "USAGE", False) for role in roles] + [("corpus_sem_publisher", "CREATE", False)]
        )
    required = admission_kernel()
    policy_marker = " IF EXISTS(SELECT FROM pg_roles WHERE rolname='corpus_sem_evaluator'"
    if policy_marker not in required:
        raise ValueError("missing privilege admission insertion boundary")
    required = required.replace(policy_marker, admission_comparison_sql() + policy_marker, 1)
    from .native_sql_body import admission_body_comparison

    body_comparison = (
        "encode(sha256(convert_to(p.prosrc,'UTF8')),'hex') IS DISTINCT FROM "
        "item.value->>'body_sha256'"
    )
    if body_comparison not in required:
        raise ValueError("missing native body admission comparison boundary")
    required = required.replace(body_comparison, admission_body_comparison(), 1)
    if any("body_profile" in item and "dependencies" not in item for item in functions.values()):
        raise ValueError("SQL-standard admission requires a server-bound normalized native object")
    # The current descriptor additionally protects normalized TABLE/OUT result columns
    # and complete ACL/grant options for series-owned functions. Historical descriptors
    # lack these keys and retain their original admitted meaning.
    if native_objects:
        marker = " OR p.proretset IS DISTINCT FROM (item.value->>'setof')::boolean"
        if marker not in required:
            raise ValueError("missing function admission comparison boundary")
        configuration, predicate = _normalized_function_sql()
        required = required.replace(
            "COALESCE(to_jsonb(p.proconfig),'[]'::jsonb)",
            configuration,
            1,
        )
        required = required.replace(marker, marker + "\n OR (" + predicate + ")", 1)
    from .native_products import function_bodies

    # Admission protects its own exact enforcing body too. The descriptor literal
    # is a separate function, so this digest has no self-reference.
    functions[required_signature]["body_sha256"] = sha256(
        function_bodies(required)["data.require_execution_release"].encode()
    ).hexdigest()
    return _descriptor_sql(descriptor) + required
