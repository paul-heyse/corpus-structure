"""Retained primary navigation projections and downstream endpoint selection."""

from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import Any

from corpus_structure.semantic.constructions.navigation import (
    INHERITANCE_QUESTION as INHERITANCE_QUESTION,
)
from corpus_structure.semantic.constructions.navigation import (
    NAMED_NATIVE_PIECES_INPUT as NAMED_NATIVE_PIECES_INPUT,
)
from corpus_structure.semantic.constructions.navigation import (
    NAMED_PIECE_VERSION as NAMED_PIECE_VERSION,
)
from corpus_structure.semantic.constructions.navigation import (
    NAMED_QUESTION as NAMED_QUESTION,
)
from corpus_structure.semantic.constructions.navigation import (
    ORDERED_LIMIT_REASON as ORDERED_LIMIT_REASON,
)
from corpus_structure.semantic.constructions.navigation import (
    ORDERED_VERSION as ORDERED_VERSION,
)
from corpus_structure.semantic.constructions.navigation import (
    QUESTION as QUESTION,
)
from corpus_structure.semantic.constructions.navigation import (
    VERSION as VERSION,
)
from corpus_structure.semantic.constructions.navigation import (
    NamedCueWitness as NamedCueWitness,
)
from corpus_structure.semantic.constructions.navigation import (
    NamedLink as NamedLink,
)
from corpus_structure.semantic.constructions.navigation import (
    NamedLinkInspection as NamedLinkInspection,
)
from corpus_structure.semantic.constructions.navigation import (
    NamedLinkMatch as NamedLinkMatch,
)
from corpus_structure.semantic.constructions.navigation import (
    NavigationIndex,
    _children,
    _parent,
)
from corpus_structure.semantic.constructions.navigation import (
    OrderedRecappedDeclaration as OrderedRecappedDeclaration,
)
from corpus_structure.semantic.constructions.navigation import (
    RecappedDeclaration as RecappedDeclaration,
)
from corpus_structure.semantic.constructions.navigation import (
    ordered_witness_selection as ordered_witness_selection,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import StructuralPassage


def retained_artifact_fields(record, field_start):
    """Project explicit primary artifact fields into the domain's native-item coordinates."""
    from corpus_structure.semantic.artifact_identity import ArtifactSourceLabel

    pointer = record.payload["pointer"]

    def extent(span):
        return dict(
            source_pointer=pointer,
            start=span[0] - field_start,
            end=span[1] - field_start,
            text="".join(fragment["text"] for fragment in span[2]),
        )

    def role_extent(role):
        span = record.span(role)
        return None if span is None else extent((*span, record.fragments(role)))

    aliases = tuple(
        role_extent(role["role"])
        for role in record.payload["roles"]
        if role["role"].startswith("alias/")
    )
    aliases = tuple(alias for alias in aliases if alias is not None)
    fields = dict(
        aliases=tuple(alias["text"] for alias in aliases),
        alias_state=record.payload.get("alias_state", "unknown"),
        alias_occurrences=aliases,
    )
    absence = role_extent("alias_absence")
    if absence is not None:
        fields["alias_absence"] = absence
    labels = []
    for kind in ("numbering_namespace", "revision"):
        evidence = []
        for label in record.payload.get("source_labels", ()):
            if label["kind"] != kind:
                continue
            fragments = [
                e for oid in label["occurrences"] for e in record.occurrences[oid]["extents"]
            ]
            if len(fragments) != 1 or fragments[0]["text"] != label["value"]:
                raise ValueError("primary artifact label differs from its literal source")
            fragment = fragments[0]
            evidence.append(extent((fragment["start"], fragment["end"], fragments)))
        values = {row["text"] for row in evidence}
        labels.append(
            ArtifactSourceLabel(
                state="unknown" if not values else "observed" if len(values) == 1 else "unresolved",
                value=next(iter(values)) if len(values) == 1 else None,
                evidence=tuple(evidence),
            )
        )
    return fields, tuple(labels), record.text("caption_title") or None


def qualified_inheritance(contributions):
    """Project already-qualified list and clause inheritance without reattaching cues."""
    rows = {row["contribution_id"]: row for row in contributions}
    qualified = [
        row
        for row in contributions
        if row.get("component", {}).get("kind") == "predicate_qualifier"
        and row["component"]["qualifier_kind"] in {"condition", "assumption"}
    ]
    edges = []
    for row in qualified:
        component = row["component"]
        cue = rows[component["qualifier_contribution_id"]]
        host = rows[component["host_contribution_id"]]
        witness = component.get("host_witness")
        governing = cue["component"].get("governing_token")
        listed = witness is not None and witness["kind"] == "list_intro"
        coordinated = (
            witness is None
            and governing is not None
            and governing != host["component"]["predicate_token"]
        )
        if listed or coordinated:
            edges.append((cue, host, row))
    return len(qualified), tuple(edges)


def procedure_artifact_bindings(contributions):
    """Index settled scoped caption references by the exact located source mention."""
    rows = {row["contribution_id"]: row for row in contributions}
    references = {}
    for row in contributions:
        if row.get("component", {}).get("attachment_kind") != "artifact_reference_target":
            continue
        mention = source_python(rows[row["members"][0]]["value"])
        key = (mention["source_pointer"], mention["start"], mention["end"])
        references.setdefault(key, []).append(row["contribution_id"])
    return {
        key: tuple(identifiers) for key, identifiers in references.items() if len(identifiers) == 1
    }


def procedure_artifact_endpoint(rows, link, annotation, artifact_id):
    """Bind the recipe's exact action token to the original caption relationship."""
    from corpus_structure.semantic.observations import source_python

    verb = annotation.tokens[link.witness.tokens["verb"]]
    actions = [
        row
        for row in rows.values()
        if row.get("semantic_type") == "structural.located_participant"
        and (value := source_python(row["value"])).get("role") == "procedure_action"
        and (value["source_pointer"], value["start"], value["end"])
        == (link.pointer, verb.start, verb.end)
        and link.witness.annotation in row["computation_dependencies"]
    ]
    if len(actions) != 1:
        return None
    artifact = rows[artifact_id]
    return actions[0], rows[artifact["members"][1]], artifact


def navigation_index(primary_layers, projection, *, source_view_id=None):
    return NavigationIndex(primary_layers, projection, source_view_id=source_view_id)


class RetainedSourceMatch:
    """Located fields retained by a primary operation; this object never scans source text."""

    def __init__(self, record, source_start=0):
        self.record, self.source_start = record, source_start
        self.primary_node = record.reference.values()

    def span(self, group=0):
        names = {0: "match", 1: "symbol", 2: "description"}
        role = names.get(group, group)
        span = self.record.span(role)
        if span is None and group == 0:
            values = [self.record.span(r["role"]) for r in self.record.payload["roles"]]
            span = min(a for a, _ in values), max(b for _, b in values)
        if span is None:
            return (-1, -1)
        return span[0] - self.source_start, span[1] - self.source_start

    def start(self, group=0):
        return self.span(group)[0]

    def end(self, group=0):
        return self.span(group)[1]

    def __getitem__(self, group):
        role = {0: "match", 1: "symbol", 2: "description"}.get(group, group)
        return self.record.text(role).translate(str.maketrans("\n\t", "  "))


def retained_source_matches(index, kind, pointer, start, end):
    return tuple(
        RetainedSourceMatch(record, start)
        for record in index.select(kind, pointer)
        if all(
            start <= e["start"] < e["end"] <= end
            for r in record.payload["roles"]
            for e in record.fragments(r["role"])
        )
    )


def _retained_match(index, kind, pointer, start, end):
    found = retained_source_matches(index, kind, pointer, start, end)
    if kind == "symbol_declaration":
        found = tuple(match for match in found if match.start() == 0)
    return found[0] if len(found) == 1 else None


def symbol_declarations(index, pointer, start, end, *, introducer=None):
    return tuple(
        match
        for match in retained_source_matches(index, "symbol_declaration", pointer, start, end)
        if introducer is None or match.record.payload.get("introducer") == introducer
    )


def named_definition_subject(
    text,
    start,
    cue_start,
    *,
    version=NAMED_PIECE_VERSION,
    primary_layers=None,
    projection=None,
    source_view_id=None,
):
    index = NavigationIndex(primary_layers, projection, source_view_id=source_view_id)
    found = [
        (
            record.span("definition_subject"),
            record.payload["definition_subject_kind"],
            record.reference.values(),
        )
        for record in index.select("named_link")
        if record.span("cue")[0] == cue_start
        and record.span("definition_subject") is not None
        and start
        <= record.span("definition_subject")[0]
        < record.span("definition_subject")[1]
        <= cue_start
    ]
    return found[0][:2] if len(found) == 1 else None


def explicit_named_definition_extent(text, start, cue_start, **kwargs):
    found = named_definition_subject(text, start, cue_start, **kwargs)
    return None if found is None else found[0]


def retained_named_definition_subject(
    primary_layers, projection, *, start, cue_start, source_view_id=None
):
    """Return an exact subject plus its qualified primary support for contextual readers."""
    index = NavigationIndex(primary_layers, projection, source_view_id=source_view_id)
    found = [
        (
            record.span("definition_subject"),
            record.payload["definition_subject_kind"],
            record.reference.values(),
        )
        for record in index.select("named_link")
        if record.span("cue")[0] == cue_start
        and record.span("definition_subject") is not None
        and start
        <= record.span("definition_subject")[0]
        < record.span("definition_subject")[1]
        <= cue_start
    ]
    return found[0] if len(found) == 1 else None


def match_named_source_links(
    text,
    pieces,
    items,
    passages,
    annotations=(),
    *,
    annotation_errors=(),
    version=NAMED_PIECE_VERSION,
    native_piece_policy=None,
    primary_layers=None,
    projection=None,
    source_view_id=None,
):
    """Project primary named roles under the caller's source selection; never match a Doc."""
    if version != NAMED_PIECE_VERSION:
        raise ValueError("current named navigation requires the retained primary recipe")
    if primary_layers is None:
        primary_layers = {
            pin: report
            for annotation in annotations
            for pin, report in getattr(annotation, "primary_layers", {}).items()
        }
    if projection is None and annotations:
        projection = annotations[0].source.projection_digest
    if source_view_id is None and annotations:
        source_view_id = annotations[0].source.source_view_id
    index = NavigationIndex(primary_layers, projection, source_view_id=source_view_id)
    matches, inspected = [], set()
    incomplete = not index.complete or bool(annotation_errors)
    by_pointer = {p["item_ref"]: p for p in pieces if p["kind"] == "native_text"}
    for passage in passages or ():
        for record in index.select("named_availability"):
            extent = record.span("source")
            if extent is not None and extent[0] < passage.end and passage.start < extent[1]:
                if record.payload["status"] == "complete":
                    inspected.add(record.payload["pointer"])
                else:
                    incomplete = True
        for record in index.select("named_link"):
            nav = record.payload
            piece = by_pointer.get(nav["pointer"])
            if piece is None:
                raise ValueError("retained navigation has no selected native piece")
            lo, hi = max(passage.start, piece["start"]), min(passage.end, piece["end"])
            left, cue, right = record.span("subject"), record.span("cue"), record.span("argument")
            if (
                left is None
                or cue is None
                or not (lo <= left[0] < left[1] <= hi and lo <= cue[0] < cue[1] <= hi)
            ):
                continue
            scoped_right = right if right is None or lo <= right[0] < right[1] <= hi else None
            state = nav["resolution"] if scoped_right == right else "insufficient_evidence"
            subject = record.span("definition_subject")
            definition_subject = (
                (subject, nav["definition_subject_kind"])
                if subject is not None and lo <= subject[0] < subject[1] <= hi
                else None
            )
            witness = NamedCueWitness(
                rule=nav["rule"],
                variant=nav["variant"],
                mechanism=nav["mechanism"],
                kind=nav["relation_kind"],
                annotation=nav["annotation"],
                block=nav["block"],
                tokens={t["name"]: t["index"] for t in nav["native_tokens"]},
                subject=left,
                cue=cue,
                argument=scoped_right,
                designator=nav.get("designator"),
                scope=passage.scope,
                effective_version=passage.effective_version,
                resolution=state,
                primary_node=record.reference.values(),
            )
            matches.append(
                NamedLinkMatch(
                    pointer=nav["pointer"],
                    kind=nav["relation_kind"],
                    left=left,
                    cue=cue,
                    target_pointer=nav["pointer"] if state == "located" else None,
                    right=scoped_right,
                    scope=passage.scope,
                    passage=passage.passage_id,
                    resolution=state,
                    witness=witness,
                    definition_subject=definition_subject,
                )
            )
    return NamedLinkInspection(tuple(matches), len(inspected), incomplete, tuple(sorted(inspected)))


def named_source_links(
    text, pieces, items, passages, *, primary_layers=None, projection=None, source_view_id=None
):
    index = NavigationIndex(primary_layers, projection, source_view_id=source_view_id).require()
    found = []
    for passage in passages or ():
        for record in index.select("lexical_named_link"):
            nav = record.payload
            left, cue, right = record.span("subject"), record.span("cue"), record.span("argument")
            if (
                left is None
                or cue is None
                or not passage.start <= min(left[0], cue[0]) < max(left[1], cue[1]) <= passage.end
            ):
                continue
            target = nav["pointer"] if right is not None else None
            if nav["relation_kind"] in {"section_citation", "definition_reference"}:
                headings = [
                    row
                    for row in index.select("section_heading")
                    if row.payload["designator"] == nav["designator"]
                    and passage.start
                    <= row.span("heading")[0]
                    < row.span("heading")[1]
                    <= passage.end
                ]
                if len(headings) == 1:
                    target, right = headings[0].payload["pointer"], headings[0].span("heading")
            found.append(
                NamedLink(
                    nav["pointer"],
                    nav["relation_kind"],
                    left,
                    cue,
                    target,
                    right,
                    passage.scope,
                    passage.passage_id,
                    nav["resolution"] if nav["relation_kind"] == "external_citation" else None,
                    designator=nav.get("designator"),
                )
            )
    return tuple(found)


def ordered_recapped_declarations(
    text: str,
    pieces: Sequence[Mapping[str, Any]],
    items: Mapping[str, Mapping[str, Any]],
    passage: StructuralPassage,
    query: StructuralPassage,
    *,
    primary_layers=None,
    projection=None,
    source_view_id=None,
) -> tuple[int, tuple[OrderedRecappedDeclaration, ...]]:
    """Inspect only selected recaps, then authenticate their wider native premises.

    The ordinary query determines the inspected recap population. The broader
    premise passage is exact retained source, not a replacement query. Native
    whitespace substitution is local to cue matching and preserves coordinates.
    """
    index = NavigationIndex(primary_layers, projection, source_view_id=source_view_id).require()
    if (
        not 0 <= passage.start <= query.start < query.end <= passage.end <= len(text)
        or (passage.source_ref, passage.scope, passage.effective_version)
        != (query.source_ref, query.scope, query.effective_version)
        or passage.passage_id == query.passage_id
        or (passage.start, passage.end) == (query.start, query.end)
        or passage.end - passage.start > 4096
        or passage.text != text[passage.start : passage.end]
        or query.text != text[query.start : query.end]
    ):
        raise ValueError("ordered formula witness differs from its bounded selected source")
    selected = tuple(
        piece for piece in pieces if piece["start"] < passage.end and passage.start < piece["end"]
    )
    if (
        not selected
        or len(selected) > 128
        or selected[0]["start"] != passage.start
        or selected[-1]["end"] != passage.end
        or any(left["end"] != right["start"] for left, right in pairwise(selected))
    ):
        raise ValueError("ordered formula witness requires complete ordered projection pieces")
    physical = {}
    for piece in selected:
        if piece.get("kind") != "native_text" or piece.get("source_field", "text") != "text":
            continue
        pointer = piece.get("item_ref")
        a, b = piece["start"], piece["end"]
        if not isinstance(pointer, str):
            continue
        node = items.get(pointer, {})
        if (
            passage.start <= a < b <= passage.end
            and "cell_index" not in piece
            and node.get("content_layer") == "body"
            and node.get("label") == "text"
            and node.get("text") == text[a:b]
        ):
            if pointer in physical:
                raise ValueError("ordered formula witness repeats a selected source piece")
            physical[pointer] = (a, b)
    inspected, results = 0, []
    for use_pointer, (a, b) in physical.items():
        if not query.start <= a < b <= query.end:
            continue
        section = _parent(items[use_pointer])
        if not isinstance(section, str):
            continue
        container = items.get(section, {})
        if container.get("label") != "section" or container.get("content_layer") != "body":
            continue
        siblings = _children(container)
        sibling_counts = Counter(siblings)
        if sibling_counts[use_pointer] != 1:
            continue
        use = _retained_match(index, "recap", use_pointer, a, b)
        if use is None:
            continue
        inspected += 1
        symbol = use["symbol"]
        cues = [
            record.span("symbol")[0]
            for record in index.select("declaration_cue")
            if passage.start <= record.span("symbol")[0] < a and record.text("symbol") == symbol
        ]
        if len(cues) != 1:
            continue
        for paragraph in siblings[: siblings.index(use_pointer)]:
            if not isinstance(paragraph, str):
                continue
            owner = items.get(paragraph, {})
            groups = _children(owner)
            if (
                owner.get("label") != "text"
                or owner.get("content_layer") != "body"
                or _parent(owner) != section
                or owner.get("text") != ""
                or len(groups) != 1
                or sibling_counts[paragraph] != 1
            ):
                continue
            (inline,) = groups
            if not isinstance(inline, str):
                continue
            group = items.get(inline, {})
            children = _children(group)
            if (
                group.get("label") != "inline"
                or group.get("content_layer") != "body"
                or _parent(group) != paragraph
                or not 2 <= len(children) <= 32
                or len(set(children)) != len(children)
                or not all(
                    isinstance(child, str) and child in physical and _parent(items[child]) == inline
                    for child in children
                )
            ):
                continue
            parts = tuple(physical[child] for child in children)
            start, end = parts[0][0], parts[-1][1]
            if end > a or any(left[1] != right[0] for left, right in pairwise(parts)):
                continue
            binding = _retained_match(index, "declaration_template", inline, start, end)
            if (
                binding is None
                or start + binding.start("symbol") != cues[0]
                or binding["symbol"] != symbol
                or binding["name"] != use["name"]
                or start + binding.end("description") > parts[0][1]
            ):
                continue
            site, description, name = (
                (start + left, start + right)
                for left, right in map(binding.span, ("symbol", "description", "name"))
            )
            original_binding = _retained_match(
                index, "symbol_declaration", children[0], start, parts[0][1]
            )
            if (
                original_binding is None
                or original_binding.span(1) != (site[0] - start, site[1] - start)
                or original_binding.span(2) != (description[0] - start, description[1] - start)
            ):
                continue
            name_parts = tuple(
                (pointer, max(left, name[0]) - left, min(right, name[1]) - left)
                for pointer, (left, right) in zip(children, parts, strict=True)
                if left < name[1] and name[0] < right
            )
            results.append(
                OrderedRecappedDeclaration(
                    children[0],
                    use_pointer,
                    symbol,
                    name,
                    description,
                    (a, a + use.end("symbol")),
                    (a + use.start("equation"), a + use.end("equation")),
                    passage.scope,
                    passage.passage_id,
                    passage.effective_version,
                    site,
                    name_parts,
                    primary_node=use.primary_node,
                    declaration_node=binding.primary_node,
                )
            )
    return inspected, tuple(results)


def recapped_declarations(
    text, pieces, items, passages, *, primary_layers=None, projection=None, source_view_id=None
):
    """Resolve a named recap only within one complete selected passage and parent."""
    index = NavigationIndex(primary_layers, projection, source_view_id=source_view_id).require()
    physical = [
        p
        for p in pieces
        if p.get("kind") == "native_text"
        and p.get("source_field", "text") == "text"
        and "cell_index" not in p
        and items.get(p.get("item_ref"), {}).get("content_layer") == "body"
    ]
    for passage in passages or ():
        rows = [
            (p, items[p["item_ref"]], text[p["start"] : p["end"]])
            for p in physical
            if passage.start <= p["start"] < p["end"] <= passage.end
        ]
        for i, (piece, node, _literal) in enumerate(rows):
            use = _retained_match(index, "recap", piece["item_ref"], piece["start"], piece["end"])
            parent = node.get("parent")
            if use is None or parent is None:
                continue
            symbol, name = use["symbol"], use["name"]
            earlier = [
                (p, block)
                for p, other, block in rows[:i]
                if other.get("parent") == parent
                and any(
                    r.payload.get("variant") == "simple_let" and r.text("symbol") == symbol
                    for r in index.select("declaration_cue", p["item_ref"])
                )
            ]
            if (
                len(earlier) != 1
                or sum(
                    r.payload.get("variant") == "simple_let" and r.text("symbol") == symbol
                    for r in index.select("declaration_cue", earlier[0][0]["item_ref"])
                )
                != 1
            ):
                continue
            declaration, _declaration_text = earlier[0]
            binding = _retained_match(
                index,
                "declaration_template",
                declaration["item_ref"],
                declaration["start"],
                declaration["end"],
            )
            if binding is None or binding["symbol"] != symbol or binding["name"] != name:
                continue

            def extent(start, match, group):
                return start + match.start(group), start + match.end(group)

            yield RecappedDeclaration(
                declaration["item_ref"],
                piece["item_ref"],
                symbol,
                extent(declaration["start"], binding, "name"),
                extent(declaration["start"], binding, "description"),
                (piece["start"], piece["start"] + use.end("symbol")),
                extent(piece["start"], use, "equation"),
                passage.scope,
                passage.passage_id,
                passage.effective_version,
                primary_node=use.primary_node,
                declaration_node=binding.primary_node,
            )
