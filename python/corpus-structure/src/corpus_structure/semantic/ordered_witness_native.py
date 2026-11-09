"""PostgreSQL reconstruction of the bounded ordered declaration source."""

from functools import lru_cache

from sqlalchemy import (
    BigInteger,
    Integer,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    literal_column,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, aggregate_order_by

_RECAP = (
    r"^((?:We have seen above that it is possible to simulate a )([^.\n]+) ([A-Za-z]))"
    r"(\.[^.\n]*\ythe simulated values for ([A-Za-z]) using the equation )([^.\n]+)\."
)
_DECLARATION = (
    r"^(Let )([A-Za-z])( be )(a [^.\n]+)"
    r"(\. A ([^.\n]+?) with these parameters is said to be a )([^.\n]+)\."
)
_PRIOR = (
    r"\y(?:[Ll][Ee][Tt]|[Ww][Hh][Ee][Rr][Ee]|[Ss][Uu][Pp][Pp][Oo][Ss][Ee]|[Dd][Ee][Ff][Ii][Nn][Ee])"
    r"[ \t\r\n]+([A-Za-z])[ \t\r\n]+"
    r"(?:[Bb][Ee]|[Dd][Ee][Nn][Oo][Tt][Ee][Ss]?|[Ii][Ss]|[Rr][Ee][Pp][Rr][Ee][Ss][Ee][Nn][Tt][Ss]?)\y"
)


def _entries(value, alias, *, order=False):
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB), **({"with_ordinality": "position"} if order else {}))
        .render_derived(name=alias)
    )


def _str(value, key):
    return value[key].astext


def _number(value, key):
    return cast(_str(value, key), BigInteger)


def _field(name, kind):
    return literal_column(f"(p_view).{name}", type_=kind)


def _items(addresses, alias):
    return (
        func.ops.read_pdf_published_items(
            _field("native_task_id", BigInteger()),
            _field("native_product_key", Text()),
            _field("native_content_digest", Text()),
            addresses,
        )
        .table_valued(column("pointer", Text), column("native_json", JSONB))
        .alias(alias)
    )


def _parent(node):
    return node["parent"]["$ref"].astext


def _body(node, label):
    return and_(_str(node, "content_layer") == "body", _str(node, "label") == label)


def _translated(value):
    return func.translate(value, literal("\n\t"), literal("  "))


def _slice(text, start, end):
    return func.substr(text, cast(start + 1, Integer), cast(end - start, Integer))


def _selection():
    projection = _field("projection", JSONB())
    config = literal_column("p_config", type_=JSONB())
    selection = config["ordered_formula_witness"]
    ordinary = config["inputs"]["passages"][0]
    text = _str(projection, "text")
    sources = _entries(config["inputs"]["sources"], "source_pin")
    source = sources.c.value
    source_reference = func.encode(
        func.sha256(
            func.convert_to(func.data.canonical_json(func.jsonb_strip_nulls(source)), "UTF8")
        ),
        "hex",
    )
    exact_source = (
        select(source)
        .where(
            _number(source, "source_view_id") == _field("id", BigInteger()),
            _number(source, "native_task_id") == _field("native_task_id", BigInteger()),
            _str(source, "native_product_key") == _field("native_product_key", Text()),
            _str(source, "native_content_digest") == _field("native_content_digest", Text()),
            _str(source, "projection_digest") == _field("projection_digest", Text()),
            _str(source, "recipe_digest") == _field("recipe_digest", Text()),
            source_reference == _str(ordinary, "source_ref"),
        )
        .exists()
    )
    pieces = _entries(projection["pieces"], "piece", order=True)
    start, end = (_number(selection, name) for name in ("start", "end"))
    a, b = (_number(pieces.c.value, name) for name in ("start", "end"))
    exact = (
        select(
            pieces.c.value.label("piece"),
            a.label("a"),
            b.label("b"),
            func.lag(b).over(order_by=pieces.c.position).label("previous_end"),
        )
        .where(a < end, start < b)
        .cte("ordered_projection")
    )
    summary = select(
        func.count().label("count"),
        func.min(exact.c.a).label("start"),
        func.max(exact.c.b).label("end"),
        func.bool_and(
            and_(
                exact.c.a < exact.c.b,
                (exact.c.previous_end == exact.c.a) | exact.c.previous_end.is_(None),
            )
        ).label("contiguous"),
    ).cte("projection_summary")
    valid = (
        select(literal(True).label("valid"))
        .select_from(summary)
        .where(
            exact_source,
            summary.c.count.between(1, 128),
            summary.c.start == start,
            summary.c.end == end,
            summary.c.contiguous,
            end - start <= 4096,
            start >= 0,
            end <= func.length(text),
            _str(selection, "text") == _slice(text, start, end),
            func.jsonb_array_length(config["inputs"]["passages"]) == 1,
            func.jsonb_array_length(config["inputs"]["sources"]) == 1,
            _str(selection, "passage_id") != _str(ordinary, "passage_id"),
            _str(selection, "source_ref") == _str(ordinary, "source_ref"),
            _str(selection, "scope") == _str(ordinary, "scope"),
            _str(selection, "effective_version").is_not_distinct_from(
                _str(ordinary, "effective_version")
            ),
            _number(ordinary, "start") >= start,
            _number(ordinary, "end") <= end,
            _number(ordinary, "start") < _number(ordinary, "end"),
            (_number(ordinary, "start") > start) | (_number(ordinary, "end") < end),
            _str(ordinary, "text")
            == _slice(text, _number(ordinary, "start"), _number(ordinary, "end")),
        )
        .cte("validated_window")
    )
    fields = (
        select(_str(exact.c.piece, "item_ref").label("pointer"), exact.c.a, exact.c.b)
        .select_from(exact.join(valid, true()))
        .where(
            _str(exact.c.piece, "kind") == "native_text",
            func.coalesce(_str(exact.c.piece, "source_field"), "text") == "text",
            ~exact.c.piece.has_key("cell_index"),
        )
        .cte("native_fields")
    )
    return text, selection, ordinary, valid, fields


def _physical(fields, text):
    def load(address, alias):
        population = (
            select(cast(func.array_agg(func.distinct(address)), ARRAY(Text)).label("pointers"))
            .where(address.is_not(None))
            .having(func.count() > 0)
            .cte(alias + "_pointers")
            .prefix_with("MATERIALIZED", dialect="postgresql")
        )
        items = _items(population.c.pointers, alias + "_items").lateral()
        return (
            select(items.c.pointer, items.c.native_json)
            .select_from(population.join(items, true()))
            .cte(alias)
        )

    def ancestors(references, alias):
        read = load(references.c.parent, alias + "_native")
        return (
            select(
                read.c.pointer,
                read.c.native_json.label("node"),
                _parent(read.c.native_json).label("parent"),
            )
            .where(read.c.native_json.is_not(None))
            .cte(alias)
        )

    leaf = load(fields.c.pointer, "selected_native_fields")
    physical = (
        select(
            leaf.c.pointer,
            leaf.c.native_json.label("node"),
            _parent(leaf.c.native_json).label("parent"),
            fields.c.a,
            fields.c.b,
            _str(leaf.c.native_json, "text").label("text"),
        )
        .join(fields, fields.c.pointer == leaf.c.pointer)
        .where(
            _body(leaf.c.native_json, "text"),
            _str(leaf.c.native_json, "text") == _slice(text, fields.c.a, fields.c.b),
        )
        .cte("physical_fields")
    )
    immediate = ancestors(physical, "immediate_owners")
    wrappers = ancestors(immediate, "wrapper_owners")
    return physical, immediate, wrappers, ancestors(wrappers, "section_owners")


def ordered_source_statement():
    text, selection, ordinary, valid, fields = _selection()
    physical, immediate, wrappers, sections = _physical(fields, text)
    section_children = _entries(immediate.c.node["children"], "section_children", order=True)
    recaps = (
        select(
            physical.c.pointer,
            physical.c.parent,
            physical.c.a,
            physical.c.b,
            immediate.c.node.label("section"),
            func.min(section_children.c.position).label("sibling_order"),
            cast(func.regexp_match(_translated(physical.c.text), _RECAP), ARRAY(Text)).label(
                "recap"
            ),
        )
        .select_from(
            physical.join(immediate, physical.c.parent == immediate.c.pointer).join(
                section_children, _str(section_children.c.value, "$ref") == physical.c.pointer
            )
        )
        .where(
            _body(immediate.c.node, "section"),
            physical.c.a >= _number(ordinary, "start"),
            physical.c.b <= _number(ordinary, "end"),
        )
        .group_by(
            physical.c.pointer,
            physical.c.parent,
            physical.c.a,
            physical.c.b,
            physical.c.text,
            immediate.c.node,
        )
        .having(func.count() == 1)
        .cte("recap_population")
    )
    recaps = (
        select(recaps)
        .where(recaps.c.recap.is_not(None), recaps.c.recap[3] == recaps.c.recap[5])
        .cte("inspected_recaps")
    )
    children = _entries(immediate.c.node["children"], "inline_children", order=True)
    wrapper_siblings = _entries(sections.c.node["children"], "wrapper_siblings", order=True)
    members = (
        select(
            wrappers.c.pointer.label("wrapper"),
            sections.c.pointer.label("section"),
            wrapper_siblings.c.position.label("sibling_order"),
            immediate.c.pointer.label("inline"),
            func.jsonb_array_length(immediate.c.node["children"]).label("population"),
            children.c.position,
            physical.c.pointer,
            physical.c.a,
            physical.c.b,
            func.lag(physical.c.b)
            .over(
                partition_by=(wrappers.c.pointer, wrapper_siblings.c.position),
                order_by=children.c.position,
            )
            .label("previous_end"),
        )
        .select_from(
            immediate.join(wrappers, immediate.c.parent == wrappers.c.pointer)
            .join(sections, wrappers.c.parent == sections.c.pointer)
            .join(wrapper_siblings, _str(wrapper_siblings.c.value, "$ref") == wrappers.c.pointer)
            .join(children, true())
            .join(
                physical,
                and_(
                    _str(children.c.value, "$ref") == physical.c.pointer,
                    physical.c.parent == immediate.c.pointer,
                ),
            )
        )
        .where(
            _body(immediate.c.node, "inline"),
            _body(wrappers.c.node, "text"),
            _body(sections.c.node, "section"),
            _str(wrappers.c.node, "text") == "",
            func.jsonb_array_length(wrappers.c.node["children"]) == 1,
            wrappers.c.node["children"][0]["$ref"].astext == immediate.c.pointer,
        )
        .cte("ordered_native_members")
    )
    spans = (
        select(
            members.c.wrapper,
            members.c.section,
            members.c.sibling_order,
            func.min(members.c.a).label("a"),
            func.max(members.c.b).label("b"),
            func.min(members.c.b).filter(members.c.position == 1).label("first_end"),
            cast(
                func.array_agg(aggregate_order_by(members.c.pointer, members.c.position)),
                ARRAY(Text),
            ).label("pointers"),
        )
        .group_by(
            members.c.wrapper, members.c.section, members.c.sibling_order, members.c.population
        )
        .having(
            members.c.population.between(2, 32),
            func.count() == members.c.population,
            func.count(func.distinct(members.c.pointer)) == members.c.population,
            func.bool_and((members.c.position == 1) | (members.c.previous_end == members.c.a)),
        )
        .cte("complete_wrappers")
    )
    declarations = select(
        spans,
        cast(
            func.regexp_match(_translated(_slice(text, spans.c.a, spans.c.b)), _DECLARATION),
            ARRAY(Text),
        ).label("declaration"),
    ).cte("declaration_shapes")
    d, r = declarations.c, recaps.c
    selection_start = _number(selection, "start")
    before = _slice(text, selection_start, r.a)
    symbol_pattern = func.replace(_PRIOR, "([A-Za-z])", literal("(") + r.recap[3] + ")")
    prior = (
        func.regexp_matches(before, symbol_pattern, "g")
        .table_valued(column("match", ARRAY(Text)))
        .render_derived(name="prior_bindings")
    )
    prior_count = (
        select(func.count())
        .select_from(prior)
        .where(prior.c.match[1] == r.recap[3])
        .correlate(recaps)
        .scalar_subquery()
    )
    # Offsets are lengths of captured prefixes, so repeated names elsewhere in the
    # same source item cannot shift a witness.
    symbol_a = d.a + func.length(d.declaration[1])
    description_a = symbol_a + func.length(d.declaration[2]) + func.length(d.declaration[3])
    description_b = description_a + func.length(d.declaration[4])
    name_a = description_b + func.length(d.declaration[5])
    equation_a = r.a + func.length(r.recap[1]) + func.length(r.recap[4])
    qualifying = (
        select(
            r.pointer.label("use_pointer"),
            d.pointers[1].label("declaration_pointer"),
            r.recap[3].label("symbol"),
            symbol_a.label("symbol_a"),
            (symbol_a + 1).label("symbol_b"),
            description_a.label("description_a"),
            description_b.label("description_b"),
            name_a.label("name_a"),
            (name_a + func.length(d.declaration[7])).label("name_b"),
            r.a.label("recap_a"),
            (r.a + func.length(r.recap[1])).label("recap_b"),
            equation_a.label("equation_a"),
            (equation_a + func.length(r.recap[6])).label("equation_b"),
        )
        .join(
            declarations, and_(d.section == r.parent, d.sibling_order < r.sibling_order, d.b <= r.a)
        )
        .where(
            d.declaration[2] == r.recap[3],
            d.declaration[7] == r.recap[2],
            func.starts_with(
                d.declaration[4], literal("a ") + d.declaration[6] + " with parameters "
            ),
            description_b <= d.first_end,
            ~_slice(text, description_a, description_b).op("~")(r"[;\n]"),
            prior_count == 1,
            selection_start + func.regexp_instr(before, symbol_pattern, 1, 1, 0, "", 1) - 1
            == symbol_a,
            select(func.count())
            .select_from(spans)
            .where(spans.c.wrapper == d.wrapper)
            .correlate(declarations)
            .scalar_subquery()
            == 1,
        )
        .cte("qualifying_declarations")
    )
    q = qualifying.c
    return select(
        func.jsonb_build_object(
            "valid",
            select(valid.c.valid).exists(),
            "inspected",
            select(func.count()).select_from(recaps).scalar_subquery(),
            "links",
            func.coalesce(
                select(
                    func.jsonb_agg(
                        aggregate_order_by(func.to_jsonb(qualifying.table_valued()), q.recap_a)
                    )
                )
                .select_from(qualifying)
                .scalar_subquery(),
                cast(literal("[]"), JSONB),
            ),
        )
    )


def ordered_report_statement():
    from ..methods.witnessed_source_links import ORDERED_LIMIT_REASON

    text, selection, ordinary, _valid, fields = _selection()
    view = literal_column("p_view")
    config = literal_column("p_config", type_=JSONB())
    population = _entries(literal_column("p_population", type_=JSONB()), "retained_row")
    operation_map = literal_column("p_operations", type_=JSONB())
    operations = (
        func.jsonb_each(operation_map)
        .table_valued(column("key", Text), column("value", JSONB))
        .render_derived(name="operations")
    )
    geometry = (
        select(cast(func.ops.ordered_formula_source(view, config), JSONB).label("body"))
        .cte("geometry")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    entries = _entries(geometry.c.body["links"], "source_links")
    links = (
        select(entries.c.value.label("row"))
        .select_from(geometry.join(entries, true()))
        .cte("source_links")
    )
    link = links.c.row
    op = (
        select(operations.c.key, operations.c.value)
        .where(_str(operations.c.value, "question") == "source_witnessed_links")
        .cte("witness_operation")
    )
    rows = (
        select(
            population.c.value.label("row"),
            _str(population.c.value, "contribution_id").label("id"),
            cast(func.data.record_source_json(population.c.value["value"]), JSONB).label("meaning"),
            _str(population.c.value, "operation_key").label("operation"),
        )
        .cte("retained_rows")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    body = rows.c.row
    meaning = rows.c.meaning
    pointer = _str(meaning, "source_pointer")
    role = _str(meaning, "role")
    component = body["component"]
    op_key = select(op.c.key).limit(1).scalar_subquery()
    native_dep = literal("native:") + cast(_field("native_task_id", BigInteger()), Text)
    pin = func.jsonb_build_object(
        "source",
        literal_column("p_source", type_=Text()),
        "native_product_task_id",
        _field("native_task_id", BigInteger()),
        "product_key",
        _field("native_product_key", Text()),
        "product_digest",
        _field("native_content_digest", Text()),
        "projection_digest",
        _field("projection_digest", Text()),
        "recipe_digest",
        _field("recipe_digest", Text()),
        "source_view_id",
        _field("id", BigInteger()),
    )

    def scope_key(value):
        return func.jsonb_build_array(
            _str(value, "passage_id"),
            _number(value, "start"),
            _number(value, "end"),
            _str(value, "effective_version"),
        )

    op_key_expected = literal("contribution-operation:") + func.encode(
        func.sha256(
            func.convert_to(
                func.data.canonical_json(
                    func.jsonb_build_array(
                        func.jsonb_build_array(
                            "source_witnessed_links",
                            "2",
                            pin,
                            func.jsonb_build_array(scope_key(ordinary), scope_key(selection)),
                        ),
                        func.jsonb_build_object(),
                    )
                ),
                "UTF8",
            )
        ),
        "hex",
    )

    def scalar_count(relation, where=None):
        statement = select(func.count()).select_from(relation)
        if where is not None:
            statement = statement.where(where)
        return statement.scalar_subquery()

    def anchors(a, b):
        f = fields.c
        lo = func.greatest(a, f.a)
        hi = func.least(b, f.b)
        return (
            select(
                func.jsonb_agg(
                    aggregate_order_by(
                        func.jsonb_build_array(f.pointer, lo - f.a, hi - f.a, _slice(text, lo, hi)),
                        f.a,
                    )
                )
            )
            .where(f.a < b, a < f.b)
            .correlate(links)
            .scalar_subquery()
        )

    actual = _entries(body["anchors"], "anchors", order=True)
    exact_anchors = (
        select(
            func.jsonb_agg(
                aggregate_order_by(
                    func.jsonb_build_array(
                        _str(actual.c.value, "pointer"),
                        _number(actual.c.value, "start"),
                        _number(actual.c.value, "end"),
                        _str(actual.c.value, "source_piece"),
                    ),
                    actual.c.position,
                )
            )
        )
        .where(
            _str(actual.c.value, "space") == "native",
            _str(actual.c.value, "precision") == "exact",
        )
        .correlate(rows)
        .scalar_subquery()
    )

    def member_match(name, *, address=None, versioned=False):
        a, b = (_number(link, name + "_" + k) for k in ("a", "b"))
        expected = anchors(a, b)
        return and_(
            _str(body, "kind") == "occurrence",
            role
            == {"name": "declared_name", "recap": "declaration_recap"}.get(
                name, name if name != "description" else "declaration"
            ),
            pointer == (address if address is not None else cast(expected, JSONB)[0][0].astext),
            _number(meaning, "start") == a,
            _number(meaning, "end") == b,
            _str(meaning, "text") == _slice(text, a, b),
            exact_anchors == expected,
            scalar_count(actual) == func.jsonb_array_length(expected),
            rows.c.operation == op_key
            if versioned
            else _str(operation_map[rows.c.operation], "question") == "source_structural_relations",
            _str(meaning, "region") == (_str(selection, "passage_id") if versioned else address),
        )

    def unique_id(condition, *, correlate):
        return (
            select(func.min(rows.c.id))
            .select_from(rows)
            .where(condition)
            .having(func.count() == 1)
            .correlate(correlate)
            .scalar_subquery()
        )

    declarations = select(
        link,
        unique_id(
            member_match("symbol", address=_str(link, "declaration_pointer")), correlate=links
        ).label("symbol"),
        unique_id(
            member_match("description", address=_str(link, "declaration_pointer")), correlate=links
        ).label("description"),
        unique_id(
            member_match("recap", address=_str(link, "use_pointer"), versioned=True),
            correlate=links,
        ).label("cue"),
        unique_id(member_match("name", versioned=True), correlate=links).label("target"),
        unique_id(
            and_(
                _str(operation_map[rows.c.operation], "question") == "source_formula_occurrences",
                role == "formula_symbol",
                pointer == _str(link, "use_pointer"),
                _str(meaning, "text") == _str(link, "symbol"),
                _number(meaning, "start") >= _number(link, "equation_a"),
                _number(meaning, "end") <= _number(link, "equation_b"),
            ),
            correlate=links,
        ).label("use"),
    ).cte("declaration_members")
    d = declarations.c
    prior = select(
        declarations,
        unique_id(
            and_(
                _str(operation_map[rows.c.operation], "question") == "source_structural_relations",
                _str(body, "kind") == "relation",
                _str(component, "attachment_kind") == "declares",
                body["members"] == func.jsonb_build_array(d.symbol, d.description),
            ),
            correlate=declarations,
        ).label("prior"),
    ).cte("prior_declarations")
    p = prior.c
    proof = select(
        prior,
        unique_id(
            and_(
                rows.c.operation == op_key,
                _str(body, "kind") == "relation",
                _str(component, "attachment_kind") == "declares",
                _str(component, "scope") == _str(selection, "scope"),
                _str(component, "effective_version").is_not_distinct_from(
                    _str(selection, "effective_version")
                ),
                body["members"] == func.jsonb_build_array(p.use, p.target),
                body["endpoints"]
                == func.jsonb_build_array(
                    func.jsonb_build_object("role", "attachment", "contribution_id", p.use),
                    func.jsonb_build_object("role", "target", "contribution_id", p.target),
                ),
                body["computation_dependencies"]
                == func.jsonb_build_array(p.use, p.target, native_dep, p.cue, p.prior),
            ),
            correlate=prior,
        ).label("relation"),
    ).cte("witness_proofs")
    published = select(proof).where(proof.c.use.is_not(None)).cte("expected_witnesses")
    eligible_count = scalar_count(published)
    expected_rows = (
        select(published.c.target)
        .union(select(published.c.cue), select(published.c.relation))
        .subquery()
    )
    emitted_count = scalar_count(rows, rows.c.operation == op_key)
    inspected = _number(geometry.c.body, "inspected")
    limited = eligible_count < inspected
    valid = and_(
        geometry.c.body["valid"] == cast(literal("true"), JSONB),
        scalar_count(op) == 1,
        op.c.key == op_key_expected,
        _str(op.c.value, "operation_version") == "2",
        _number(op.c.value, "inspected_count") == inspected,
        _number(op.c.value, "emitted_count") == emitted_count,
        op.c.value["computation_dependencies"] == func.jsonb_build_array(native_dep),
        emitted_count == scalar_count(expected_rows),
        _str(op.c.value, "outcome")
        == case((limited, "limited"), (eligible_count > 0, "succeeded"), else_="empty"),
        _str(op.c.value, "reason").is_not_distinct_from(case((limited, ORDERED_LIMIT_REASON))),
        ~select(prior).where(prior.c.prior.is_(None)).exists(),
        ~select(published)
        .where(
            (published.c.target.is_(None))
            | (published.c.cue.is_(None))
            | (published.c.relation.is_(None))
        )
        .exists(),
    )
    return select(
        func.coalesce(
            select(valid).select_from(geometry.join(op, true())).limit(1).scalar_subquery(), False
        )
    )


@lru_cache(maxsize=1)
def ordered_formula_witness_sql() -> str:
    """Render native functions for both deployment and independent catalog checks."""
    from sqlalchemy.dialects.postgresql import dialect

    definitions = (
        (
            "ordered_formula_source",
            "p_view kb.source_view,p_config jsonb",
            "kb.source_view,jsonb",
            "jsonb",
            ordered_source_statement(),
        ),
        (
            "ordered_formula_report",
            "p_view kb.source_view,p_config jsonb,p_population jsonb,"
            "p_operations jsonb,p_source text",
            "kb.source_view,jsonb,jsonb,jsonb,text",
            "boolean",
            ordered_report_statement(),
        ),
    )
    result = []
    for name, parameters, types, returns, statement in definitions:
        body = statement.compile(
            dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
        )
        result.append(f"""
CREATE OR REPLACE FUNCTION ops.{name}({parameters})
RETURNS {returns} LANGUAGE sql STABLE SECURITY INVOKER SET search_path=pg_catalog,pg_temp
BEGIN ATOMIC {body}; END;
REVOKE ALL ON FUNCTION ops.{name}({types}) FROM PUBLIC;
""")
    return "".join(result)
