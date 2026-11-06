"""One exact published placement and finite selected native read projections.

Public product identity stays the semantic three-part pin. Physical placement is
resolved once by its published reader and independently inside native effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import (
    BigInteger,
    Text,
    and_,
    any_,
    bindparam,
    case,
    func,
    literal,
    literal_column,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY, aggregate_order_by, array, dialect
from sqlalchemy.sql import Select, visitors
from sqlalchemy.sql.elements import BindParameter

from .metadata import table
from .product_reference import ProductReference


@dataclass(frozen=True, slots=True)
class PublishedDocumentBinding:
    reference: ProductReference
    native_build_id: str
    native_revision_id: str
    producer_release_id: str

    @classmethod
    def from_revision(cls, reference: ProductReference, revision: dict[str, Any]):
        if (
            (revision.get("task_id"), revision.get("product_key"), revision.get("logical_digest"))
            != (reference.task_id, reference.product_key, reference.content_digest)
            or not isinstance(revision.get("build_id"), str)
            or not revision["build_id"]
            or not isinstance(revision.get("release_id"), str)
            or not revision["release_id"]
        ):
            raise ValueError("published document placement differs from exact product pin")
        return cls(reference, revision["build_id"], revision["build_id"], revision["release_id"])

    def require_placement(self, row):
        if (row["native_build_id"], row["native_revision_id"]) != (
            self.native_build_id,
            self.native_revision_id,
        ):
            raise ValueError("published document address placement differs from product pin")


def published_read_statements() -> dict[str, Select]:
    """Resolve field/type references through the existing physical model once."""
    access = table("kb.pdf_record_access")
    region = table("kb.pdf_record_region")
    build, revision = (
        bindparam("_native_build_id", type_=Text()),
        bindparam("_native_revision_id", type_=Text()),
    )

    def bound(relation):
        return and_(relation.c.product_id == build, relation.c.revision_id == revision)

    selected = select(access).where(bound(access)).cte("access")
    lineage = (
        select(
            selected.c.pointer.label("section_pointer"),
            selected.c.parent_pointer.label("ancestor"),
            literal(0).label("depth"),
        )
        .where(selected.c.label.in_(("section", "chapter")), selected.c.parent_pointer.is_not(None))
        .cte("section_ancestors", recursive=True)
    )
    parent_node = selected.alias("parent_node")
    lineage = lineage.union_all(
        select(lineage.c.section_pointer, parent_node.c.parent_pointer, lineage.c.depth + 1)
        .join(parent_node, parent_node.c.pointer == lineage.c.ancestor)
        .where(parent_node.c.parent_pointer.is_not(None))
    )
    ancestor_path = (
        select(func.array_agg(aggregate_order_by(lineage.c.ancestor, lineage.c.depth.desc())))
        .where(lineage.c.section_pointer == selected.c.pointer)
        .scalar_subquery()
    )
    sections = (
        select(
            selected.c.pointer,
            selected.c.parent_pointer,
            selected.c.ordinal,
            selected.c.label,
            selected.c.content_layer,
            selected.c.native_json["name"].astext.label("name"),
            func.coalesce(ancestor_path, array([], type_=Text()))
            .cast(ARRAY(Text()))
            .label("ancestors"),
            selected.c.section_pointer,
            selected.c.text,
        )
        .where(selected.c.label.in_(("section", "chapter")))
        .order_by(selected.c.ordinal)
    )
    pointers = bindparam("p_pointers", type_=ARRAY(Text()))
    items = (
        select(access)
        .where(bound(access), access.c.pointer == any_(pointers))
        .order_by(access.c.ordinal)
    )
    root = bindparam("p_section", type_=Text())
    membership = bindparam("p_membership", type_=Text())
    members = (
        select(selected.c.pointer)
        .where(selected.c.pointer == root, selected.c.content_layer == "body")
        .cte("members", recursive=True)
    )
    child = selected.alias("child")
    members = members.union_all(
        select(child.c.pointer)
        .join(members, child.c.parent_pointer == members.c.pointer)
        .where(
            child.c.content_layer == "body",
            or_(membership == "descendants", child.c.label.not_in(("section", "chapter"))),
        )
    )
    ancestors = (
        select(selected.c.parent_pointer.label("pointer"))
        .where(selected.c.pointer == root, selected.c.parent_pointer.is_not(None))
        .cte("ancestors", recursive=True)
    )
    parent = selected.alias("parent")
    ancestors = ancestors.union_all(
        select(parent.c.parent_pointer)
        .join(ancestors, parent.c.pointer == ancestors.c.pointer)
        .where(parent.c.parent_pointer.is_not(None))
    )
    is_member = selected.c.pointer.in_(select(members.c.pointer))
    closure = (
        select(
            *selected.c,
            case((is_member, literal("selected")), else_=literal("ancestor")).label("role"),
        )
        .where(
            or_(
                is_member,
                and_(
                    selected.c.pointer.in_(select(ancestors.c.pointer)),
                    selected.c.pointer.not_in(("#/body", "#/furniture")),
                ),
            )
        )
        .order_by(selected.c.ordinal)
    )
    regions = select(region).where(
        bound(region),
        region.c.pointer == bindparam("p_pointer", type_=Text()),
        region.c.region_index == bindparam("p_region_index", type_=BigInteger()),
    )
    companion = table("kb.pdf_record_companion")
    reports = (
        select(
            companion.c.local_id,
            companion.c.ordinal,
            case(
                (companion.c.body["kind"].astext == "formula_outcomes", companion.c.body),
                else_=func.ops.pdf_companion_body(
                    companion.c.product_id,
                    companion.c.revision_id,
                    companion.c.family,
                    companion.c.local_id,
                    companion.c.body,
                    type_=companion.c.body.type,
                ),
            ).label("body"),
        )
        .where(
            bound(companion),
            companion.c.family == "native_metadata",
            companion.c.body["kind"].astext.in_(("formula_outcomes", "recognition_coverage")),
        )
        .cte("reports")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    scoped_reports = (
        select(reports)
        .where(
            or_(
                and_(
                    reports.c.body["kind"].astext == "formula_outcomes",
                    reports.c.body["pointer"].astext == any_(pointers),
                ),
                and_(
                    reports.c.body["kind"].astext == "recognition_coverage",
                    reports.c.body["value"]["section_pointer"].astext
                    == any_(bindparam("p_sections", type_=ARRAY(Text()))),
                ),
            )
        )
        .order_by(reports.c.ordinal, reports.c.local_id.collate("C"))
    )
    page_scope = (
        select(selected.c.pointer)
        .where(selected.c.pointer == root)
        .cte("page_scope", recursive=True)
    )
    descendant = selected.alias("page_child")
    page_scope = page_scope.union_all(
        select(descendant.c.pointer).join(
            page_scope, descendant.c.parent_pointer == page_scope.c.pointer
        )
    )
    section_filter = or_(
        root.is_(None),
        and_(membership == "direct", selected.c.section_pointer == root),
        and_(membership == "descendants", selected.c.pointer.in_(select(page_scope.c.pointer))),
    )
    pointer = bindparam("p_pointer", type_=Text())
    page = (
        select(*(column for column in selected.c if column.key != "native_json"))
        .where(
            section_filter,
            or_(pointer.is_(None), selected.c.pointer == pointer),
            selected.c.ordinal > bindparam("p_after", type_=BigInteger()),
        )
        .order_by(selected.c.ordinal)
        .limit(bindparam("p_limit", type_=BigInteger()))
    )
    all_regions = (
        select(region)
        .where(bound(region), region.c.pointer == pointer)
        .order_by(region.c.region_index)
    )
    region_batch = (
        select(region)
        .where(bound(region), region.c.pointer == any_(pointers))
        .order_by(region.c.pointer.collate("C"), region.c.region_index)
    )
    item_ancestry = (
        select(selected.c.pointer, selected.c.parent_pointer)
        .where(selected.c.pointer == pointer)
        .cte("item_ancestry", recursive=True)
    )
    ancestor = selected.alias("item_parent")
    item_ancestry = item_ancestry.union(
        select(ancestor.c.pointer, ancestor.c.parent_pointer).join(
            item_ancestry, ancestor.c.pointer == item_ancestry.c.parent_pointer
        )
    )
    item_ancestors = (
        select(*(column for column in selected.c if column.key != "native_json"))
        .where(selected.c.pointer.in_(select(item_ancestry.c.pointer)))
        .order_by(selected.c.ordinal)
    )
    return {
        "sections": sections,
        "section_nodes": closure,
        "items": items,
        "region": regions,
        "section_reports": scoped_reports,
        "item_page": page,
        "regions": all_regions,
        "region_batch": region_batch,
        "item_ancestors": item_ancestors,
    }


def _published_read_selectors():
    return {
        "sections": (),
        "section_nodes": (("p_section", Text()), ("p_membership", Text())),
        "items": (("p_pointers", ARRAY(Text())),),
        "region": (("p_pointer", Text()), ("p_region_index", BigInteger())),
        "section_reports": (("p_pointers", ARRAY(Text())), ("p_sections", ARRAY(Text()))),
        "item_page": (
            ("p_section", Text()),
            ("p_membership", Text()),
            ("p_pointer", Text()),
            ("p_after", BigInteger()),
            ("p_limit", BigInteger()),
        ),
        "regions": (("p_pointer", Text()),),
        "region_batch": (("p_pointers", ARRAY(Text())),),
        "item_ancestors": (("p_pointer", Text()),),
    }


def _published_read_guard(name):
    pointers = """
IF p_pointers IS NULL OR array_position(p_pointers,NULL) IS NOT NULL THEN RAISE EXCEPTION
'published item pointers are required' USING ERRCODE='22023'; END IF;"""
    return {
        "sections": "",
        "section_nodes": """
IF p_section IS NULL OR p_membership IS NULL OR p_membership NOT IN
('direct','descendants') OR NOT EXISTS(SELECT FROM kb.pdf_record_access a WHERE
 a.product_id=published.build_id AND a.revision_id=published.build_id AND
 a.pointer=p_section AND (a.label IN ('section','chapter') OR
 (p_section='#/body' AND p_membership='direct' AND a.parent_pointer IS NULL
 AND a.content_layer='body' AND a.native_json->>'self_ref'='#/body'))) THEN RAISE EXCEPTION
'invalid published section selection' USING ERRCODE='22023'; END IF;""",
        "items": pointers,
        "section_reports": """
IF p_pointers IS NULL OR p_sections IS NULL OR array_position(p_pointers,NULL) IS NOT NULL
OR array_position(p_sections,NULL) IS NOT NULL THEN RAISE EXCEPTION
'published report pointers/sections are required' USING ERRCODE='22023'; END IF;""",
        "region": """
IF p_pointer IS NULL OR p_region_index IS NULL OR p_region_index<0 THEN RAISE EXCEPTION
'invalid published region selector' USING ERRCODE='22023'; END IF;""",
        "item_page": """
IF p_membership IS NULL OR p_membership NOT IN ('direct','descendants') OR
p_after IS NULL OR p_after< -1 OR p_limit IS NULL OR p_limit<1 OR p_limit>1000 THEN
RAISE EXCEPTION 'invalid published item page selector' USING ERRCODE='22023'; END IF;""",
        "regions": """
IF p_pointer IS NULL THEN RAISE EXCEPTION 'published item pointer is required'
USING ERRCODE='22023'; END IF;""",
        "region_batch": pointers,
        "item_ancestors": """
IF p_pointer IS NULL THEN RAISE EXCEPTION 'published item pointer is required'
USING ERRCODE='22023'; END IF;""",
    }[name]


def _published_read_native(statement, selectors):
    variables = {key: key for key, _ in selectors}
    variables.update(_native_build_id="p_build", _native_revision_id="p_revision")

    def replace(element, **kw):
        if isinstance(element, BindParameter) and element.key in variables:
            return literal_column(variables[element.key], type_=element.type)
        return None

    native = visitors.replacement_traverse(statement, {}, replace)
    if not isinstance(native, Select):
        raise TypeError("native read lowering must retain its Core SELECT")
    return native


def published_readers_sql() -> str:
    """Guard exact publication first, then call its private Core-derived SQL body."""
    pg = dialect(paramstyle="named")
    quote = pg.identifier_preparer.quote
    result = []
    for name, statement in published_read_statements().items():
        selectors = _published_read_selectors()[name]
        native = _published_read_native(statement, selectors)
        body = str(native.compile(dialect=pg, compile_kwargs={"literal_binds": True}))
        selector_parameters = "".join(
            "," + key + " " + typ.compile(dialect=pg) for key, typ in selectors
        )
        selector_types = "".join("," + typ.compile(dialect=pg) for _, typ in selectors)
        selector_arguments = "".join("," + key for key, _ in selectors)
        columns = ",".join(
            quote(key) + " " + column.type.compile(dialect=pg)
            for key, column in statement.selected_columns.items()
        )
        function = "ops.read_pdf_published_" + name
        private = function + "_rows"
        result.append(f"""CREATE OR REPLACE FUNCTION {private}(
p_build text,p_revision text{selector_parameters})
RETURNS TABLE({columns}) LANGUAGE sql STABLE SECURITY INVOKER
SET search_path=pg_catalog,pg_temp BEGIN ATOMIC {body}; END;
REVOKE ALL ON FUNCTION {private}(text,text{selector_types}) FROM PUBLIC;
CREATE OR REPLACE FUNCTION {function}(
p_task bigint,p_product text,p_digest text{selector_parameters})
RETURNS TABLE({columns}) LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $read$
DECLARE published ops.pdf_published_revision;
BEGIN
 SELECT * INTO STRICT published FROM ops.read_pdf_published_revision(p_task,p_product,p_digest);
 PERFORM sem.require_execution_operation(published.release_id,'read_native_source');
 {_published_read_guard(name)}
 RETURN QUERY SELECT * FROM {private}(published.build_id,published.build_id{selector_arguments});
END $read$;
REVOKE ALL ON FUNCTION {function}(bigint,text,text{selector_types}) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION {function}(bigint,text,text{selector_types})
TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;
""")
    return "\n".join(result)


def published_reader_definitions(connection):
    """Explicit native definitions for the same public envelopes and private bodies."""
    from pglast import ast

    from .native_objects import definition_from_sql
    from .prepared_sql import prepare_sql

    prepared = prepare_sql(published_readers_sql(), source="published-document:forward")
    result = []
    for index, raw in enumerate(prepared.statements):
        if not isinstance(raw.stmt, ast.CreateFunctionStmt):
            continue
        names = tuple(part.sval for part in raw.stmt.funcname or ())
        private = names[-1].endswith("_rows")
        result.append(
            definition_from_sql(
                connection,
                prepared.excerpt(index),
                source="published-document:forward",
                owner="corpus_sem_publisher",
                grants=()
                if private
                else tuple(
                    (role, "EXECUTE", False)
                    for role in ("corpus_sem_reader", "corpus_sem_writer", "corpus_sem_evaluator")
                ),
            )
        )
    return tuple(result)


def published_address_precondition_sql() -> str:
    """Refuse legacy addresses lacking an exact published placement before successor DDL.

    This does not create compatibility publications or authorize migration. The
    native authoring owner runs it before adding/backfilling required placement.
    """
    published = table("ops.pdf_published_revision").alias("published")
    checks = []
    pg = dialect(paramstyle="named")
    for name, target in (
        ("kb.source_view", "kb.pdf_record_access"),
        ("ops.native_region_artifact", "kb.pdf_record_region"),
    ):
        consumer = table(name).alias("prior")
        relation = table(target).alias("address")
        placement_fk = next(
            key
            for key in table(name).foreign_key_constraints
            if key.referred_table.fullname == "ops.pdf_published_revision"
        )
        address_fk = next(
            key
            for key in table(name).foreign_key_constraints
            if key.referred_table.fullname == target
        )
        publication_match = [
            published.c[element.column.name] == consumer.c[element.parent.name]
            for element in placement_fk.elements
            if element.parent.name != "native_build_id"
        ]
        address_match = [
            relation.c[element.column.name]
            == (
                published.c.build_id
                if element.parent.name in {"native_build_id", "native_revision_id"}
                else consumer.c[element.parent.name]
            )
            for element in address_fk.elements
        ]
        valid = (
            select(literal(1))
            .select_from(published.join(relation, and_(*address_match)))
            .where(*publication_match)
            .correlate(consumer)
            .exists()
        )
        unbound = select(literal(1)).select_from(consumer).where(~valid)
        query = str(unbound.compile(dialect=pg, compile_kwargs={"literal_binds": True}))
        checks.append(
            f"IF EXISTS({query}) THEN RAISE EXCEPTION "
            "'unbound legacy published address in %; preserve archived revision', "
            f"'{name}' USING ERRCODE='55000'; END IF;"
        )
    return "DO $placement$ BEGIN " + "\n".join(checks) + " END $placement$;"
