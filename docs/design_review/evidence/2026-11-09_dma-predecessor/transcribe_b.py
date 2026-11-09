"""Transcribe the retained independent B notes, preserving their different role choices."""

import json

from transcribe_preface_a import CLAUSE, POINTER, RAW, field
from transcribe_section_a import (
    CONDITION,
    INTRO,
    PREDICATE,
    TERM,
    assertion,
    decision,
    definition,
    formula,
)


def preface_assertion():
    fields = {
        "subject": field("literal", [POINTER, "Probability theory"]),
        "predicate": field("literal", [POINTER, "makes predictions about"]),
        "object": field(
            "literal", [POINTER, "experiments whose outcomes depend upon chance"]
        ),
        "polarity": field(
            "classified",
            [POINTER, "makes predictions"],
            value=dict(kind="assertion_polarity", label="positive"),
        ),
        "modality": field(
            "classified",
            [POINTER, "makes predictions"],
            value=dict(kind="assertion_modality", label="asserted"),
        ),
    }
    for role, reason in {
        "attribution": "This clause does not name an attributed source.",
        "condition": "The relative clause limits the object; there is no separate condition.",
        "quantification": "The clause supplies no separate quantifier.",
        "scope": "The clause supplies no separate scope.",
    }.items():
        fields[role] = field(
            "literal", [POINTER, CLAUSE], state="unstated", reason=reason
        )
    return decision(
        "AssertionRecordFields",
        "assertion",
        ["subject", "predicate", "object"],
        **fields,
    )


def trial_bound():
    pointer = "#/texts/18"
    vicinity = [
        pointer,
        "being able to calculate exact binomial probabilities for experiments up to 1000 trials",
    ]
    return decision(
        "MeasurementRecordFields",
        "measurement",
        ["referent", "property", "original_value"],
        referent=field("literal", [pointer, "experiments"]),
        property=field("literal", [pointer, "trials"]),
        original_value=field("literal", [pointer, "1000"]),
        value_role=field(
            "classified",
            [pointer, "up to 1000 trials"],
            value=dict(kind="measurement_value_role", label="bound"),
        ),
        unit=field("literal", [pointer, "trials"]),
        comparator=field("literal", [pointer, "up to"]),
        uncertainty=field(
            "literal", vicinity, state="unstated", reason="No uncertainty is stated."
        ),
        reference_quantity=field(
            "literal",
            vicinity,
            state="unstated",
            reason="No separate reference quantity is stated.",
        ),
        condition=field(
            "literal", [pointer, "being able to calculate exact binomial probabilities"]
        ),
        normalized_value=dict(
            field(
                "normalized",
                vicinity,
                state="inapplicable",
                reason="This reference subset preserves original spelling only.",
            ),
            meaning_changing=False,
        ),
    )


def subsection():
    source = json.loads((RAW / "source-53.json").read_bytes())
    projected = source["source_frame"]["source_views"][0]["projection"]

    def whole(pointer):
        [piece] = [
            piece for piece in projected["pieces"] if piece.get("item_ref") == pointer
        ]
        return projected["text"][piece["start"] : piece["end"]]

    first, second = "#/texts/21403", "#/texts/21408"
    b_definition = definition()
    b_definition["fields"]["relation_type"]["locations"] = [
        ["#/texts/21405", "We call"],
        [INTRO, "define"],
    ]
    b_assertion = assertion()
    b_assertion["fields"]["polarity"]["locations"] = [[PREDICATE, "we get"]]
    b_assertion["fields"]["modality"]["locations"] = [[PREDICATE, "we get"]]
    b_assertion["fields"]["modality"]["value"]["label"] = "asserted"
    name = [[TERM, "moment generating function"], [PREDICATE, "for X"]]
    return [
        b_definition,
        b_assertion,
        formula(first, whole(first), "g(t)", 0, name),
        formula(first, whole(first), "t", 0, [[INTRO, "a new variable"]]),
        formula(second, whole(second), "g(t)", 0, name, [PREDICATE, CONDITION]),
    ]


def main():
    readings = [
        dict(
            unit_id=51,
            reason="B inspected the full selected preface. The direct assertion is explicit, "
            "as is the illustrative upper trial bound in its stated calculation context. "
            "B retained the passive simulation and attributed doubt as source limitations.",
            records=[preface_assertion(), trial_bound()],
        ),
        dict(
            unit_id=52,
            reason="B inspected both heading items; the chapter number is navigation, not a reading.",
            records=[],
        ),
        dict(
            unit_id=53,
            reason="B inspected the complete selected subsection. The stated consequent retains "
            "its ordered condition; the definition is the complete three-piece naming clause. "
            "The literal display bytes support the intact formula bindings recorded here. "
            "Other first-use or meaning ambiguities remain in the retained independent notes.",
            records=subsection(),
        ),
    ]
    for reading in readings:
        with (RAW / f"reading-{reading['unit_id']}-b.json").open(
            "x", encoding="utf-8"
        ) as stream:
            json.dump(reading, stream, ensure_ascii=False, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    main()
