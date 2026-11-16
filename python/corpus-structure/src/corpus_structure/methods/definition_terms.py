"""Original-relative location of exact retained definition spans."""

from corpus_structure.semantic.source_contexts import evidence_anchor


def locate_definition_span(context, span, *, offset=0):
    """Map one retained half-open literal span through its actual source owner."""
    anchors, coordinates = [], []
    for piece in context.map_span(
        span["start"] - offset, span["end"] - offset, literal=span["text"], allow_multiple=True
    ):
        anchor, coordinate = evidence_anchor(context, piece, native=True)
        anchors.append(anchor)
        coordinates.append(coordinate)
    return tuple(anchors), tuple(coordinates)
