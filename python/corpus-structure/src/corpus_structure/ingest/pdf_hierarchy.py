"""Native Docling organization and source-qualified views; never Markdown round trips."""

from __future__ import annotations

import json
import re
import warnings
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from hashlib import sha256
from importlib.resources import files
from typing import TYPE_CHECKING, Any, Literal

from corpus_structure.semantic.identity import canonical_bytes

if TYPE_CHECKING:
    from docling_core.types.doc import DoclingDocument

    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.types import PreparedRelease


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


def load_snapshot(value: NativeSnapshot) -> DoclingDocument:
    """Check exact bytes and declared native state without serializer normalization."""
    from corpus_structure.semantic.pdf_records import validate_native_callbacks

    from .pdf_retained_stream import derive_retained_native_projection

    if sha256(value.payload).hexdigest() != value.digest:
        raise ValueError("native document integrity mismatch")
    # Native exports include model-owned computed grids; record values omit them.
    # Verify that serialization view, then use the same strict supplied-state
    # callback boundary as publication. Export serializers are not native state.
    supplied = json.loads(value.payload)
    if not isinstance(supplied, dict):
        raise ValueError("native document must be a JSON object")
    native, _ = derive_retained_native_projection(supplied)
    document = validate_native_callbacks(native)
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


@cache
def _section_text_policy_bytes() -> bytes:
    return (
        files("corpus_structure").joinpath("model/semantic/section-text-recipe.json").read_bytes()
    )


def _section_text_policy_digest(prepared: PreparedRelease) -> str | None:
    return dict(json.loads(prepared.manifest)["dependencies"]).get(
        "execution/implementation/pdf/section-text-recipe.json"
    )


def section_text_policy(prepared: PreparedRelease) -> bytes:
    policy = _section_text_policy_bytes()
    digest = _section_text_policy_digest(prepared)
    if digest == sha256(policy).hexdigest():
        return policy
    raise ValueError("section text recipe differs from the selected release")


def retained_section_text_policy(
    connection, prepared: PreparedRelease, *, read_budget=None
) -> bytes | None:
    """Resolve formula policy bytes against the Reader's immutable release."""
    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table

    digest = _section_text_policy_digest(prepared)
    if digest is None:
        return None
    inputs = table("sem.input")
    statement = select(inputs.c.content).where(
        inputs.c.release_id == prepared.release_id,
        inputs.c.input_kind == "dependency",
        inputs.c.input_name == "execution/implementation/pdf/section-text-recipe.json",
    )
    if read_budget is not None:
        read_budget.preflight(connection, statement)
    content = connection.scalar(statement)
    if content is None or sha256(content).hexdigest() != digest:
        raise ValueError("section text policy differs from the retained release")
    retained = bytes(content)
    if read_budget is not None:
        read_budget.value(retained)
    return retained


def readable_formula_original(
    policy: Mapping[str, Any],
    original_digest: str | None,
    pointer: str,
    node: Any,
) -> str | None:
    """Select source-checked spelling only for the corresponding native occurrence."""

    def field(name, default=None):
        return (
            node.get(name, default) if isinstance(node, Mapping) else getattr(node, name, default)
        )

    original = field("orig")
    if not original:
        return None
    digest = sha256(original.encode()).hexdigest()
    if policy.get("recipe") != "native-section-text-v10":
        return None
    witnesses = [
        witness
        for witness in policy.get("readable_formula_originals", ())
        if witness["original_digest"] == original_digest and witness["pointer"] == pointer
    ]
    if len(witnesses) > 1:
        raise ValueError("readable formula witness is ambiguous")
    if not witnesses:
        return None
    witness = witnesses[0]
    parent = field("parent")
    parent_pointer = (
        parent.get("$ref") if isinstance(parent, Mapping) else getattr(parent, "cref", None)
    )
    provenance = [
        item
        if isinstance(item, Mapping)
        else item.model_dump(mode="json", by_alias=True, exclude_none=True)
        for item in (field("prov") or ())
    ]
    if (
        witness["orig_digest"] == digest
        and witness["parent"] == parent_pointer
        and witness["prov"] == provenance
    ):
        return original
    return None


def section_text_recipe(
    native_product: ProductReference, *, analysis_eligible: bool, policy: bytes | None = None
) -> bytes:
    return canonical_bytes(
        {
            **json.loads(policy if policy is not None else _section_text_policy_bytes()),
            "analysis_eligible": analysis_eligible,
            "organization_owner": native_product.values(),
        }
    )


def section_view_key(
    consumer_release: str,
    native: ProductReference,
    section: str,
    membership: str,
    analysis_eligible: bool,
    recipe: bytes,
) -> str:
    return (
        "source-view:"
        + sha256(
            canonical_bytes(
                {
                    "consumer_release": consumer_release,
                    "native": native.values(),
                    "section": section,
                    "membership": membership,
                    "analysis_eligible": analysis_eligible,
                    "recipe": sha256(recipe).hexdigest(),
                }
            )
        ).hexdigest()
    )


def project_section(
    document: Any,
    document_digest: str,
    section_ref: str,
    membership: Literal["direct", "descendant"],
    *,
    section_refs: frozenset[str],
    node_index: dict[str, Any] | None = None,
    selected_items: Iterable[str] = (),
    projection_policy: bytes | None = None,
    original_digest: str | None = None,
) -> TextProjection:
    """One explicit section view, retaining tables/cells and synthetic separators."""
    nodes = native_nodes(document) if node_index is None else node_index
    return project_section_nodes(
        nodes,
        document_digest,
        section_ref,
        membership,
        section_refs=section_refs,
        selected_items=selected_items,
        projection_policy=projection_policy,
        original_digest=original_digest,
    )


def retained_formula_originals(pieces: Iterable[Mapping[str, Any]]) -> frozenset[str]:
    """Reuse field choices already qualified by an immutable source view."""
    return frozenset(
        piece["item_ref"]
        for piece in pieces
        if piece.get("kind") == "native_text" and piece.get("source_field") == "orig"
    )


def project_section_nodes(
    nodes: Mapping[str, Any],
    document_digest: str,
    section_ref: str,
    membership: Literal["direct", "descendant"],
    *,
    section_refs: frozenset[str],
    selected_items: Iterable[str] = (),
    projection_policy: bytes | None = None,
    original_digest: str | None = None,
    retained_originals: frozenset[str] = frozenset(),
) -> TextProjection:
    """Project an admitted selected closure without fabricating a partial document.

    Native objects and retained native mappings share this constructor. Table caption
    recovery requires the caller's exact selected body membership. Subtree callers
    without such a selection use the existing structural traversal.
    """
    if membership not in {"direct", "descendant"}:
        raise ValueError("membership must be direct or descendant")
    if section_ref not in section_refs or section_ref not in nodes:
        raise ValueError("section selector is not qualified by this organization")
    text: list[str] = []
    pieces: list[ProjectedPiece] = []
    position = 0
    selected = frozenset(selected_items)
    emitted_captions: set[str] = set()
    policy = json.loads(projection_policy) if projection_policy is not None else {}

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

    def field(value: Any, name: str, default: Any = None) -> Any:
        return (
            value.get(name, default)
            if isinstance(value, Mapping)
            else getattr(value, name, default)
        )

    def reference(value: Any) -> str:
        pointer = field(value, "$ref") if isinstance(value, Mapping) else field(value, "cref")
        if not isinstance(pointer, str):
            raise ValueError("selected native closure is missing a referenced occurrence")
        return pointer

    def is_body(node: Any) -> bool:
        layer = field(node, "content_layer", "body")
        return field(layer, "value", layer) == "body"

    def append_table_captions(table: Any, pointer: str, rich_cell_refs: set[str]) -> None:
        for ref in (*field(table, "children", ()), *field(table, "captions", ())):
            target = reference(ref)
            if target not in selected or target in emitted_captions or target in rich_cell_refs:
                continue
            caption = nodes.get(target)
            if field(caption, "self_ref") != target or field(caption, "label") != "caption":
                continue
            parent = field(caption, "parent")
            value = field(caption, "text")
            # Native containment is a tree. A table-owned caption has no ordinary child path,
            # and a reference to a caption under an ordinary parent cannot move that caption.
            if parent is None or reference(parent) != pointer or not is_body(caption):
                continue
            if isinstance(value, str) and value:
                append(value, target)
                emitted_captions.add(target)

    def visit(node: Any, separator: bool = True, cell_index: int | None = None) -> None:
        if not is_body(node):
            return
        if (
            field(node, "self_ref") != section_ref
            and field(node, "self_ref") in section_refs
            and membership == "direct"
        ):
            return
        pointer = field(node, "self_ref")
        cells = field(field(node, "data"), "table_cells")
        if cells is not None:
            rich_cell_refs: set[str] = set()
            for index, cell in enumerate(cells):
                target = field(cell, "ref")
                if target is not None:
                    target_pointer = reference(target)
                    rich_cell_refs.add(target_pointer)
                    if target_pointer not in nodes:
                        raise ValueError(
                            "selected native closure is missing a rich-cell occurrence"
                        )
                    visit(nodes[target_pointer], cell_index=index)
                else:
                    append(field(cell, "text"), pointer, index, "cell_text")
            if (
                pointer in selected
                and nodes.get(pointer) is node
                and field(node, "label") == "table"
            ):
                append_table_captions(node, pointer, rich_cell_refs)
            # Rich-cell subtrees are represented by the cell above, not duplicated.
            return
        chart = field(field(node, "meta"), "tabular_chart")
        if chart is not None:
            if field(chart, "title"):
                append(field(chart, "title"), pointer, source_field="chart_title")
            for index, cell in enumerate(field(field(chart, "chart_data"), "table_cells")):
                append(field(cell, "text"), pointer, index, "chart_cell_text")
        value = field(node, "text")
        if value is not None:
            original = None
            if field(node, "label") == "formula":
                if pointer in retained_originals:
                    original = field(node, "orig")
                    if not original:
                        raise ValueError(
                            "selected readable original is missing from its native occurrence"
                        )
                else:
                    original = readable_formula_original(policy, original_digest, pointer, node)
            append(
                original if original is not None else value,
                pointer,
                cell_index,
                source_field="orig" if original is not None else "text",
                separator=separator,
            )
        for index, child in enumerate(field(node, "children", ())):
            target = reference(child)
            if target not in nodes:
                if membership == "direct" and target in section_refs:
                    continue
                raise ValueError("selected native closure is missing a referenced occurrence")
            child_separator = (
                (separator if index == 0 else False)
                if str(field(node, "label")) == "inline"
                else True
            )
            visit(nodes[target], separator=child_separator, cell_index=cell_index)

    visit(nodes[section_ref])
    return TextProjection(document_digest, section_ref, membership, "".join(text), tuple(pieces))
