"""Native Docling organization and source-qualified views; never Markdown round trips."""

from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class NativeSnapshot:
    payload: bytes
    digest: str
    schema_version: str


def snapshot(document: Any) -> NativeSnapshot:
    """Complete native normalization before immutable identity, not during a stored read."""
    document.validate_document()
    payload = json.dumps(
        document.export_to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return NativeSnapshot(payload, sha256(payload).hexdigest(), str(document.version))


def load_snapshot(value: NativeSnapshot) -> Any:
    """A read checks integrity and native shape without mutating retained meaning."""
    from docling_core.types.doc import DoclingDocument

    if sha256(value.payload).hexdigest() != value.digest:
        raise ValueError("native document integrity mismatch")
    document = DoclingDocument.model_validate_json(value.payload)
    # validate_document can clamp geometry. A retained product must already be normalized.
    if snapshot(document).payload != value.payload:
        raise ValueError("retained native document was not normalized before identity")
    if document.version != value.schema_version:
        raise ValueError("native schema version differs from binding")
    return document


def native_nodes(document: Any) -> dict[str, Any]:
    """Index all native collection nodes, including layers omitted by default traversal."""
    # The pinned native model retains this deprecated root for archived references.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=DeprecationWarning)
        furniture = document.furniture
    result = {document.body.self_ref: document.body, furniture.self_ref: furniture}
    for name in type(document).model_fields:
        if name in {"body", "furniture"}:
            continue
        collection = getattr(document, name)
        if isinstance(collection, list):
            for node in collection:
                if hasattr(node, "self_ref"):
                    if node.self_ref in result:
                        raise ValueError("duplicate native occurrence pointer")
                    result[node.self_ref] = node
    return result


@dataclass(frozen=True, slots=True)
class SectionPolicy:
    """Explicit application rule input; a native heading label alone is insufficient."""

    rule_id: str
    numbered_pattern: str = r"^\d+(?:\.\d+)*\s*[:.)-]?\s+\S"
    organizational_refs: frozenset[str] = frozenset()
    organizational_pattern: str = r"\S"
    local_heading_pattern: str = (
        r"(?i)^\s*(?:(?:proof|answer|solution)\b.*|"
        r"(?:definition|theorem|lemma|example|exercise|remark|corollary|proposition|claim|note)"
        r"(?:\s+\d+(?:\.\d+)*|\s*\([^)]*\))?\s*[:.]?)\s*$"
    )

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError("section policy requires its admitted rule identity")
        re.compile(self.numbered_pattern)
        re.compile(self.organizational_pattern)
        re.compile(self.local_heading_pattern)


@dataclass(frozen=True, slots=True)
class SectionBasis:
    """Convenience index over persisted facts, not an independent provenance artifact.

    A new group's first child is its source heading; native heading.level and the producing
    task's archived section policy provide level/rule. The parent product pin distinguishes
    pre-existing native groups from newly allocated organizational groups by pointer presence.
    """

    group_ref: str
    heading_ref: str
    level: int
    rule_id: str


@dataclass(frozen=True, slots=True)
class OrganizedDocument:
    source_digest: str
    document: NativeSnapshot
    sections: tuple[SectionBasis, ...]
    # Local pointers deliberately retain occurrence identity across this derivation only.
    source_pointers: tuple[str, ...]


def organize(source: NativeSnapshot, policy: SectionPolicy) -> OrganizedDocument:
    """Derive containers while retaining source occurrence pointers and native reading order.

    Each newly allocated group has its triggering native heading as its first child.
    Publication binds the immutable parent native product and producer configuration; together
    with that heading/containment relation they preserve the meaning indexed by SectionBasis.
    Existing native groups keep their original pointers and remain identifiable in the parent.
    """
    from docling_core.types.doc import ContentLayer, DocItemLabel, GroupLabel

    document = load_snapshot(source)
    nodes = native_nodes(document)
    missing = policy.organizational_refs - nodes.keys()
    if missing:
        raise ValueError(f"section policy names missing occurrences: {sorted(missing)}")
    for ref in policy.organizational_refs:
        if nodes[ref].label != DocItemLabel.SECTION_HEADER:
            raise ValueError("organizational selection is not a native heading")
    before = [
        n.self_ref
        for n, _ in document.iterate_items(
            traverse_pictures=True, included_content_layers=set(ContentLayer)
        )
    ]
    pattern = re.compile(policy.numbered_pattern)
    organizational = re.compile(policy.organizational_pattern)
    local = re.compile(policy.local_heading_pattern)
    section_rows: list[SectionBasis] = []
    original_pointers = tuple(nodes)

    def regroup(parent: Any) -> None:
        original = list(parent.children)
        parent.children = []
        stack: list[tuple[int, Any]] = []
        for reference in original:
            item = nodes[reference.cref]
            # Preserve existing list/table/picture and other native containment.
            if item.children:
                regroup(item)
            is_section = item.label == DocItemLabel.SECTION_HEADER and (
                item.self_ref in policy.organizational_refs
                or (
                    (
                        pattern.search(item.text) is not None
                        or organizational.search(item.text) is not None
                    )
                    and local.search(item.text) is None
                )
            )
            if is_section:
                level = item.level
                while stack and stack[-1][0] >= level:
                    stack.pop()
                group_parent = stack[-1][1] if stack else parent
                group = document.add_group(
                    label=GroupLabel.SECTION, name=item.text, parent=group_parent
                )
                stack.append((level, group))
                section_rows.append(
                    SectionBasis(group.self_ref, item.self_ref, level, policy.rule_id)
                )
            owner = stack[-1][1] if stack else parent
            item.parent = owner.get_ref()
            owner.children.append(item.get_ref())

    regroup(document.body)
    after = [
        n.self_ref
        for n, _ in document.iterate_items(
            traverse_pictures=True, included_content_layers=set(ContentLayer)
        )
    ]
    if before != after:
        raise ValueError("organization changed native content reading order")
    return OrganizedDocument(
        source.digest, snapshot(document), tuple(section_rows), original_pointers
    )


@dataclass(frozen=True, slots=True)
class ProjectedPiece:
    item_ref: str | None
    start: int
    end: int
    kind: Literal["native_text", "synthetic_separator"]
    cell_index: int | None = None
    source_field: Literal["text", "orig", "cell_text", "chart_title", "chart_cell_text"] | None = (
        None
    )

    def to_wire(self) -> dict[str, Any]:
        value: dict[str, Any] = dict(start=self.start, end=self.end, kind=self.kind)
        for name in ("item_ref", "cell_index", "source_field"):
            field = getattr(self, name)
            if field is not None:
                value[name] = field
        return value


@dataclass(frozen=True, slots=True)
class TextProjection:
    document_digest: str
    section_ref: str
    membership: Literal["direct", "descendant"]
    text: str
    pieces: tuple[ProjectedPiece, ...]


def project_section(
    document: Any,
    document_digest: str,
    section_ref: str,
    membership: Literal["direct", "descendant"],
    *,
    section_refs: frozenset[str],
    node_index: dict[str, Any] | None = None,
) -> TextProjection:
    """One explicit section view, retaining tables/cells and synthetic separators."""
    if membership not in {"direct", "descendant"}:
        raise ValueError("membership must be direct or descendant")
    nodes = native_nodes(document) if node_index is None else node_index
    if section_ref not in section_refs or section_ref not in nodes:
        raise ValueError("section selector is not qualified by this organization")
    text: list[str] = []
    pieces: list[ProjectedPiece] = []
    position = 0

    def append(
        value: str,
        ref: str,
        cell_index: int | None = None,
        source_field: Literal[
            "text", "orig", "cell_text", "chart_title", "chart_cell_text"
        ] = "text",
        separator: bool = True,
    ) -> None:
        nonlocal position
        if not value:
            return
        if text and separator:
            text.append("\n")
            pieces.append(ProjectedPiece(None, position, position + 1, "synthetic_separator"))
            position += 1
        text.append(value)
        pieces.append(
            ProjectedPiece(
                ref, position, position + len(value), "native_text", cell_index, source_field
            )
        )
        position += len(value)

    def visit(node: Any, separator: bool = True, cell_index: int | None = None) -> None:
        if node.content_layer.value != "body":
            return
        if (
            node.self_ref != section_ref
            and node.self_ref in section_refs
            and membership == "direct"
        ):
            return
        if hasattr(node, "data") and hasattr(node.data, "table_cells"):
            for index, cell in enumerate(node.data.table_cells):
                reference = getattr(cell, "ref", None)
                if reference is not None:
                    visit(nodes[reference.cref], cell_index=index)
                else:
                    append(cell.text, node.self_ref, index, "cell_text")
            # Rich-cell subtrees are represented by the cell above, not duplicated.
            return
        chart = getattr(getattr(node, "meta", None), "tabular_chart", None)
        if chart is not None:
            if chart.title:
                append(chart.title, node.self_ref, source_field="chart_title")
            for index, cell in enumerate(chart.chart_data.table_cells):
                append(cell.text, node.self_ref, index, "chart_cell_text")
        if hasattr(node, "text"):
            append(node.text, node.self_ref, cell_index, separator=separator)
        for index, child in enumerate(node.children):
            child_separator = (
                (separator if index == 0 else False) if str(node.label) == "inline" else True
            )
            visit(nodes[child.cref], separator=child_separator, cell_index=cell_index)

    visit(nodes[section_ref])
    return TextProjection(document_digest, section_ref, membership, "".join(text), tuple(pieces))
