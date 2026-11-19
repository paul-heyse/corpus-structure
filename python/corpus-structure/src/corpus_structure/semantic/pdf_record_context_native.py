"""Current PDF companion context queries from the compiled physical model."""

from sqlalchemy import (
    BigInteger,
    Integer,
    Text,
    and_,
    any_,
    case,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
    true,
    union,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, array

from corpus_structure.schema.integrity import role_name

from .native_objects import (
    INTERNAL_PROGRAM,
    NativeIdentity,
    NativeProgramAccess,
    native_privilege_sql,
    native_sql_script,
)
from .native_program import (
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    column_type,
    core_variable,
    pg_type,
)
from .native_program import literal as pg_literal
from .native_program_registry import ProgramDeclaration


def _materialized(query, name):
    return query.cte(name).prefix_with("MATERIALIZED")


def _parameters(model, key_name="p_key"):
    publication = model.tables["ops.pdf_published_revision"]
    pointers = pg_type("text")
    from pglast import ast

    pointers.arrayBounds = (ast.Integer(ival=-1),)
    return (
        Parameter("p_task", column_type(publication.c.task_id)),
        Parameter(key_name, column_type(publication.c.product_key)),
        Parameter("p_digest", column_type(publication.c.logical_digest)),
        Parameter("p_pointers", pointers),
        Parameter("p_section", pg_type("text")),
    )


def _selection(model, key_name="p_key"):
    publication = model.tables["ops.pdf_published_revision"]
    companion = model.tables["kb.pdf_record_companion"]
    access_relation = model.tables["kb.pdf_record_access"]
    endpoint_relation = model.tables["kb.pdf_record_endpoint"]
    task = core_variable("p_task", publication.c.task_id.type)
    key = core_variable(key_name, publication.c.product_key.type)
    digest = core_variable("p_digest", publication.c.logical_digest.type)
    pointers = core_variable("p_pointers", ARRAY(Text()))
    section = core_variable("p_section", Text())
    published_rows = func.ops.read_pdf_published_revision(task, key, digest).table_valued(
        *(column(field.name, field.type) for field in publication.c)
    )
    published = _materialized(select(published_rows), "published")

    def placement(relation):
        return and_(
            relation.c.product_id == published.c.build_id,
            relation.c.revision_id == published.c.build_id,
        )

    access = _materialized(
        select(
            *(
                access_relation.c[name]
                for name in (
                    "product_id",
                    "revision_id",
                    "pointer",
                    "parent_pointer",
                    "native_json",
                )
            )
        ).select_from(access_relation.join(published, placement(access_relation))),
        "access",
    )
    seeds = union(select(func.unnest(pointers).label("pointer")), select(section)).subquery(
        "pointer_seeds"
    )
    scopes = select(seeds.c.pointer).cte("scope_pointers", recursive=True)
    scopes = scopes.union(
        select(access.c.parent_pointer)
        .select_from(access.join(scopes, access.c.pointer == scopes.c.pointer))
        .where(access.c.parent_pointer.is_not(None))
    )
    selected = _materialized(
        select(companion)
        .select_from(companion.join(published, placement(companion)))
        .where(
            companion.c.family == "occurrence",
            companion.c.body["pointer"].astext == any_(pointers),
        ),
        "selected",
    )
    related = _materialized(
        select(endpoint_relation.c.relation_id)
        .distinct()
        .select_from(
            endpoint_relation.join(published, placement(endpoint_relation)).join(
                selected, selected.c.local_id == endpoint_relation.c.occurrence_id
            )
        )
        .where(
            or_(
                and_(
                    endpoint_relation.c.target_task_id == task,
                    endpoint_relation.c.target_product_key == key,
                    endpoint_relation.c.target_content_digest == digest,
                ),
                and_(
                    endpoint_relation.c.target_task_id == 0,
                    endpoint_relation.c.target_product_key == "@self",
                    endpoint_relation.c.target_content_digest == "@self",
                ),
            )
        ),
        "related",
    )
    endpoints = _materialized(
        select(endpoint_relation).select_from(
            endpoint_relation.join(published, placement(endpoint_relation)).join(
                related, related.c.relation_id == endpoint_relation.c.relation_id
            )
        ),
        "endpoints",
    )
    provenance = func.jsonb_array_elements(
        func.coalesce(access.c.native_json["prov"], cast(literal("[]"), JSONB()))
    ).table_valued(column("value", JSONB()))
    page_number = selected.c.body["page_no"].astext
    provenance_number = provenance.c.value["page_no"].astext
    pages = _materialized(
        union(
            select(cast(page_number, BigInteger()).label("page_no"))
            .distinct()
            .where(page_number.regexp_match("^[0-9]+$")),
            select(cast(provenance_number, BigInteger()))
            .distinct()
            .select_from(access.join(provenance, true()))
            .where(access.c.pointer == any_(pointers), provenance_number.regexp_match("^[0-9]+$")),
        ),
        "pages",
    )
    memberships = select(
        func.unnest(array(["direct", "descendants"], type_=Text())).label("membership")
    ).subquery("memberships")
    scope = companion.c.body["scope"].astext
    lower = cast(func.split_part(func.split_part(scope, ":", 2), "-", 1), BigInteger())
    upper = cast(func.split_part(func.split_part(scope, ":", 2), "-", 2), BigInteger())
    covered = _materialized(
        select(companion)
        .select_from(companion.join(published, placement(companion)))
        .where(
            companion.c.family == "coverage",
            or_(
                scope == "whole_document",
                scope.in_(
                    select(scopes.c.pointer + ":" + memberships.c.membership).select_from(
                        scopes.join(memberships, true())
                    )
                ),
                scope.in_(select(literal("page:") + cast(pages.c.page_no, Text()))),
                case(
                    (
                        scope.regexp_match("^pages:[0-9]+-[0-9]+$"),
                        exists(
                            select(1)
                            .select_from(pages)
                            .where(pages.c.page_no.between(lower, upper))
                        ),
                    ),
                    else_=False,
                ),
            ),
        ),
        "covered",
    )
    supports = func.jsonb_array_elements(
        func.coalesce(covered.c.body["supports"], cast(literal("[]"), JSONB()))
    ).table_valued(column("value", JSONB()))
    inputs = _materialized(
        select(companion)
        .select_from(companion.join(published, placement(companion)))
        .where(
            companion.c.family == "input",
            or_(
                exists(
                    select(1)
                    .select_from(endpoints)
                    .where(
                        endpoints.c.role != "output",
                        endpoints.c.target_task_id
                        == cast(companion.c.body["task_id"].astext, BigInteger()),
                        endpoints.c.target_product_key == companion.c.body["product_key"].astext,
                        endpoints.c.target_content_digest
                        == companion.c.body["content_digest"].astext,
                    )
                    .correlate(companion)
                ),
                companion.c.local_id.in_(
                    select(supports.c.value["input_index"].astext).select_from(
                        covered.join(supports, true())
                    )
                ),
            ),
        ),
        "inputs",
    )
    chosen = union_all(
        select(selected),
        select(covered),
        select(inputs),
        select(companion)
        .select_from(companion.join(published, placement(companion)))
        .where(
            companion.c.family == "relation",
            companion.c.local_id.in_(select(related.c.relation_id)),
        ),
        select(companion)
        .select_from(companion.join(published, placement(companion)))
        .where(
            companion.c.family == "mapping_report",
            companion.c.body["input_index"].astext.in_(select(inputs.c.local_id)),
        ),
    ).cte("chosen")
    return chosen, published


def _privileges(name, parameters, *, readers=False):
    from pglast.stream import RawStream

    identity = NativeIdentity(
        "function", "ops", name, tuple(RawStream()(item.type_) for item in parameters)
    )
    return (
        native_privilege_sql(identity, "PUBLIC", grant=False),
        *(
            native_privilege_sql(identity, role, "execute")
            for role in (
                (role_name("reader"), role_name("writer"), role_name("evaluator"))
                if readers
                else ()
            )
        ),
    )


def pdf_record_context_programs(model) -> tuple[ProgramDeclaration, ...]:
    """Generate the shared selected companion rows and integrated set result."""
    companion = model.tables["kb.pdf_record_companion"]
    parameters = _parameters(model)
    chosen, _ = _selection(model)
    body = func.ops.pdf_companion_body(
        chosen.c.product_id, chosen.c.revision_id, chosen.c.family, chosen.c.local_id, chosen.c.body
    )
    row_columns = tuple(
        (name, column_type(companion.c[name])) for name in ("family", "local_id", "ordinal", "body")
    )
    returns = pg_type("record")
    returns.setof = True
    rows = NativeRoutine(
        "ops",
        "pdf_record_context_rows",
        parameters=parameters,
        returns=returns,
        table_columns=row_columns,
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=select(chosen.c.family, chosen.c.local_id, chosen.c.ordinal, body),
    )
    return (
        ProgramDeclaration(
            rows, "target-current:PDF publication", role_name("publisher"), INTERNAL_PROGRAM
        ),
        _integrated_context_program(model),
    )


def _context_program_sql(item):
    return native_sql_script(
        (
            item.render(),
            *_privileges(
                item.identity.name, item.routine.parameters, readers=item.access != INTERNAL_PROGRAM
            ),
        )
    )


def pdf_record_context_sql(model):
    rows, integrated = pdf_record_context_programs(model)
    return (
        native_sql_script(
            (
                rows.render(),
                *_privileges(rows.identity.name, rows.routine.parameters),
                _context_program_sql(integrated),
            )
        )
        + "\n"
    )


def pdf_record_context_page_programs(model) -> tuple[ProgramDeclaration, ...]:
    """Generate the keyset page from the same selected context relation."""
    parameters = (
        *_parameters(model, "p_product"),
        Parameter("p_family", pg_type("text")),
        Parameter("p_after", pg_type("text")),
        Parameter("p_limit", pg_type("int4")),
    )
    chosen, published = _selection(model, "p_product")
    companion = model.tables["kb.pdf_record_companion"]
    family = core_variable("p_family", companion.c.family.type)
    limit = core_variable("p_limit", Integer())
    pointers = core_variable("p_pointers", ARRAY(Text()))
    fields = ("product_id", "revision_id", "family", "local_id", "body")
    selected = union_all(
        select(*(chosen.c[name] for name in fields)).where(chosen.c.family == family),
        select(*(companion.c[name] for name in fields))
        .select_from(
            companion.join(
                published,
                and_(
                    companion.c.product_id == published.c.build_id,
                    companion.c.revision_id == published.c.build_id,
                ),
            )
        )
        .where(family == "health", companion.c.family == "health"),
    ).cte("selected_context")
    page = _materialized(
        select(selected)
        .where(selected.c.local_id > func.coalesce(core_variable("p_after", Text()), ""))
        .order_by(selected.c.local_id)
        .limit(limit),
        "requested_page",
    )
    returns = pg_type("jsonb")
    returns.setof = True
    declaration = NativeRoutine(
        "ops",
        "read_pdf_record_context_rows",
        parameters=parameters,
        returns=returns,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                If(
                    or_(
                        limit.is_(None),
                        ~limit.between(1, 1000),
                        pointers.is_(None),
                        family.is_(None),
                        family.not_in(
                            (
                                "occurrence",
                                "relation",
                                "input",
                                "coverage",
                                "mapping_report",
                                "health",
                            )
                        ),
                    ),
                    (Raise("invalid published context page", "22023"),),
                ),
                SelectInto(select(published), ("placement",), strict=True),
                ReturnQuery(
                    select(
                        func.jsonb_build_object(
                            "local_id",
                            page.c.local_id,
                            "body",
                            func.ops.pdf_companion_body(
                                page.c.product_id,
                                page.c.revision_id,
                                page.c.family,
                                page.c.local_id,
                                page.c.body,
                            ),
                        )
                    ).order_by(page.c.local_id)
                ),
            ),
            (Local("placement", pg_type("record")),),
        ),
    )
    return (
        ProgramDeclaration(
            declaration,
            "target-current:PDF publication",
            role_name("publisher"),
            NativeProgramAccess(purposes=("read", "write", "evaluate")),
        ),
    )


def pdf_record_context_page_sql(model):
    return _context_program_sql(pdf_record_context_page_programs(model)[0]) + "\n"


def _integrated_context_program(model) -> ProgramDeclaration:
    publication = model.tables["ops.pdf_published_revision"]
    companion = model.tables["kb.pdf_record_companion"]
    endpoint = model.tables["kb.pdf_record_endpoint"]
    task = core_variable("p_task", publication.c.task_id.type)
    key = core_variable("p_key", publication.c.product_key.type)
    digest = core_variable("p_digest", publication.c.logical_digest.type)
    pointers = core_variable("p_pointers", ARRAY(Text()))
    section = core_variable("p_section", Text())
    membership = core_variable("p_membership", Text())
    budget = core_variable("p_row_budget", BigInteger())
    count = core_variable("actual_rows", BigInteger())
    result = core_variable("result_", JSONB())
    published_build = core_variable("published", publication.c.build_id.type, "build_id")
    publication_rows = func.ops.read_pdf_published_revision(task, key, digest).table_valued(
        *(column(field.name, field.type) for field in publication.c)
    )
    arguments = (task, key, digest, pointers, section)
    rows = func.ops.pdf_record_context_rows(*arguments).table_valued(
        *(
            column(name, companion.c[name].type)
            for name in ("family", "local_id", "ordinal", "body")
        )
    )
    count_query = select(
        func.count()
        + func.coalesce(
            func.sum(
                case(
                    (
                        rows.c.family == "relation",
                        func.jsonb_array_length(rows.c.body["endpoints"]),
                    ),
                    else_=0,
                )
            ),
            0,
        )
    ).select_from(rows)
    chosen = _materialized(select(rows), "chosen")
    body = chosen.c.body
    endpoint_body = func.jsonb_build_object(
        "task_id",
        task,
        "product_key",
        key,
        "relation_id",
        endpoint.c.relation_id,
        "endpoint_index",
        endpoint.c.ordinal,
        "role",
        endpoint.c.role,
        "target_task_id",
        case((endpoint.c.target_task_id == 0, task), else_=endpoint.c.target_task_id),
        "target_product_key",
        case((endpoint.c.target_task_id == 0, key), else_=endpoint.c.target_product_key),
        "target_content_digest",
        case((endpoint.c.target_task_id == 0, digest), else_=endpoint.c.target_content_digest),
        "occurrence_id",
        endpoint.c.occurrence_id,
    )
    endpoints = (
        select(func.jsonb_agg(endpoint_body).aggregate_order_by(endpoint.c.ordinal))
        .where(
            endpoint.c.product_id == published_build,
            endpoint.c.revision_id == published_build,
            endpoint.c.relation_id == chosen.c.local_id,
        )
        .correlate(chosen)
        .scalar_subquery()
    )
    empty = cast(literal("[]"), JSONB())

    def object_(*args):
        return func.jsonb_build_object(*args, type_=JSONB())

    payload = case(
        (
            chosen.c.family == "input",
            object_(
                "input_index",
                cast(chosen.c.local_id, BigInteger()),
                "role",
                body["role"],
                "input_task_id",
                cast(body["task_id"].astext, BigInteger()),
                "input_product_key",
                body["product_key"],
                "input_content_digest",
                body["content_digest"],
            ),
        ),
        (
            chosen.c.family == "occurrence",
            object_(
                "occurrence_id",
                chosen.c.local_id,
                "pointer",
                body["pointer"],
                "kind",
                body["kind"],
                "precision",
                body["precision"],
                "address_space",
                body["address_space"],
                "body",
                body,
            ),
        ),
        (chosen.c.family == "coverage", object_("coverage_id", chosen.c.local_id, "body", body)),
        (
            chosen.c.family == "mapping_report",
            object_(
                "report_index",
                cast(chosen.c.local_id, BigInteger()),
                "input_index",
                cast(body["input_index"].astext, BigInteger()),
                "body",
                body,
            ),
        ),
        (
            chosen.c.family == "relation",
            object_(
                "relation_id",
                chosen.c.local_id,
                "kind",
                body["kind"],
                "body",
                body.op("-")("endpoints"),
                "endpoints",
                func.coalesce(endpoints, empty),
            ),
        ),
        else_=cast(literal("{}"), JSONB()),
    )
    wrapped = select(
        chosen.c.family,
        chosen.c.ordinal,
        chosen.c.local_id,
        object_("task_id", task, "product_key", key).op("||")(payload).label("body"),
    ).cte("wrapped")
    grouped = (
        select(
            wrapped.c.family,
            func.jsonb_agg(wrapped.c.body)
            .aggregate_order_by(wrapped.c.ordinal, wrapped.c.local_id)
            .label("body"),
        )
        .group_by(wrapped.c.family)
        .cte("grouped")
    )
    families = (
        ("inputs", "input"),
        ("occurrences", "occurrence"),
        ("relations", "relation"),
        ("coverage", "coverage"),
        ("mapping_reports", "mapping_report"),
    )
    final = select(
        object_(
            "selection",
            object_("task_id", task, "product_key", key, "content_digest", digest),
            "descriptor",
            object_(
                "version",
                2,
                "kind",
                "integrated",
                "revision",
                func.to_jsonb(core_variable("published", JSONB())),
            ),
            *(
                value
                for plural, singular in families
                for value in (
                    plural,
                    func.coalesce(
                        select(grouped.c.body)
                        .where(grouped.c.family == singular)
                        .scalar_subquery(),
                        empty,
                    ),
                )
            ),
        )
    )
    parameters = (
        *_parameters(model),
        Parameter("p_membership", pg_type("text")),
        Parameter("p_row_budget", pg_type("int8"), default=pg_literal(None)),
    )
    declaration = NativeRoutine(
        "ops",
        "record_integrated_source_context",
        parameters=parameters,
        returns=pg_type("jsonb"),
        security_definer=True,
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                If(
                    or_(
                        pointers.is_(None),
                        section.is_(None),
                        membership.is_(None),
                        membership.not_in(("direct", "descendants")),
                        and_(budget.is_not(None), budget < 1),
                    ),
                    (Raise("invalid published source context selector", "22023"),),
                ),
                SelectInto(select(publication_rows), ("published",), strict=True),
                If(
                    budget.is_not(None),
                    (
                        SelectInto(count_query, ("actual_rows",)),
                        If(
                            count > budget,
                            (
                                Raise(
                                    "PDF mandatory companion exceeds requested row budget", "23514"
                                ),
                            ),
                        ),
                    ),
                ),
                SelectInto(final, ("result_",)),
                Return(result),
            ),
            (
                Local("published", pg_type("record")),
                Local("actual_rows", pg_type("int8")),
                Local("result_", pg_type("jsonb")),
            ),
        ),
    )
    return ProgramDeclaration(
        declaration,
        "target-current:PDF publication",
        role_name("publisher"),
        NativeProgramAccess(purposes=("read", "write", "evaluate")),
    )
