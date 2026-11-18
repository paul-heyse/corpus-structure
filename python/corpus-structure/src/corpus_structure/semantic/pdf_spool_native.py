"""Model-owned original producer and immutable recovery contributor custody."""

from pglast.stream import RawStream
from sqlalchemy import (
    BigInteger,
    Column,
    MetaData,
    Table,
    Text,
    and_,
    cast,
    column,
    exists,
    func,
    literal,
    not_,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, aggregate_order_by, insert

from .metadata import metadata
from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
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
    ReturnQuery,
    SelectInto,
    Sql,
    column_type,
    core_relation_row,
    core_variable,
    function,
    pg_type,
    sql_function,
)


def pdf_spool_native_sql(*, target_metadata: MetaData | None = None) -> str:
    """Compile current spool fences from the supplied captured physical model."""
    model = metadata if target_metadata is None else target_metadata
    build = model.tables["ops.pdf_stage_build"]
    producers = model.tables["ops.pdf_spool_producer"]
    contributors = model.tables["ops.pdf_spool_contributor"]
    runtime = model.tables["sem.runtime_binding"]
    inputs = model.tables["sem.input"]

    def value(name, field):
        return core_variable(name, field.type)

    def row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    def obj(**pairs):
        return func.jsonb_build_object(
            *(part for name, item in pairs.items() for part in (literal(name), item))
        )

    def digest(raw):
        return func.encode(func.sha256(raw), "hex")

    def json_digest(*parts):
        return digest(func.convert_to(cast(func.jsonb_build_array(*parts), Text()), "UTF8"))

    def json_bytes(raw):
        return cast(func.convert_from(raw, "UTF8"), JSONB())

    def refuse(condition, message, state="P0001"):
        return If(condition, (Raise(message, state),))

    empty_array = cast(literal("[]"), JSONB())
    p_build, p_task, p_attempt, p_holder, p_runtime = (
        value(name, field)
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
            ("p_runtime", runtime.c.runtime_id),
        )
    )
    fence_fields = (
        ("p_build", build.c.build_id),
        ("p_task", build.c.task_id),
        ("p_attempt", build.c.attempt),
        ("p_holder", build.c.holder),
    )
    runtime_field = ("p_runtime", runtime.c.runtime_id)
    programs, identities = [], []

    def routine(name, fields, statements, locals_, *, result=None, output=()):
        parameters = tuple(Parameter(name, column_type(field)) for name, field in fields)
        identities.append(
            NativeIdentity("function", "ops", name, tuple(RawStream()(p.type_) for p in parameters))
        )
        programs.append(
            function(
                "ops",
                name,
                parameters=parameters,
                returns=result or column_type(producers.c.producer_id),
                table_columns=tuple((name, column_type(field)) for name, field in output),
                body=Block(tuple(statements), tuple(locals_)),
                security_definer=True,
                search_path=("pg_catalog", "pg_temp"),
            )
        )

    # The native producer-basis routine owns its composite output. SELECT alias.*
    # retains every admitted field, including additions, without a second codec.
    basis = (
        func.ops.read_pdf_producer_basis(p_task, p_attempt, p_holder, p_runtime)
        .table_valued()
        .alias("spool_basis")
    )
    basis_row = core_relation_row(Table("spool_basis", MetaData()))
    require_build = Assign("b", func.ops.require_pdf_build(p_build, p_task, p_attempt, p_holder))
    require_operation = Perform(
        func.ops.require_pdf_operation(row("b", build, "release_id"), "stage_pdf_producer")
    )
    device, inode, premises_bytes = (
        value(name, field)
        for name, field in (
            ("p_device", producers.c.writer_device),
            ("p_inode", producers.c.writer_inode),
            ("p_premises", producers.c.premises_bytes),
        )
    )
    premises, identity = core_variable("premises_", JSONB()), value("id_", producers.c.producer_id)
    routine(
        "register_pdf_spool_producer",
        (
            *fence_fields,
            runtime_field,
            ("p_device", producers.c.writer_device),
            ("p_inode", producers.c.writer_inode),
            ("p_premises", producers.c.premises_bytes),
        ),
        (
            require_build,
            require_operation,
            SelectInto(select(basis_row).select_from(basis), ("basis_",), strict=True),
            Assign("premises_", json_bytes(premises_bytes)),
            refuse(
                or_(
                    device.is_(None),
                    device < 0,
                    inode.is_(None),
                    inode < 1,
                    premises["producer"].is_distinct_from(
                        func.to_jsonb(core_variable("basis_", JSONB()))
                    ),
                    premises["source_digest"].astext.is_distinct_from(
                        row("b", build, "source_digest")
                    ),
                    premises["native_recipe_digest"].astext.is_distinct_from(
                        row("b", build, "recipe_digest")
                    ),
                    premises["native_schema_digest"].astext.is_distinct_from(
                        row("b", build, "schema_digest")
                    ),
                    func.coalesce(premises["payload_schema_digest"].astext, "").bool_op("!~")(
                        "^[0-9a-f]{64}$"
                    ),
                    func.jsonb_typeof(premises["packages"]).is_distinct_from("array"),
                    func.jsonb_array_length(premises["packages"]) == 0,
                ),
                "PDF spool producer premises differ from admitted native basis",
                "23514",
            ),
            Assign("id_", json_digest(p_build, p_task, p_attempt, p_holder, device, inode)),
            Sql(
                insert(producers)
                .values(
                    producer_id=identity,
                    build_id=p_build,
                    task_id=p_task,
                    attempt=p_attempt,
                    holder=p_holder,
                    writer_device=device,
                    writer_inode=inode,
                    premises_bytes=premises_bytes,
                )
                .on_conflict_do_nothing()
            ),
            SelectInto(
                select(core_relation_row(producers)).where(producers.c.producer_id == identity),
                ("prior",),
                strict=True,
            ),
            refuse(
                row("prior", producers, "premises_bytes").is_distinct_from(premises_bytes),
                "PDF spool producer replay differs",
                "23514",
            ),
            Return(identity),
        ),
        (
            Local("b", build),
            Local("basis_", pg_type("record")),
            Local("premises_", pg_type("jsonb")),
            Local("id_", column_type(producers.c.producer_id)),
            Local("prior", producers),
        ),
    )
    p_producer, manifest_bytes, selected_bytes = (
        value(name, field)
        for name, field in (
            ("p_producer", producers.c.producer_id),
            ("p_manifest", contributors.c.manifest_bytes),
            ("p_selected", contributors.c.selected_replays),
        )
    )
    (
        original,
        current_basis,
        current_premises,
        header,
        declaration,
        entry,
        selected,
        replay,
        inventory,
    ) = (
        core_variable(name, JSONB())
        for name in (
            "original_",
            "current_basis_",
            "current_premises_",
            "header_",
            "declaration_",
            "entry_",
            "selected_",
            "replay_",
            "inventory_",
        )
    )
    lines, line = core_variable("lines_", ARRAY(Text())), core_variable("line_", Text())
    manifest_text = func.convert_from(manifest_bytes, "UTF8")
    manifest_digest, selection_digest, contributor_id = (
        value(name, field)
        for name, field in (
            ("manifest_", contributors.c.manifest_digest),
            ("selection_", contributors.c.selection_digest),
            ("id_", contributors.c.contributor_id),
        )
    )
    manifest_lines = (
        func.unnest(lines)
        .table_valued(column("value", Text()), with_ordinality="ordinal")
        .render_derived(name="manifest_line")
    )
    selected_rows = (
        func.jsonb_array_elements(selected)
        .table_valued(column("value", JSONB()))
        .render_derived(name="selected_replay")
    )
    inventory_rows = (
        func.jsonb_array_elements(inventory)
        .table_valued(column("value", JSONB()))
        .render_derived(name="inventory_member")
    )

    def strip_runtime(producer):
        return producer.op("-")("runtime_id").op("-")("runtime_manifest_digest")

    routine(
        "register_pdf_spool_contributor",
        (
            *fence_fields,
            runtime_field,
            ("p_producer", producers.c.producer_id),
            ("p_manifest", contributors.c.manifest_bytes),
            ("p_selected", contributors.c.selected_replays),
        ),
        (
            require_build,
            require_operation,
            SelectInto(select(basis_row).select_from(basis), ("current_",), strict=True),
            SelectInto(
                select(core_relation_row(producers)).where(producers.c.producer_id == p_producer),
                ("producer_",),
                strict=True,
            ),
            Assign("original_", json_bytes(row("producer_", producers, "premises_bytes"))),
            Assign(
                "current_basis_", strip_runtime(func.to_jsonb(core_variable("current_", JSONB())))
            ),
            SelectInto(
                select(json_bytes(producers.c.premises_bytes)).where(
                    producers.c.build_id == p_build,
                    producers.c.attempt == p_attempt,
                    producers.c.holder == p_holder,
                ),
                ("current_premises_",),
                strict=True,
            ),
            refuse(
                or_(
                    row("producer_", producers, "build_id").is_distinct_from(p_build),
                    row("producer_", producers, "task_id").is_distinct_from(p_task),
                    row("producer_", producers, "attempt") > p_attempt,
                    and_(
                        row("producer_", producers, "attempt") == p_attempt,
                        row("producer_", producers, "holder") != p_holder,
                    ),
                    strip_runtime(original["producer"]).is_distinct_from(current_basis),
                    original["source_digest"].astext.is_distinct_from(
                        row("b", build, "source_digest")
                    ),
                    original["native_recipe_digest"].astext.is_distinct_from(
                        row("b", build, "recipe_digest")
                    ),
                    original["native_schema_digest"].astext.is_distinct_from(
                        row("b", build, "schema_digest")
                    ),
                    original.op("-")("producer").is_distinct_from(
                        current_premises.op("-")("producer")
                    ),
                ),
                "PDF spool contributor has no matching original producer",
                "23514",
            ),
            refuse(
                or_(
                    manifest_bytes.is_(None),
                    func.octet_length(manifest_bytes) == 0,
                    func.right(manifest_text, 1) != "\n",
                ),
                "PDF spool manifest has no durable complete entries",
                "23514",
            ),
            Assign("lines_", func.string_to_array(func.rtrim(manifest_text, "\n"), "\n")),
            refuse(func.cardinality(lines) < 2, "PDF spool manifest lacks producer declaration"),
            Assign("header_", cast(lines[1], JSONB())),
            Assign("declaration_", cast(lines[2], JSONB())),
            refuse(
                or_(
                    header["version"].astext.is_distinct_from("pdf-build-spool-1"),
                    header["build_id"].astext.is_distinct_from(p_build),
                    *(
                        cast(header[key].astext, field.type).is_distinct_from(
                            row("producer_", producers, field.name)
                        )
                        for key, field in (
                            ("task_id", producers.c.task_id),
                            ("attempt", producers.c.attempt),
                        )
                    ),
                    header["holder"].astext.is_distinct_from(row("producer_", producers, "holder")),
                    *(
                        cast(header["writer"][key].astext, field.type).is_distinct_from(
                            row("producer_", producers, field.name)
                        )
                        for key, field in (
                            ("device", producers.c.writer_device),
                            ("inode", producers.c.writer_inode),
                        )
                    ),
                    declaration["producer_id"].astext.is_distinct_from(p_producer),
                    declaration["premises"].is_distinct_from(original),
                ),
                "PDF manifest differs from immutable original producer custody",
                "23514",
            ),
            # Ordered UNNEST is the original FOREACH over lines_[3:], retaining
            # duplicate manifest entries and the no-entry termination case.
            ForQuery(
                ("line_",),
                select(manifest_lines.c.value)
                .where(manifest_lines.c.ordinal >= 3)
                .order_by(manifest_lines.c.ordinal),
                (
                    Assign("entry_", cast(line, JSONB())),
                    If(
                        entry.bool_op("?")("replay"),
                        (
                            Assign(
                                "inventory_",
                                inventory.concat(func.jsonb_build_array(entry["replay"])),
                            ),
                        ),
                        (
                            refuse(
                                not_(entry.bool_op("?")("completion")),
                                "PDF spool manifest entry is not declared",
                            ),
                        ),
                    ),
                ),
            ),
            Assign("selected_", json_bytes(selected_bytes)),
            refuse(
                or_(
                    func.jsonb_typeof(selected).is_distinct_from("array"),
                    func.jsonb_array_length(selected) == 0,
                ),
                "PDF spool contributor selected no files",
            ),
            ForQuery(
                ("replay_",),
                select(selected_rows.c.value),
                (
                    refuse(
                        or_(
                            not_(
                                exists(
                                    select(1)
                                    .select_from(inventory_rows)
                                    .where(inventory_rows.c.value == replay)
                                )
                            ),
                            func.coalesce(replay["digest"].astext, "").bool_op("!~")(
                                "^[0-9a-f]{64}$"
                            ),
                            cast(replay["byte_length"].astext, BigInteger()) < 0,
                            func.nullif(replay["path"].astext, "").is_(None),
                        ),
                        "selected PDF replay differs from original manifest membership",
                        "23514",
                    ),
                ),
            ),
            refuse(
                func.jsonb_array_length(selected).is_distinct_from(
                    select(
                        func.count(selected_rows.c.value["path"].astext.distinct())
                    ).scalar_subquery()
                ),
                "PDF spool contributor repeats a selected path",
            ),
            Assign("manifest_", digest(manifest_bytes)),
            Assign("selection_", digest(selected_bytes)),
            Assign("id_", json_digest(p_build, p_producer, manifest_digest, selection_digest)),
            Sql(
                insert(contributors)
                .values(
                    contributor_id=contributor_id,
                    build_id=p_build,
                    producer_id=p_producer,
                    manifest_digest=manifest_digest,
                    selection_digest=selection_digest,
                    manifest_bytes=manifest_bytes,
                    selected_replays=selected_bytes,
                    adopter_attempt=p_attempt,
                    adopter_holder=p_holder,
                )
                .on_conflict_do_nothing()
            ),
            SelectInto(
                select(core_relation_row(contributors)).where(
                    contributors.c.contributor_id == contributor_id
                ),
                ("prior",),
                strict=True,
            ),
            refuse(
                or_(
                    row("prior", contributors, "manifest_bytes").is_distinct_from(manifest_bytes),
                    row("prior", contributors, "selected_replays").is_distinct_from(selected_bytes),
                ),
                "PDF contributor replay differs",
            ),
            Return(contributor_id),
        ),
        (
            Local("b", build),
            Local("producer_", producers),
            Local("current_", pg_type("record")),
            *(
                Local(name, pg_type("jsonb"))
                for name in (
                    "original_",
                    "current_basis_",
                    "current_premises_",
                    "header_",
                    "declaration_",
                    "entry_",
                    "selected_",
                    "replay_",
                )
            ),
            Local("inventory_", pg_type("jsonb"), empty_array),
            Local("lines_", column_type(Column("lines_", ARRAY(Text())))),
            Local("line_", pg_type("text")),
            Local("id_", column_type(contributors.c.contributor_id)),
            Local("manifest_", column_type(contributors.c.manifest_digest)),
            Local("selection_", column_type(contributors.c.selection_digest)),
            Local("prior", contributors),
        ),
    )
    output = (
        ("producer_id", producers.c.producer_id),
        ("task_id", producers.c.task_id),
        ("producer_attempt", producers.c.attempt),
        ("producer_holder", producers.c.holder),
        ("runtime_id", runtime.c.runtime_id),
        ("runtime_manifest_digest", inputs.c.content_digest),
        ("manifest_digest", contributors.c.manifest_digest),
        ("selection_digest", contributors.c.selection_digest),
        ("adopter_attempt", contributors.c.adopter_attempt),
        ("adopter_holder", contributors.c.adopter_holder),
    )
    producer_json = json_bytes(producers.c.premises_bytes)["producer"]
    summary = obj(
        producer_id=producers.c.producer_id,
        task_id=producers.c.task_id,
        producer_attempt=producers.c.attempt,
        producer_holder=producers.c.holder,
        runtime_id=producer_json["runtime_id"].astext,
        runtime_manifest_digest=producer_json["runtime_manifest_digest"].astext,
        manifest_digest=contributors.c.manifest_digest,
        selection_digest=contributors.c.selection_digest,
        adopter_attempt=contributors.c.adopter_attempt,
        adopter_holder=contributors.c.adopter_holder,
    )
    aggregate = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(
                        summary,
                        producers.c.producer_id,
                        contributors.c.manifest_digest,
                        contributors.c.selection_digest,
                    )
                ),
                empty_array,
            )
        )
        .select_from(
            contributors.join(producers, producers.c.producer_id == contributors.c.producer_id)
        )
        .where(contributors.c.build_id == p_build)
    )
    summary_parameters = (Parameter("p_build", column_type(build.c.build_id)),)
    programs.append(
        sql_function(
            "ops",
            "pdf_spool_contributors",
            parameters=summary_parameters,
            returns=pg_type("jsonb"),
            body=aggregate,
            volatility="stable",
            search_path=("pg_catalog", "pg_temp"),
        )
    )
    identities.append(
        NativeIdentity(
            "function", "ops", "pdf_spool_contributors", (RawStream()(summary_parameters[0].type_),)
        )
    )
    returned = (
        func.jsonb_to_recordset(func.ops.pdf_spool_contributors(p_build))
        .table_valued(*(column(name, field.type) for name, field in output))
        .render_derived(name="r", with_types=True)
    )
    result = pg_type("record")
    result.setof = True
    routine(
        "read_pdf_spool_contributors",
        fence_fields,
        (
            Perform(func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder)),
            refuse(
                not_(
                    exists(
                        select(1)
                        .select_from(build)
                        .where(build.c.build_id == p_build, build.c.task_id == p_task)
                    )
                ),
                "PDF contributor read has no owned build",
            ),
            ReturnQuery(
                select(returned).order_by(
                    returned.c.producer_id, returned.c.manifest_digest, returned.c.selection_digest
                )
            ),
        ),
        (),
        result=result,
        output=output,
    )
    return (
        native_sql_script(
            (
                *programs,
                *(native_privilege_sql(identity, "PUBLIC", grant=False) for identity in identities),
                *(
                    native_privilege_sql(identity, "corpus_sem_writer", "execute")
                    for identity in identities
                    if identity.name != "pdf_spool_contributors"
                ),
            )
        )
        + "\n"
    )
