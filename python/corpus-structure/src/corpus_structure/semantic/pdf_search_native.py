"""Compile publication search programs from captured relational and call models."""

from __future__ import annotations

from typing import Any

from pglast import ast, enums, parse_sql
from pglast.stream import RawStream
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Float,
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
    not_,
    or_,
    select,
    union,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB, REGCONFIG, TSQUERY, aggregate_order_by, insert
from sqlalchemy.types import TypeEngine

from .native_call_contracts import OperationCallBinding
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
    call,
    column_type,
    core_variable,
    function,
    pg_type,
    variable,
)


def _json(value: str):
    return cast(literal(value), JSONB())


def _object(**values):
    return func.jsonb_build_object(
        *(part for name, value in values.items() for part in (literal(name), value)), type_=JSONB()
    )


def _aggregate(value, *order):
    return func.coalesce(
        func.jsonb_agg(aggregate_order_by(value, *order) if order else value),
        _json("[]"),
        type_=JSONB(),
    )


def _elements(value, name, *, text=False, ordinal=False):
    operator = func.jsonb_array_elements_text if text else func.jsonb_array_elements
    arguments = {"with_ordinality": "ordinal"} if ordinal else {}
    return (
        operator(value)
        .table_valued(column("value", Text()) if text else column("value", JSONB()), **arguments)
        .render_derived(name=name)
    )


def _array_aggregate(value, *order):
    return func.coalesce(
        func.array_agg(aggregate_order_by(value, *order) if order else value),
        cast(literal("{}"), ARRAY(Text())),
        type_=ARRAY(Text()),
    )


def _field(relation, name: str, column_name: str):
    return core_variable(name, relation.c[column_name].type, relation.c[column_name].name)


def _reader(bindings: dict[str, OperationCallBinding], name: str, *arguments):
    binding = bindings[name]
    schema, symbol = binding.symbol.split(".")
    types = {
        "integer": BigInteger,
        "string": Text,
        "boolean": Boolean,
        "json_payload": JSONB,
        "float": Float,
    }
    fields = []
    for field in binding.result_fields:
        resolved = field.resolved
        if resolved is None or resolved.kind not in types:
            raise ValueError(f"{binding.id}.{field.name}: unresolved search reader field")
        kind: TypeEngine[Any] = types[resolved.kind]()
        if resolved.multivalued:
            kind = ARRAY(kind)
        fields.append(column(field.native_field or field.name, kind))
    if len(arguments) != len(binding.parameters):
        raise ValueError(f"{binding.id}: search reader arguments differ from captured call")
    return getattr(getattr(func, schema), symbol)(*arguments).table_valued(*fields).alias(name)


def _declaration(name, body, *, table_result=None):
    result = function(
        "ops",
        name,
        parameters=(Parameter("p_payload", pg_type("jsonb")),),
        returns=pg_type("jsonb") if table_result is None else pg_type("record"),
        body=body,
        volatility="volatile",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    if table_result is None:
        return result + ";\n"
    statement = parse_sql(result)[0].stmt
    if not isinstance(statement, ast.CreateFunctionStmt) or statement.returnType is None:
        raise ValueError("search key declaration requires a typed function")
    statement.parameters = (
        *(statement.parameters or ()),
        *(
            ast.FunctionParameter(
                name=name, argType=type_, mode=enums.FunctionParameterMode.FUNC_PARAM_TABLE
            )
            for name, type_ in table_result
        ),
    )
    statement.returnType.setof = True
    return RawStream()(statement) + ";\n"


def _ensure(model, readers, max_fill_bytes, configuration):
    publications = model.tables["ops.pdf_published_revision"]
    populations = model.tables["ops.pdf_source_search_population"]
    sections = model.tables["ops.pdf_source_search_section"]
    p = core_variable("p", JSONB())
    pin = core_variable("pin", JSONB())
    rows = core_variable("rows", JSONB())
    item = core_variable("item", JSONB())
    catalog = core_variable("catalog", JSONB())
    selected = core_variable("selected", JSONB())
    ancestors = core_variable("ancestors", JSONB())
    outcomes = core_variable("outcomes", JSONB())
    expected = core_variable("expected", JSONB())
    actual = core_variable("actual", JSONB())
    body = core_variable("body", JSONB())
    digest = core_variable("digest", Text())
    bound = core_variable("bound", BigInteger())
    byte_count = core_variable("byte_count", BigInteger())
    population_id = _field(populations, "population", "population_id")
    population_digest = _field(populations, "population", "set_digest")
    population_count = _field(populations, "population", "row_count")

    def pub(name):
        return _field(publications, "publication", name)

    pub_args = (pub("task_id"), pub("product_key"), pub("logical_digest"))
    source_rows = _elements(p["rows"], "source_rows")
    ordered_rows = _elements(rows, "ordered_rows")
    row = ordered_rows.c.value
    catalog_sections = _reader(readers, "read_published_sections", *pub_args)
    catalog_nodes = _reader(
        readers, "read_published_section_nodes", *pub_args, literal("#/body"), literal("direct")
    )
    catalog_entries = _elements(catalog, "catalog_entries")
    memberships = union_all(
        select(literal("direct").label("membership")),
        select(literal("descendants").label("membership")),
    ).subquery("memberships")
    expected_keys = union_all(
        select(
            catalog_entries.c.value["pointer"].astext.label("pointer"), memberships.c.membership
        ),
        select(literal("#/body"), literal("direct")).where(
            exists(
                select(1)
                .select_from(catalog_nodes)
                .where(catalog_nodes.c.role == "selected", catalog_nodes.c.pointer != "#/body")
            )
        ),
    ).subquery("expected_keys")
    nodes = _reader(
        readers,
        "read_published_section_nodes",
        *pub_args,
        item["section_pointer"].astext,
        item["membership"].astext,
    )
    selected_items = _elements(selected, "selected_items", text=True)
    ancestor_items = _elements(ancestors, "ancestor_items", text=True)
    report_scopes = union(
        select(item["section_pointer"].astext.label("pointer")),
        select(ancestor_items.c.value),
    ).subquery("report_scopes")
    reports = _reader(
        readers,
        "read_published_section_reports",
        *pub_args,
        select(_array_aggregate(selected_items.c.value)).scalar_subquery(),
        select(_array_aggregate(report_scopes.c.pointer)).scalar_subquery(),
    )
    section_names = (
        "population_id",
        "section_pointer",
        "membership",
        "text",
        "projection_digest",
        "packet_digest",
    )
    lookup_population = SelectInto(
        select(populations).where(populations.c.population_id == pin["population_id"].astext),
        ("population",),
    )
    ready = Return(
        _object(
            payload=_object(
                state=literal("ready"),
                population_id=population_id,
                set_digest=population_digest,
                row_count=population_count,
            )
        )
    )
    return _declaration(
        "ensure_pdf_search_projection",
        Block(
            locals=(
                Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())),
                Local("pin", pg_type("jsonb")),
                Local("publication", publications),
                Local("population", populations),
                *(
                    Local(name, pg_type("jsonb"))
                    for name in (
                        "catalog",
                        "expected",
                        "actual",
                        "item",
                        "nodes",
                        "selected",
                        "ancestors",
                        "outcomes",
                        "body",
                        "rows",
                    )
                ),
                Local("digest", pg_type("text")),
                Local("byte_count", pg_type("bigint")),
                Local("bound", pg_type("bigint")),
            ),
            statements=(
                Assign("pin", func.ops.ddo_pdf_search_pin(p["source"], p["recipe"], type_=JSONB())),
                Assign(
                    "publication",
                    call(
                        "pg_catalog",
                        "jsonb_populate_record",
                        ast.TypeCast(
                            arg=ast.A_Const(isnull=True),
                            typeName=pg_type(str(publications.schema), publications.name),
                        ),
                        ast.A_Expr(
                            kind=enums.A_Expr_Kind.AEXPR_OP,
                            name=(ast.String(sval="->"),),
                            lexpr=variable("pin"),
                            rexpr=ast.A_Const(val=ast.String(sval="publication")),
                        ),
                    ),
                ),
                If(
                    p["configuration"].astext.is_distinct_from(configuration),
                    (Raise("unsupported search text configuration", "23514"),),
                ),
                lookup_population,
                If(
                    population_id.is_(None),
                    (
                        Perform(
                            func.pg_advisory_xact_lock(
                                func.hashtextextended(pin["population_id"].astext, 0)
                            )
                        ),
                        lookup_population,
                    ),
                ),
                If(
                    not_(p.has_key("rows")),
                    (
                        Return(
                            _object(
                                payload=_object(
                                    state=case(
                                        (population_id.is_(None), literal("missing")),
                                        else_=literal("ready"),
                                    ),
                                    population_id=pin["population_id"].astext,
                                    set_digest=population_digest,
                                    row_count=func.coalesce(population_count, 0),
                                )
                            )
                        ),
                    ),
                ),
                Assign(
                    "bound",
                    func.coalesce(p["fill_max_bytes"].astext.cast(BigInteger()), max_fill_bytes),
                ),
                Assign(
                    "byte_count",
                    func.octet_length(func.convert_to(func.data.canonical_json(p), "UTF8")),
                ),
                If(
                    or_(not_(bound.between(1, max_fill_bytes)), byte_count > bound),
                    (Raise("publication search fill exceeds its byte bound", "54000"),),
                ),
                SelectInto(
                    select(
                        _aggregate(
                            source_rows.c.value,
                            source_rows.c.value["section_pointer"].astext.collate("C"),
                            source_rows.c.value["membership"].astext.collate("C"),
                        )
                    ),
                    ("rows",),
                ),
                If(
                    exists(
                        select(1)
                        .select_from(ordered_rows)
                        .group_by(row["section_pointer"].astext, row["membership"].astext)
                        .having(func.count() != 1)
                    ),
                    (Raise("search projection repeats a section/membership", "23514"),),
                ),
                Assign("digest", func.ops.ddo_digest(rows)),
                If(
                    population_id.is_not(None),
                    (
                        If(
                            or_(
                                population_digest.is_distinct_from(digest),
                                population_count != func.jsonb_array_length(rows),
                                exists(
                                    select(1)
                                    .select_from(ordered_rows)
                                    .where(
                                        not_(
                                            exists(
                                                select(1)
                                                .select_from(sections)
                                                .where(
                                                    sections.c.population_id == population_id,
                                                    sections.c.section_pointer
                                                    == row["section_pointer"].astext,
                                                    sections.c.membership
                                                    == row["membership"].astext,
                                                    sections.c.text
                                                    == row["projection"]["text"].astext,
                                                    sections.c.projection_digest
                                                    == row["projection_digest"].astext,
                                                    sections.c.packet_digest
                                                    == func.ops.ddo_digest(row),
                                                )
                                            )
                                        )
                                    )
                                ),
                                select(func.count())
                                .select_from(sections)
                                .where(sections.c.population_id == population_id)
                                .scalar_subquery()
                                != population_count,
                            ),
                            (Raise("search projection exact-set replay differs", "23514"),),
                        ),
                        ready,
                    ),
                ),
                SelectInto(
                    select(
                        _aggregate(
                            _object(
                                pointer=catalog_sections.c.pointer,
                                name=catalog_sections.c.name,
                                ancestors=func.to_jsonb(catalog_sections.c.ancestors),
                            ),
                            catalog_sections.c.ordinal,
                        )
                    ),
                    ("catalog",),
                ),
                SelectInto(
                    select(
                        _aggregate(
                            func.jsonb_build_array(
                                expected_keys.c.pointer, expected_keys.c.membership
                            ),
                            expected_keys.c.pointer.collate("C"),
                            expected_keys.c.membership.collate("C"),
                        )
                    ),
                    ("expected",),
                ),
                SelectInto(
                    select(
                        _aggregate(
                            func.jsonb_build_array(
                                row["section_pointer"].astext, row["membership"].astext
                            ),
                            row["section_pointer"].astext.collate("C"),
                            row["membership"].astext.collate("C"),
                        )
                    ),
                    ("actual",),
                ),
                If(
                    actual.is_distinct_from(expected),
                    (
                        Raise(
                            "search projection is not the complete publication section/membership set",
                            "23514",
                        ),
                    ),
                ),
                ForQuery(
                    ("item",),
                    select(row),
                    (
                        SelectInto(
                            select(
                                _aggregate(nodes.c.native_json, nodes.c.ordinal),
                                func.coalesce(
                                    func.jsonb_agg(
                                        aggregate_order_by(
                                            func.to_jsonb(nodes.c.pointer), nodes.c.ordinal
                                        )
                                    ).filter(nodes.c.role == "selected"),
                                    _json("[]"),
                                ),
                                func.coalesce(
                                    func.jsonb_agg(
                                        aggregate_order_by(
                                            func.to_jsonb(nodes.c.pointer), nodes.c.ordinal
                                        )
                                    ).filter(nodes.c.role == "ancestor"),
                                    _json("[]"),
                                ),
                            ),
                            ("nodes", "selected", "ancestors"),
                        ),
                        If(
                            or_(
                                item["projection"]["items"].is_distinct_from(selected),
                                item["projection"]["ancestors"].is_distinct_from(ancestors),
                            ),
                            (
                                Raise(
                                    "search projection original member/ancestor population differs",
                                    "23514",
                                ),
                            ),
                        ),
                        SelectInto(
                            select(
                                _aggregate(
                                    _object(
                                        pointer=reports.c.body["pointer"].astext,
                                        outcome=reports.c.body["outcome"],
                                    ),
                                    reports.c.ordinal,
                                )
                            ).where(reports.c.body["kind"].astext == "formula_outcomes"),
                            ("outcomes",),
                        ),
                        If(
                            item["projection"]["health"]["formula_outcomes"].is_distinct_from(
                                outcomes
                            ),
                            (
                                Raise(
                                    "search projection recognition differs from original source reports",
                                    "23514",
                                ),
                            ),
                        ),
                        Assign(
                            "body",
                            func.ops.ddo_native_source_body(
                                pin["selected"]["original_source"].astext,
                                item["section_pointer"].astext,
                                item["membership"].astext,
                                item["projection"],
                                item["projection_digest"].astext,
                                core_variable("nodes", JSONB()),
                                func.jsonb_build_array(
                                    _object(projection=item["projection_digest"].astext)
                                ),
                                type_=JSONB(),
                            ),
                        ),
                        If(
                            body["source"]["projection"].astext.is_distinct_from(
                                item["projection_digest"].astext
                            ),
                            (
                                Raise(
                                    "search projection digest differs from authentic source packet",
                                    "23514",
                                ),
                            ),
                        ),
                    ),
                ),
                Sql(
                    insert(populations).values(
                        {
                            "population_id": pin["population_id"].astext,
                            "project_id": p["source"]["project_id"].astext,
                            "build_id": pub("build_id"),
                            "task_id": pub("task_id"),
                            "product_key": pub("product_key"),
                            "logical_digest": pub("logical_digest"),
                            "recipe_digest": pin["recipe_digest"].astext,
                            "configuration": configuration,
                            "set_digest": digest,
                            "row_count": func.jsonb_array_length(rows),
                            "byte_count": byte_count,
                            "sections": catalog,
                        }
                    )
                ),
                Sql(
                    insert(sections).from_select(
                        section_names,
                        select(
                            pin["population_id"].astext,
                            row["section_pointer"].astext,
                            row["membership"].astext,
                            row["projection"]["text"].astext,
                            row["projection_digest"].astext,
                            func.ops.ddo_digest(row),
                        ),
                    )
                ),
                Return(
                    _object(
                        payload=_object(
                            state=literal("ready"),
                            population_id=pin["population_id"].astext,
                            set_digest=digest,
                            row_count=func.jsonb_array_length(rows),
                        )
                    )
                ),
            ),
        ),
    )


def _keys(model):
    populations = model.tables["ops.pdf_source_search_population"]
    sections = model.tables["ops.pdf_source_search_section"]
    p = core_variable("p_payload", JSONB())
    source = core_variable("source", JSONB())
    pin = core_variable("pin", JSONB())
    current_cut = core_variable("current_cut", JSONB())
    first_cut = core_variable("first_cut", JSONB())
    chosen = core_variable("chosen", ARRAY(Text()))
    selectors = core_variable("selectors", ARRAY(Text()))
    population_id = _field(populations, "population", "population_id")
    catalog = _field(populations, "population", "sections")
    idx = core_variable("idx", Integer())
    sources = _elements(p["sources"], "sources", ordinal=True)
    selector_items = _elements(p["binding"]["sections"], "selectors", text=True)
    entries = _elements(catalog, "entries")
    entry_ancestors = _elements(entries.c.value["ancestors"], "entry_ancestors", text=True)
    ancestor_chosen = exists(
        select(1).select_from(entry_ancestors).where(entry_ancestors.c.value == any_(chosen))
    )
    text_array = pg_type("text")
    text_array.arrayBounds = (ast.Integer(ival=-1),)
    return _declaration(
        "ddo_pdf_search_keys",
        Block(
            locals=(
                Local("source", pg_type("jsonb")),
                Local("pin", pg_type("jsonb")),
                Local("population", populations),
                Local("chosen", text_array),
                Local("selectors", text_array),
                Local("current_cut", pg_type("jsonb")),
                Local("first_cut", pg_type("jsonb")),
                Local("idx", pg_type("integer"), literal(0)),
            ),
            statements=(
                If(
                    p["binding"]["sources"].is_distinct_from(
                        select(
                            func.jsonb_agg(
                                aggregate_order_by(sources.c.value["source"], sources.c.ordinal)
                            )
                        ).scalar_subquery()
                    ),
                    (Raise("search population differs from its request binding", "23514"),),
                ),
                Assign(
                    "selectors", select(_array_aggregate(selector_items.c.value)).scalar_subquery()
                ),
                ForQuery(
                    ("source",),
                    select(sources.c.value),
                    (
                        If(
                            or_(
                                *(
                                    source["source"][name].astext.is_distinct_from(
                                        p["binding"][name].astext
                                    )
                                    for name in ("project_id", "demand_id", "read_id")
                                )
                            ),
                            (Raise("search population spans different selected cuts", "23514"),),
                        ),
                        Assign(
                            "pin",
                            func.ops.ddo_pdf_search_pin(
                                source["source"], source["recipe"], type_=JSONB()
                            ),
                        ),
                        Assign("current_cut", pin["selected"]["cut"]),
                        If(
                            and_(first_cut.is_not(None), current_cut.is_distinct_from(first_cut)),
                            (Raise("search source pins have different current cuts", "23514"),),
                        ),
                        Assign("first_cut", current_cut),
                        SelectInto(
                            select(populations).where(
                                populations.c.population_id == pin["population_id"].astext
                            ),
                            ("population",),
                            strict=True,
                        ),
                        SelectInto(
                            select(_array_aggregate(entries.c.value["pointer"].astext)).where(
                                or_(
                                    func.cardinality(selectors) == 0,
                                    entries.c.value["pointer"].astext == any_(selectors),
                                    entries.c.value["name"].astext == any_(selectors),
                                )
                            ),
                            ("chosen",),
                        ),
                        If(
                            and_(
                                func.cardinality(selectors) > 0,
                                func.cardinality(chosen) != func.cardinality(selectors),
                            ),
                            (
                                Raise(
                                    "requested intact section selection is missing or ambiguous",
                                    "22023",
                                ),
                            ),
                        ),
                        ReturnQuery(
                            select(
                                idx,
                                sections.c.population_id,
                                sections.c.section_pointer,
                                sections.c.membership,
                                func.data.canonical_json(
                                    func.jsonb_build_array(
                                        source["source"],
                                        sections.c.section_pointer,
                                        sections.c.membership,
                                        sections.c.projection_digest,
                                    )
                                ),
                            ).where(
                                sections.c.population_id == population_id,
                                or_(
                                    and_(
                                        sections.c.section_pointer == "#/body",
                                        func.cardinality(selectors) == 0,
                                        sections.c.membership == "direct",
                                    ),
                                    and_(
                                        sections.c.membership == p["binding"]["membership"].astext,
                                        exists(
                                            select(1)
                                            .select_from(entries)
                                            .where(
                                                entries.c.value["pointer"].astext
                                                == sections.c.section_pointer,
                                                case(
                                                    (
                                                        sections.c.membership == "direct",
                                                        or_(
                                                            entries.c.value["pointer"].astext
                                                            == any_(chosen),
                                                            ancestor_chosen,
                                                        ),
                                                    ),
                                                    else_=and_(
                                                        entries.c.value["pointer"].astext
                                                        == any_(chosen),
                                                        not_(ancestor_chosen),
                                                    ),
                                                ),
                                            )
                                        ),
                                    ),
                                ),
                            )
                        ),
                        Assign("idx", idx + 1),
                    ),
                ),
            ),
        ),
        table_result=(
            ("source_index", pg_type("integer")),
            ("population_id", column_type(sections.c.population_id)),
            ("section_pointer", column_type(sections.c.section_pointer)),
            ("membership", column_type(sections.c.membership)),
            ("key", pg_type("text")),
        ),
    )


def _rank(model, configuration):
    sections = model.tables["ops.pdf_source_search_section"]
    p = core_variable("p_payload", JSONB())
    keys = core_variable("keys", JSONB())
    selection = core_variable("selection", Text())
    query = core_variable("query", TSQUERY())
    after_score = core_variable("after_score", Float())
    after_key = core_variable("after_key", Text())
    page_limit = core_variable("page_limit", Integer())
    key_rows = (
        func.ops.ddo_pdf_search_keys(p)
        .table_valued(
            column("source_index", Integer()),
            column("population_id", sections.c.population_id.type),
            column("section_pointer", sections.c.section_pointer.type),
            column("membership", sections.c.membership.type),
            column("key", Text()),
        )
        .alias("key_rows")
    )
    entries = _elements(keys, "entries")
    entry = entries.c.value
    key_match = and_(
        sections.c.population_id == entry["population_id"].astext,
        sections.c.section_pointer == entry["section_pointer"].astext,
        sections.c.membership == entry["membership"].astext,
    )
    candidates = (
        select(
            entry["source_index"].astext.cast(Integer()).label("source_index"),
            sections.c.population_id,
            sections.c.section_pointer,
            sections.c.membership,
            sections.c.projection_digest,
            entry["key"].astext.label("key"),
            func.ts_rank_cd(sections.c.search_vector, query).cast(Float()).label("score"),
        )
        .select_from(entries.join(sections, key_match))
        .where(sections.c.search_vector.bool_op("@@")(query))
        .cte("candidates")
        .prefix_with("MATERIALIZED")
    )
    limited = (
        select(candidates)
        .where(
            or_(
                after_key.is_(None),
                candidates.c.score < after_score,
                and_(
                    candidates.c.score == after_score,
                    candidates.c.key.collate("C") > after_key.collate("C"),
                ),
            )
        )
        .order_by(candidates.c.score.desc(), candidates.c.key.collate("C"))
        .limit(page_limit + 1)
        .cte("limited")
        .prefix_with("MATERIALIZED")
    )
    page = (
        select(limited)
        .order_by(limited.c.score.desc(), limited.c.key.collate("C"))
        .limit(page_limit)
        .cte("page")
        .prefix_with("MATERIALIZED")
    )
    returned = (
        select(page, sections.c.text)
        .select_from(
            page.join(
                sections,
                and_(
                    *(
                        sections.c[name] == page.c[name]
                        for name in ("population_id", "section_pointer", "membership")
                    )
                ),
            )
        )
        .cte("returned")
        .prefix_with("MATERIALIZED")
    )
    ranked_row = _object(
        source_index=returned.c.source_index,
        section_pointer=returned.c.section_pointer,
        membership=returned.c.membership,
        projection_digest=returned.c.projection_digest,
        key=returned.c.key,
        score=returned.c.score,
        excerpt=func.ts_headline(
            cast(literal(configuration), REGCONFIG()),
            returned.c.text,
            query,
            literal("MaxWords=45,MinWords=15"),
        ),
    )
    return _declaration(
        "rank_pdf_search_projection",
        Block(
            locals=(
                Local("keys", pg_type("jsonb")),
                Local("selection", pg_type("text")),
                Local("result", pg_type("jsonb")),
                Local("query", pg_type("tsquery")),
                Local("after_score", pg_type("float8")),
                Local("after_key", pg_type("text")),
                Local("page_limit", pg_type("integer"), p["limit"].astext.cast(Integer())),
            ),
            statements=(
                SelectInto(select(_aggregate(func.to_jsonb(key_rows.table_valued()))), ("keys",)),
                Assign(
                    "selection",
                    func.ops.ddo_digest(
                        func.jsonb_build_array(
                            p["binding"],
                            p["cut_id"].astext,
                            select(
                                _aggregate(entry["key"].astext, entry["key"].astext.collate("C"))
                            ).scalar_subquery(),
                        )
                    ),
                ),
                If(
                    p.has_key("after"),
                    (
                        If(
                            p["after"]["selection"].astext.is_distinct_from(selection),
                            (
                                Raise(
                                    "search continuation belongs to another source population",
                                    "22023",
                                ),
                            ),
                        ),
                        Assign("after_score", p["after"]["score"].astext.cast(Float())),
                        Assign("after_key", p["after"]["key"].astext),
                    ),
                ),
                Assign(
                    "query",
                    func.websearch_to_tsquery(
                        cast(literal(configuration), REGCONFIG()), p["binding"]["text"].astext
                    ),
                ),
                SelectInto(
                    select(
                        _object(
                            selection=selection,
                            more=select(func.count() > page_limit)
                            .select_from(limited)
                            .scalar_subquery(),
                            rows=_aggregate(
                                ranked_row, returned.c.score.desc(), returned.c.key.collate("C")
                            ),
                        )
                    ),
                    ("result",),
                ),
                Return(_object(payload=core_variable("result", JSONB()))),
            ),
        ),
    )


def search_program_sql(model, bindings, *, max_fill_bytes: int, configuration: str) -> str:
    readers = {binding.id: binding for _owner, binding in bindings}
    return (
        _ensure(model, readers, max_fill_bytes, configuration)
        + _keys(model)
        + _rank(model, configuration)
    )
