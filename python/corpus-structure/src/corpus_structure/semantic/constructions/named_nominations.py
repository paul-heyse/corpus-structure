"""Finite source-local demonstrative nominations for passive naming constructions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NamedNomination:
    demonstrative: bool | None
    status: str
    antecedent_nodes: tuple[int, ...] = ()
    antecedent_extents: tuple[tuple[int, int], ...] = ()
    context_start: int | None = None
    reason: str | None = None


def _signature(span, head):
    return tuple(
        (
            token.lemma_.casefold(),
            token.pos_,
            tuple(token.morph.get("Number", None)),
            (token.dep_, token.head.i - span.start) if token.i != head else None,
        )
        for token in span
    )


def naming_nomination(view, match, role):
    if (match.rule, match.variant) != ("naming", "passive_called_term"):
        return None
    columns = {
        column.attribute for column in view.product.availability if column.status == "complete"
    }
    if not {"DEP", "SENT_START"} <= columns:
        return NamedNomination(
            None,
            "unavailable",
            reason="demonstrative nomination requires retained dependency and sentence columns",
        )
    if not role.nodes:
        return NamedNomination(False, "not_applicable")
    doc, product = view.doc, view.product
    first = doc[role.nodes[0]]
    demonstrative = (
        first.i == first.sent.start
        and first.lower_ in {"this", "that", "these", "those"}
        and first.dep_ == "det"
        and first.head.i == role.head
    )
    if not demonstrative:
        return NamedNomination(False, "not_applicable")
    if not {"LEMMA", "POS", "MORPH"} <= columns:
        return NamedNomination(
            True,
            "unavailable",
            reason="restricted nominal resolution requires retained lemma/POS/morphology",
        )

    def unresolved(reason):
        return NamedNomination(True, "unresolved", reason=reason)

    start, end = role.nodes[0], role.nodes[-1] + 1
    if (
        role.status != "complete"
        or len(role.nodes) < 2
        or role.nodes != tuple(range(start, end))
        or not start
        or doc[role.head].pos_ != "NOUN"
    ):
        return unresolved("demonstrative role lacks one complete contiguous nominal")
    prior = doc[start - 1].sent
    head_offset = role.head - start - 1
    signature = _signature(doc[start + 1 : end], role.head)
    candidates = [
        index
        for index in range(prior.start, prior.end - len(signature) + 1)
        if _signature(doc[index : index + len(signature)], index + head_offset) == signature
    ]
    if len(candidates) != 1 or candidates[0] == prior.start:
        return unresolved("preceding sentence has no unique restricted nominal")
    nominal = candidates[0]
    article, head = doc[nominal - 1], doc[nominal + head_offset]
    if article.lower_ != "the" or article.dep_ != "det" or article.head != head:
        return unresolved("preceding nominal lacks its declared definite article relation")
    markers = [
        i
        for i in range(nominal + len(signature), prior.end - 2)
        if doc[i].lower_ == "such" and doc[i + 1].lower_ == "that"
    ]
    if len(markers) != 1 or head not in doc[markers[0] + 1].ancestors:
        return unresolved("preceding nominal lacks one attached such-that restriction")
    restriction = doc[markers[0] + 2 : prior.end]
    if not any(not token.is_punct for token in restriction) or any(
        token.is_quote
        or token.text in {";", ":"}
        or (
            token.i >= restriction.start
            and "Fin" in token.morph.get("VerbForm", None)
            and head not in token.ancestors
        )
        for token in prior
    ):
        return unresolved(
            "quotation, independent finite clause or terminator blocks "
            "restricted nominal inheritance"
        )
    piece = product.tokens[start].piece_indices
    if len(piece) != 1 or any(
        token.piece_indices != piece for token in product.tokens[prior.start : end]
    ):
        return unresolved(
            "restricted nominal and demonstrative do not share one original source piece"
        )
    nodes = tuple(range(article.i, prior.end))
    extents = tuple((product.tokens[index].start, product.tokens[index].end) for index in nodes)
    return NamedNomination(True, "resolved", nodes, extents, product.tokens[prior.start].start)
