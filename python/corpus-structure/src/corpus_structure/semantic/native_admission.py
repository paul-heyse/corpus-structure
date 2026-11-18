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
    from .native_admission_release import (
        CATALOG_END,
        CATALOG_START,
        PHYSICAL_CATALOG_END,
        PHYSICAL_CATALOG_START,
    )

    marker = " -- " + CATALOG_START
    if marker in body:
        boundaries = ((marker, CATALOG_END),)
    else:
        receipt_boundary = (
            CATALOG_END
            if CATALOG_END in body
            else " IF NOT EXISTS(SELECT FROM sem.deployment_admission "
        )
        boundaries = (
            (
                PHYSICAL_CATALOG_START
                if PHYSICAL_CATALOG_START in body
                else " IF NOT EXISTS(SELECT FROM sem.physical_contract ",
                PHYSICAL_CATALOG_END
                if PHYSICAL_CATALOG_END in body
                else " IF EXISTS(SELECT FROM sem.release archived CROSS JOIN LATERAL",
            ),
            (
                " SELECT item.value INTO spec FROM jsonb_array_elements(expected->'functions')",
                receipt_boundary,
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
    from .alembic_privileges import desired_policies

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
    required = admission_kernel(target_metadata=target_metadata)
    if any("body_profile" in item and "dependencies" not in item for item in functions.values()):
        raise ValueError("SQL-standard admission requires a server-bound normalized native object")
    from .native_products import function_bodies

    # Admission protects its own exact enforcing body too. The descriptor literal
    # is a separate function, so this digest has no self-reference.
    functions[required_signature]["body_sha256"] = sha256(
        function_bodies(required)["data.require_execution_release"].encode()
    ).hexdigest()
    return _descriptor_sql(descriptor) + required
