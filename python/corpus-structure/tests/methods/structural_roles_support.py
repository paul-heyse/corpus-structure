"""Controlled inputs and builders shared by the structural roles consumers."""

from types import SimpleNamespace


def annotation(text, specifications, *, source_pin=None):
    tokens = []
    cursor = 0
    for word, pos, dependency, head, tag in specifications:
        start = text.index(word, cursor)
        end = start + len(word)
        cursor = end
        tokens.append(
            SimpleNamespace(
                start=start,
                end=end,
                pos=pos,
                dependency=dependency,
                head=head,
                tag=tag,
                role="prose",
                space=False,
                sentence=0,
            )
        )
    from hashlib import sha256

    from corpus_structure.ingest.annotations import (
        AnnotationAvailability,
        AnnotationProduct,
        AnnotationProfile,
        SentenceAnnotation,
        TokenAnnotation,
    )
    from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.source_contexts import NativeSourcePin
    from methods.primary_reading_fixture import primary_product

    if cursor < len(text) and text[cursor:] == ".":
        root = next(i for i, t in enumerate(tokens) if t.dependency == "ROOT")
        tokens.append(
            SimpleNamespace(
                start=cursor,
                end=len(text),
                pos="PUNCT",
                dependency="punct",
                head=root,
                tag=".",
                role="prose",
                sentence=0,
            )
        )
    profile = AnnotationProfile()
    digest = sha256(text.encode()).hexdigest()
    rows = tuple(
        TokenAnnotation(
            t.start,
            t.end,
            text[t.end : t.end + 1] == " ",
            t.role,
            text[t.start : t.end].lower(),
            t.pos,
            t.tag,
            (),
            t.dependency,
            t.head,
            t.sentence,
            (0,),
        )
        for t in tokens
    )
    product = AnnotationProduct(
        source=source_pin
        or NativeSourcePin(
            7,
            "source:7",
            ProductReference(17, "integrated", "a" * 64),
            "#/groups/7",
            "descendants",
            "b" * 64,
            "c" * 64,
            3,
        ),
        block_id="#/texts/0",
        kind="paragraph",
        block_start=0,
        block_end=len(text),
        display_spans=(),
        text_digest=digest,
        native_pieces=(ProjectedPiece("#/texts/0", 0, len(text), "native_text"),),
        layout_digest=digest,
        layout_recipe="canonical-token-layout-1",
        profile_recipe=profile.recipe,
        profile_digest=sha256(canonical_bytes(profile.identity())).hexdigest(),
        spacy_version=profile.configuration.spacy_version,
        model=profile.configuration.model,
        model_version=profile.configuration.model_version,
        components=(),
        pipeline_config_digest=digest,
        availability=tuple(
            AnnotationAvailability(name, "complete")
            for name in ("LEMMA", "POS", "TAG", "MORPH", "DEP", "SENT_START")
        ),
        tokens=rows,
        sentences=(SentenceAnnotation(0, len(text)),),
        dependency_digest=digest,
    )
    return primary_product(text, product, profile)
