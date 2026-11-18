"""Model-owned transactional programs for immutable shared PDF bytes."""

from pglast import ast, enums, parse_sql
from pglast.stream import RawStream
from sqlalchemy import (
    BigInteger,
    Boolean,
    Text,
    and_,
    case,
    cast,
    column,
    delete,
    exists,
    func,
    literal,
    not_,
    or_,
    select,
    tuple_,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, array, insert

from corpus_structure.schema.integrity import role_name

from .native_program import (
    Assign,
    Block,
    ForQuery,
    ForRelation,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    Sql,
    While,
    column_type,
    core_variable,
    function,
    pg_type,
    variable,
)
from .pdf_record_model import artifact_part_upload_table


def _routine(name, parameters, body, *, result=None, writer=False, defaults=(), trigger=False):
    declaration = parse_sql(
        function(
            "ops",
            name,
            parameters=parameters,
            returns=pg_type("record") if result else pg_type("trigger" if trigger else "void"),
            body=body,
            security_definer=writer,
            search_path=("pg_catalog", "pg_temp"),
        )
    )[0].stmt
    if not isinstance(declaration, ast.CreateFunctionStmt) or declaration.returnType is None:
        raise ValueError("shared-byte writer requires its typed function declaration")
    for param in declaration.parameters or ():
        if param.name in dict(defaults):
            param.defexpr = dict(defaults)[param.name]
    if result:
        declaration.returnType.setof = True
        declaration.parameters = (
            *(declaration.parameters or ()),
            *(
                ast.FunctionParameter(
                    name=field,
                    argType=pg_type(kind),
                    mode=enums.FunctionParameterMode.FUNC_PARAM_TABLE,
                )
                for field, kind in result
            ),
        )
    identity = ast.ObjectWithArgs(
        objname=(ast.String(sval="ops"), ast.String(sval=name)),
        objargs=tuple(p.type_ for p in parameters),
        args_unspecified=False,
    )
    revoke = ast.GrantStmt(
        is_grant=False,
        targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
        objtype=enums.ObjectType.OBJECT_FUNCTION,
        objects=(identity,),
        grantees=(ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_PUBLIC),),
        grant_option=False,
        behavior=enums.DropBehavior.DROP_RESTRICT,
    )
    statements = [declaration, revoke]
    if writer:
        grant = ast.GrantStmt(
            is_grant=True,
            targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
            objtype=enums.ObjectType.OBJECT_FUNCTION,
            objects=(identity,),
            privileges=(ast.AccessPriv(priv_name="execute"),),
            grantees=(
                ast.RoleSpec(
                    roletype=enums.RoleSpecType.ROLESPEC_CSTRING, rolename=role_name("writer")
                ),
            ),
            behavior=enums.DropBehavior.DROP_RESTRICT,
        )
        statements.append(grant)
    return ";\n".join(RawStream()(statement) for statement in statements) + ";\n"


def shared_stream_writes_sql(model):
    build = model.tables["ops.pdf_stage_build"]
    content = model.tables["ops.pdf_shared_stream"]
    verified = model.tables["ops.pdf_shared_stream_verification"]
    parts = model.tables["ops.pdf_shared_stream_part"]
    stage = model.tables["ops.pdf_stage_artifact_stream"]
    task = model.tables["ops.task"]
    request = model.tables["ops.data_request"]

    def scalar(name, type_=None):
        return core_variable(name, Text() if type_ is None else type_)

    def row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    def key(relation, project, profile, length, root):
        size = "stream_length" if relation is parts else "byte_length"
        return and_(
            relation.c.project_id == project,
            relation.c.encoding_profile == profile,
            relation.c[size] == length,
            relation.c.byte_root == root,
        )

    def stream_key(relation):
        return key(
            relation,
            scalar("project"),
            row("stream", stage, "encoding_profile"),
            row("stream", stage, "byte_length"),
            row("stream", stage, "byte_root"),
        )

    def ready():
        return func.ops.pdf_shared_stream_ready(
            scalar("p_build"),
            row("stream", stage, "encoding_profile"),
            row("stream", stage, "byte_length"),
            row("stream", stage, "byte_root"),
        )

    def owner_fence():
        return tuple_(
            *(
                row("content", content, name)
                for name in ("owner_build_id", "owner_attempt", "owner_holder")
            )
        ).is_distinct_from(
            tuple_(*(row("owner", build, name) for name in ("build_id", "attempt", "holder")))
        )

    def add_content(conflict=False):
        statement = insert(content).values(
            {
                content.c.project_id: scalar("project"),
                content.c.encoding_profile: row("stream", stage, "encoding_profile"),
                content.c.byte_length: row("stream", stage, "byte_length"),
                content.c.byte_root: row("stream", stage, "byte_root"),
                content.c.owner_build_id: row("owner", build, "build_id"),
                content.c.owner_attempt: row("owner", build, "attempt"),
                content.c.owner_holder: row("owner", build, "holder"),
            }
        )
        return Sql(statement.on_conflict_do_nothing() if conflict else statement)

    def reclaim():
        return Perform(
            func.ops.pdf_reclaim_pending_stream(
                scalar("project"),
                row("stream", stage, "encoding_profile"),
                row("stream", stage, "byte_length"),
                row("stream", stage, "byte_root"),
            )
        )

    p_build = scalar("p_build")
    p_stream = scalar("p_stream")
    project_local = Local("project", pg_type("text"), func.ops.pdf_stream_project(p_build))
    owner_query = SelectInto(select(build).where(build.c.build_id == p_build), ("owner",), True)
    p_key = key(
        content,
        scalar("p_project"),
        scalar("p_profile"),
        scalar("p_length", BigInteger()),
        scalar("p_root"),
    )
    v_key = key(
        verified,
        scalar("p_project"),
        scalar("p_profile"),
        scalar("p_length", BigInteger()),
        scalar("p_root"),
    )
    stream_query = select(stage).where(
        stage.c.product_id == p_build, stage.c.revision_id == p_build, stage.c.stream_id == p_stream
    )
    incoming = artifact_part_upload_table(model)
    part_names = tuple(incoming.c.keys())
    part_locals = tuple(Local("part_" + name, column_type(incoming.c[name])) for name in part_names)
    part = {name: scalar("part_" + name, incoming.c[name].type) for name in part_names}
    common_parameters = (Parameter("p_build", pg_type("text")),)
    out = []

    packet, descriptor = scalar("packet", JSONB()), scalar("descriptor", JSONB())
    required = (
        "product_id",
        "revision_id",
        "stream_id",
        "encoding_profile",
        "byte_length",
        "byte_root",
    )
    string_fields = ("product_id", "revision_id", "stream_id", "encoding_profile", "byte_root")
    serialized = descriptor["serialization_sha256"]
    bad_descriptor = or_(
        *(func.jsonb_typeof(descriptor[name]).is_distinct_from("string") for name in string_fields),
        descriptor["product_id"].astext.is_distinct_from(p_build),
        descriptor["revision_id"].astext.is_distinct_from(p_build),
        func.nullif(descriptor["stream_id"].astext, "").is_(None),
        func.nullif(descriptor["encoding_profile"].astext, "").is_(None),
        func.jsonb_typeof(descriptor["byte_length"]).is_distinct_from("number"),
        not_(func.coalesce(descriptor["byte_length"].astext.op("~")("^(0|[1-9][0-9]*)$"), False)),
        not_(func.coalesce(descriptor["byte_root"].astext.op("~")("^[0-9a-f]{64}$"), False)),
        and_(
            descriptor.has_key("serialization_sha256"),
            serialized != cast(literal("null"), JSONB()),
            or_(
                func.jsonb_typeof(serialized).is_distinct_from("string"),
                not_(
                    func.coalesce(
                        descriptor["serialization_sha256"].astext.op("~")("^[0-9a-f]{64}$"), False
                    )
                ),
            ),
        ),
    )
    elements = func.jsonb_array_elements(packet).table_valued("value")
    out.append(
        _routine(
            "probe_pdf_shared_streams",
            (
                *common_parameters,
                Parameter("p_task", pg_type("bigint")),
                Parameter("p_attempt", pg_type("bigint")),
                Parameter("p_holder", pg_type("text")),
                Parameter("p_streams", pg_type("bytea")),
            ),
            Block(
                (
                    Assign(
                        "build",
                        func.ops.require_pdf_build(
                            p_build,
                            scalar("p_task", BigInteger()),
                            scalar("p_attempt", BigInteger()),
                            scalar("p_holder"),
                        ),
                    ),
                    Perform(
                        func.ops.require_pdf_operation(
                            row("build", build, "release_id"), "adopt_pdf_batch"
                        )
                    ),
                    If(
                        or_(
                            scalar("p_streams", BYTEA()).is_(None),
                            func.octet_length(scalar("p_streams", BYTEA())) > 67108864,
                        ),
                        (Raise("shared stream probe exceeds its upload bound", "23514"),),
                    ),
                    Assign(
                        "packet",
                        cast(func.convert_from(scalar("p_streams", BYTEA()), "UTF8"), JSONB()),
                    ),
                    If(
                        func.jsonb_typeof(packet).is_distinct_from("array"),
                        (Raise("shared stream probe requires an array", "23514"),),
                    ),
                    If(
                        func.jsonb_array_length(packet) > 65536,
                        (Raise("shared stream probe requires a bounded descriptor set", "23514"),),
                    ),
                    ForQuery(
                        ("descriptor",),
                        select(elements.c.value),
                        (
                            Perform(
                                func.ops.ddo_fields(
                                    descriptor,
                                    array(required, type_=Text()),
                                    array(["serialization_sha256"], type_=Text()),
                                )
                            ),
                            If(
                                bad_descriptor,
                                (
                                    Raise(
                                        "shared stream probe changes its owned build/key", "23514"
                                    ),
                                ),
                            ),
                            ReturnQuery(
                                select(
                                    descriptor["stream_id"].astext,
                                    func.ops.pdf_shared_stream_ready(
                                        p_build,
                                        descriptor["encoding_profile"].astext,
                                        cast(descriptor["byte_length"].astext, BigInteger()),
                                        descriptor["byte_root"].astext,
                                    ),
                                )
                            ),
                        ),
                    ),
                ),
                (
                    Local("build", build),
                    Local("packet", pg_type("jsonb")),
                    Local("descriptor", pg_type("jsonb")),
                ),
            ),
            result=(("stream_id", "text"), ("verified", "boolean")),
            writer=True,
        )
    )

    dependent = build.alias("dependent")
    dependent_task = task.alias("dependent_task")
    live_dependent = exists(
        select(1)
        .select_from(
            stage.join(dependent, dependent.c.build_id == stage.c.product_id).join(
                dependent_task, dependent_task.c.id == dependent.c.task_id
            )
        )
        .where(
            stage.c.encoding_profile == scalar("p_profile"),
            stage.c.byte_length == scalar("p_length", BigInteger()),
            stage.c.byte_root == scalar("p_root"),
            func.ops.pdf_stream_project(dependent.c.build_id) == scalar("p_project"),
            dependent.c.build_id != row("owner", build, "build_id"),
            dependent.c.state == "open",
            dependent_task.c.status == "running",
            dependent_task.c.lease_until > func.clock_timestamp(),
            dependent_task.c.attempt == dependent.c.attempt,
            dependent_task.c.claimed_by == dependent.c.holder,
        )
    )
    out.append(
        _routine(
            "pdf_reclaim_pending_stream",
            (
                Parameter("p_project", pg_type("text")),
                Parameter("p_profile", pg_type("text")),
                Parameter("p_length", pg_type("bigint")),
                Parameter("p_root", pg_type("text")),
            ),
            Block(
                (
                    SelectInto(select(content).where(p_key).with_for_update(), ("content",), True),
                    SelectInto(
                        select(build).where(
                            build.c.build_id == row("content", content, "owner_build_id")
                        ),
                        ("owner",),
                        True,
                    ),
                    SelectInto(
                        select(task).where(task.c.id == row("owner", build, "task_id")),
                        ("job",),
                        True,
                    ),
                    SelectInto(
                        select(request.c.id)
                        .where(request.c.id == row("job", task, "data_request_id"))
                        .with_for_update(nowait=True),
                        ("lock_request",),
                    ),
                    SelectInto(
                        select(task.c.id)
                        .where(task.c.id == row("job", task, "id"))
                        .with_for_update(nowait=True),
                        ("lock_id",),
                    ),
                    SelectInto(
                        select(build.c.build_id)
                        .where(build.c.build_id == row("owner", build, "build_id"))
                        .with_for_update(nowait=True),
                        ("lock_build",),
                    ),
                    If(
                        or_(
                            not_(func.ops.pdf_pending_stream_owner_dead(scalar("content"))),
                            exists(select(1).select_from(verified).where(v_key)),
                        ),
                        (
                            Raise(
                                "shared stream is verified or still has a live append owner",
                                "55P03",
                            ),
                        ),
                    ),
                    If(
                        live_dependent,
                        (Raise("pending shared stream still has a live dependent build", "55P03"),),
                    ),
                    Sql(
                        delete(parts).where(
                            key(
                                parts,
                                scalar("p_project"),
                                scalar("p_profile"),
                                scalar("p_length", BigInteger()),
                                scalar("p_root"),
                            )
                        )
                    ),
                    Sql(delete(content).where(p_key)),
                ),
                (
                    Local("content", content),
                    Local("owner", build),
                    Local("job", task),
                    Local("lock_request", column_type(request.c.id)),
                    Local("lock_id", column_type(task.c.id)),
                    Local("lock_build", column_type(build.c.build_id)),
                ),
            ),
        )
    )

    same_key = and_(
        *(
            verified.c[name] == content.c[name]
            for name in ("project_id", "encoding_profile", "byte_length", "byte_root")
        )
    )
    out.append(
        _routine(
            "pdf_cleanup_pending_build",
            common_parameters,
            Block(
                (
                    ForQuery(
                        ("content",),
                        select(content)
                        .where(
                            content.c.owner_build_id == p_build,
                            ~exists(select(1).select_from(verified).where(same_key)),
                        )
                        .order_by(
                            *(
                                content.c[name]
                                for name in (
                                    "project_id",
                                    "encoding_profile",
                                    "byte_length",
                                    "byte_root",
                                )
                            )
                        ),
                        (
                            Perform(
                                func.ops.pdf_reclaim_pending_stream(
                                    *(
                                        row("content", content, name)
                                        for name in (
                                            "project_id",
                                            "encoding_profile",
                                            "byte_length",
                                            "byte_root",
                                        )
                                    )
                                )
                            ),
                        ),
                    ),
                ),
                (Local("content", content),),
            ),
        )
    )

    # A trigger's NEW/OLD rows are supplied by PostgreSQL under the owning table's row type.
    tg_op = scalar("tg_op")
    row_json = scalar("row_", JSONB())
    row_length = func.coalesce(
        cast(row_json["stream_length"].astext, BigInteger()),
        cast(row_json["byte_length"].astext, BigInteger()),
    )
    trigger_body = Block(
        (
            If(
                tg_op.in_(("UPDATE", "TRUNCATE")),
                (Raise("shared content cannot be updated or truncated", "23514"),),
            ),
            Assign(
                "row_",
                case(
                    (tg_op == "INSERT", func.to_jsonb(scalar("new"))),
                    else_=func.to_jsonb(scalar("old")),
                ),
            ),
            SelectInto(
                select(content).where(
                    key(
                        content,
                        row_json["project_id"].astext,
                        row_json["encoding_profile"].astext,
                        row_length,
                        row_json["byte_root"].astext,
                    )
                ),
                ("content",),
                True,
            ),
            If(
                exists(
                    select(1)
                    .select_from(verified)
                    .where(
                        key(
                            verified,
                            *(
                                row("content", content, name)
                                for name in (
                                    "project_id",
                                    "encoding_profile",
                                    "byte_length",
                                    "byte_root",
                                )
                            ),
                        )
                    )
                ),
                (Raise("verified content is immutable", "23514"),),
            ),
            If(
                tg_op == "INSERT",
                (
                    If(
                        func.ops.pdf_pending_stream_owner_dead(scalar("content")),
                        (Raise("pending byte append fence is closed", "P0004"),),
                    ),
                    Return(scalar("new")),
                ),
            ),
            If(
                not_(func.ops.pdf_pending_stream_owner_dead(scalar("content"))),
                (Raise("verified content or live pending content is immutable", "23514"),),
            ),
            Return(scalar("old")),
        ),
        (Local("row_", pg_type("jsonb")), Local("content", content)),
    )
    out.append(_routine("pdf_shared_stream_mutation_guard", (), trigger_body, trigger=True))

    out.append(
        _routine(
            "pdf_adopt_shared_stream_descriptors",
            (*common_parameters, Parameter("p_streams", pg_type("regclass"))),
            Block(
                (
                    If(
                        scalar("project").is_(None),
                        (Raise("shared stream has no actual build project", "23514"),),
                    ),
                    owner_query,
                    ForRelation(
                        ("stream",),
                        tuple(stage.c.keys()),
                        variable("p_streams"),
                        (
                            column("encoding_profile").collate("C"),
                            column("byte_length"),
                            column("byte_root").collate("C"),
                        ),
                        (
                            add_content(True),
                            SelectInto(
                                select(content).where(stream_key(content)).with_for_update(),
                                ("content",),
                                True,
                            ),
                            If(and_(not_(ready()), owner_fence()), (reclaim(), add_content())),
                        ),
                    ),
                ),
                (
                    Local("stream", stage),
                    project_local,
                    Local("content", content),
                    Local("owner", build),
                ),
            ),
        )
    )

    out.append(
        _routine(
            "pdf_adopt_shared_stream_parts",
            (*common_parameters, Parameter("p_parts", pg_type("regclass"))),
            Block(
                (
                    owner_query,
                    ForRelation(
                        tuple("part_" + name for name in part_names),
                        part_names,
                        variable("p_parts"),
                        (column("stream_id").collate("C"), column("ordinal")),
                        (
                            SelectInto(
                                select(stage).where(
                                    stage.c.product_id == p_build,
                                    stage.c.revision_id == p_build,
                                    stage.c.stream_id == part["stream_id"],
                                ),
                                ("stream",),
                            ),
                            If(
                                not_(scalar("found", Boolean())),
                                (
                                    Raise(
                                        "shared parts require their descriptor before bytes",
                                        "23514",
                                    ),
                                ),
                            ),
                            If(
                                or_(
                                    part["product_id"].is_distinct_from(p_build),
                                    part["revision_id"].is_distinct_from(p_build),
                                    part["ordinal"] < 0,
                                    part["byte_offset"] < 0,
                                    ~part["byte_length"].between(1, 65536),
                                    part["byte_length"] != func.octet_length(part["body"]),
                                    part["sha256_digest"]
                                    != func.encode(func.sha256(part["body"]), "hex"),
                                    part["byte_offset"] + part["byte_length"]
                                    > row("stream", stage, "byte_length"),
                                ),
                                (
                                    Raise(
                                        "shared stream incoming part differs from its descriptor/bytes",
                                        "23514",
                                    ),
                                ),
                            ),
                            SelectInto(
                                select(content).where(stream_key(content)).with_for_update(),
                                ("content",),
                                True,
                            ),
                            If(
                                not_(ready()),
                                (
                                    If(
                                        owner_fence(),
                                        (
                                            Raise(
                                                "pending shared parts belong to another append fence",
                                                "55P03",
                                            ),
                                        ),
                                    ),
                                    Sql(
                                        insert(parts)
                                        .values(
                                            {
                                                parts.c.project_id: scalar("project"),
                                                parts.c.encoding_profile: row(
                                                    "stream", stage, "encoding_profile"
                                                ),
                                                parts.c.stream_length: row(
                                                    "stream", stage, "byte_length"
                                                ),
                                                parts.c.byte_root: row(
                                                    "stream", stage, "byte_root"
                                                ),
                                                **{
                                                    parts.c[name]: part[name]
                                                    for name in (
                                                        "ordinal",
                                                        "byte_offset",
                                                        "byte_length",
                                                        "body",
                                                        "sha256_digest",
                                                    )
                                                },
                                            }
                                        )
                                        .on_conflict_do_nothing()
                                    ),
                                ),
                            ),
                            SelectInto(
                                select(parts).where(
                                    stream_key(parts), parts.c.ordinal == part["ordinal"]
                                ),
                                ("retained",),
                            ),
                            If(
                                or_(
                                    not_(scalar("found", Boolean())),
                                    tuple_(
                                        *(
                                            row("retained", parts, name)
                                            for name in (
                                                "byte_offset",
                                                "byte_length",
                                                "body",
                                                "sha256_digest",
                                            )
                                        )
                                    ).is_distinct_from(
                                        tuple_(
                                            *(
                                                part[name]
                                                for name in (
                                                    "byte_offset",
                                                    "byte_length",
                                                    "body",
                                                    "sha256_digest",
                                                )
                                            )
                                        )
                                    ),
                                ),
                                (Raise("shared stream part replay differs", "23514"),),
                            ),
                        ),
                    ),
                ),
                (
                    *part_locals,
                    Local("stream", stage),
                    project_local,
                    Local("retained", parts),
                    Local("content", content),
                    Local("owner", build),
                ),
            ),
        )
    )

    pending, state = scalar("pending", BYTEA()), scalar("state", BYTEA())
    ordinal, offset, block = (
        scalar(name, BigInteger()) for name in ("next_ordinal", "offset_", "block_ordinal")
    )
    out.append(
        _routine(
            "pdf_verify_shared_stream",
            (
                *common_parameters,
                Parameter("p_stream", pg_type("text")),
                Parameter("p_complete", pg_type("boolean")),
            ),
            Block(
                (
                    SelectInto(stream_query, ("stream",), True),
                    SelectInto(
                        select(content).where(stream_key(content)).with_for_update(),
                        ("content",),
                        True,
                    ),
                    If(ready(), (Return(),)),
                    owner_query,
                    If(
                        owner_fence(),
                        (Raise("pending fold belongs to another append fence", "55P03"),),
                    ),
                    Assign("state", func.ops.pdf_identity_fold_start("bytes")),
                    SelectInto(
                        select(func.coalesce(func.sum(parts.c.byte_length), 0)).where(
                            stream_key(parts)
                        ),
                        ("present",),
                    ),
                    If(
                        and_(
                            not_(scalar("p_complete", Boolean())),
                            scalar("present", BigInteger()) < row("stream", stage, "byte_length"),
                        ),
                        (Return(),),
                    ),
                    ForQuery(
                        ("part",),
                        select(parts).where(stream_key(parts)).order_by(parts.c.ordinal),
                        (
                            If(
                                or_(
                                    row("part", parts, "ordinal") != ordinal,
                                    row("part", parts, "byte_offset") != offset,
                                    row("part", parts, "byte_length")
                                    != func.octet_length(row("part", parts, "body")),
                                    ~row("part", parts, "byte_length").between(1, 65536),
                                    row("part", parts, "sha256_digest")
                                    != func.encode(func.sha256(row("part", parts, "body")), "hex"),
                                ),
                                (
                                    Raise(
                                        "shared stream actual bytes/ordinal/offset/length/hash differs",
                                        "23514",
                                    ),
                                ),
                            ),
                            Assign("pending", pending.op("||")(row("part", parts, "body"))),
                            While(
                                func.octet_length(pending) >= 65536,
                                (
                                    Assign(
                                        "state",
                                        func.ops.pdf_identity_fold_step(
                                            state, block, func.substr(pending, 1, 65536)
                                        ),
                                    ),
                                    Assign("pending", func.substr(pending, 65537)),
                                    Assign("block_ordinal", block + 1),
                                ),
                            ),
                            Assign("offset_", offset + row("part", parts, "byte_length")),
                            Assign("next_ordinal", ordinal + 1),
                        ),
                    ),
                    If(
                        func.octet_length(pending) > 0,
                        (
                            Assign("state", func.ops.pdf_identity_fold_step(state, block, pending)),
                            Assign("block_ordinal", block + 1),
                        ),
                    ),
                    If(
                        or_(
                            offset != row("stream", stage, "byte_length"),
                            func.encode(
                                func.ops.pdf_identity_fold_finish(state, block, offset), "hex"
                            )
                            != row("stream", stage, "byte_root"),
                        ),
                        (Raise("shared stream actual fold differs from its content key", "23514"),),
                    ),
                    Sql(
                        insert(verified)
                        .values(
                            {
                                verified.c.project_id: scalar("project"),
                                verified.c.encoding_profile: row(
                                    "stream", stage, "encoding_profile"
                                ),
                                verified.c.byte_length: row("stream", stage, "byte_length"),
                                verified.c.byte_root: row("stream", stage, "byte_root"),
                                verified.c.part_count: ordinal,
                            }
                        )
                        .on_conflict_do_nothing()
                    ),
                ),
                (
                    Local("stream", stage),
                    project_local,
                    Local("part", parts),
                    Local("state", pg_type("bytea")),
                    Local("pending", pg_type("bytea"), cast(literal(""), BYTEA())),
                    Local("next_ordinal", pg_type("bigint"), literal(0)),
                    Local("offset_", pg_type("bigint"), literal(0)),
                    Local("block_ordinal", pg_type("bigint"), literal(0)),
                    Local("present", pg_type("bigint")),
                    Local("content", content),
                    Local("owner", build),
                ),
            ),
            defaults=(("p_complete", ast.A_Const(val=ast.Boolean(boolval=True))),),
        )
    )
    return "\n".join(out)
