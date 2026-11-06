"""Independent retained dependency fixtures, not a spaCy provider efficacy claim."""

from types import SimpleNamespace

from corpus_structure.methods.structural_roles import procedure_frames


def annotation(text, specifications):
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
    return SimpleNamespace(
        tokens=tuple(tokens),
        availability=(
            SimpleNamespace(attribute="DEP", status="complete"),
            SimpleNamespace(attribute="POS", status="complete"),
        ),
        dependency_digest="independent-fixture",
    )


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
    assert frame["voice"] == "passive" and frame["behavior"] == "prescribed"


def test_coordinated_actions_inherit_only_unambiguous_roles_and_keep_negation():
    text = "Manager must not inspect and approve Table 5.1."
    product = annotation(
        text,
        [
            ("Manager", "NOUN", "nsubj", 4, "NN"),
            ("must", "AUX", "aux", 4, "MD"),
            ("not", "PART", "neg", 4, "RB"),
            ("inspect", "VERB", "ROOT", 3, "VB"),
            ("and", "CCONJ", "cc", 3, "CC"),
            ("approve", "VERB", "conj", 3, "VB"),
            ("Table", "NOUN", "dobj", 5, "NN"),
            ("5.1", "NUM", "nummod", 6, "CD"),
        ],
    )
    # Independent fixture heads: auxiliaries and subject belong to inspect.
    for i in range(3):
        product.tokens[i].head = 3
    frames = procedure_frames(text, (product,))
    assert len(frames) == 2
    assert all(values(text, f, "actor") == ("Manager",) for f in frames)
    assert all(values(text, f, "object") == ("Table 5.1",) for f in frames)
    assert frames[0]["polarity"] == "negative"
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
