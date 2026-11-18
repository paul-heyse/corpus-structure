"""Compile the current runtime binding checks and registration from the model."""

from sqlalchemy import Text, cast, column, distinct, exists, func, literal, or_, select
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, aggregate_order_by, array, insert

from .data_operation_runtime import (
    ARCHIVE_FIELDS,
    ARCHIVE_VERSION,
    INPUT_FIELDS,
    MANIFEST_FIELDS,
    VERSION,
)
from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    Sql,
    core_variable,
    function,
    pg_type,
)


def runtime_binding_sql(target):
    artifacts = target.tables["sem.artifact"]
    bindings = target.tables["sem.runtime_binding"]
    r = core_variable("r", Text())
    runtime = core_variable("runtime", Text())
    manifest_bytes = core_variable("manifest_content", BYTEA())
    archive_bytes = core_variable("archive_content", BYTEA())
    parameter_names = ("r", "runtime", "manifest_content", "archive_content")
    parameter_types = ("text", "text", "bytea", "bytea")

    def routine(name, body, *, locals_=(), returns="void", reads_bytes=True):
        count = 4 if reads_bytes else 2
        return (
            function(
                "sem",
                name,
                parameters=tuple(
                    Parameter(key, pg_type(kind))
                    for key, kind in zip(
                        parameter_names[:count], parameter_types[:count], strict=True
                    )
                ),
                returns=pg_type(returns),
                body=Block(body, tuple(Local(key, pg_type(kind)) for key, kind in locals_)),
                security_definer=True,
                search_path=("pg_catalog", "pg_temp"),
            )
            + ";\n"
        )

    def as_json(value):
        return cast(func.pg_catalog.convert_from(value, "UTF8"), JSONB())

    def digest(value):
        return func.pg_catalog.encode(func.pg_catalog.sha256(value), "hex", type_=Text())

    def check(condition, message, state="23514"):
        return If(condition, (Raise(message, state),))

    def fields(value, keys):
        return Perform(func.ops.ddo_fields(value, array(list(keys), type_=Text())))

    def rows(value, name):
        return (
            func.pg_catalog.jsonb_array_elements(value)
            .table_valued(column("value", JSONB()))
            .render_derived(name=name)
        )

    def artifact(name):
        return artifacts.c.release_id == r, artifacts.c.artifact_name == name

    manifest = core_variable("manifest", JSONB())
    archive = core_variable("archive", JSONB())
    expected = core_variable("expected", JSONB())
    actual = core_variable("actual", JSONB())
    model = core_variable("model", JSONB())
    item = core_variable("item", JSONB())
    operation = core_variable("operation_", JSONB())
    profile = core_variable("profile_", JSONB())
    profiles = core_variable("profiles_", JSONB())
    source = core_variable("runtime_source", JSONB())
    archive_rows = rows(archive["inputs"], "archive_inputs")
    value = archive_rows.c.value
    actual_rows = rows(actual, "actual_inputs")
    operation_rows = rows(model["operations"], "operations")
    runtime_meaning, attestation = manifest["runtime_meaning"], manifest["attestation_meaning"]
    provider_fields = ("profile", "attestation", "runtime_contract", "runtime_sha256")
    object_ = func.pg_catalog.jsonb_build_object
    kind = func.pg_catalog.jsonb_typeof
    nullif = func.nullif

    def envelope_differs(envelope, tag):
        return (
            envelope[0].is_distinct_from(cast(literal('"ddo"'), JSONB())),
            envelope[1].is_distinct_from(cast(literal('"' + tag + '"'), JSONB())),
            envelope[2].is_distinct_from(cast(literal('"1"'), JSONB())),
        )

    validate = routine(
        "validate_runtime_binding",
        (
            Assign("manifest", as_json(manifest_bytes)),
            Assign("archive", as_json(archive_bytes)),
            check(
                manifest["version"].astext.is_distinct_from(VERSION),
                "unsupported target runtime version",
            ),
            Perform(func.sem.require_admission_caller()),
            fields(manifest, MANIFEST_FIELDS),
            fields(archive, ARCHIVE_FIELDS),
            check(
                or_(
                    manifest_bytes.is_distinct_from(
                        func.pg_catalog.convert_to(func.data.canonical_json(manifest), "UTF8")
                    ),
                    archive_bytes.is_distinct_from(
                        func.pg_catalog.convert_to(func.data.canonical_json(archive), "UTF8")
                    ),
                    runtime.is_distinct_from(literal("runtime:").concat(digest(manifest_bytes))),
                    manifest["release_id"].astext.is_distinct_from(r),
                    archive["version"].astext.is_distinct_from(ARCHIVE_VERSION),
                    nullif(manifest["python_version"].astext, "").is_(None),
                    nullif(manifest["execution_profile"].astext, "").is_(None),
                    ~exists(
                        select(1).where(
                            *artifact("data_operations.json"),
                            artifacts.c.content_digest == manifest["model_digest"].astext,
                        )
                    ),
                ),
                "target runtime identity or release differs",
            ),
            SelectInto(
                select(as_json(artifacts.c.content)).where(
                    *artifact("data_operation_runtime_inputs.json")
                ),
                ("expected",),
                strict=True,
            ),
            check(
                or_(
                    manifest["semantic_inputs"].is_distinct_from(expected),
                    kind(archive["inputs"]).is_distinct_from("array"),
                    kind(manifest["implementation_inputs"]).is_distinct_from("array"),
                ),
                "target runtime input requirements differ",
            ),
            ForQuery(
                ("item",),
                select(value),
                (
                    fields(item, INPUT_FIELDS),
                    check(
                        or_(
                            nullif(item["name"].astext, "").is_(None),
                            ~item["content_hex"].astext.regexp_match("^([0-9a-f]{2})*$"),
                            item["sha256"].astext.is_distinct_from(
                                digest(func.pg_catalog.decode(item["content_hex"].astext, "hex"))
                            ),
                        ),
                        "target runtime source bytes differ",
                    ),
                ),
            ),
            SelectInto(
                select(
                    func.coalesce(
                        func.pg_catalog.jsonb_agg(
                            aggregate_order_by(
                                object_(
                                    "name", value["name"].astext, "sha256", value["sha256"].astext
                                ),
                                value["name"].astext.collate("C"),
                            )
                        ),
                        cast(literal("[]"), JSONB()),
                    )
                ),
                ("actual",),
            ),
            check(
                or_(
                    actual.is_distinct_from(manifest["implementation_inputs"]),
                    select(
                        func.count() != func.count(distinct(actual_rows.c.value["name"].astext))
                    ).scalar_subquery(),
                    ~actual.contains(expected),
                ),
                "target runtime source closure differs",
            ),
            check(
                or_(
                    *envelope_differs(runtime_meaning, "runtime-artifact"),
                    func.data.ddo_identity("runtime-artifact", runtime_meaning[3]).is_distinct_from(
                        manifest["runtime_artifact"].astext
                    ),
                    func.data.ddo_json(runtime_meaning[3]).is_distinct_from(
                        object_("python", manifest["python_version"].astext, "inputs", actual)
                    ),
                    *envelope_differs(attestation, "execution-attestation"),
                    func.data.ddo_identity(
                        "execution-attestation", attestation[3]
                    ).is_distinct_from(manifest["attestation"].astext),
                    func.data.ddo_json(attestation[3]).is_distinct_from(
                        object_(
                            "runtime_artifact",
                            manifest["runtime_artifact"].astext,
                            "release",
                            r,
                            "execution_profile",
                            manifest["execution_profile"].astext,
                            "observed",
                            manifest["observed"],
                        )
                    ),
                ),
                "target runtime artifact or attestation differs",
            ),
            SelectInto(
                select(as_json(artifacts.c.content)).where(*artifact("data_operations.json")),
                ("model",),
                strict=True,
            ),
            Assign("profiles_", cast(literal("{}"), JSONB())),
            ForQuery(
                ("operation_",),
                select(operation_rows.c.value),
                (
                    Assign("profile_", func.sem.ddo_provider_profile(r, operation)),
                    If(
                        profile.is_not(None),
                        (
                            Assign(
                                "item",
                                manifest["provider_profiles"][operation["semantic_id"].astext],
                            ),
                            fields(item, provider_fields),
                            check(
                                item["profile"].is_distinct_from(profile),
                                "runtime provider semantic contract differs",
                                "P0001",
                            ),
                            SelectInto(
                                select(value).where(
                                    value["name"].astext
                                    == literal("data-operations/contracts/").concat(
                                        item["runtime_contract"].astext
                                    )
                                ),
                                ("runtime_source",),
                                strict=True,
                            ),
                            check(
                                or_(
                                    source["sha256"].astext.is_distinct_from(
                                        item["runtime_sha256"].astext
                                    ),
                                    as_json(
                                        func.pg_catalog.decode(source["content_hex"].astext, "hex")
                                    )["provider_profile"].is_distinct_from(item["attestation"]),
                                ),
                                "runtime provider execution asset differs",
                                "P0001",
                            ),
                            Perform(
                                func.sem.ddo_validate_provider_attestation(
                                    item["attestation"], profile
                                )
                            ),
                            Assign(
                                "profiles_",
                                profiles.concat(object_(operation["semantic_id"].astext, item)),
                            ),
                        ),
                    ),
                ),
            ),
            check(
                manifest["provider_profiles"].is_distinct_from(profiles),
                "runtime provider profile operation coverage differs",
                "P0001",
            ),
        ),
        locals_=tuple(
            (name, "jsonb")
            for name in (
                "manifest",
                "archive",
                "model",
                "expected",
                "actual",
                "item",
                "operation_",
                "profile_",
                "profiles_",
                "runtime_source",
            )
        ),
    )

    bound = bindings.c.release_id == r, bindings.c.runtime_id == runtime
    register = routine(
        "register_runtime_binding",
        (
            Perform(func.sem.validate_runtime_binding(r, runtime, manifest_bytes, archive_bytes)),
            Sql(
                insert(bindings)
                .values(
                    {
                        bindings.c.release_id: r,
                        bindings.c.runtime_id: runtime,
                        bindings.c.manifest_bytes: manifest_bytes,
                        bindings.c.archive_bytes: archive_bytes,
                        bindings.c.execution_profile: as_json(manifest_bytes)[
                            "execution_profile"
                        ].astext,
                    }
                )
                .on_conflict_do_nothing()
            ),
            SelectInto(select(bindings).where(*bound), ("previous",), strict=True),
            check(
                or_(
                    core_variable(
                        "previous", BYTEA(), bindings.c.manifest_bytes.name
                    ).is_distinct_from(manifest_bytes),
                    core_variable(
                        "previous", BYTEA(), bindings.c.archive_bytes.name
                    ).is_distinct_from(archive_bytes),
                ),
                "runtime identity already denotes different provenance",
                "23505",
            ),
            Return(runtime),
        ),
        locals_=(("previous", bindings.fullname),),
        returns="text",
    )
    require = routine(
        "require_runtime_binding",
        (check(~exists(select(1).where(*bound)), "unknown same-release runtime binding"),),
        reads_bytes=False,
    )
    return validate + register + require
