"""Explicit cross-block qualifier witnesses over the selected native tree."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .predicate_frames import FrameCue, LocatedFrameSpan

if TYPE_CHECKING:
    from corpus_structure.ingest.annotations import AnnotationProduct


@dataclass(frozen=True, slots=True)
class CrossBlockTarget:
    frame: str
    reading: str
    interpretation: str
    polarity: str
    annotation: AnnotationProduct
    predicate: int


@dataclass(frozen=True, slots=True)
class CrossBlockQualifier:
    source: AnnotationProduct
    cue: FrameCue
    targets: tuple[CrossBlockTarget, ...]
    witness: dict[str, str] | None


def _cue(product, variant, start, stop, marker):
    tokens = product.tokens

    def span(first, end):
        return LocatedFrameSpan(
            tuple(range(first, end)),
            ((tokens[first].start, tokens[end - 1].end),),
        )

    return FrameCue(
        product.block_id,
        product.dependency_digest,
        "assumption",
        variant,
        span(start, stop),
        span(marker, marker + 1),
        "located",
        (),
        None,
    )


def _sentences(product):
    by_sentence = defaultdict(list)
    for index, token in enumerate(product.tokens):
        if token.sentence is not None:
            by_sentence[token.sentence].append(index)
    return tuple(tuple(indices) for indices in by_sentence.values())


def _whole_piece(product, piece):
    return piece is not None and (product.block_start, product.block_end) == (
        piece["start"],
        piece["end"],
    )


def _siblings(items, node):
    parent = items.get((node.get("parent") or {}).get("$ref"), {})
    children = tuple(ref["$ref"] for ref in parent.get("children", ()))
    pointer = node["self_ref"]
    if children.count(pointer) != 1:
        return (), -1
    return children, children.index(pointer)


def cross_block_qualifiers(frame, annotations, selected, hosts, population, native, pieces):
    """Return one local cue with exact frame references per authenticated layout route."""
    items = {item["self_ref"]: item for item in (*native["ancestors"], *native["items"])}
    selected_items = {item["self_ref"] for item in native["items"]}
    by_piece = {piece.get("item_ref"): piece for piece in pieces if "cell_index" not in piece}
    position = {piece.get("item_ref"): i for i, piece in enumerate(pieces)}
    by_block = defaultdict(list)
    for host in hosts:
        by_block[host.annotation.block_id].append(host)
    text = frame.text

    def complete_block(product):
        return (
            product.block_id in selected_items
            and selected.start <= product.block_start < product.block_end <= selected.end
            and _whole_piece(product, by_piece.get(product.block_id))
            and items[product.block_id].get("content_layer") == "body"
        )

    def words(product):
        return tuple(text[token.start : token.end] for token in product.tokens)

    def list_intro(product, node, spelling, sentences):
        prefix = ("for", "each", "of", "the", "following", ",", "assume", "that")
        tokens = product.tokens
        if (
            product.kind != "paragraph"
            or len(sentences) != 1
            or tuple(s.lower() for s in spelling[:8]) != prefix
            or len(spelling) < 11
            or spelling[-1] != ":"
            or tokens[6].dependency != "ROOT"
            or sum(t.head == 6 and t.dependency == "ccomp" for t in tokens[8:-1]) != 1
        ):
            return None
        cue = _cue(product, "list_assumption", 6, len(tokens) - 1, 6)
        siblings, index = _siblings(items, node)
        if index < 0 or index + 1 == len(siblings):
            return CrossBlockQualifier(product, cue, (), None)
        group = siblings[index + 1]
        group_node = items.get(group, {})
        children = tuple(ref["$ref"] for ref in group_node.get("children", ()))
        following = position[product.block_id] + 1
        if (
            group not in selected_items
            or siblings.count(group) != 1
            or group_node.get("label") != "list"
            or group_node.get("content_layer") != "body"
            or group_node.get("parent") != node.get("parent")
            or not children
            or len(set(children)) != len(children)
            or following == len(pieces)
            or pieces[following].get("item_ref") != children[0]
        ):
            return CrossBlockQualifier(product, cue, (), None)
        targets = []
        for pointer in children:
            candidates = [
                target
                for target in by_block[pointer]
                if target.annotation.tokens[target.predicate].dependency == "ROOT"
                and target.annotation.tokens[target.predicate].pos in {"VERB", "AUX"}
            ]
            if len(candidates) != 1:
                continue
            (host,) = candidates
            if (
                sum(
                    t.dependency == "ROOT" and t.pos in {"VERB", "AUX"}
                    for t in host.annotation.tokens
                )
                != 1
            ):
                continue
            child = items.get(pointer, {})
            if (
                host.annotation.kind == "list_item"
                and child.get("label") == "list_item"
                and child.get("parent") == {"$ref": group}
                and complete_block(host.annotation)
            ):
                targets.append(host)
        return CrossBlockQualifier(
            product, cue, tuple(targets), dict(kind="list_intro", list_group=group)
        )

    def parameter_note(product, node, spelling, sentences):
        suffix = ("and", "thus", "it", "is", "assumed", "to", "be", "positive", ".")
        tokens = product.tokens
        for indices in sentences:
            a, b = indices[0], indices[-1] + 1
            folded = tuple(s.lower() for s in spelling[a:b])
            if (
                b - a < 13
                or folded[:2] != ("the", "parameter")
                or sum(folded[i : i + 2] == ("the", "parameter") for i in range(len(folded) - 1))
                != 1
                or folded[-9:] != suffix
                or len(spelling[a + 2]) != 1
                or not spelling[a + 2].isalpha()
            ):
                continue
            assumed = b - 5
            if (
                tokens[b - 7].head != assumed
                or tokens[b - 7].dependency != "nsubjpass"
                or tokens[b - 6].head != assumed
                or tokens[b - 6].dependency != "auxpass"
                or tokens[b - 4].head != b - 3
                or tokens[b - 4].dependency != "aux"
                or tokens[b - 3].head != assumed
                or tokens[b - 3].dependency != "xcomp"
                or tokens[b - 2].head != b - 3
                or tokens[b - 2].dependency != "acomp"
            ):
                continue
            cue = _cue(product, "parameter_positive", b - 7, b - 1, assumed)
            siblings, index = _siblings(items, node)
            targets = []
            if index >= 2:
                origin, display = siblings[index - 2 : index]
                host_candidates = by_block[origin]
                if (
                    items.get(display, {}).get("label") == "formula"
                    and display in selected_items
                    and items[display].get("content_layer") == "body"
                    and items.get(origin, {}).get("label") == "text"
                    and items[display].get("parent") == node.get("parent")
                    and items.get(origin, {}).get("parent") == node.get("parent")
                    and position.get(origin) == position[product.block_id] - 2
                    and position.get(display) == position[product.block_id] - 1
                ):
                    for host in host_candidates:
                        if not complete_block(host.annotation):
                            continue
                        for relation in population.values():
                            comp = relation.get("component", {})
                            if (
                                comp.get("qualifier_kind") != "parameterization"
                                or comp.get("host_contribution_id") != host.frame
                            ):
                                continue
                            parameter = population[comp["qualifier_contribution_id"]]["component"]
                            if parameter["variant"] != "nominal_parameter_pair":
                                continue
                            symbol = host.annotation.tokens[parameter["token_indices"][-1]]
                            if text[symbol.start : symbol.end] == spelling[a + 2]:
                                targets.append((host, relation["contribution_id"]))
            if len(targets) == 1:
                host, predecessor = targets[0]
                yield CrossBlockQualifier(
                    product,
                    cue,
                    (host,),
                    dict(kind="parameter_note", parameterization=predecessor),
                )
            else:
                yield CrossBlockQualifier(product, cue, (), None)

    for product in annotations:
        if not complete_block(product):
            continue
        node = items[product.block_id]
        if node.get("label") != "text":
            continue
        spelling = words(product)
        sentences = _sentences(product)
        intro = list_intro(product, node, spelling, sentences)
        if intro is not None:
            yield intro
        yield from parameter_note(product, node, spelling, sentences)
