"""Frozen forward realization of native section views and their actual consumers."""

from .metadata import metadata
from .native_products import NativeAuthoringProvenance


def _admission_descriptor(admission):
    import json

    from pglast import ast, parse_sql

    from .native_products import function_bodies

    descriptor_body = function_bodies(admission)["data.execution_contract_descriptor"]
    statement = parse_sql(descriptor_body)[0].stmt
    if not isinstance(statement, ast.SelectStmt) or not statement.targetList:
        raise ValueError("descriptor must be literal SELECT")
    cast = statement.targetList[0].val
    if (
        not isinstance(cast, ast.TypeCast)
        or not isinstance(cast.arg, ast.A_Const)
        or not isinstance(cast.arg.val, ast.String)
    ):
        raise ValueError("descriptor must be JSONB string")
    literal = cast.arg.val.sval
    if literal is None:
        raise ValueError("descriptor string is absent")
    return json.loads(literal)


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


def native_admission_sql(
    sql,
    model=None,
    *,
    extra_relations=(),
    base_admission=None,
    authoring_provenance: NativeAuthoringProvenance | None = None,
    native_objects=(),
    retire=(),
):
    from hashlib import sha256

    from .identity import canonical_bytes
    from .native_products import admission_kernel, current_admission_fields

    if base_admission is None:
        raise ValueError("native admission requires an explicit frozen predecessor")
    descriptor = _admission_descriptor(base_admission)
    descriptor.update(current_admission_fields(model))
    descriptor.pop("base_derived_protocol", None)
    descriptor.pop("parsing_relationship_profiles", None)
    owned_relations = (
        set(metadata.tables)
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
        for relation in metadata.tables.values()
        for index in relation.indexes
    }
    descriptor["indexes"] = [
        item for item in descriptor["indexes"] if item["index"] in owned_indexes
    ]
    descriptor["checks"] = [
        item for item in descriptor["checks"] if item["relation"] in metadata.tables
    ]
    if authoring_provenance is not None:
        # This explicit authoring witness affects no enforcement field. In
        # particular, do not inherit predecessor provenance as head provenance.
        descriptor.update(authoring_provenance.descriptor_fields())
    from .native_inventory import update_function_inventory

    functions = {item["signature"]: item for item in descriptor["functions"]}
    update_function_inventory(
        functions, sql.replace("__MIGRATION_OWNER__", "corpus_migration_owner")
    )
    desired_identities = {item.identity for item in native_objects}
    for identity in retire:
        if identity in desired_identities:
            raise ValueError("retired native identity remains desired: " + identity.qualified)
        if identity.kind == "function":
            functions.pop(identity.qualified, None)
    required_signature = "data.require_execution_release(text)"
    for native in native_objects:
        if native.identity.kind != "function":
            continue
        signature = native.identity.qualified
        if signature not in functions:
            raise ValueError(
                f"normalized native function is absent from source inventory: {signature}"
            )
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
        name: relation_descriptor(metadata.tables[name])
        for name in tables
        if name in metadata.tables
    }
    # Removed stored relations cannot retain trigger or table admission authority.
    # Current views are separately owned NativeObjects, never stored-table metadata.
    descriptor["triggers"] = [
        trigger for trigger in descriptor["triggers"] if trigger["relation"] in metadata.tables
    ]
    for name in extra_relations:
        relation = metadata.tables[name]
        tables[name] = relation_descriptor(relation)
        descriptor["triggers"] = [
            t
            for t in descriptor["triggers"]
            if not (t["relation"] == name and t["name"] == "semantic_immutable")
        ]
        if relation.info.get("immutability", "immutable") == "immutable":
            descriptor["triggers"].append(
                dict(
                    relation=name,
                    name="semantic_immutable",
                    function="sem.refuse_immutable_mutation()",
                    type=58,
                    columns=[],
                    when=None,
                    args="",
                    deferrable=False,
                    deferred=False,
                )
            )
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
        tables[relation] = relation_descriptor(metadata.tables[relation])
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
    descriptor["tables"] = sorted(tables.values(), key=lambda item: item["relation"])
    required = admission_kernel()
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
        required = required.replace(
            "COALESCE(to_jsonb(p.proconfig),'[]'::jsonb) IS DISTINCT FROM item.value->'config'",
            "(CASE WHEN item.value ? 'result_definition' THEN COALESCE((SELECT "
            "jsonb_agg(v ORDER BY v) FROM unnest(p.proconfig) v),'[]'::jsonb) ELSE "
            "COALESCE(to_jsonb(p.proconfig),'[]'::jsonb) END) IS DISTINCT FROM "
            "item.value->'config'",
        )
        required = required.replace(
            marker,
            marker
            + (
                "\n OR (item.value ? 'result_definition' AND "
                "pg_get_function_result(p.oid) IS DISTINCT FROM "
                "item.value->>'result_definition')\n OR (item.value ? "
                "'argument_definition' AND pg_get_function_arguments(p.oid) IS DISTINCT "
                "FROM item.value->>'argument_definition')\n OR (item.value ? "
                "'argument_defaults' AND pg_get_expr(p.proargdefaults,0) IS DISTINCT "
                "FROM item.value->>'argument_defaults')\n OR (item.value ? 'cost' AND "
                "p.procost IS DISTINCT FROM (item.value->>'cost')::real)\n OR "
                "(item.value ? 'rows' AND p.prorows IS DISTINCT FROM "
                "(item.value->>'rows')::real)\n OR (item.value ? 'support' AND "
                "p.prosupport::regproc::text IS DISTINCT FROM item.value->>'support')\n "
                "OR (item.value ? 'catalog_acl' AND COALESCE((SELECT "
                "jsonb_agg(jsonb_build_array(\n CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE "
                "pg_get_userbyid(a.grantee) END,a.privilege_type,a.is_grantable)\n ORDER "
                "BY CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) "
                "END,a.privilege_type,a.is_grantable)\n FROM "
                "aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) "
                "a),'[]'::jsonb) IS DISTINCT FROM\n COALESCE((SELECT "
                "jsonb_agg(jsonb_build_array(grantee,privilege,grantable) ORDER BY "
                "grantee,privilege,grantable)\n FROM (SELECT CASE WHEN "
                "entry->>0='$migration_owner' THEN owner_name::text ELSE entry->>0 END "
                "AS grantee,\n entry->>1 AS privilege,bool_or((entry->>2)::boolean) AS "
                "grantable\n FROM jsonb_array_elements(item.value->'catalog_acl') entry "
                "GROUP BY 1,2) bound_acl),'[]'::jsonb))"
            ),
            1,
        )
    from .native_products import function_bodies

    # Admission protects its own exact enforcing body too. The descriptor literal
    # is a separate function, so this digest has no self-reference.
    functions[required_signature]["body_sha256"] = sha256(
        function_bodies(required)["data.require_execution_release"].encode()
    ).hexdigest()
    encoded = canonical_bytes(descriptor).decode().replace("'", "''")
    admission = (
        (
            "SET LOCAL ROLE corpus_sem_publisher;\nCREATE OR REPLACE FUNCTION "
            "data.execution_contract_descriptor() RETURNS jsonb LANGUAGE sql "
            "IMMUTABLE SET search_path=pg_catalog,pg_temp AS $descriptor$\n SELECT '"
        )
        + encoded
        + "'::jsonb\n$descriptor$;"
        + required
    )
    return admission
