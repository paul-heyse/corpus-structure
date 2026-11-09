"""Transcribe the separately retained source reading A into explicit sealing decisions."""

import json
from pathlib import Path

RAW = Path(__file__).parent / "raw"
POINTER = "#/texts/16008"
CLAUSE = "Probability theory makes predictions about experiments whose outcomes depend upon chance"


def field(kind, location, *, state="present", **details):
    return dict(
        kind=kind, state=state, meaning_changing=True, locations=[location], **details
    )


def main():
    fields = {
        "subject": field("literal", [POINTER, "Probability theory"]),
        "predicate": field("literal", [POINTER, "makes predictions about"]),
        "object": field(
            "literal", [POINTER, "experiments whose outcomes depend upon chance"]
        ),
        "polarity": field(
            "classified",
            [POINTER, "makes"],
            value=dict(kind="assertion_polarity", label="positive"),
        ),
        "modality": field(
            "classified",
            [POINTER, "makes"],
            value=dict(kind="assertion_modality", label="asserted"),
        ),
    }
    for role, reason in {
        "attribution": "The local clause states the relation directly without a named source.",
        "condition": "The relative clause restricts the object; there is no separate condition.",
        "quantification": "The local clause states no quantifier.",
        "scope": "The local clause states no separate scope.",
    }.items():
        fields[role] = field(
            "literal", [POINTER, CLAUSE], state="unstated", reason=reason
        )
    readings = [
        dict(
            unit_id=51,
            reason="A read the complete preface and retained one direct assertion. A separately "
            "recorded an embedded attributed stance as a source limitation.",
            records=[
                dict(
                    contract="AssertionRecordFields",
                    family="assertion",
                    occurrence_roles=["subject", "predicate", "object"],
                    fields=fields,
                )
            ],
        ),
        dict(
            unit_id=52,
            reason="A inspected the heading and structural wrapper; no eligible family reading.",
            records=[],
        ),
    ]
    for reading in readings:
        with (RAW / f"reading-{reading['unit_id']}-a.json").open(
            "x", encoding="utf-8"
        ) as stream:
            json.dump(reading, stream, ensure_ascii=False, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    main()
