"""One exact published placement and finite selected native read projections.

Public product identity stays the semantic three-part pin. Physical placement is
resolved once by its published reader and independently inside native effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import (
    BigInteger,
    Column,
    Text,
    and_,
    any_,
    bindparam,
    case,
    column,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY, aggregate_order_by, array
from sqlalchemy.sql import Select, visitors
from sqlalchemy.sql.elements import BindParameter

from corpus_structure.schema.integrity import role_name

from .metadata import table
from .native_objects import INTERNAL_PROGRAM, NativeProgramAccess, native_privilege_sql
from .native_program import (
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    ReturnQuery,
    SelectInto,
    column_type,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration, RenderedProgram
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


def published_read_statements(*, target_metadata=None) -> dict[str, Select]:
    """Resolve field/type references through the existing physical model once."""
    selected_table = table if target_metadata is None else target_metadata.tables.__getitem__
    access = selected_table("kb.pdf_record_access")
    region = selected_table("kb.pdf_record_region")
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
    companion = selected_table("kb.pdf_record_companion")
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
        and_(
            membership == "direct",
            or_(
                selected.c.section_pointer == root,
                and_(root == "#/body", selected.c.pointer.in_(select(members.c.pointer))),
            ),
        ),
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


def _published_read_selectors(name, statement):
    names = {
        "sections": (),
        "section_nodes": ("p_section", "p_membership"),
        "items": ("p_pointers",),
        "region": ("p_pointer", "p_region_index"),
        "section_reports": ("p_pointers", "p_sections"),
        "item_page": ("p_section", "p_membership", "p_pointer", "p_after", "p_limit"),
        "regions": ("p_pointer",),
        "region_batch": ("p_pointers",),
        "item_ancestors": ("p_pointer",),
    }[name]
    types = {
        element.key: element.type
        for element in visitors.iterate(statement)
        if isinstance(element, BindParameter)
    }
    return tuple((key, types[key]) for key in names)


def _published_read_guards(name, selectors, access, published) -> tuple[If, ...]:
    value = {key: core_variable(key, kind) for key, kind in selectors}
    if name == "sections":
        return ()
    if name in {"items", "region_batch"}:
        pointers = value["p_pointers"]
        condition = or_(pointers.is_(None), func.array_position(pointers, None).is_not(None))
        message = "published item pointers are required"
    elif name == "section_nodes":
        section, membership = value["p_section"], value["p_membership"]
        selected = access.alias("a")
        valid = (
            select(1)
            .select_from(selected)
            .where(
                selected.c.product_id == published["build_id"],
                selected.c.revision_id == published["build_id"],
                selected.c.pointer == section,
                or_(
                    selected.c.label.in_(("section", "chapter")),
                    and_(
                        section == "#/body",
                        membership == "direct",
                        selected.c.parent_pointer.is_(None),
                        selected.c.content_layer == "body",
                        selected.c.native_json["self_ref"].astext == "#/body",
                    ),
                ),
            )
            .exists()
        )
        condition = or_(
            section.is_(None),
            membership.is_(None),
            membership.not_in(("direct", "descendants")),
            ~valid,
        )
        message = "invalid published section selection"
    elif name == "section_reports":
        pointers, sections = value["p_pointers"], value["p_sections"]
        condition = or_(
            pointers.is_(None),
            sections.is_(None),
            func.array_position(pointers, None).is_not(None),
            func.array_position(sections, None).is_not(None),
        )
        message = "published report pointers/sections are required"
    elif name == "region":
        pointer, region = value["p_pointer"], value["p_region_index"]
        condition = or_(pointer.is_(None), region.is_(None), region < 0)
        message = "invalid published region selector"
    elif name == "item_page":
        membership, after, limit = value["p_membership"], value["p_after"], value["p_limit"]
        condition = or_(
            membership.is_(None),
            membership.not_in(("direct", "descendants")),
            after.is_(None),
            after < -1,
            limit.is_(None),
            limit < 1,
            limit > 1000,
        )
        message = "invalid published item page selector"
    elif name in {"regions", "item_ancestors"}:
        condition = value["p_pointer"].is_(None)
        message = "published item pointer is required"
    else:
        raise ValueError("unknown published reader selector")
    return (If(condition, (Raise(message, "22023"),)),)


def _published_read_native(statement, selectors):
    variables = {key: key for key, _ in selectors}
    variables.update(_native_build_id="p_build", _native_revision_id="p_revision")

    def replace(element, **kw):
        if isinstance(element, BindParameter) and element.key in variables:
            return core_variable(variables[element.key], element.type)
        return None

    native = visitors.replacement_traverse(statement, {}, replace)
    if not isinstance(native, Select):
        raise TypeError("native read lowering must retain its Core SELECT")
    return native


def published_readers_programs(*, target_metadata=None) -> tuple[ProgramDeclaration, ...]:
    """Guard exact publication first, then call its private Core-derived SQL body."""
    selected_table = table if target_metadata is None else target_metadata.tables.__getitem__
    publication = selected_table("ops.pdf_published_revision")
    access = selected_table("kb.pdf_record_access")
    published = {
        field.name: core_variable("published", field.type, field.name) for field in publication.c
    }
    producer_parameters = tuple(
        Parameter(key, column_type(field))
        for key, field in (
            ("p_task", publication.c.task_id),
            ("p_product", publication.c.product_key),
            ("p_digest", publication.c.logical_digest),
        )
    )
    placement_parameters = tuple(
        Parameter(key, column_type(field))
        for key, field in (
            ("p_build", access.c.product_id),
            ("p_revision", access.c.revision_id),
        )
    )
    result = []
    for name, statement in published_read_statements(target_metadata=target_metadata).items():
        selectors = _published_read_selectors(name, statement)
        selector_parameters = tuple(
            Parameter(key, column_type(Column(key, kind))) for key, kind in selectors
        )
        columns = tuple(
            (field.name, column_type(Column(field.name, field.type)))
            for field in statement.selected_columns
        )
        returns = pg_type("record")
        returns.setof = True
        public_name = "read_pdf_published_" + name
        private_name = public_name + "_rows"
        private_parameters = (*placement_parameters, *selector_parameters)
        public_parameters = (*producer_parameters, *selector_parameters)
        native = _published_read_native(statement, selectors)
        private = NativeRoutine(
            "ops",
            private_name,
            parameters=private_parameters,
            returns=returns,
            table_columns=columns,
            body=native,
            volatility="stable",
            search_path=("pg_catalog", "pg_temp"),
            sql_standard=True,
        )
        revision = func.ops.read_pdf_published_revision(
            *(
                core_variable(parameter.name, field.type)
                for parameter, field in zip(
                    producer_parameters,
                    (
                        publication.c.task_id,
                        publication.c.product_key,
                        publication.c.logical_digest,
                    ),
                    strict=True,
                )
            )
        ).table_valued(*(column(field.name, field.type) for field in publication.c))
        rows = getattr(func.ops, private_name)(
            published["build_id"],
            published["build_id"],
            *(core_variable(key, kind) for key, kind in selectors),
        ).table_valued(*(column(field.name, field.type) for field in statement.selected_columns))
        public = NativeRoutine(
            "ops",
            public_name,
            parameters=public_parameters,
            returns=returns,
            table_columns=columns,
            volatility="stable",
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
            body=Block(
                (
                    SelectInto(select(*revision.c), ("published",), strict=True),
                    Perform(
                        func.ops.require_pdf_operation(
                            published["release_id"], "read_native_source"
                        )
                    ),
                    *_published_read_guards(name, selectors, access, published),
                    ReturnQuery(select(*rows.c)),
                ),
                (Local("published", publication),),
            ),
        )
        result.extend(
            (
                ProgramDeclaration(
                    private, "published-document:forward", role_name("publisher"), INTERNAL_PROGRAM
                ),
                ProgramDeclaration(
                    public,
                    "published-document:forward",
                    role_name("publisher"),
                    NativeProgramAccess(purposes=("read", "write", "evaluate")),
                ),
            )
        )
    return tuple(result)


def published_readers_sql(*, target_metadata=None) -> str:
    """Render the bound private SELECTs and their guarded public reader declarations."""
    result = []
    for item in published_readers_programs(target_metadata=target_metadata):
        result.extend((item.render(), native_privilege_sql(item.identity, "PUBLIC", grant=False)))
        if item.access != INTERNAL_PROGRAM:
            result.extend(
                native_privilege_sql(item.identity, role, "EXECUTE")
                for role in (role_name("reader"), role_name("writer"), role_name("evaluator"))
            )
    return ";\n".join(result) + ";\n"


def published_reader_definitions(connection, *, target_metadata=None):
    """Bind the same explicit reader declarations without scanning rendered SQL."""
    return tuple(
        RenderedProgram(item, item.render(), frozenset(), frozenset()).definition(connection)
        for item in published_readers_programs(target_metadata=target_metadata)
    )
