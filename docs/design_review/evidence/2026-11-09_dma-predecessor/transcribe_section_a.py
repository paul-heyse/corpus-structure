"""Transcribe the independent A source decisions for the retained native subsection."""

import json
from pathlib import Path

from transcribe_preface_a import field

RAW = Path(__file__).parent / "raw"
SECTION = "#/groups/590"
INTRO = "#/texts/2100"
TERM = "#/texts/21406"
PREDICATE = "#/texts/21407"
CONDITION = "if we differentiate g(t) n times and then set t = 0"


def literal(*locations, meaning_changing=True):
    return dict(
        kind="literal",
        state="present",
        meaning_changing=meaning_changing,
        locations=locations,
    )


def absent(kind, reason, *, meaning_changing=True):
    return dict(
        kind=kind,
        state="unstated",
        meaning_changing=meaning_changing,
        locations=[[SECTION]],
        reason=reason,
    )


def decision(contract, family, primary, **fields):
    return dict(
        contract=contract, family=family, occurrence_roles=primary, fields=fields
    )


def definition():
    cue = "#/texts/21405"
    return decision(
        "DefinitionRecordFields",
        "definition",
        ["term", "defining_text"],
        term=literal([TERM, "moment generating function"]),
        defining_text=literal(
            [cue, "We call g(t) the "],
            [TERM, "moment generating function"],
            [PREDICATE, " for X"],
        ),
        scope=field("native", [SECTION]),
        alias=absent(
            "literal",
            "g(t) is the named notation, not another term for the name.",
            meaning_changing=False,
        ),
        relation_type=dict(
            kind="classified",
            state="present",
            meaning_changing=False,
            value=dict(kind="definition_relation", label="definition"),
            locations=[[cue, "call"]],
        ),
    )


def assertion():
    return decision(
        "AssertionRecordFields",
        "assertion",
        ["subject", "predicate", "object"],
        subject=literal([PREDICATE, "we", 1]),
        predicate=literal([PREDICATE, "get"]),
        object=literal([PREDICATE, "μn"]),
        polarity=field(
            "classified",
            [PREDICATE, "get"],
            value=dict(kind="assertion_polarity", label="positive"),
        ),
        modality=field(
            "classified",
            [PREDICATE, "if we differentiate"],
            value=dict(kind="assertion_modality", label="hypothetical"),
        ),
        attribution=absent(
            "literal",
            "The local voice is first-person plural; no separate attribution.",
        ),
        condition=literal([PREDICATE, CONDITION]),
        quantification=absent(
            "literal", "n times is part of the stated operation in the condition."
        ),
        scope=absent(
            "literal",
            "No scope separate from the displayed local definition and condition.",
        ),
    )


def formula(pointer, exact, symbol, first, meaning, assumption=None):
    return decision(
        "FormulaRecordFields",
        "formula_context",
        ["formula", "symbol"],
        formula=literal([pointer, exact]),
        scope=field("native", [SECTION]),
        symbol=literal([pointer, symbol, first]),
        meaning=literal(*meaning),
        domain=absent(
            "literal",
            "The subsection does not state a separate domain for this binding.",
        ),
        assumption=literal(assumption)
        if assumption
        else absent(
            "literal",
            "No separate assumption is written for this displayed definition.",
        ),
    )


def main():
    source = json.loads((RAW / "source-53.json").read_bytes())
    projected = source["source_frame"]["source_views"][0]["projection"]

    def whole(pointer):
        [piece] = [
            piece for piece in projected["pieces"] if piece.get("item_ref") == pointer
        ]
        return projected["text"][piece["start"] : piece["end"]]

    first, second = "#/texts/21403", "#/texts/21408"
    name = [[TERM, "moment generating function"], [PREDICATE, " for X"]]
    reading = dict(
        unit_id=53,
        reason="A inspected all items in the retained subsection. The naming clause and preceding "
        "display identify the definition; the ordered differentiation and substitution "
        "are a condition. Exact formula binding records preserve t and g(t) where the "
        "first source spelling is independently identifiable. Other ambiguous compact "
        "notation remains in A's retained source limitations.",
        records=[
            definition(),
            assertion(),
            formula(first, whole(first), "t", 0, [[INTRO, "a new variable"]]),
            formula(first, whole(first), "g(t)", 0, name),
            formula(second, whole(second), "g(t)", 0, name, [PREDICATE, CONDITION]),
        ],
    )
    with (RAW / "reading-53-a.json").open("x", encoding="utf-8") as stream:
        json.dump(reading, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
