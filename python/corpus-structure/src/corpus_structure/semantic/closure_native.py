"""Compile immutable release guards, admission receipts and activation from tables."""

from sqlalchemy import (
    Boolean,
    Integer,
    Text,
    and_,
    case,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
    tuple_,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, OID, aggregate_order_by, insert

from corpus_structure.schema.integrity import integrity, physical_schemas, role_name

from .native_program import (
    Assign,
    Block,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    Sql,
    column_type,
    core_relation_row,
    core_variable,
    function,
    pg_type,
)


def _routine(schema, name, parameters, steps, *, locals_=(), **properties):
    return function(
        schema,
        name,
        parameters=parameters,
        returns=pg_type(properties.pop("result", "void")),
        body=Block(steps, locals_),
        search_path=("pg_catalog", "pg_temp"),
        **properties,
    )


def _finite_float():
    value = core_variable("value", Text())
    exponent = core_variable("exponent", Integer())
    return _routine(
        "data",
        "require_float_lexical",
        (Parameter("value", pg_type("text")),),
        (
            If(value.in_(("0x0.0p+0", "-0x0.0p+0")), (Return(value),)),
            If(
                and_(
                    value.op("~")("^-?0x0[.][0-9a-f]{13}p-1022$"),
                    func.split_part(value, ".", 2).not_like("0000000000000p%"),
                ),
                (Return(value),),
            ),
            If(
                value.op("~")("^-?0x1[.][0-9a-f]{13}p[+-](0|[1-9][0-9]{0,3})$"),
                (
                    Assign("exponent", cast(func.split_part(value, "p", 2), Integer())),
                    If(
                        and_(exponent.between(-1022, 1023), value.not_like("%p-0")),
                        (Return(value),),
                    ),
                ),
            ),
            Raise("invalid finite float hexadecimal representation", "23514"),
        ),
        locals_=(Local("exponent", pg_type("int4")),),
        result="text",
        volatility="immutable",
        strict=True,
    )


def _principal_guards():
    from .native_catalog import namespace, pg, procedure, relation, roles

    principal = core_variable("principal", Text())
    required = core_variable("required_role", Text())
    owner = core_variable("owner_oid", OID())
    purpose = core_variable("purpose", Text())

    def has_role(role, mode):
        return pg.pg_has_role(principal, role, mode, type_=Boolean())

    def table_access(schema, privileges, *, mutation=False):
        oid = relation.c.oid
        grant = pg.has_table_privilege(principal, oid, privileges, type_=Boolean())
        if mutation:
            grant = or_(grant, pg.has_any_column_privilege(principal, oid, "INSERT,UPDATE"))
        return (
            select(oid)
            .select_from(relation.join(namespace, relation.c.relnamespace == namespace.c.oid))
            .where(namespace.c.nspname.in_(schema), relation.c.relkind.in_(("r", "p")), grant)
            .exists()
        )

    owner_lookup = SelectInto(
        select(namespace.c.nspowner).where(namespace.c.nspname == "sem"), ("owner_oid",)
    )
    elevated = or_(
        has_role(role_name("publisher"), "MEMBER"),
        select(roles.c.oid)
        .where(
            roles.c.rolname == principal,
            or_(
                roles.c.rolsuper,
                roles.c.rolcreaterole,
                roles.c.rolcreatedb,
                roles.c.rolbypassrls,
                roles.c.rolreplication,
            ),
        )
        .exists(),
        pg.has_database_privilege(principal, pg.current_database(), "TEMP"),
        select(namespace.c.oid)
        .where(
            namespace.c.nspname.in_(physical_schemas()),
            pg.has_schema_privilege(principal, namespace.c.oid, "CREATE"),
        )
        .exists(),
        table_access(("sem", "data"), "INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER", mutation=True),
    )
    reference_access = table_access(("eval",), "SELECT,INSERT,UPDATE,DELETE,TRUNCATE")
    contracts = func.jsonb_array_elements(
        func.data.execution_contract_descriptor(type_=JSONB())["functions"]
    ).table_valued(column("value", JSONB()))
    contract = contracts.c.value
    function_match = procedure.c.oid == pg.to_regprocedure(contract["signature"].astext)

    def differing_grants(role, *, include_missing=False):
        expected = contract["execute_roles"].has_key(role)
        actual = pg.has_function_privilege(principal, procedure.c.oid, "EXECUTE", type_=Boolean())
        gap = actual.is_distinct_from(expected)
        if include_missing:
            gap = or_(procedure.c.oid.is_(None), gap)
        return (
            select(1)
            .select_from(contracts.join(procedure, function_match, isouter=include_missing))
            .where(gap)
            .exists()
        )

    def cannot_call(signature):
        return ~func.coalesce(
            pg.has_function_privilege(principal, pg.to_regprocedure(signature), "EXECUTE"),
            False,
            type_=Boolean(),
        )

    principal_locals = (
        Local("principal", pg_type("name"), func.session_user()),
        Local("owner_oid", pg_type("oid")),
    )
    runtime = _routine(
        "data",
        "require_runtime_principal",
        (Parameter("purpose", pg_type("text")),),
        (
            Assign(
                "required_role",
                case(
                    {
                        purpose: role
                        for purpose, role in integrity().purposes.items()
                        if role is not None
                    },
                    value=purpose,
                ),
            ),
            If(required.is_(None), (Raise("unknown runtime purpose", "P0001"),)),
            owner_lookup,
            If(
                or_(
                    ~has_role(required, "USAGE"),
                    pg.current_setting("role").not_in(("none", cast(principal, Text()))),
                    has_role(owner, "MEMBER"),
                    elevated,
                ),
                (
                    Raise(
                        pg.format("unrestricted or mismatched runtime principal for %s", purpose),
                        "42501",
                    ),
                ),
            ),
            If(
                or_(
                    ~pg.has_table_privilege(principal, "sem.release", "SELECT", type_=Boolean()),
                    ~pg.has_schema_privilege(principal, "ops", "USAGE", type_=Boolean()),
                    and_(
                        purpose.in_(("read", "write", "evaluate")),
                        cannot_call("ops.read_demand_result(jsonb)"),
                    ),
                    and_(purpose == "write", cannot_call("ops.initialize_source_project(jsonb)")),
                    and_(
                        purpose.in_(("write", "evaluate")),
                        cannot_call("ops.register_data_demand(jsonb)"),
                    ),
                    and_(purpose == "evaluate", cannot_call("ops.admit_authored_data(jsonb)")),
                    and_(
                        purpose == "admit",
                        or_(
                            cannot_call("sem.publish_release_archive(text)"),
                            cannot_call("ops.inspect_data_execution(jsonb)"),
                        ),
                    ),
                ),
                (Raise("required runtime capability unavailable", "42501"),),
            ),
            If(
                differing_grants(required, include_missing=True),
                (Raise("runtime operation privileges differ from purpose contract", "42501"),),
            ),
            If(
                and_(purpose != "evaluate", reference_access),
                (Raise("runtime principal has independent reference access", "42501"),),
            ),
        ),
        locals_=(*principal_locals, Local("required_role", pg_type("text"))),
        security_definer=True,
    )
    admission = _routine(
        "sem",
        "require_admission_caller",
        (),
        (
            owner_lookup,
            If(has_role(owner, "MEMBER"), (Return(),)),
            If(
                or_(
                    ~has_role(role_name("admitter"), "USAGE"),
                    elevated,
                    reference_access,
                    differing_grants(role_name("admitter")),
                ),
                (Raise("unrestricted admission caller", "42501"),),
            ),
        ),
        locals_=principal_locals,
        security_definer=True,
    )
    return runtime, admission


def closure_foundation_sql(target):
    """Generate archive verification alongside the database-purpose and value guards."""
    from .native_objects import native_sql_script
    from .types import SEMANTIC_ARCHIVE_FORMAT, SEMANTIC_COMPILER_VERSION, SEMANTIC_PROFILE_VERSIONS

    releases = target.tables["sem.release"]
    inputs = target.tables["sem.input"]
    artifacts = target.tables["sem.artifact"]
    r = core_variable("r", releases.c.release_id.type)
    archive_type = pg_type(str(releases.schema), releases.name)
    loaded = {
        name: core_variable("archived", releases.c[name].type, name)
        for name in ("release_id", "profile", "content_digest", "prepared_bytes", "manifest_bytes")
    }
    document, manifest = (core_variable(name, JSONB()) for name in ("document", "manifest"))
    products = document["products"]

    def sha(content):
        return func.encode(func.sha256(content), "hex")

    def refuse(condition, message):
        return If(condition, (Raise(message, "23514"),))

    def inventory(name, digest):
        ordered = aggregate_order_by(func.jsonb_build_array(name, digest), name)
        return func.coalesce(func.jsonb_agg(ordered), cast(literal("[]"), JSONB()))

    archived_inputs = inputs.c.release_id == r
    archived_artifacts = artifacts.c.release_id == r
    manifest_inputs = tuple(
        refuse(
            manifest[field].is_distinct_from(
                select(inventory(inputs.c.input_name, inputs.c.content_digest))
                .where(archived_inputs, inputs.c.input_kind == kind)
                .scalar_subquery()
            ),
            "archive input manifest differs: " + kind,
        )
        for kind, field in (("source", "sources"), ("dependency", "dependencies"))
    )
    expected = func.jsonb_array_elements(products["artifacts"]).table_valued(
        column("value", JSONB())
    )
    archive_pairs = (
        select(inventory(artifacts.c.artifact_name, artifacts.c.content_digest))
        .where(archived_artifacts)
        .scalar_subquery()
    )
    declared_pairs = select(
        inventory(expected.c.value["kind"].astext, expected.c.value["digest"].astext)
    ).scalar_subquery()
    input_count = select(func.count()).select_from(inputs).where(archived_inputs)
    closed_metadata_inputs = tuple(
        (name, name) for name in ("profile", "vocabulary", "ontology_sources")
    )
    archive_check = _routine(
        "sem",
        "require_archive_bytes",
        (Parameter("r", column_type(releases.c.release_id)),),
        (
            SelectInto(
                select(core_relation_row(releases))
                .select_from(releases)
                .where(releases.c.release_id == r),
                ("archived",),
                strict=True,
            ),
            Assign("document", cast(func.convert_from(loaded["prepared_bytes"], "UTF8"), JSONB())),
            Assign("manifest", cast(func.convert_from(loaded["manifest_bytes"], "UTF8"), JSONB())),
            refuse(
                or_(
                    loaded["profile"].not_in(SEMANTIC_PROFILE_VERSIONS),
                    document["format"].astext.is_distinct_from(SEMANTIC_ARCHIVE_FORMAT),
                    manifest["profile"]["compiler_version"].astext.is_distinct_from(
                        SEMANTIC_COMPILER_VERSION
                    ),
                    loaded["release_id"]
                    != literal("release:").concat(sha(loaded["manifest_bytes"])),
                    loaded["content_digest"] != sha(loaded["prepared_bytes"]),
                    products["release_id"].astext.is_distinct_from(r),
                    manifest["profile"]["version"].astext.is_distinct_from(loaded["profile"]),
                ),
                "archive manifest identity differs",
            ),
            *manifest_inputs,
            refuse(
                or_(
                    archive_pairs.is_distinct_from(declared_pairs),
                    select(1)
                    .where(archived_inputs, inputs.c.content_digest != sha(inputs.c.content))
                    .exists(),
                    select(1)
                    .where(
                        archived_artifacts, artifacts.c.content_digest != sha(artifacts.c.content)
                    )
                    .exists(),
                    input_count.scalar_subquery()
                    != func.jsonb_array_length(manifest["sources"])
                    + func.jsonb_array_length(manifest["dependencies"])
                    + len(closed_metadata_inputs),
                    input_count.where(
                        tuple_(inputs.c.input_kind, inputs.c.input_name).in_(closed_metadata_inputs)
                    ).scalar_subquery()
                    != len(closed_metadata_inputs),
                ),
                "archive product or input closure differs",
            ),
            If(
                manifest.has_key("data_operation_model"),
                (
                    refuse(
                        or_(
                            manifest.has_key("execution_model_id"),
                            products.has_key("execution_model_id"),
                            ~select(1)
                            .where(
                                archived_artifacts,
                                artifacts.c.artifact_name == "data_operations.json",
                                artifacts.c.content_digest
                                == manifest["data_operation_model"].astext,
                            )
                            .exists(),
                            ~select(1)
                            .where(
                                archived_inputs,
                                inputs.c.input_kind == "dependency",
                                inputs.c.input_name == "data-operations/manifest.json",
                            )
                            .exists(),
                            select(1)
                            .where(
                                archived_inputs,
                                inputs.c.input_kind == "dependency",
                                inputs.c.input_name.like("execution/%"),
                            )
                            .exists(),
                        ),
                        "target operation archive binding differs",
                    ),
                ),
            ),
        ),
        locals_=(
            Local("archived", archive_type),
            Local("document", pg_type("jsonb")),
            Local("manifest", pg_type("jsonb")),
        ),
        security_definer=True,
    )
    return native_sql_script((*_principal_guards(), archive_check, _finite_float()))


def closure_native_sql(target):
    finalized = target.tables["sem.release_finalization"]
    deployments = target.tables["sem.deployment_admission"]
    admissions = target.tables["sem.sql_admission"]
    projects = target.tables["data.project"]
    r = core_variable("r", finalized.c.release_id.type)

    def routine(name, statements, parameters=(), *, returns=None, locals_=(), protected=True):
        return function(
            "sem",
            name,
            parameters=parameters,
            returns=returns or pg_type("void"),
            body=Block(statements, locals_),
            security_definer=protected,
            search_path=("pg_catalog", "pg_temp"),
        )

    def finalized_guard():
        return If(
            ~exists(select(1).select_from(finalized).where(finalized.c.release_id == r)),
            (Raise("release is not finalized", "P0001"),),
        )

    immutable = routine(
        "refuse_immutable_mutation",
        (
            Raise(
                func.pg_catalog.format(
                    "immutable semantic content: %s.%s %s",
                    core_variable("tg_table_schema", Text()),
                    core_variable("tg_table_name", Text()),
                    core_variable("tg_op", Text()),
                ),
                "23514",
            ),
        ),
        returns=pg_type("trigger"),
        protected=False,
    )
    new_release = core_variable("new", finalized.c.release_id.type, "release_id")
    intrinsic = routine(
        "guard_finalized_insert",
        (
            If(
                exists(
                    select(1).select_from(finalized).where(finalized.c.release_id == new_release)
                ),
                (
                    Raise(
                        func.pg_catalog.format(
                            "finalized release cannot acquire intrinsic meaning: %s", new_release
                        ),
                        "23514",
                    ),
                ),
            ),
            Return(core_variable("new", Text())),
        ),
        returns=pg_type("trigger"),
    )

    def receipt(relation, name, fields, message):
        values = {
            column: core_variable(parameter, relation.c[column].type)
            for parameter, column in fields
        }
        content = values["content"]
        values = {
            **values,
            "content_digest": func.pg_catalog.encode(func.pg_catalog.sha256(content), "hex"),
        }
        return routine(
            name,
            (
                Perform(func.sem.require_admission_caller()),
                finalized_guard(),
                Sql(insert(relation).values(values).on_conflict_do_nothing()),
                If(
                    ~exists(
                        select(1)
                        .select_from(relation)
                        .where(*(relation.c[column] == value for column, value in values.items()))
                    ),
                    (Raise(message, "23505"),),
                ),
            ),
            tuple(
                Parameter(parameter, column_type(relation.c[column]))
                for parameter, column in fields
            ),
        )

    deployment = receipt(
        deployments,
        "record_deployment_admission",
        (
            ("r", "release_id"),
            ("p", "physical_id"),
            ("d", "deployment_id"),
            ("k", "kind"),
            ("c", "content"),
        ),
        "deployment admission replay differs",
    )
    sql_admission = receipt(
        admissions,
        "record_sql_admission",
        (
            ("r", "release_id"),
            ("ik", "input_kind"),
            ("n", "input_name"),
            ("p", "physical_id"),
            ("c", "content"),
        ),
        "SQL admission replay differs",
    )
    project = core_variable("p", projects.c.project_id.type)
    parent = core_variable("parent", projects.c.active_release_id.type)
    generation = core_variable("g", projects.c.generation.type)
    activation = routine(
        "activate_release",
        (
            Perform(func.sem.require_admission_caller()),
            finalized_guard(),
            Perform(func.data.require_execution_release(r)),
            SelectInto(
                update(projects)
                .where(
                    projects.c.project_id == project,
                    projects.c.active_release_id.is_not_distinct_from(parent),
                    projects.c.generation == generation,
                )
                .values(active_release_id=r, generation=projects.c.generation + 1)
                .returning(projects.c.generation),
                ("result",),
            ),
            If(~core_variable("found", Boolean()), (Raise("stale activation token", "40001"),)),
            Return(core_variable("result", projects.c.generation.type)),
        ),
        (
            Parameter("p", column_type(projects.c.project_id)),
            Parameter("r", column_type(finalized.c.release_id)),
            Parameter("parent", column_type(projects.c.active_release_id)),
            Parameter("g", column_type(projects.c.generation)),
        ),
        returns=column_type(projects.c.generation),
        locals_=(Local("result", column_type(projects.c.generation)),),
    )
    return ";\n".join((immutable, intrinsic, deployment, sql_admission, activation)) + ";\n"
