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

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError("section policy requires its admitted rule identity")
        re.compile(self.numbered_pattern)


@dataclass(frozen=True, slots=True)
class SectionBasis:
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
                item.self_ref in policy.organizational_refs or pattern.search(item.text) is not None
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
) -> TextProjection:
    """One explicit section view, retaining tables/cells and synthetic separators."""
    if membership not in {"direct", "descendant"}:
        raise ValueError("membership must be direct or descendant")
    nodes = native_nodes(document)
    if section_ref not in section_refs or section_ref not in nodes:
        raise ValueError("section selector is not qualified by this organization")
    text: list[str] = []
    pieces: list[ProjectedPiece] = []
    position = 0

    def append(value: str, ref: str, cell_index: int | None = None) -> None:
        nonlocal position
        if not value:
            return
        if text:
            text.append("\n")
            pieces.append(ProjectedPiece(None, position, position + 1, "synthetic_separator"))
            position += 1
        text.append(value)
        pieces.append(
            ProjectedPiece(ref, position, position + len(value), "native_text", cell_index)
        )
        position += len(value)

    def visit(node: Any) -> None:
        if (
            node.self_ref != section_ref
            and node.self_ref in section_refs
            and membership == "direct"
        ):
            return
        if hasattr(node, "data") and hasattr(node.data, "table_cells"):
            for index, cell in enumerate(node.data.table_cells):
                append(cell.text, node.self_ref, index)
            # Rich-cell formula children are represented by the cell above, not duplicated.
            return
        if hasattr(node, "text"):
            append(node.text, node.self_ref)
        for child in node.children:
            visit(nodes[child.cref])

    visit(nodes[section_ref])
    return TextProjection(document_digest, section_ref, membership, "".join(text), tuple(pieces))
