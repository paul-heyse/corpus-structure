"""Model-bound release, catalog and native admission receipt programs."""

from sqlalchemy import (
    Boolean,
    Integer,
    SmallInteger,
    Text,
    and_,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, aggregate_order_by, array

from .native_program import (
    Assign,
    Block,
    Comment,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    SelectInto,
    core_variable,
    function,
    pg_type,
)

CATALOG_START = "native catalog checks begin"
CATALOG_END = " -- native catalog checks complete"
PHYSICAL_CATALOG_START = " -- native physical catalog checks begin"
PHYSICAL_CATALOG_END = " -- native physical catalog checks complete"


def release_preconditions(metadata):
    finalized = metadata.tables["sem.release_finalization"]
    release = metadata.tables["sem.release"]
    selected = core_variable("r", Text())
    return (
        If(
            ~exists(select(1).select_from(finalized).where(finalized.c.release_id == selected)),
            (Raise("release is not finalized", "23514"),),
        ),
        Perform(func.sem.require_execution_projection(selected)),
        If(
            ~exists(select(1).select_from(release).where(release.c.release_id == selected)),
            (Raise("unknown execution release", "23514"),),
        ),
        Assign("expected", func.data.execution_contract_descriptor()),
    )


def native_receipt_admission(metadata):
    receipt = metadata.tables["sem.deployment_admission"]
    selected = core_variable("r", Text())
    expected = core_variable("expected", JSONB())
    owner = core_variable("owner_name", Text())
    content = func.convert_to(cast(expected, Text()), "UTF8")
    identity = func.encode(func.sha256(content), "hex")
    physical_id = expected["physical_id"].astext
    recorded = exists(
        select(1)
        .select_from(receipt)
        .where(
            receipt.c.release_id == selected,
            receipt.c.physical_id == physical_id,
            receipt.c.deployment_id == identity,
            receipt.c.kind == "native",
            receipt.c.content == content,
        )
    )
    authorized = or_(
        func.pg_has_role(func.session_user(), "corpus_sem_admitter", "USAGE"),
        func.pg_has_role(func.session_user(), owner, "MEMBER"),
    )
    return (
        If(
            ~recorded,
            (
                If(
                    ~authorized,
                    (Raise("native admission requires restricted admission phase", "42501"),),
                ),
                Perform(
                    func.sem.record_deployment_admission(
                        selected, physical_id, identity, "native", content
                    )
                ),
            ),
        ),
    )


def _catalog_failure(query, message):
    return (
        SelectInto(query.limit(1), ("spec",)),
        If(core_variable("found", Boolean()), (Raise(message, "23514"),)),
    )


def _diagnostic(message, *fields):
    spec = core_variable("spec", JSONB())
    return func.format(message, *(func.coalesce(spec[name].astext, "<NULL>") for name in fields))


def physical_catalog_checks(metadata):
    """Bind physical CHECK declarations and selected views to observed catalogs."""
    from . import native_catalog as catalog

    expected = core_variable("expected", JSONB())
    artifact = metadata.tables["sem.physical_contract"].alias("artifact")
    checks = _json_items(artifact.c.checks, "item").lateral()
    item = checks.c.value
    constraint = catalog.constraint.alias("c")
    relation = catalog.relation.alias("rel")
    namespace = catalog.namespace.alias("ns")
    physical_id = expected["physical_id"].astext
    declared = artifact.join(checks, true())
    observed = declared.outerjoin(
        constraint,
        and_(
            constraint.c.conrelid == func.to_regclass(item["relation"].astext),
            constraint.c.conname == item["name"].astext,
            constraint.c.contype == "c",
        ),
    )
    matching = exists(
        select(1)
        .select_from(declared)
        .where(
            artifact.c.physical_id == physical_id,
            item["relation"].astext == namespace.c.nspname + "." + relation.c.relname,
            item["name"].astext == constraint.c.conname,
        )
        .correlate(constraint, relation, namespace)
    )
    views = _json_items(expected["views"], "item")

    def normalized_view(value):
        return func.regexp_replace(
            func.regexp_replace(value, r"\mAS\M", "", "gi"), "[[:space:]();]", "", "g"
        )

    return (
        If(
            ~exists(
                select(1)
                .select_from(artifact)
                .where(
                    artifact.c.physical_id == physical_id,
                    artifact.c.source_digest == expected["physical_checks_source_digest"].astext,
                )
            ),
            (Raise("physical CHECK contract is unavailable", "23514"),),
        ),
        *_catalog_failure(
            select(item)
            .select_from(observed)
            .where(
                artifact.c.physical_id == physical_id,
                or_(
                    constraint.c.oid.is_(None),
                    ~constraint.c.convalidated,
                    func.pg_get_expr(constraint.c.conbin, constraint.c.conrelid).is_distinct_from(
                        item["expression"].astext
                    ),
                ),
            ),
            _diagnostic("physical CHECK expression differs: %s.%s", "relation", "name"),
        ),
        If(
            exists(
                select(1)
                .select_from(
                    constraint.join(relation, relation.c.oid == constraint.c.conrelid).join(
                        namespace, namespace.c.oid == relation.c.relnamespace
                    )
                )
                .where(
                    constraint.c.contype == "c",
                    expected["physical_relations"].has_key(
                        namespace.c.nspname + "." + relation.c.relname
                    ),
                    ~matching,
                )
            ),
            (Raise("unexpected physical CHECK", "23514"),),
        ),
        *_catalog_failure(
            select(views.c.value).where(
                or_(
                    func.to_regclass(views.c.value["relation"].astext).is_(None),
                    normalized_view(
                        func.pg_get_viewdef(
                            func.to_regclass(views.c.value["relation"].astext), True
                        )
                    ).is_distinct_from(normalized_view(views.c.value["query"].astext)),
                )
            ),
            "native selected-fact view differs",
        ),
    )


def trigger_catalog_checks():
    """Keep transition flags, ordered update columns and trigger arguments exact."""
    from . import native_catalog as catalog

    expected = core_variable("expected", JSONB())
    items = _json_items(expected["triggers"], "item")
    item = items.c.value
    observed = catalog.trigger.alias("t")
    attributes = catalog.attribute.alias("a")
    columns = (
        func.unnest(cast(observed.c.tgattr, ARRAY(SmallInteger())))
        .table_valued(column("num", SmallInteger()), with_ordinality="position")
        .render_derived("attrs")
    )
    ordered_names = (
        select(
            func.to_jsonb(
                func.coalesce(
                    func.array_agg(
                        aggregate_order_by(cast(attributes.c.attname, Text()), columns.c.position)
                    ),
                    array([], type_=Text()),
                )
            )
        )
        .select_from(
            columns.join(
                attributes,
                and_(
                    attributes.c.attrelid == observed.c.tgrelid,
                    attributes.c.attnum == columns.c.num,
                ),
            )
        )
        .correlate(observed)
        .scalar_subquery()
    )
    return _catalog_failure(
        select(item)
        .select_from(
            items.outerjoin(
                observed,
                and_(
                    observed.c.tgrelid == func.to_regclass(item["relation"].astext),
                    observed.c.tgname == item["name"].astext,
                    ~observed.c.tgisinternal,
                ),
            )
        )
        .where(
            or_(
                observed.c.oid.is_(None),
                observed.c.tgenabled.not_in(("O", "A")),
                observed.c.tgfoid.is_distinct_from(func.to_regprocedure(item["function"].astext)),
                observed.c.tgtype != cast(item["type"].astext, Integer()),
                observed.c.tgdeferrable.is_distinct_from(
                    cast(item["deferrable"].astext, Boolean())
                ),
                observed.c.tginitdeferred.is_distinct_from(
                    cast(item["deferred"].astext, Boolean())
                ),
                ordered_names.is_distinct_from(item["columns"]),
                func.pg_get_expr(observed.c.tgqual, observed.c.tgrelid).is_distinct_from(
                    item["when"].astext
                ),
                func.encode(observed.c.tgargs, "hex").is_distinct_from(item["args"].astext),
            )
        ),
        _diagnostic("native execution guard differs: %s.%s", "relation", "name"),
    )


def index_catalog_checks():
    from . import native_catalog as catalog

    expected = core_variable("expected", JSONB())
    items = _json_items(expected["indexes"], "item")
    item = items.c.value
    observed = catalog.index.alias("i")
    return _catalog_failure(
        select(item)
        .select_from(
            items.outerjoin(
                observed, observed.c.indexrelid == func.to_regclass(item["index"].astext)
            )
        )
        .where(
            or_(
                observed.c.indexrelid.is_(None),
                ~observed.c.indisvalid,
                ~observed.c.indisready,
                observed.c.indrelid.is_distinct_from(func.to_regclass(item["relation"].astext)),
                func.pg_get_indexdef(observed.c.indexrelid).is_distinct_from(
                    item["definition"].astext
                ),
            )
        ),
        "native source search index differs",
    )


def native_check_catalog_checks():
    from . import native_catalog as catalog

    expected = core_variable("expected", JSONB())
    items = _json_items(expected["checks"], "item")
    item = items.c.value
    observed = catalog.constraint.alias("c")
    return _catalog_failure(
        select(item)
        .select_from(
            items.outerjoin(
                observed,
                and_(
                    observed.c.conrelid == func.to_regclass(item["relation"].astext),
                    observed.c.conname == item["name"].astext,
                ),
            )
        )
        .where(
            or_(
                observed.c.oid.is_(None),
                ~observed.c.convalidated,
                func.pg_get_constraintdef(observed.c.oid).is_distinct_from(
                    item["definition"].astext
                ),
            )
        ),
        _diagnostic("native CHECK expression differs: %s", "relation"),
    )


def admission_kernel(metadata) -> str:
    """Generate the execution guard and its fixed purpose-role grants."""
    from .alembic_privileges import PUBLISHER, privilege_admission_checks
    from .native_admission_functions import function_catalog_checks
    from .native_admission_principals import principal_catalog_checks, restricted_principal_checks
    from .native_admission_tables import reader_catalog_checks, table_catalog_checks
    from .native_catalog import namespace_owner
    from .native_objects import (
        NativeIdentity,
        native_owner_sql,
        native_privilege_sql,
        native_sql_script,
    )

    guard = NativeIdentity("function", "data", "require_execution_release", ("text",))
    descriptor = NativeIdentity("function", "data", "execution_contract_descriptor")
    body = function(
        guard.schema,
        guard.name,
        parameters=(Parameter("r", pg_type("text")),),
        returns=pg_type("void"),
        volatility="volatile",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                *release_preconditions(metadata),
                SelectInto(namespace_owner(), ("owner_name",)),
                Comment(CATALOG_START),
                *physical_catalog_checks(metadata),
                *function_catalog_checks(),
                *trigger_catalog_checks(),
                *table_catalog_checks(),
                *reader_catalog_checks(),
                *index_catalog_checks(),
                *privilege_admission_checks(),
                *principal_catalog_checks(),
                *native_check_catalog_checks(),
                *restricted_principal_checks(),
                Comment(CATALOG_END.removeprefix(" -- ")),
                *release_semantic_checks(metadata),
                *native_receipt_admission(metadata),
            ),
            (
                Local("expected", pg_type("jsonb")),
                Local("spec", pg_type("jsonb")),
                Local("owner_name", pg_type("text")),
            ),
        ),
    )
    return native_sql_script(
        (
            body,
            native_owner_sql(guard, PUBLISHER),
            native_privilege_sql(guard, "PUBLIC", grant=False),
            *(
                native_privilege_sql(guard, role, "EXECUTE")
                for role in (
                    "corpus_sem_writer",
                    "corpus_sem_reader",
                    "corpus_sem_evaluator",
                    "corpus_sem_admitter",
                )
            ),
            native_privilege_sql(descriptor, "corpus_sem_admitter", "EXECUTE"),
        )
    )


def _decoded_json(content):
    return cast(func.convert_from(content, "UTF8"), JSONB())


def _json_items(value, name):
    from sqlalchemy import column

    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()))
        .render_derived(name=name)
    )


def _refuse(condition, message):
    return If(condition, (Raise(message, "23514"),))


def _release_asset_checks(metadata):
    from sqlalchemy import and_

    release = metadata.tables["sem.release"]
    inputs = metadata.tables["sem.input"]
    admissions = metadata.tables["sem.sql_admission"]
    selected = core_variable("r", Text())
    expected = core_variable("expected", JSONB())
    diagnostic = _json_items(
        _decoded_json(release.c.prepared_bytes)["products"]["diagnostics"], "diagnostic"
    )
    item = diagnostic.c.value
    rejected_diagnostic = (
        select(1)
        .select_from(release.join(diagnostic, literal(True)))
        .where(
            release.c.release_id == selected,
            or_(
                item["outcome"].astext.in_(("unsupported", "unresolved")),
                and_(
                    item["outcome"].astext == "unchecked",
                    ~and_(
                        item["code"].astext == "unchecked_term",
                        item["message"].astext == "not4curation:unchecked",
                    ),
                ),
            ),
        )
        .exists()
    )
    admitted = _decoded_json(admissions.c.content)
    invalid_authored_sql = (
        select(1)
        .select_from(
            inputs.outerjoin(
                admissions,
                and_(
                    admissions.c.release_id == inputs.c.release_id,
                    admissions.c.input_kind == inputs.c.input_kind,
                    admissions.c.input_name == inputs.c.input_name,
                    admissions.c.physical_id == expected["physical_id"].astext,
                ),
            )
        )
        .where(
            inputs.c.release_id == selected,
            inputs.c.input_kind == "dependency",
            func.starts_with(inputs.c.input_name, "authored-sql/"),
            or_(
                func.right(inputs.c.input_name, 4) != ".sql",
                func.length(inputs.c.input_name) <= func.length("authored-sql/.sql"),
                func.encode(func.sha256(inputs.c.content), "hex").is_distinct_from(
                    inputs.c.content_digest
                ),
                admissions.c.release_id.is_(None),
                func.encode(func.sha256(admissions.c.content), "hex").is_distinct_from(
                    admissions.c.content_digest
                ),
                admitted["sql"].astext.is_distinct_from(
                    func.convert_from(inputs.c.content, "UTF8")
                ),
                admitted["release_id"].astext.is_distinct_from(selected),
                admitted["physical_id"].astext.is_distinct_from(expected["physical_id"].astext),
            ),
        )
        .exists()
    )
    return (
        _refuse(rejected_diagnostic, "release contains unresolved or unchecked required semantics"),
        _refuse(
            invalid_authored_sql, "required authored SQL lacks exact current physical admission"
        ),
    )


def _native_constraint_checks(metadata):
    from sqlalchemy import Boolean, and_, literal, union

    artifacts = metadata.tables["sem.artifact"]
    classes = metadata.tables["sem.class_definition"]
    applicability = metadata.tables["sem.property_applicability"]
    hierarchy = metadata.tables["sem.class_hierarchy"]
    selected = core_variable("r", Text())
    native, model = artifacts.alias("native"), artifacts.alias("model")
    native_value, model_value = _decoded_json(native.c.content), _decoded_json(model.c.content)
    descriptor = cast(func.sem.data_operation_native_descriptor(), JSONB())
    archived = (
        select(native_value.label("projection"), model_value.label("model"))
        .select_from(
            native.join(
                model,
                and_(
                    model.c.release_id == native.c.release_id,
                    model.c.artifact_name == "data_operations.json",
                ),
            )
        )
        .where(
            native.c.release_id == selected,
            native.c.artifact_name == "data_operation_native_definitions.json",
            native_value["model_digest"].astext == func.encode(func.sha256(model.c.content), "hex"),
            native_value["native_digest"].astext == descriptor["source_digest"].astext,
        )
        .cte("archived_native_constraint_projection")
    )
    projected = _json_items(archived.c.projection["kinds"], "projected_kind")
    declared = _json_items(archived.c.model["kinds"], "declared_kind")
    roots = (
        select(classes.c.class_id)
        .select_from(
            archived.join(projected, literal(True)).join(
                classes,
                and_(
                    classes.c.release_id == selected,
                    classes.c.class_id == projected.c.value["kind"].astext,
                ),
            )
        )
        .where(
            select(1)
            .select_from(declared)
            .where(
                declared.c.value["semantic_id"].astext == classes.c.class_id,
                declared.c.value["category"].astext == "class",
            )
            .correlate(archived, classes)
            .exists()
        )
        .cte("native_constraint_json_roots")
    )
    edges = union(
        select(applicability.c.class_id.label("source"), classes.c.class_id.label("target"))
        .select_from(
            applicability.join(
                classes,
                and_(
                    classes.c.release_id == applicability.c.release_id,
                    classes.c.name == applicability.c.range_name,
                ),
            )
        )
        .where(
            applicability.c.release_id == selected,
            func.coalesce(cast(applicability.c.constraints["inlined"].astext, Boolean()), False),
        ),
        select(hierarchy.c.class_id, hierarchy.c.ancestor_id).where(
            hierarchy.c.release_id == selected
        ),
    ).cte("native_constraint_json_edges")
    owned = select(roots.c.class_id).cte("native_constraint_json_classes", recursive=True)
    owned = owned.union(
        select(edges.c.target).select_from(owned.join(edges, edges.c.source == owned.c.class_id))
    )
    empty = cast(literal("[]"), JSONB())
    null_value = cast(literal("null"), JSONB())
    invalid = (
        select(1)
        .select_from(applicability)
        .where(
            applicability.c.release_id == selected,
            or_(
                applicability.c.constraint_scope.not_in(("shape", "accepted_value")),
                and_(
                    or_(
                        applicability.c.constraints["pattern"].astext.is_not(None),
                        func.coalesce(applicability.c.constraints["patterns"], empty).not_in(
                            (empty, null_value)
                        ),
                    ),
                    ~and_(
                        applicability.c.constraint_scope == "shape",
                        applicability.c.class_id.in_(select(owned.c.class_id)),
                    ),
                ),
            ),
        )
        .exists()
    )
    missing_projection = and_(
        ~select(1).select_from(archived).exists(),
        select(1)
        .select_from(artifacts)
        .where(
            artifacts.c.release_id == selected, artifacts.c.artifact_name == "data_operations.json"
        )
        .exists(),
    )
    return If(
        invalid,
        (
            _refuse(
                missing_projection,
                "archived DDO native constraint projection is missing or incompatible with installed descriptor",
            ),
            Raise("unsupported required native constraint scope or pattern", "23514"),
        ),
    )


def _native_inference_check(metadata):
    from sqlalchemy import Boolean, and_, case, column, literal, union_all, values

    registry = metadata.tables["sem.registry_row"]
    applicability = metadata.tables["sem.property_applicability"]
    classes = metadata.tables["sem.class_definition"]
    hierarchy = metadata.tables["sem.class_hierarchy"]
    selected = core_variable("r", Text())
    rules = (
        select(_decoded_json(registry.c.body).label("rule"))
        .where(
            registry.c.release_id == selected,
            registry.c.kind == "inference_rule",
        )
        .cte("admitted_inference_rules")
    )
    signatures = select(
        rules.c.rule["kind"].astext.label("kind"),
        rules.c.rule["predicate"].astext.label("predicate"),
        func.coalesce(
            func.nullif(rules.c.rule["target"].astext, ""), rules.c.rule["predicate"].astext
        ).label("target"),
    ).cte("admitted_inference_signatures")
    source_range = classes.alias("source_range")
    target_range = classes.alias("target_range")
    target = applicability.alias("target")
    inverse = applicability.alias("inverse")

    def declared_property(identity):
        return (
            select(1)
            .select_from(applicability)
            .where(applicability.c.release_id == selected, applicability.c.property_id == identity)
            .exists()
        )

    malformed = (
        select(literal(1).label("invalid"))
        .select_from(signatures)
        .where(
            or_(
                signatures.c.kind.is_(None),
                signatures.c.predicate.is_(None),
                signatures.c.target.is_(None),
                signatures.c.kind.not_in(("inverse", "symmetric", "transitive", "subproperty")),
                ~declared_property(signatures.c.predicate),
                ~declared_property(signatures.c.target),
            )
        )
    )
    expected_range = case(
        (signatures.c.kind.in_(("subproperty", "transitive")), source_range.c.class_id),
        else_=applicability.c.class_id,
    )
    incompatible = (
        select(literal(1))
        .select_from(
            signatures.join(
                applicability,
                and_(
                    applicability.c.release_id == selected,
                    applicability.c.property_id == signatures.c.predicate,
                ),
            )
            .outerjoin(
                source_range,
                and_(
                    source_range.c.release_id == selected,
                    source_range.c.name == applicability.c.range_name,
                ),
            )
            .outerjoin(
                target,
                and_(
                    target.c.release_id == selected,
                    target.c.property_id == signatures.c.target,
                    target.c.class_id
                    == case(
                        (signatures.c.kind == "subproperty", applicability.c.class_id),
                        else_=source_range.c.class_id,
                    ),
                ),
            )
            .outerjoin(
                target_range,
                and_(
                    target_range.c.release_id == selected,
                    target_range.c.name == target.c.range_name,
                ),
            )
        )
        .where(
            or_(
                func.coalesce(
                    cast(applicability.c.constraints["inlined"].astext, Boolean()), False
                ),
                source_range.c.class_id.is_(None),
                target.c.property_id.is_(None),
                func.coalesce(cast(target.c.constraints["inlined"].astext, Boolean()), False),
                target_range.c.class_id.is_(None),
                ~or_(
                    target_range.c.class_id == expected_range,
                    select(1)
                    .select_from(hierarchy)
                    .where(
                        hierarchy.c.release_id == selected,
                        hierarchy.c.ancestor_id == target_range.c.class_id,
                        hierarchy.c.class_id == expected_range,
                    )
                    .correlate(signatures, applicability, source_range, target_range)
                    .exists(),
                ),
            )
        )
    )
    flags = (
        values(column("name", Text()))
        .data([("symmetric",), ("transitive",)])
        .alias("inference_flag")
    )
    missing_flag = (
        select(literal(1))
        .select_from(applicability.join(flags, literal(True)))
        .where(
            applicability.c.release_id == selected,
            func.coalesce(cast(applicability.c.constraints[flags.c.name].astext, Boolean()), False),
            ~select(1)
            .select_from(signatures)
            .where(
                signatures.c.kind == flags.c.name,
                signatures.c.predicate == applicability.c.property_id,
                signatures.c.target == applicability.c.property_id,
            )
            .correlate(applicability, flags)
            .exists(),
        )
    )
    inverse_target = (
        select(
            func.count(inverse.c.property_id.distinct()).label("count"),
            func.min(inverse.c.property_id).label("target"),
        )
        .where(
            inverse.c.release_id == selected,
            or_(
                inverse.c.property_id == applicability.c.constraints["inverse"].astext,
                inverse.c.constraints["name"].astext
                == applicability.c.constraints["inverse"].astext,
            ),
        )
        .correlate(applicability)
        .lateral("inverse_target")
    )
    missing_inverse = (
        select(literal(1))
        .select_from(applicability.outerjoin(inverse_target, literal(True)))
        .where(
            applicability.c.release_id == selected,
            func.nullif(applicability.c.constraints["inverse"].astext, "").is_not(None),
            or_(
                inverse_target.c.count != 1,
                ~select(1)
                .select_from(signatures)
                .where(
                    signatures.c.kind == "inverse",
                    signatures.c.predicate == applicability.c.property_id,
                    signatures.c.target == inverse_target.c.target,
                )
                .correlate(applicability, inverse_target)
                .exists(),
            ),
        )
    )
    invalid = union_all(malformed, incompatible, missing_flag, missing_inverse).subquery(
        "invalid_native_inference"
    )
    return _refuse(
        select(1).select_from(invalid).exists(),
        "unsupported required native binary inference profile",
    )


def release_semantic_checks(metadata):
    """Interpret release obligations directly from the current typed physical model."""
    from sqlalchemy import and_

    release = metadata.tables["sem.release"]
    registry = metadata.tables["sem.registry_row"]
    artifact = metadata.tables["sem.artifact"]
    selected = core_variable("r", Text())
    return (
        *_release_asset_checks(metadata),
        _native_constraint_checks(metadata),
        _refuse(
            ~select(1)
            .select_from(release)
            .where(release.c.release_id == selected, release.c.profile == "semantic-2")
            .exists(),
            "execution requires a current composed release",
        ),
        _native_inference_check(metadata),
        _refuse(
            ~select(1)
            .select_from(release)
            .where(
                release.c.release_id == selected,
                _decoded_json(release.c.manifest_bytes).has_key("data_operation_model"),
            )
            .exists(),
            "native execution requires the current declared data operation model",
        ),
        _refuse(
            select(1)
            .select_from(registry)
            .where(registry.c.release_id == selected, registry.c.kind == "execution_model")
            .exists(),
            "target archive contains legacy execution model",
        ),
        If(
            select(1)
            .select_from(artifact)
            .where(
                and_(
                    artifact.c.release_id == selected,
                    artifact.c.artifact_name == "operation/scientific-policy.json",
                )
            )
            .exists(),
            (Perform(func.sem.require_scientific_layout(selected)),),
        ),
    )
