"""Captured PDF validation/projection contracts and exact frozen-check witnesses."""

from hashlib import sha256

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Float,
    Numeric,
    Text,
    and_,
    any_,
    cast,
    column,
    exists,
    func,
    literal,
    select,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import BYTEA, DOUBLE_PRECISION, JSONB, array, insert

from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    PerformQuery,
    Raise,
    Return,
    SelectInto,
    Sql,
    column_type,
    core_variable,
    function,
    pg_type,
)


def _equal_rows(model, current, previous, *relations):
    """Compare multisets, preserving JSON/decimal spelling and exact float8 bits."""
    predicates = []
    for name in relations:
        relation = model.tables[name]
        values = []
        for field in relation.columns:
            if field.name in {"product_id", "revision_id"}:
                continue
            if isinstance(field.type, Float):
                value = func.float8send(cast(field, DOUBLE_PRECISION()))
            elif isinstance(field.type, (JSON, Numeric)):
                value = func.convert_to(cast(field, Text()), "UTF8")
            else:
                value = field
            values.append(value)
        current_rows = select(*values).where(
            relation.c.product_id == current, relation.c.revision_id == current
        )
        previous_rows = select(*values).where(
            relation.c.product_id == previous, relation.c.revision_id == previous
        )
        predicates.append(
            ~exists(
                union_all(
                    current_rows.except_all(previous_rows), previous_rows.except_all(current_rows)
                )
            )
        )
    return and_(*predicates)


def pdf_validation_native_programs(model, *, pdf_domain=None):
    """Generate the three installed routines from one captured model/policy basis."""
    from .identity import canonical_bytes
    from .pdf_contracts import (
        _context_from_domain,
        integrated_metadata_policy,
        projection_write_levels,
        trusted_pdf_context,
    )

    context = (
        trusted_pdf_context() if pdf_domain is None else _context_from_domain(None, pdf_domain)
    )
    levels = projection_write_levels(context, model.info["physical_sources"]["pdf-staging.yaml"])
    policy_digest = sha256(canonical_bytes({"allowed_isolation": levels})).hexdigest()
    metadata_digest = sha256(canonical_bytes(integrated_metadata_policy(context))).hexdigest()

    inputs = model.tables["sem.input"]
    build = model.tables["ops.pdf_stage_build"]
    checks = model.tables["ops.pdf_validation_check"]
    published = model.tables["ops.pdf_published_revision"]
    validated = model.tables["ops.pdf_build_validation"]
    frozen = model.tables["ops.pdf_frozen_build"]
    tasks = model.tables["ops.task"]
    episodes = model.tables["ops.data_derivation"]
    project_type = model.tables["ops.data_request"].c.project_id.type

    def value(name, type_=None):
        return core_variable(name, Text() if type_ is None else type_)

    def row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    def routine(name, parameters, result, body, *, stable=False):
        return (
            function(
                "ops",
                name,
                parameters=parameters,
                returns=pg_type(result),
                body=body,
                security_definer=True,
                search_path=("pg_catalog", "pg_temp"),
                volatility="stable" if stable else None,
            )
            + ";\n"
        )

    state, count, length, frame = (
        value("state_", BYTEA()),
        value("count_", BigInteger()),
        value("length_", BigInteger()),
        value("frame_", BYTEA()),
    )
    fold_step = (
        Assign("state_", func.ops.pdf_identity_fold_step(state, count, frame)),
        Assign("count_", count + 1),
        Assign("length_", length + func.octet_length(frame)),
    )
    fold_result = Return(
        func.encode(func.ops.pdf_identity_fold_finish(state, count, length), "hex")
    )

    def fold_locals(domain):
        return (
            Local("item_", pg_type("record")),
            Local("state_", pg_type("bytea"), func.ops.pdf_identity_fold_start(domain)),
            Local("count_", pg_type("bigint"), literal(0)),
            Local("length_", pg_type("bigint"), literal(0)),
            Local("frame_", pg_type("bytea")),
        )

    p_release = value("p_release", inputs.c.release_id.type)
    p_build = value("p_build", build.c.build_id.type)
    dependency_name = row("item_", inputs, "input_name")
    dependency_content = row("item_", inputs, "content")
    dependency_frame = (
        func.int8send(cast(func.octet_length(dependency_name), BigInteger()))
        .op("||")(func.convert_to(dependency_name, "UTF8"))
        .op("||")(func.sha256(dependency_content))
    )
    validation_contract = routine(
        "pdf_validation_contract",
        (Parameter("p_release", column_type(inputs.c.release_id)),),
        "text",
        Block(
            (
                ForQuery(
                    ("item_",),
                    select(inputs.c.input_name, inputs.c.content)
                    .where(inputs.c.release_id == p_release, inputs.c.input_kind == "dependency")
                    .order_by(inputs.c.input_name.collate("C")),
                    (
                        Assign("frame_", dependency_frame),
                        *fold_step,
                    ),
                ),
                If(count == 0, (Raise("PDF validation release dependencies missing", "P0001"),)),
                Assign(
                    "frame_",
                    func.convert_to("pdf-projection-write-profile-v1", "UTF8").op("||")(
                        func.decode(policy_digest, "hex")
                    ),
                ),
                *fold_step,
                Assign(
                    "frame_",
                    func.convert_to("pdf-integrated-metadata-policy-v1", "UTF8").op("||")(
                        func.decode(metadata_digest, "hex")
                    ),
                ),
                *fold_step,
                fold_result,
            ),
            fold_locals("pdf-validation-contract-v5"),
        ),
        stable=True,
    )

    projections = []
    for family in ("access", "region"):
        relation = model.tables["kb.pdf_record_" + family].alias("r")
        body = (
            cast(func.to_jsonb(relation.table_valued()), JSONB())
            .op("-")(literal("product_id"))
            .op("-")(literal("revision_id"))
        )
        projections.append(
            select(
                literal(family).label("family"), func.data.canonical_json(body).label("body")
            ).where(relation.c.product_id == p_build, relation.c.revision_id == p_build)
        )
    rows = union_all(*projections).subquery("rows_")
    projection_contract = routine(
        "pdf_projection_contract",
        (
            Parameter("p_build", column_type(build.c.build_id)),
            Parameter("p_release", column_type(inputs.c.release_id)),
        ),
        "text",
        Block(
            (
                Assign("frame_", func.decode(func.ops.pdf_validation_contract(p_release), "hex")),
                *fold_step,
                ForQuery(
                    ("item_",),
                    select(rows).order_by(rows.c.family.collate("C"), rows.c.body.collate("C")),
                    (
                        Assign(
                            "frame_",
                            func.convert_to(core_variable("item_", Text(), "family"), "UTF8").op(
                                "||"
                            )(
                                func.sha256(
                                    func.convert_to(core_variable("item_", Text(), "body"), "UTF8")
                                )
                            ),
                        ),
                        *fold_step,
                    ),
                ),
                fold_result,
            ),
            fold_locals("pdf-validation-projection-v1"),
        ),
        stable=True,
    )

    p_task = value("p_task", build.c.task_id.type)
    p_attempt = value("p_attempt", build.c.attempt.type)
    p_holder = value("p_holder", build.c.holder.type)
    p_frozen = value("p_frozen", frozen.c.frozen_digest.type)
    p_check = value("p_check", checks.c.check_name.type)
    contract, result, prior, reused = (
        value(name) for name in ("contract_", "result_", "prior_", "reused_")
    )
    fence_args = (p_build, p_task, p_attempt, p_holder, p_frozen)
    require_owner = Perform(func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder))
    require_frozen = func.ops.require_pdf_frozen(*fence_args)
    exact_check = and_(
        checks.c.build_id == p_build,
        checks.c.attempt == p_attempt,
        checks.c.holder == p_holder,
        checks.c.frozen_digest == p_frozen,
        checks.c.contract_digest == contract,
    )
    task_context = func.ops.pdf_task_context(row("b", build, "task_id")).table_valued(
        column("project_id", project_type)
    )
    project = select(task_context.c.project_id).scalar_subquery()
    previous_context = (
        func.ops.pdf_task_context(tasks.c.id)
        .table_valued(column("project_id", project_type))
        .lateral("previous_context")
    )
    prior_build = (
        select(published.c.build_id)
        .select_from(
            published.join(
                validated,
                and_(
                    validated.c.build_id == published.c.build_id,
                    validated.c.frozen_digest == published.c.frozen_digest,
                    validated.c.logical_digest == published.c.logical_digest,
                    validated.c.native_contract_digest == contract,
                    validated.c.native_callbacks,
                ),
            )
            .join(tasks, tasks.c.id == published.c.task_id)
            .join(previous_context, true())
            .join(frozen, and_(frozen.c.build_id == p_build, frozen.c.kind == published.c.kind))
        )
        .where(
            exists(
                select(1)
                .select_from(episodes)
                .where(
                    episodes.c.producer_task_id == tasks.c.id,
                    func.ops.ddo_node_valid("episode", episodes.c.id),
                )
            ),
            *(
                published.c[name] == row("b", build, name)
                for name in ("source_digest", "schema_digest", "recipe_digest", "release_id")
            ),
            previous_context.c.project_id == project,
        )
        .order_by(tasks.c.id.desc())
        .limit(1)
    )
    access_equal = _equal_rows(
        model, p_build, prior, "kb.pdf_record_access", "kb.pdf_record_region"
    )
    native_equal = _equal_rows(
        model,
        p_build,
        prior,
        "ops.pdf_record_document",
        "kb.pdf_record_native",
        "kb.pdf_record_membership",
        "ops.pdf_artifact_stream",
    )
    no_other_revision = and_(
        *(
            ~exists(
                select(1)
                .select_from(model.tables[name])
                .where(
                    model.tables[name].c.product_id == p_build,
                    model.tables[name].c.revision_id != p_build,
                )
            )
            for name in ("kb.pdf_record_access", "kb.pdf_record_region")
        )
    )
    certification = func.ops.read_pdf_certification_requirement(*fence_args).table_valued(
        column("oracle_receipt_id", Text())
    )
    dispatch = If(
        p_check == "inventory",
        (
            Perform(
                func.ops.pdf_check_build_inventory(
                    p_build, row("b", build, "source_digest"), project
                )
            ),
        ),
        (
            If(
                p_check == "access",
                (
                    If(
                        and_(prior.is_not(None), access_equal, native_equal, no_other_revision),
                        (Assign("reused_", prior),),
                        (Perform(func.ops.pdf_check_access_correspondence(p_build)),),
                    ),
                ),
                (
                    If(
                        p_check == "identity",
                        (
                            Assign(
                                "result_", func.ops.pdf_record_logical_identity(p_build, p_build)
                            ),
                        ),
                        (
                            If(
                                p_check == "projection",
                                (
                                    If(
                                        and_(prior.is_not(None), access_equal),
                                        (
                                            SelectInto(
                                                select(validated.c.contract_digest).where(
                                                    validated.c.build_id == prior,
                                                    validated.c.native_contract_digest == contract,
                                                ),
                                                ("result_",),
                                                True,
                                            ),
                                            Assign("reused_", prior),
                                        ),
                                        (
                                            Assign(
                                                "result_",
                                                func.ops.pdf_projection_contract(
                                                    p_build, row("b", build, "release_id")
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                                (Raise("unknown frozen PDF check", "23514"),),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    check_program = routine(
        "check_pdf_build",
        tuple(
            Parameter(name, column_type(source))
            for name, source in (
                ("p_build", build.c.build_id),
                ("p_task", build.c.task_id),
                ("p_attempt", build.c.attempt),
                ("p_holder", build.c.holder),
                ("p_frozen", frozen.c.frozen_digest),
                ("p_check", checks.c.check_name),
            )
        ),
        "void",
        Block(
            (
                If(
                    ~(
                        func.current_setting("transaction_isolation")
                        == any_(array(levels, type_=Text()))
                    ),
                    (
                        Raise(
                            "PDF projection admission requires " + ", ".join(levels).upper(),
                            "25000",
                        ),
                    ),
                ),
                If(
                    p_check == "seal",
                    (
                        require_owner,
                        PerformQuery(
                            select(literal(1))
                            .select_from(build)
                            .where(build.c.build_id == p_build)
                            .with_for_update(key_share=True)
                        ),
                    ),
                ),
                Assign("b", require_frozen),
                Perform(
                    func.ops.require_pdf_operation(
                        row("b", build, "release_id"), "validate_pdf_build"
                    )
                ),
                If(
                    row("b", build, "state") != "frozen",
                    (Raise("PDF check requires a frozen private build", "P0001"),),
                ),
                Assign(
                    "contract_", func.ops.pdf_validation_contract(row("b", build, "release_id"))
                ),
                If(
                    p_check == "seal",
                    (
                        If(
                            ~exists(
                                select(1)
                                .select_from(certification)
                                .where(certification.c.oracle_receipt_id.is_not(None))
                            ),
                            (Raise("PDF lowering has no passed round-trip oracle", "23514"),),
                        ),
                        If(
                            exists(
                                select(1)
                                .select_from(checks)
                                .where(exact_check, checks.c.check_name == "seal")
                            ),
                            (Return(),),
                        ),
                        SelectInto(prior_build, ("reused_",)),
                    ),
                    (
                        SelectInto(
                            select(checks.c.predecessor_build_id).where(
                                exact_check, checks.c.check_name == "seal"
                            ),
                            ("prior_",),
                        ),
                        If(
                            ~value("found", Boolean()),
                            (Raise("PDF projection seal missing or stale", "23514"),),
                        ),
                        If(
                            exists(
                                select(1)
                                .select_from(checks)
                                .where(exact_check, checks.c.check_name == p_check)
                            ),
                            (Return(),),
                        ),
                        dispatch,
                    ),
                ),
                If(p_check != "seal", (require_owner,)),
                Perform(require_frozen),
                Sql(
                    insert(checks)
                    .values(
                        build_id=p_build,
                        attempt=p_attempt,
                        holder=p_holder,
                        frozen_digest=p_frozen,
                        contract_digest=contract,
                        check_name=p_check,
                        result_digest=result,
                        predecessor_build_id=reused,
                    )
                    .on_conflict_do_nothing()
                ),
                If(
                    ~exists(
                        select(1)
                        .select_from(checks)
                        .where(
                            exact_check,
                            checks.c.check_name == p_check,
                            checks.c.result_digest == result,
                            checks.c.predecessor_build_id.is_not_distinct_from(reused),
                        )
                    ),
                    (Raise("PDF check result differs for sealed premises", "23514"),),
                ),
            ),
            (
                Local("b", build),
                Local("contract_", pg_type("text")),
                Local("result_", pg_type("text"), literal("")),
                Local("prior_", pg_type("text")),
                Local("reused_", pg_type("text")),
            ),
        ),
    )
    return {
        "validation_contract": validation_contract,
        "projection_contract": projection_contract,
        "check_build": check_program,
    }
