"""Model-owned byte equality and scoped published PDF health queries."""

from pglast import ast
from sqlalchemy import Text, and_, any_, case, cast, func, literal, select
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, array

from corpus_structure.schema.integrity import role_name

from .native_objects import (
    INTERNAL_PROGRAM,
    NativeProgramAccess,
    native_privilege_sql,
    native_sql_script,
)
from .native_program import NativeRoutine, Parameter, column_type, core_variable, pg_type
from .native_program_registry import ProgramDeclaration


def pdf_reference_bytes_equal_program(metadata) -> ProgramDeclaration:
    streams = metadata.tables["ops.pdf_artifact_stream"]
    left, right = streams.alias("left_stream"), streams.alias("right_stream")
    product = core_variable("p_product", streams.c.product_id.type)
    revision = core_variable("p_revision", streams.c.revision_id.type)
    anchor = select(literal(1)).subquery("anchor")

    def representation(relation, text_name, stream_name):
        text = core_variable(text_name, Text())
        stream_id = core_variable(stream_name, streams.c.stream_id.type)
        inline = func.convert_to(text, "UTF8")
        length = case(
            (stream_id.is_(None), func.octet_length(inline)), else_=relation.c.byte_length
        )
        root = case(
            (stream_id.is_(None), func.encode(func.ops.pdf_identity_byte_root(inline), "hex")),
            else_=relation.c.byte_root,
        )
        match = and_(
            relation.c.product_id == product,
            relation.c.revision_id == revision,
            relation.c.stream_id == stream_id,
        )
        return length, root, match

    left_length, left_root, left_matches = representation(left, "p_left", "p_left_stream")
    right_length, right_root, right_matches = representation(right, "p_right", "p_right_stream")
    text = pg_type("text")
    stream_id = column_type(streams.c.stream_id)
    routine = NativeRoutine(
        "ops",
        "pdf_reference_bytes_equal",
        parameters=(
            Parameter("p_product", column_type(streams.c.product_id)),
            Parameter("p_revision", column_type(streams.c.revision_id)),
            Parameter("p_left", text),
            Parameter("p_left_stream", stream_id),
            Parameter("p_right", text),
            Parameter("p_right_stream", stream_id),
        ),
        returns=pg_type("bool"),
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
        body=select(
            func.coalesce(and_(left_length == right_length, left_root == right_root), False)
        ).select_from(anchor.outerjoin(left, left_matches).outerjoin(right, right_matches)),
    )
    return ProgramDeclaration(
        routine, "authoring/pdf-publication-read.sql", role_name("publisher"), INTERNAL_PROGRAM
    )


def pdf_record_scope_health_program(metadata) -> ProgramDeclaration:
    published = metadata.tables["ops.pdf_published_revision"]
    companion = metadata.tables["kb.pdf_record_companion"]
    health, formula = companion.alias("health"), companion.alias("formula")
    body = formula.c.body
    task = core_variable("p_task", published.c.task_id.type)
    key = core_variable("p_key", published.c.product_key.type)
    digest = core_variable("p_digest", published.c.logical_digest.type)
    pointers = core_variable("p_pointers", ARRAY(Text()))

    def scope(relation):
        return (
            relation.c.product_id == published.c.build_id,
            relation.c.revision_id == published.c.build_id,
        )

    diagnostic = func.jsonb_build_object(
        "diagnostic_ref",
        func.jsonb_build_object(
            "task_id",
            published.c.task_id,
            "product_key",
            published.c.product_key,
            "content_digest",
            published.c.logical_digest,
            "family",
            "native_metadata",
            "local_id",
            formula.c.local_id,
        ),
        type_=JSONB(),
    )
    outcome = func.jsonb_build_object(
        "pointer",
        body["pointer"],
        "outcome",
        body["outcome"],
        type_=JSONB(),
    ).op("||")(
        case(
            (body["has_diagnostic"] == cast(literal("true"), JSONB()), diagnostic),
            else_=cast(literal("{}"), JSONB()),
        )
    )
    details = (
        select(func.jsonb_agg(outcome).aggregate_order_by(formula.c.ordinal, formula.c.local_id))
        .where(
            *scope(formula),
            formula.c.family == "native_metadata",
            body["kind"].astext == "formula_outcomes",
            body["pointer"].astext == any_(pointers),
        )
        .correlate(published)
        .scalar_subquery()
    )
    fields = array(["source_scope", "page_start", "page_end", "formula_outcomes"], type_=Text())
    result = health.c.body.op("-")(fields).op("||")(
        func.jsonb_build_object(
            "formula_outcomes", func.coalesce(details, cast(literal("[]"), JSONB()))
        )
    )
    pointer_type = pg_type("text")
    pointer_type.arrayBounds = (ast.Integer(ival=-1),)
    routine = NativeRoutine(
        "ops",
        "pdf_record_scope_health",
        parameters=(
            Parameter("p_task", column_type(published.c.task_id)),
            Parameter("p_key", column_type(published.c.product_key)),
            Parameter("p_digest", column_type(published.c.logical_digest)),
            Parameter("p_pointers", pointer_type),
        ),
        returns=pg_type("jsonb"),
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=select(result)
        .select_from(
            published.join(
                health,
                and_(
                    *scope(health),
                    health.c.family == "health",
                    health.c.body.bool_op("?")("source_scope"),
                ),
            )
        )
        .where(
            published.c.task_id == task,
            published.c.product_key == key,
            published.c.logical_digest == digest,
        ),
    )
    return ProgramDeclaration(
        routine,
        "authoring/pdf-publication-read.sql",
        role_name("publisher"),
        NativeProgramAccess(purposes=("write", "read")),
    )


def pdf_publication_projection_program(metadata) -> ProgramDeclaration:
    """Bind the exact sealed producer receipt to its current PDF product."""
    from sqlalchemy import column, or_, tuple_

    from .native_program import (
        Block,
        If,
        Local,
        NativeRoutine,
        Raise,
        Return,
        SelectInto,
        core_relation_row,
    )

    publications = metadata.tables["ops.pdf_published_revision"]
    builds = metadata.tables["ops.pdf_stage_build"]
    validations = metadata.tables["ops.pdf_build_validation"]
    frozen = metadata.tables["ops.pdf_frozen_build"]
    companion = metadata.tables["kb.pdf_record_companion"]
    document = metadata.tables["kb.document"]
    receipt = core_variable("p_receipt", JSONB())
    task = core_variable("p_task", publications.c.task_id.type)
    attempt = core_variable("p_attempt", builds.c.attempt.type)
    holder = core_variable("p_holder", builds.c.holder.type)
    health = core_variable("health", companion.c.body.type)

    def publication(field):
        return core_variable("publication", publications.c[field].type, field)

    def build(field):
        return core_variable("build", builds.c[field].type, field)

    context_fields = (
        ("document_id", document.c.id.type),
        ("release_id", publications.c.release_id.type),
        ("source_digest", publications.c.source_digest.type),
    )

    def context(field, type_):
        return core_variable("context", type_, field)

    context_rows = func.ops.pdf_task_context(task).table_valued(
        *(column(field, type_) for field, type_ in context_fields)
    )
    build_id = publication("build_id")
    certified = (
        select(validations.c.build_id)
        .where(
            validations.c.build_id == build_id,
            receipt["certification"]
            == func.jsonb_build_object(
                "basis",
                validations.c.certification_basis,
                "lowering_identity",
                validations.c.lowering_identity,
                "attested_logical_digest",
                validations.c.attested_logical_digest,
                "native_document_digest",
                validations.c.native_document_digest,
                "oracle_receipt_id",
                validations.c.oracle_receipt_id,
            ),
        )
        .exists()
    )
    validated_frozen = (
        select(frozen.c.build_id)
        .select_from(
            frozen.join(
                validations,
                and_(
                    validations.c.build_id == frozen.c.build_id,
                    validations.c.frozen_digest == frozen.c.frozen_digest,
                ),
            )
        )
        .where(
            frozen.c.build_id == build_id,
            frozen.c.kind == publication("kind"),
            frozen.c.frozen_digest == publication("frozen_digest"),
            validations.c.native_callbacks,
            validations.c.logical_digest == publication("logical_digest"),
            validations.c.native_contract_digest
            == func.ops.pdf_validation_contract(publication("release_id")),
        )
        .exists()
    )
    custody_fields = ("release_id", "source_digest", "schema_digest", "recipe_digest")
    differing_fence = or_(
        attempt.is_(None),
        attempt < 1,
        func.nullif(holder, "").is_(None),
        func.to_jsonb(core_variable("publication", JSONB()), type_=JSONB()).is_distinct_from(
            receipt["publication"]
        ),
        publication("task_id").is_distinct_from(task),
        build("task_id").is_distinct_from(task),
        build("attempt").is_distinct_from(
            cast(receipt["publisher_attempt"].astext, builds.c.attempt.type)
        ),
        build("holder").is_distinct_from(receipt["publisher_holder"].astext),
        build("attempt") > attempt,
        and_(build("attempt") == attempt, build("holder").is_distinct_from(holder)),
        receipt["contributors"].is_distinct_from(func.ops.pdf_spool_contributors(build_id)),
        ~certified,
        build("state") != "published",
        tuple_(*(build(field) for field in custody_fields)).is_distinct_from(
            tuple_(*(publication(field) for field in custody_fields))
        ),
        tuple_(publication("release_id"), publication("source_digest")).is_distinct_from(
            tuple_(*(context(field, type_) for field, type_ in context_fields[1:]))
        ),
        ~validated_frozen,
    )
    health_fields = ("conversion", "display_coverage", "inline_coverage", "cell_coverage")
    result = func.jsonb_build_object(
        "document",
        select(document.c.key)
        .where(document.c.id == context("document_id", document.c.id.type))
        .scalar_subquery(),
        *(item for field in custody_fields[1:] for item in (field, publication(field))),
        "logical_digest",
        publication("logical_digest"),
        "kind",
        publication("kind"),
        "health",
        func.jsonb_build_object(
            *(item for field in health_fields for item in (field, health[field]))
        ),
    )
    routine = NativeRoutine(
        "ops",
        "pdf_publication_projection",
        parameters=(
            Parameter("p_receipt", pg_type("jsonb")),
            Parameter("p_task", column_type(publications.c.task_id)),
            Parameter("p_attempt", column_type(builds.c.attempt)),
            Parameter("p_holder", column_type(builds.c.holder)),
        ),
        returns=pg_type("jsonb"),
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                SelectInto(
                    select(core_relation_row(publications))
                    .select_from(publications)
                    .where(publications.c.build_id == receipt["publication"]["build_id"].astext),
                    ("publication",),
                    strict=True,
                ),
                SelectInto(
                    select(core_relation_row(builds))
                    .select_from(builds)
                    .where(builds.c.build_id == build_id),
                    ("build",),
                    strict=True,
                ),
                SelectInto(
                    select(*(context_rows.c[field] for field, _ in context_fields)),
                    ("context",),
                    strict=True,
                ),
                If(
                    differing_fence,
                    (Raise("PDF execution receipt differs from actual sealed publisher", "23514"),),
                ),
                SelectInto(
                    select(companion.c.body).where(
                        companion.c.product_id == build_id,
                        companion.c.revision_id == build_id,
                        companion.c.family == "health",
                        companion.c.body.bool_op("?")("conversion"),
                    ),
                    ("health",),
                    strict=True,
                ),
                Return(result),
            ),
            (
                Local("publication", publications),
                Local("build", builds),
                Local("context", pg_type("record")),
                Local("health", pg_type("jsonb")),
            ),
        ),
    )
    return ProgramDeclaration(
        routine, "authoring/pdf-publication-read.sql", role_name("publisher"), INTERNAL_PROGRAM
    )


def _render_publication_program(program):
    return (
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
    )


def pdf_reference_bytes_equal_sql(metadata):
    return _render_publication_program(pdf_reference_bytes_equal_program(metadata))


def pdf_record_scope_health_sql(metadata):
    return _render_publication_program(pdf_record_scope_health_program(metadata))


def pdf_publication_projection_sql(metadata):
    return _render_publication_program(pdf_publication_projection_program(metadata))
