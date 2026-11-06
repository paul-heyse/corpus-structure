"""Consumer-local native views over authenticated retained linguistic columns.

No tokenizer or language-model pipeline runs here. Callers restore source/profile
custody with ``restore_annotations`` before constructing a view. The mutable Doc
belongs to this demand; source pieces and sentence ownership remain detached.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from spacy.tokens import Doc
from spacy.vocab import Vocab

from .annotations import AnnotationProduct, AnnotationUnavailable
from .sentences import Block, boundaries


@dataclass(frozen=True)
class AnnotationView:
    product: AnnotationProduct
    doc: Doc

    def check_layout(self) -> None:
        """A matcher cannot silently consume a retokenized or altered native view."""
        product = self.product
        if (
            len(self.doc) != len(product.tokens)
            or sha256(self.doc.text.encode()).hexdigest() != product.text_digest
        ):
            raise ValueError("annotation view text/token population changed")
        for native, retained in zip(self.doc, product.tokens, strict=True):
            if (
                native.idx + product.block_start,
                native.idx + product.block_start + len(native.text),
                bool(native.whitespace_),
            ) != (retained.start, retained.end, retained.space):
                raise ValueError("annotation view was retokenized")


def annotation_view(
    product: AnnotationProduct,
    text: str,
    vocab: Vocab,
    *,
    required: tuple[str, ...] = ("LEMMA", "POS", "TAG", "MORPH", "DEP", "SENT_START"),
) -> AnnotationView:
    """Restore a whole block with absolute block-token dependency head indices.

    ``text`` is exactly the retained block, not the whole source projection. Native
    sentence inference is checked against retained ownership rather than assuming
    ``sent_starts`` survives construction with heads (spaCy overrides it).
    """
    availability = {column.attribute: column.status for column in product.availability}
    if any(availability.get(name) not in {"complete", "not_applicable"} for name in required):
        raise AnnotationUnavailable(
            "retained columns cannot satisfy native view demand", availability=product.availability
        )
    if (
        len(text) != product.block_end - product.block_start
        or sha256(text.encode()).hexdigest() != product.text_digest
    ):
        raise ValueError("annotation block text differs from retained source")
    rows = product.tokens
    if any(
        not product.block_start <= row.start < row.end <= product.block_end
        or not 0 <= row.head < len(rows)
        for row in rows
    ):
        raise ValueError("invalid retained token extent or head index")
    # These indices are already absolute within the original block Doc. Do not
    # apply the relative HEAD-array convention to the constructor's heads argument.
    complete_dep = availability.get("DEP") == "complete"
    doc = Doc(
        vocab,
        words=[
            text[row.start - product.block_start : row.end - product.block_start] for row in rows
        ],
        spaces=[row.space for row in rows],
        lemmas=[row.lemma for row in rows],
        pos=[row.pos for row in rows],
        tags=[row.tag for row in rows],
        morphs=["|".join(row.morphology) for row in rows],
        heads=[row.head for row in rows] if complete_dep else None,
        deps=[row.dependency for row in rows] if complete_dep else None,
        sent_starts=None if complete_dep else [row.start in {s.start for s in product.sentences} for row in rows],
    )
    view = AnnotationView(product, doc)
    view.check_layout()
    if rows:
        actual = tuple(
            (product.block_start + a, product.block_start + b)
            for a, b in boundaries(Block(text, (), (), ()), doc)
        )
        expected = tuple((sentence.start, sentence.end) for sentence in product.sentences)
        if actual != expected:
            raise AnnotationUnavailable(
                "reconstructed dependency sentences differ from retained ownership"
            )
    for native, retained in zip(doc, rows, strict=True):
        if (
            native.lemma_, native.pos_, native.tag_,
            tuple(str(native.morph).split("|")) if str(native.morph) else (),
        ) != (retained.lemma, retained.pos, retained.tag, retained.morphology):
            raise ValueError("native view changed retained linguistic columns")
        if complete_dep and (native.dep_, native.head.i) != (retained.dependency, retained.head):
            raise ValueError("native view changed retained dependency columns")
    return view
