"""Compile selected recognition custody from the captured physical PDF model."""

from sqlalchemy import MetaData, Text, and_, cast, column, exists, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import JSONB, array

from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
from .native_program import (
    Block,
    CatchStrictLookup,
    If,
    Local,
    Parameter,
    Raise,
    Return,
    SelectInto,
    column_type,
    core_variable,
    function,
    pg_type,
)


def source_record_recognition_sql(model: MetaData) -> str:
    """Require exact selected decision endpoints and retained original provider bytes."""
    published = model.tables["ops.pdf_published_revision"]
    companion = model.tables["kb.pdf_record_companion"]
    endpoint = model.tables["kb.pdf_record_endpoint"]
    occurrence = model.tables["kb.pdf_occurrence"]
    product = model.tables["ops.pdf_product"]
    body = model.tables["ops.pdf_product_body"]
    task = core_variable("p_task", published.c.task_id.type)
    key = core_variable("p_key", published.c.product_key.type)
    digest = core_variable("p_digest", published.c.logical_digest.type)
    pointer = core_variable("p_pointer", Text())
    address = core_variable("p_address", JSONB())
    selected_body = core_variable("selected_body", JSONB())
    relation_body = core_variable("relation_body", JSONB())
    provider = core_variable("provider", JSONB())
    observation = core_variable("observation", JSONB())
    build = core_variable("placement", published.c.build_id.type, "build_id")
    placement = func.ops.read_pdf_published_revision(task, key, digest).table_valued(
        *(column(field.name, field.type) for field in published.c)
    )
    context = func.ops.pdf_record_context_rows(
        task, key, digest, array((pointer,)), pointer
    ).table_valued(
        *(
            column(name, companion.c[name].type)
            for name in ("family", "local_id", "ordinal", "body")
        )
    )
    endpoint_scope = (
        endpoint.c.product_id == build,
        endpoint.c.revision_id == build,
        endpoint.c.relation_id == address["relation_id"].astext,
    )
    endpoint_pin = tuple_(
        endpoint.c.target_task_id,
        endpoint.c.target_product_key,
        endpoint.c.target_content_digest,
    )
    source_task = cast(address["task_id"].astext, published.c.task_id.type)
    source_key = address["product_key"].astext
    source_digest = address["content_digest"].astext
    output = exists(
        select(1)
        .select_from(endpoint)
        .where(
            *endpoint_scope,
            endpoint.c.role == "output",
            endpoint.c.occurrence_id == address["selected_occurrence_id"].astext,
            or_(
                endpoint_pin == tuple_(task, key, digest),
                endpoint_pin == tuple_(0, "@self", "@self"),
            ),
        )
    )
    source = exists(
        select(1)
        .select_from(endpoint)
        .where(
            *endpoint_scope,
            endpoint.c.role == address["endpoint_role"].astext,
            endpoint.c.occurrence_id == address["occurrence_id"].astext,
            endpoint_pin == tuple_(source_task, source_key, source_digest),
        )
    )
    steps = (
        SelectInto(select(placement), ("placement",), strict=True),
        SelectInto(
            select(context.c.body).where(
                context.c.family == "occurrence",
                context.c.local_id == address["selected_occurrence_id"].astext,
            ),
            ("selected_body",),
            strict=True,
        ),
        If(
            selected_body["pointer"].astext.is_distinct_from(pointer),
            (
                Raise(
                    "captured recognition selected occurrence differs from source pointer", "23514"
                ),
            ),
        ),
        SelectInto(
            select(context.c.body).where(
                context.c.family == "relation",
                context.c.local_id == address["relation_id"].astext,
            ),
            ("relation_body",),
            strict=True,
        ),
        If(
            or_(
                address["endpoint_role"].astext.not_in(("input", "evidence", "alternative")),
                address["relation_kind"].astext.is_distinct_from("decision"),
                relation_body["kind"].astext.is_distinct_from(address["relation_kind"].astext),
                relation_body["outcome"].astext.is_distinct_from(
                    address["relation_outcome"].astext
                ),
                relation_body["outcome"].astext.not_in(
                    ("selected", "added", "replaced", "retained_alternative")
                ),
                ~output,
                ~source,
            ),
            (Raise("unsupported or forged captured recognition decision lineage", "23514"),),
        ),
        SelectInto(
            select(occurrence.c.body, body.c.descriptor["observation"])
            .select_from(
                occurrence.join(
                    product,
                    and_(
                        occurrence.c.task_id == product.c.task_id,
                        occurrence.c.product_key == product.c.product_key,
                    ),
                ).join(
                    body,
                    and_(
                        occurrence.c.task_id == body.c.task_id,
                        occurrence.c.product_key == body.c.product_key,
                    ),
                )
            )
            .where(
                occurrence.c.task_id == source_task,
                occurrence.c.product_key == source_key,
                product.c.content_digest == source_digest,
                product.c.kind == "recognition_observation",
                func.encode(func.sha256(body.c.payload), "hex") == product.c.content_digest,
                occurrence.c.occurrence_id == address["occurrence_id"].astext,
            ),
            ("provider", "observation"),
            strict=True,
        ),
        If(
            or_(
                provider.is_distinct_from(
                    cast(address["provider_occurrence_json"].astext, JSONB())
                ),
                observation.is_distinct_from(cast(address["observation_json"].astext, JSONB())),
                provider["precision"].astext.not_in(("unknown", "coarse", "block")),
                provider.has_key("start"),
                provider.has_key("end"),
                func.jsonb_typeof(provider["text"]).is_distinct_from("string"),
            ),
            (
                Raise(
                    "captured recognition provider custody or original precision differs", "23514"
                ),
            ),
        ),
        Return(provider["text"].astext),
    )
    identity = NativeIdentity(
        "function",
        "ops",
        "record_captured_recognition_text",
        ("bigint", "text", "text", "text", "jsonb"),
    )
    definition = function(
        identity.schema,
        identity.name,
        parameters=(
            Parameter("p_task", column_type(published.c.task_id)),
            Parameter("p_key", column_type(published.c.product_key)),
            Parameter("p_digest", column_type(published.c.logical_digest)),
            Parameter("p_pointer", pg_type("text")),
            Parameter("p_address", pg_type("jsonb")),
        ),
        returns=pg_type("text"),
        body=Block(
            (
                CatchStrictLookup(
                    steps,
                    (
                        Raise(
                            "captured recognition has no unique admitted retained lineage/body",
                            "23514",
                        ),
                    ),
                ),
            ),
            (
                Local("placement", published),
                *(
                    Local(name, pg_type("jsonb"))
                    for name in ("selected_body", "relation_body", "provider", "observation")
                ),
            ),
        ),
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    return native_sql_script(
        (
            definition,
            native_privilege_sql(identity, "PUBLIC", grant=False),
            *(
                native_privilege_sql(identity, role, "EXECUTE")
                for role in ("corpus_sem_reader", "corpus_sem_writer", "corpus_sem_evaluator")
            ),
        )
    )
