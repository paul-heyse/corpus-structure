"""Independent exact-form expectations and provenance/refusal controls."""

import json

import pytest

from corpus_structure.evaluate.affine import NonzeroPremise, assess_exact_affine
from corpus_structure.methods.math.prepared import PreparedMathInput
from corpus_structure.semantic.analysis_contracts import (
    SymbolDeclaration,
    prepare_interpretation_context,
)


def _context(*names, scope="statement-a", assumptions=(), competing=False):
    declarations = [
        SymbolDeclaration(name, "variable", "source", f"source:{scope}:{name}", "fixture", scope)
        for name in names
    ]
    if competing:
        declarations.append(
            SymbolDeclaration(names[-1], "variable", "source", "other-binding", "fixture", scope)
        )
    return prepare_interpretation_context(
        macros={},
        kind="formula",
        demand="symbolic",
        source_id="fixture",
        scope=scope,
        declarations=declarations,
        assumptions=assumptions,
    )


@pytest.mark.parametrize(
    ("expression", "outcome"),
    [
        (r"X = \sigma Z + \mu", "equivalent"),
        (r"X = \mu + Z\sigma", "equivalent"),
        (r"X = \mu - \sigma Z", "different"),
        (r"X = \sigma Z + \mu + 1", "different"),
        (r"X = \sigma Z^2 + \mu", "different"),
        (r"\sigma Z + \mu = X", "undecided"),
        (r"X + 0 = \sigma Z + \mu", "undecided"),
    ],
)
def test_form_comparison_preserves_directed_output_and_exact_coefficients(expression, outcome):
    context = _context("X", "Z", r"\sigma", r"\mu")
    result = assess_exact_affine(
        PreparedMathInput(context, expression, source_text=expression, source_start=237),
        output="X",
        generator="Z",
        coefficient=r"\sigma",
        offset=r"\mu",
    )
    assert result["outcome"] == outcome, result["detail"]
    assert result["numeric"] == "not_run"
    scope = json.loads(result["context"])
    assert scope["exact_source"] == expression
    assert scope["source_start"] == 237
    if outcome == "equivalent":
        assert scope["actual"] == {"degree": 1, "coefficient": "sigma", "offset": "mu"}


def test_same_affine_assessor_for_calibration_and_an_exact_fraction():
    context = _context("y", "t", "g")
    result = assess_exact_affine(
        PreparedMathInput(context, r"y = gt + \frac{1}{8}"),
        output="y",
        generator="t",
        coefficient="g",
        offset=r"\frac{1}{8}",
    )
    assert result["outcome"] == "equivalent"
    assert json.loads(result["context"])["actual"]["offset"] == "1/8"


def test_approximate_native_coefficient_does_not_acquire_exact_standing():
    context = _context("y", "t")
    result = assess_exact_affine(
        PreparedMathInput(context, "y = 0.125t"),
        output="y",
        generator="t",
        coefficient=r"\frac{1}{8}",
        offset="0",
    )
    assert result["outcome"] == "undecided"
    assert "exact bounded scalar algebra" in result["detail"]


def test_cancellation_needs_the_same_scope_nonzero_premise():
    context = _context("y", "z")
    operand = PreparedMathInput(context, r"y = \frac{z^2 - 1}{z - 1}")
    kwargs = dict(output="y", generator="z", coefficient="1", offset="1")
    assert assess_exact_affine(operand, **kwargs)["outcome"] == "undecided"
    premise = PreparedMathInput(context, r"z \ne 1", kind="relation")
    decision = assess_exact_affine(
        operand, **kwargs, nonzero=(NonzeroPremise(premise, "same-section-exclusion"),)
    )
    assert decision["outcome"] == "equivalent", decision["detail"]
    foreign = PreparedMathInput(
        _context("y", "z", scope="statement-b"), r"z \ne 1", kind="relation"
    )
    assert (
        assess_exact_affine(operand, **kwargs, nonzero=(NonzeroPremise(foreign, "other-section"),))[
            "outcome"
        ]
        == "undecided"
    )


@pytest.mark.parametrize("context", [_context("y"), _context("y", "z", competing=True)])
def test_algebra_does_not_supply_missing_or_competing_source_bindings(context):
    result = assess_exact_affine(
        PreparedMathInput(context, "y = 2z + 1"),
        output="y",
        generator="z",
        coefficient="2",
        offset="1",
    )
    assert result["outcome"] == "undecided"
