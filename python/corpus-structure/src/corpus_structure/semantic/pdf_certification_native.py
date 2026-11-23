"""Model-owned native producer attestation and reconstruction oracle custody."""

from corpus_structure.ingest._pdf_producer_profiles import (
    DEMAND_LOWERING,
    STANDARD_LOWERING,
    STANDARD_SCOPE,
)
from corpus_structure.schema.integrity import role_name

from .native_objects import (
    INTERNAL_PROGRAM,
    NativeProgramAccess,
    native_privilege_sql,
    native_sql_script,
)
from .native_program_registry import ProgramDeclaration
from .pdf_domain import PREFIX
from .pdf_lowering import (
    CAPTURE_LOWERING_CODE,
    CAPTURE_LOWERING_CONTRACT,
    LOWERING_CODE,
)
from .pdf_spool_native import PDF_CAPTURE_OPERATION, pdf_task_operation


def pdf_certification_native_programs(*, target_metadata=None) -> tuple[ProgramDeclaration, ...]:
    from sqlalchemy import (
        BigInteger,
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
    from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, array, insert

    from .metadata import get_metadata
    from .native_program import (
        Assign,
        Block,
        ForQuery,
        If,
        Local,
        NativeRoutine,
        Parameter,
        Perform,
        Raise,
        Return,
        ReturnQuery,
        SelectInto,
        Sql,
        column_type,
        core_variable,
        pg_type,
    )
    from .native_program import literal as pg_literal

    model = get_metadata() if target_metadata is None else target_metadata
    build = model.tables["ops.pdf_stage_build"]
    stream = model.tables["ops.pdf_artifact_stream"]
    certification = model.tables["ops.pdf_producer_certification"]
    oracle = model.tables["ops.pdf_roundtrip_oracle"]
    frozen = model.tables["ops.pdf_frozen_build"]
    published = model.tables["ops.pdf_published_revision"]
    validation = model.tables["ops.pdf_build_validation"]

    def value(name, type_=None):
        return core_variable(name, Text() if type_ is None else type_)

    def row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    p_build = value("p_build", build.c.build_id.type)
    p_task = value("p_task", build.c.task_id.type)
    p_attempt = value("p_attempt", build.c.attempt.type)
    p_holder = value("p_holder", build.c.holder.type)
    p_frozen = value("p_frozen", frozen.c.frozen_digest.type)
    fence = tuple(
        Parameter(name, column_type(source))
        for name, source in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
        )
    )
    frozen_fence = (*fence, Parameter("p_frozen", column_type(frozen.c.frozen_digest)))
    build_local = Local("b", build)
    require_build = Assign("b", func.ops.require_pdf_build(p_build, p_task, p_attempt, p_holder))
    require_frozen = Assign(
        "b", func.ops.require_pdf_frozen(p_build, p_task, p_attempt, p_holder, p_frozen)
    )

    def routine(
        name,
        parameters,
        returns,
        statements,
        locals_,
        *,
        stable=False,
        definer=True,
        writer=True,
        output=(),
    ):
        return ProgramDeclaration(
            NativeRoutine(
                "ops",
                name,
                parameters,
                returns,
                Block(tuple(statements), tuple(locals_)),
                table_columns=tuple((field, column_type(source)) for field, source in output),
                security_definer=definer,
                search_path=("pg_catalog", "pg_temp"),
                volatility="stable" if stable else None,
            ),
            "authoring/pdf-certification.sql",
            role_name("publisher"),
            NativeProgramAccess(purposes=("write",)) if writer else INTERNAL_PROGRAM,
        )

    out = []
    content, contract, item, contract_name = (
        value("content_", BYTEA()),
        value("contract_", JSONB()),
        value("item_", JSONB()),
        value("contract_name_"),
    )
    profile = contract["profile"].astext
    selected_standard = profile == STANDARD_LOWERING
    origin_task = value("p_origin_task", build.c.task_id.type)
    release = value("p_release")
    scoped_capture = contract_name == CAPTURE_LOWERING_CONTRACT
    expected_code = case(
        (scoped_capture, literal(PREFIX + CAPTURE_LOWERING_CODE)),
        else_=literal(PREFIX + LOWERING_CODE),
    )
    code = contract["code_identity"]
    complete = cast(literal("true"), JSONB())
    inputs = func.jsonb_array_elements(contract["inputs"]).table_valued(column("value", JSONB()))
    out.append(
        routine(
            "pdf_lowering_identity",
            (
                Parameter("p_release", pg_type("text")),
                Parameter("p_origin_task", column_type(build.c.task_id), pg_literal(None)),
            ),
            pg_type("text"),
            (
                Assign("contract_name_", func.ops.pdf_lowering_contract_name(release, origin_task)),
                Assign(
                    "content_",
                    func.ops.pdf_contract_input(release, contract_name),
                ),
                Assign("contract_", cast(func.convert_from(content, "UTF8"), JSONB())),
                If(
                    or_(
                        and_(
                            ~scoped_capture,
                            profile.is_distinct_from(DEMAND_LOWERING),
                            or_(
                                profile.is_distinct_from(STANDARD_LOWERING),
                                pdf_task_operation(model, release, origin_task).is_distinct_from(
                                    PDF_CAPTURE_OPERATION
                                ),
                            ),
                        ),
                        and_(scoped_capture, profile.is_distinct_from(STANDARD_LOWERING)),
                        and_(
                            selected_standard,
                            or_(
                                code["scope"].astext.is_distinct_from(STANDARD_SCOPE),
                                code["complete"].is_distinct_from(complete),
                            ),
                        ),
                        func.jsonb_typeof(code["complete"]).is_distinct_from("boolean"),
                        and_(
                            code["complete"] == complete,
                            func.coalesce(code["sha256"].astext, "").bool_op("!~")(
                                "^[0-9a-f]{64}$"
                            ),
                        ),
                        and_(
                            code["complete"] == cast(literal("false"), JSONB()),
                            # The code owner emits no reusable meaning digest
                            # for incomplete capture. The full retained contract
                            # and each captured input still authenticate this
                            # producer's exact attribution below.
                            code["sha256"].is_distinct_from(cast(literal("null"), JSONB())),
                        ),
                        func.jsonb_typeof(contract["inputs"]).is_distinct_from("array"),
                        func.jsonb_typeof(contract["libraries"]).is_distinct_from("object"),
                        contract["libraries"] == cast(literal("{}"), JSONB()),
                    ),
                    (Raise("unsupported released PDF lowering contract", "23514"),),
                ),
                If(
                    func.jsonb_array_length(contract["inputs"]) == 0,
                    (Raise("released PDF lowering has no captured inputs", "23514"),),
                ),
                If(
                    and_(
                        selected_standard,
                        ~select(1)
                        .select_from(inputs)
                        .where(
                            inputs.c.value["name"].astext == expected_code,
                            inputs.c.value["sha256"].astext == code["sha256"].astext,
                        )
                        .exists(),
                    ),
                    (
                        Raise(
                            "selected PDF producer identity differs from its captured code", "23514"
                        ),
                    ),
                ),
                ForQuery(
                    ("item_",),
                    select(inputs.c.value),
                    (
                        If(
                            or_(
                                func.left(item["name"].astext, 11) != "pdf-domain/",
                                func.encode(
                                    func.sha256(
                                        func.ops.pdf_contract_input(
                                            release, func.substr(item["name"].astext, 12)
                                        )
                                    ),
                                    "hex",
                                ).is_distinct_from(item["sha256"].astext),
                            ),
                            (
                                Raise(
                                    "released PDF lowering source/codec/schema custody differs",
                                    "23514",
                                ),
                            ),
                        ),
                    ),
                ),
                Return(func.encode(func.sha256(content), "hex")),
            ),
            (
                Local("content_", pg_type("bytea")),
                Local("contract_", pg_type("jsonb")),
                Local("item_", pg_type("jsonb")),
                Local("contract_name_", pg_type("text")),
            ),
            stable=True,
            writer=False,
        )
    )

    state, frame = value("state_", BYTEA()), value("frame_", BYTEA())
    count, total = value("count_", BigInteger()), value("total_", BigInteger())
    serialization = row("row_", stream, "serialization_sha256")
    frame_values = (
        func.ops.pdf_identity_scalar(
            "i", func.convert_to(cast(row("row_", stream, "byte_length"), Text()), "UTF8")
        ),
        func.ops.pdf_identity_scalar(
            "s", func.convert_to(row("row_", stream, "byte_root"), "UTF8")
        ),
        func.ops.pdf_identity_scalar(
            "s", func.convert_to(row("row_", stream, "encoding_profile"), "UTF8")
        ),
        case(
            (
                serialization.is_(None),
                func.ops.pdf_identity_scalar("n", cast(literal(""), BYTEA())),
            ),
            else_=func.ops.pdf_identity_scalar("s", func.convert_to(serialization, "UTF8")),
        ),
    )
    out.append(
        routine(
            "pdf_producer_stream_identity",
            (
                Parameter("p_build", column_type(build.c.build_id)),
                Parameter("p_schema", pg_type("text")),
            ),
            pg_type("text"),
            (
                ForQuery(
                    ("row_",),
                    select(stream)
                    .where(stream.c.product_id == p_build, stream.c.revision_id == p_build)
                    .order_by(stream.c.stream_id.collate("C")),
                    (
                        Assign(
                            "frame_",
                            func.ops.pdf_identity_record_frame(
                                value("p_schema"),
                                "producer-stream",
                                row("row_", stream, "stream_id"),
                                array(
                                    [
                                        "byte_length",
                                        "byte_root",
                                        "encoding_profile",
                                        "serialization_sha256",
                                    ],
                                    type_=Text(),
                                ),
                                array(frame_values).cast(ARRAY(BYTEA())),
                            ),
                        ),
                        Assign("state_", func.ops.pdf_identity_fold_step(state, count, frame)),
                        Assign("count_", count + 1),
                        Assign("total_", total + func.octet_length(frame)),
                    ),
                ),
                Return(func.encode(func.ops.pdf_identity_fold_finish(state, count, total), "hex")),
            ),
            (
                Local("row_", stream),
                Local(
                    "state_",
                    pg_type("bytea"),
                    func.ops.pdf_identity_fold_start("pdf-producer-streams-v1"),
                ),
                Local("frame_", pg_type("bytea")),
                Local("count_", pg_type("bigint"), literal(0)),
                Local("total_", pg_type("bigint"), literal(0)),
            ),
            stable=True,
            definer=False,
            writer=False,
        )
    )

    input_fields = {
        "p_lowering": "lowering_identity",
        "p_kind": "kind",
        "p_logical": "logical_digest",
        "p_native": "native_document_digest",
        "p_streams": "stream_inventory_digest",
    }
    p = {name: value(name, certification.c[field].type) for name, field in input_fields.items()}
    certification_values = {
        certification.c.build_id: p_build,
        certification.c.attempt: p_attempt,
        certification.c.holder: p_holder,
        **{certification.c[field]: p[name] for name, field in input_fields.items()},
        **{
            certification.c[field]: row("b", build, field)
            for field in ("source_digest", "recipe_digest", "schema_digest")
        },
    }
    certification_match = and_(
        certification.c.build_id == p_build,
        *(certification.c[field] == p[name] for name, field in input_fields.items()),
        *(
            certification.c[field] == row("b", build, field)
            for field in ("source_digest", "recipe_digest", "schema_digest")
        ),
    )
    out.append(
        routine(
            "record_pdf_producer_certification",
            (
                *fence,
                *(
                    Parameter(name, column_type(certification.c[field]))
                    for name, field in input_fields.items()
                ),
            ),
            pg_type("void"),
            (
                require_build,
                Perform(
                    func.ops.require_pdf_operation(
                        row("b", build, "release_id"), "stage_pdf_producer"
                    )
                ),
                If(
                    or_(
                        p["p_lowering"].is_distinct_from(
                            func.ops.pdf_lowering_identity(row("b", build, "release_id"), p_task)
                        ),
                        p["p_kind"].is_(None),
                        p["p_kind"].not_in(("native", "integrated")),
                        *(
                            func.coalesce(p[name], "").op("!~")("^[0-9a-f]{64}$")
                            for name in ("p_logical", "p_native", "p_streams")
                        ),
                    ),
                    (Raise("PDF producer certification basis differs", "23514"),),
                ),
                Sql(insert(certification).values(certification_values).on_conflict_do_nothing()),
                If(
                    ~exists(select(1).select_from(certification).where(certification_match)),
                    (Raise("changed PDF producer certification", "23514"),),
                ),
            ),
            (build_local,),
        )
    )

    c = {
        field: row("c", certification, field)
        for field in (column_.name for column_ in certification.c)
    }
    current_oracle = (
        select(oracle.c.oracle_receipt_id)
        .where(
            oracle.c.build_id == p_build,
            oracle.c.frozen_digest == p_frozen,
            oracle.c.lowering_identity == c["lowering_identity"],
            oracle.c.kind == c["kind"],
            oracle.c.logical_digest == c["logical_digest"],
            oracle.c.native_document_digest == c["native_document_digest"],
            oracle.c.state == "passed",
        )
        .order_by(oracle.c.oracle_receipt_id)
        .limit(1)
    )
    prior_build = build.alias("prior_build")
    build_release = row("b", build, "release_id")
    current_lowering = cast(
        func.convert_from(
            func.ops.pdf_contract_input(
                build_release, func.ops.pdf_lowering_contract_name(build_release, p_task)
            ),
            "UTF8",
        ),
        JSONB(),
    )
    prior_oracle = (
        select(oracle.c.oracle_receipt_id)
        .select_from(
            oracle.join(
                published,
                and_(
                    published.c.build_id == oracle.c.build_id,
                    published.c.frozen_digest == oracle.c.frozen_digest,
                    published.c.logical_digest == oracle.c.logical_digest,
                    published.c.kind == oracle.c.kind,
                ),
            )
            .join(
                validation,
                and_(
                    validation.c.build_id == published.c.build_id,
                    validation.c.frozen_digest == published.c.frozen_digest,
                    validation.c.logical_digest == published.c.logical_digest,
                    validation.c.oracle_receipt_id == oracle.c.oracle_receipt_id,
                ),
            )
            .join(
                prior_build,
                prior_build.c.build_id == oracle.c.build_id,
            )
        )
        .where(
            oracle.c.lowering_identity == c["lowering_identity"],
            # Exact attribution permits incomplete code capture for this build.
            # Reusing another producer's oracle requires a complete shared code
            # basis and authenticated archived inputs for that original release.
            current_lowering["code_identity"]["complete"] == cast(literal("true"), JSONB()),
            func.ops.pdf_lowering_identity(prior_build.c.release_id, prior_build.c.task_id)
            == c["lowering_identity"],
            oracle.c.kind == c["kind"],
            oracle.c.state == "passed",
        )
        .order_by(oracle.c.oracle_receipt_id)
        .limit(1)
    )
    requirement_type = pg_type("record")
    requirement_type.setof = True
    output = (
        *(
            (field, certification.c[field])
            for field in ("lowering_identity", "kind", "logical_digest", "native_document_digest")
        ),
        ("oracle_receipt_id", oracle.c.oracle_receipt_id),
        ("certification_basis", oracle.c.state),
    )
    out.append(
        routine(
            "read_pdf_certification_requirement",
            frozen_fence,
            requirement_type,
            (
                require_frozen,
                SelectInto(
                    select(certification).where(certification.c.build_id == p_build), ("c",), True
                ),
                If(
                    or_(
                        c["lowering_identity"].is_distinct_from(
                            func.ops.pdf_lowering_identity(build_release, p_task)
                        ),
                        tuple_(
                            *(
                                c[field]
                                for field in (
                                    "source_digest",
                                    "recipe_digest",
                                    "schema_digest",
                                    "kind",
                                )
                            )
                        ).is_distinct_from(
                            tuple_(
                                *(
                                    row("b", build, field)
                                    for field in ("source_digest", "recipe_digest", "schema_digest")
                                ),
                                select(frozen.c.kind)
                                .where(frozen.c.build_id == p_build)
                                .scalar_subquery(),
                            )
                        ),
                    ),
                    (Raise("frozen PDF producer certification differs", "23514"),),
                ),
                SelectInto(current_oracle, ("oracle_",)),
                Assign("basis_", literal("round-trip-verified")),
                If(
                    value("oracle_").is_(None),
                    (
                        SelectInto(prior_oracle, ("oracle_",)),
                        Assign("basis_", literal("producer-certified")),
                    ),
                ),
                ReturnQuery(
                    select(
                        *(
                            c[field]
                            for field in (
                                "lowering_identity",
                                "kind",
                                "logical_digest",
                                "native_document_digest",
                            )
                        ),
                        value("oracle_"),
                        value("basis_"),
                    )
                ),
            ),
            (
                build_local,
                Local("c", certification),
                Local("oracle_", pg_type("text")),
                Local("basis_", pg_type("text")),
            ),
            output=output,
        )
    )

    required = func.ops.read_pdf_certification_requirement(
        p_build, p_task, p_attempt, p_holder, p_frozen
    ).table_valued(*(column(field, source.type) for field, source in output))
    out.append(
        routine(
            "begin_pdf_roundtrip_oracle",
            frozen_fence,
            pg_type("text"),
            (
                Perform(func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder)),
                SelectInto(
                    select(build.c.build_id)
                    .where(build.c.build_id == p_build)
                    .with_for_update(key_share=True),
                    ("locked_build",),
                ),
                require_frozen,
                SelectInto(select(required), ("c",), True),
                SelectInto(
                    select(func.count()).select_from(oracle).where(oracle.c.build_id == p_build),
                    ("index_",),
                ),
                Assign(
                    "id_",
                    func.encode(
                        func.sha256(
                            func.convert_to(
                                cast(
                                    func.jsonb_build_array(
                                        p_build,
                                        p_frozen,
                                        core_variable(
                                            "c",
                                            certification.c.lowering_identity.type,
                                            "lowering_identity",
                                        ),
                                        p_attempt,
                                        p_holder,
                                        value("index_", BigInteger()),
                                    ),
                                    Text(),
                                ),
                                "UTF8",
                            )
                        ),
                        "hex",
                    ),
                ),
                Sql(
                    insert(oracle).values(
                        {
                            oracle.c.oracle_receipt_id: value("id_"),
                            oracle.c.build_id: p_build,
                            oracle.c.attempt: p_attempt,
                            oracle.c.holder: p_holder,
                            oracle.c.frozen_digest: p_frozen,
                            **{
                                oracle.c[field]: core_variable(
                                    "c", certification.c[field].type, field
                                )
                                for field in (
                                    "lowering_identity",
                                    "kind",
                                    "logical_digest",
                                    "native_document_digest",
                                )
                            },
                            oracle.c.state: "running",
                        }
                    )
                ),
                Return(value("id_")),
            ),
            (
                build_local,
                Local("c", pg_type("record")),
                Local("locked_build", pg_type("text")),
                Local("index_", pg_type("bigint")),
                Local("id_", pg_type("text")),
            ),
        )
    )

    p_oracle, p_state, p_actual, p_error = (
        value(name) for name in ("p_oracle", "p_state", "p_actual", "p_error")
    )
    o = {field: row("o", oracle, field) for field in (column_.name for column_ in oracle.c)}
    out.append(
        routine(
            "finish_pdf_roundtrip_oracle",
            (
                *frozen_fence,
                *(
                    Parameter(name, pg_type("text"))
                    for name in ("p_oracle", "p_state", "p_actual", "p_error")
                ),
            ),
            pg_type("void"),
            (
                require_frozen,
                SelectInto(
                    select(oracle).where(oracle.c.oracle_receipt_id == p_oracle).with_for_update(),
                    ("o",),
                    True,
                ),
                If(
                    or_(
                        tuple_(
                            *(
                                o[field]
                                for field in ("build_id", "attempt", "holder", "frozen_digest")
                            )
                        ).is_distinct_from(tuple_(p_build, p_attempt, p_holder, p_frozen)),
                        p_state.not_in(("passed", "failed", "interrupted")),
                        p_state.is_(None),
                        and_(
                            p_state == "passed",
                            or_(
                                p_actual.is_distinct_from(o["native_document_digest"]),
                                p_error.is_not(None),
                            ),
                        ),
                        and_(p_state != "passed", func.nullif(p_error, "").is_(None)),
                    ),
                    (
                        Raise(
                            "PDF round-trip oracle result differs from original producer", "23514"
                        ),
                    ),
                ),
                If(
                    o["state"] != "running",
                    (
                        If(
                            tuple_(
                                o["state"], o["actual_native_digest"], o["error_message"]
                            ).is_not_distinct_from(tuple_(p_state, p_actual, p_error)),
                            (Return(),),
                        ),
                        Raise("completed PDF oracle receipt is immutable", "23514"),
                    ),
                ),
                Sql(
                    update(oracle)
                    .values(
                        {
                            oracle.c.state: p_state,
                            oracle.c.actual_native_digest: p_actual,
                            oracle.c.error_message: p_error,
                        }
                    )
                    .where(oracle.c.oracle_receipt_id == p_oracle)
                ),
            ),
            (build_local, Local("o", oracle)),
        )
    )

    targets, target, result, meaning = (
        value(name, JSONB()) for name in ("p_targets", "item_", "result_", "meaning_")
    )
    target_rows = func.jsonb_array_elements(targets).table_valued(column("value", JSONB()))
    out.append(
        routine(
            "read_pdf_certification_targets",
            (*fence, Parameter("p_targets", pg_type("jsonb"))),
            pg_type("bytea"),
            (
                require_build,
                If(
                    or_(
                        func.jsonb_typeof(targets).is_distinct_from("array"),
                        func.jsonb_array_length(targets) > 512,
                    ),
                    (Raise("PDF producer targets must be a bounded array", "P0001"),),
                ),
                ForQuery(
                    ("item_",),
                    select(target_rows.c.value),
                    (
                        Assign(
                            "meaning_",
                            func.ops.pdf_identity_published_target(
                                cast(target[0].astext, BigInteger()),
                                target[1].astext,
                                target[2].astext,
                            ),
                        ),
                        If(
                            meaning["source_digest"].astext.is_distinct_from(
                                row("b", build, "source_digest")
                            ),
                            (Raise("PDF producer target changes original source", "23514"),),
                        ),
                        Assign(
                            "result_",
                            result.op("||")(
                                func.jsonb_build_array(
                                    func.jsonb_build_object("pin", target, "meaning", meaning)
                                )
                            ),
                        ),
                    ),
                ),
                Return(func.convert_to(cast(result, Text()), "UTF8")),
            ),
            (
                build_local,
                Local("item_", pg_type("jsonb")),
                Local("result_", pg_type("jsonb"), cast(literal("[]"), JSONB())),
                Local("meaning_", pg_type("jsonb")),
            ),
        )
    )
    return tuple(out)


def pdf_certification_native_sql(*, target_metadata=None) -> str:
    return "\n".join(
        native_sql_script(
            (
                program.render(),
                native_privilege_sql(program.identity, "PUBLIC", grant=False),
                *(
                    native_privilege_sql(program.identity, role, "execute")
                    for role, _, _ in program.access.grants(program.owner)
                ),
            )
        )
        + "\n"
        for program in pdf_certification_native_programs(target_metadata=target_metadata)
    )
