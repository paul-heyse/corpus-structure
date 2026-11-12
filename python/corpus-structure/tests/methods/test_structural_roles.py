"""Independent retained dependency fixtures, not a spaCy provider efficacy claim."""

from types import SimpleNamespace

from corpus_structure.methods.structural_roles import procedure_frames


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

    from .primary_reading_fixture import primary_product

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


def values(text, frame, name):
    return tuple(text[a:b] for a, b in frame[name])


def test_passive_voice_keeps_agent_as_actor_and_subject_as_object():
    text = "Table 5.1 must be reviewed by Manager."
    product = annotation(
        text,
        [
            ("Table", "NOUN", "nsubjpass", 4, "NN"),
            ("5.1", "NUM", "nummod", 0, "CD"),
            ("must", "AUX", "aux", 4, "MD"),
            ("be", "AUX", "auxpass", 4, "VB"),
            ("reviewed", "VERB", "ROOT", 4, "VBN"),
            ("by", "ADP", "agent", 4, "IN"),
            ("Manager", "NOUN", "pobj", 5, "NN"),
        ],
    )
    (frame,) = procedure_frames(text, (product,))
    assert values(text, frame, "actor") == ("Manager",)
    assert values(text, frame, "object") == ("Table 5.1",)
    assert values(text, frame, "modality") == ("must",)
    assert frame["voice"] == "passive"
    # A modal cue alone leaves source function unresolved without policy context.
    assert frame["behavior"] == "described_or_example_unresolved"


def test_coordinated_actions_inherit_only_unambiguous_roles_and_keep_negation():
    text = "Manager must not inspect and approve Table 5.1."
    product = annotation(
        text,
        [
            ("Manager", "NOUN", "nsubj", 3, "NN"),
            ("must", "AUX", "aux", 3, "MD"),
            ("not", "PART", "neg", 3, "RB"),
            ("inspect", "VERB", "ROOT", 3, "VB"),
            ("and", "CCONJ", "cc", 3, "CC"),
            ("approve", "VERB", "conj", 3, "VB"),
            ("Table", "NOUN", "dobj", 5, "NN"),
            ("5.1", "NUM", "nummod", 6, "CD"),
        ],
    )
    frames = procedure_frames(text, (product,))
    assert len(frames) == 2
    assert all(values(text, f, "actor") == ("Manager",) for f in frames)
    assert all(values(text, f, "object") == ("Table 5.1",) for f in frames)
    # The shared source reading preserves the two possible scopes of not across and.
    assert frames[0]["polarity"] == "negative_scope_unresolved"
    assert frames[1]["polarity"] == "negative_scope_unresolved"


def test_source_conditions_and_order_are_dependency_cued_not_textual_order():
    text = "Manager reviews Table after Analyst signs Form."
    product = annotation(
        text,
        [
            ("Manager", "NOUN", "nsubj", 1, "NN"),
            ("reviews", "VERB", "ROOT", 1, "VBZ"),
            ("Table", "NOUN", "dobj", 1, "NN"),
            ("after", "SCONJ", "mark", 5, "IN"),
            ("Analyst", "NOUN", "nsubj", 5, "NN"),
            ("signs", "VERB", "advcl", 1, "VBZ"),
            ("Form", "NOUN", "dobj", 5, "NN"),
        ],
    )
    frames = procedure_frames(text, (product,))
    review = frames[0]
    earlier, later = review["orders"][0]
    assert text[slice(*earlier)] == "signs" and text[slice(*later)] == "reviews"
    assert values(text, frames[1], "actor") == ("Analyst",)


def test_missing_dependency_columns_supply_no_role_claims():
    product = SimpleNamespace(availability=(), tokens=(), dependency_digest="missing")
    assert procedure_frames("Manager reviews Table.", (product,)) == ()


def test_coordinate_passive_preserves_shared_agent_patient_and_explicit_modal_wins():
    text = "Table must be inspected and approved by Manager."
    product = annotation(
        text,
        [
            ("Table", "NOUN", "nsubjpass", 3, "NN"),
            ("must", "AUX", "aux", 3, "MD"),
            ("be", "AUX", "auxpass", 3, "VB"),
            ("inspected", "VERB", "ROOT", 3, "VBN"),
            ("and", "CCONJ", "cc", 3, "CC"),
            ("approved", "VERB", "conj", 3, "VBN"),
            ("by", "ADP", "agent", 5, "IN"),
            ("Manager", "NOUN", "pobj", 6, "NN"),
        ],
    )
    frames = procedure_frames(text, (product,))
    assert all(f["voice"] == "passive" for f in frames)
    assert all(values(text, f, "actor") == ("Manager",) for f in frames)
    assert all(values(text, f, "object") == ("Table",) for f in frames)
    text = "Manager must not inspect and may approve Table."
    product = annotation(
        text,
        [
            ("Manager", "NOUN", "nsubj", 3, "NN"),
            ("must", "AUX", "aux", 3, "MD"),
            ("not", "PART", "neg", 3, "RB"),
            ("inspect", "VERB", "ROOT", 3, "VB"),
            ("and", "CCONJ", "cc", 3, "CC"),
            ("may", "AUX", "aux", 6, "MD"),
            ("approve", "VERB", "conj", 3, "VB"),
            ("Table", "NOUN", "dobj", 6, "NN"),
        ],
    )
    frames = procedure_frames(text, (product,))
    assert values(text, frames[1], "modality") == ("may",)
    assert frames[1]["polarity"] == "positive"
