"""Independent retained dependency fixtures, not a spaCy provider efficacy claim."""

from dataclasses import replace

from corpus_structure.methods.structural_roles import procedure_frames
from methods.structural_roles_support import annotation as annotation


def values(text, frame, name):
    return tuple(text[a:b] for a, b in frame[name])


def test_passive_voice_keeps_agent_as_actor_and_subject_as_object():
    text = "Table 5.1 must be reviewed by Manager."
    product, primary = annotation(
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
        explicit_products=True,
    )
    (frame,) = procedure_frames(text, (product,), primary_products=(primary,))
    assert values(text, frame, "actor") == ("Manager",)
    assert values(text, frame, "object") == ("Table 5.1",)
    assert values(text, frame, "modality") == ("must",)
    assert frame["voice"] == "passive"
    # A modal cue alone leaves source function unresolved without policy context.
    assert frame["behavior"] == "described_or_example_unresolved"


def test_coordinated_actions_inherit_only_unambiguous_roles_and_keep_negation():
    text = "Manager must not inspect and approve Table 5.1."
    product, primary = annotation(
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
        explicit_products=True,
    )
    frames = procedure_frames(text, (product,), primary_products=(primary,))
    assert len(frames) == 2
    assert all(values(text, f, "actor") == ("Manager",) for f in frames)
    assert all(values(text, f, "object") == ("Table 5.1",) for f in frames)
    # The shared source reading preserves the two possible scopes of not across and.
    assert frames[0]["polarity"] == "negative_scope_unresolved"
    assert frames[1]["polarity"] == "negative_scope_unresolved"


def test_source_conditions_and_order_are_dependency_cued_not_textual_order():
    text = "Manager reviews Table after Analyst signs Form."
    product, primary = annotation(
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
        explicit_products=True,
    )
    frames = procedure_frames(text, (product,), primary_products=(primary,))
    review = frames[0]
    earlier, later = review["orders"][0]
    assert text[slice(*earlier)] == "signs" and text[slice(*later)] == "reviews"
    assert values(text, frames[1], "actor") == ("Analyst",)


def test_missing_dependency_columns_supply_no_role_claims():
    product, primary = annotation(
        "Manager reviews Table.",
        [
            ("Manager", "NOUN", "nsubj", 1, "NN"),
            ("reviews", "VERB", "ROOT", 1, "VBZ"),
            ("Table", "NOUN", "dobj", 1, "NN"),
        ],
        explicit_products=True,
    )
    missing = replace(product, availability=())
    assert procedure_frames("Manager reviews Table.", (missing,), primary_products=(primary,)) == ()


def test_coordinate_passive_preserves_shared_agent_patient_and_explicit_modal_wins():
    text = "Table must be inspected and approved by Manager."
    product, primary = annotation(
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
        explicit_products=True,
    )
    frames = procedure_frames(text, (product,), primary_products=(primary,))
    assert all(f["voice"] == "passive" for f in frames)
    assert all(values(text, f, "actor") == ("Manager",) for f in frames)
    assert all(values(text, f, "object") == ("Table",) for f in frames)
    text = "Manager must not inspect and may approve Table."
    product, primary = annotation(
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
        explicit_products=True,
    )
    frames = procedure_frames(text, (product,), primary_products=(primary,))
    assert values(text, frames[1], "modality") == ("may",)
    assert frames[1]["polarity"] == "positive"
