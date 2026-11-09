"""Select C's exact adjudicated source records from protected A and B submissions."""

import json
from pathlib import Path

RAW = Path(__file__).parent / "raw"
SELECTIONS = {
    51: (
        [("B", 0), ("B", 1)],
        "Retain the explicit assertion and the illustrated trial bound under its stated "
        "calculation circumstance. Do not flatten attributed doubt or invent the object of "
        "the passive simulation clause; these remain source limitations.",
    ),
    52: (
        [],
        "Both readers inspected the chapter heading and found no eligible reading.",
    ),
    53: (
        [("B", 0), ("B", 1), ("A", 2), ("A", 3), ("A", 4)],
        "Retain the three-piece definition name, the asserted consequence with the complete "
        "conditional operation, and the exact formula bindings with defensible first uses. "
        "Do not reconstruct ambiguous display typography or declare the local result a new symbol.",
    ),
}


def main():
    for unit, (selected, reason) in SELECTIONS.items():
        packet = json.loads((RAW / f"adjudication-{unit}.json").read_bytes())
        parents = dict(zip(("A", "B"), packet["adjudication_passes"], strict=True))
        reading = dict(
            unit_id=unit,
            reason=reason,
            adopt=[
                dict(pass_id=parents[author], record_index=index)
                for author, index in selected
            ],
        )
        with (RAW / f"reading-{unit}-c.json").open("x", encoding="utf-8") as stream:
            json.dump(reading, stream, ensure_ascii=False, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    main()
