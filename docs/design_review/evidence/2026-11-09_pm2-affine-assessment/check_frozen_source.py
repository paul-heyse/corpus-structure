"""Read the exact protected affine source and assess only the available bindings."""

import json
from pathlib import Path

from corpus_structure.evaluate.affine import assess_exact_affine
from corpus_structure.methods.math.prepared import PreparedMathInput
from corpus_structure.semantic.analysis_contracts import (
    SymbolDeclaration,
    prepare_interpretation_context,
)
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.settings import Settings


def main():
    previous = Path(__file__).resolve().parent.parent / "2026-11-09_pm2-adoption"
    inputs = json.loads((previous / "raw/query-inputs.json").read_bytes())
    (pin,) = inputs["sources"]
    (reference,) = [p for p in inputs["passages"] if p["passage_id"] == "affine"]
    request = StructuralPassageSelection(
        run_id=pin["run_id"],
        source_view_id=pin["source_view_id"],
        passage_id=reference["passage_id"],
        start=reference["start"],
        end=reference["end"],
        scope=reference["scope"],
    )
    with open_runtime_engine(Settings(), "pm2-affine-assessment", purpose="read") as reader:
        frozen = prepare_structural_sources(
            reader,
            (request,),
            read_budget=PublishedReadBudget(max_rows=100_000, max_bytes=256 * 1024 * 1024),
        )
    (source,) = frozen.sources
    (passage,) = frozen.passages
    if source.model_dump(mode="json") != pin or passage.text != reference["text"]:
        raise ValueError("selected affine source no longer matches the protected frame")
    cases = json.loads((previous / "raw/retrieval-case-source.json").read_bytes())
    first, second = (cases[key]["anchor"] for key in ("affine-x", "affine-z"))
    (native_start,) = [
        i
        for i, letter in enumerate(passage.text)
        if letter == "X" and passage.text[i:].startswith("X = σZ + μ.")
    ]
    if (
        first["pointer"] != second["pointer"]
        or (first["source_piece"], second["source_piece"]) != ("X", "Z")
        or first["start"] != native_start
        or second["start"] - first["start"] != len("X = σ")
    ):
        raise ValueError("frozen source carrier roles differ")
    literal = passage.text[native_start:-1]
    if literal != "X = σZ + μ":
        raise ValueError("protected equation differs")
    context = prepare_interpretation_context(
        macros={},
        bindings=({"kind": "unresolved", "symbol": "Z"},),
        kind="formula",
        source_id=source.identity,
        scope=reference["passage_id"],
        demand="symbolic",
    )
    result = assess_exact_affine(
        PreparedMathInput(
            context,
            r"X = \sigma Z + \mu",
            source_text=literal,
            source_start=passage.start + native_start,
        ),
        output="X",
        generator="Z",
        coefficient=r"\sigma",
        offset=r"\mu",
    )
    if result["outcome"] != "undecided":
        raise ValueError("an unauthenticated declaration must not qualify the affine case")

    fixture = "Set output y to gain g times input t, plus 1/8: y = gt + 1/8"
    calibration = prepare_interpretation_context(
        macros={},
        kind="formula",
        source_id="authored-calibration",
        scope="calibration-instruction",
        demand="symbolic",
        declarations=tuple(
            SymbolDeclaration(
                symbol,
                "variable",
                "source",
                evidence,
                "authored-calibration",
                "calibration-instruction",
            )
            for symbol, evidence in (("y", "output y"), ("g", "gain g"), ("t", "input t"))
        ),
    )
    control = assess_exact_affine(
        PreparedMathInput(
            calibration,
            r"y = gt + \frac{1}{8}",
            source_text="y = gt + 1/8",
            source_start=fixture.index("y ="),
        ),
        output="y",
        generator="t",
        coefficient="g",
        offset=r"\frac{1}{8}",
    )
    if control["outcome"] != "equivalent":
        raise ValueError(control["detail"])
    print(
        json.dumps(
            dict(source=pin, carriers=[first, second], assessment=result, calibration=control),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
