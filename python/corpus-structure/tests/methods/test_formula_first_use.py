"""Exact lexical first-use custody, independent of TeX expansion or model behavior."""

import pytest

from corpus_structure.methods.record_assembly import _first_exact_formula_use, _pin
from methods.record_assembly_support import context


def pieces(text, ranges=None):
    pin = _pin(context(text))
    return [
        dict(
            pin=pin,
            space="selected_projection",
            pointer=f"#/texts/{i}",
            precision="exact",
            start=a,
            end=b,
            source_piece=text[a:b],
        )
        for i, (a, b) in enumerate(ranges or [(0, len(text))])
    ]


@pytest.mark.parametrize(
    "text,spelling,expected",
    [
        (r"\lambdax + \lambda + \lambda", r"\lambda", (11, 18)),
        (r"\infty+\frac{1}{2}+f", "f", (19, 20)),
        (r"\omega_2+\omega_1", r"\omega_1", (9, 17)),
        (r"\omega_{1}+\omega_1", r"\omega_1", (11, 19)),
        (r"\lceil  x\rceil+\lceil x\rceil", r"\lceil x\rceil", (16, 30)),
        (r"\lfloor x\rfloor", r"\lfloor x\rfloor", (0, 16)),
        ("xx + x1 + x", "x", (10, 11)),
    ],
)
def test_exact_first_literal_preserves_position_and_control_word_boundaries(
    text, spelling, expected
):
    actual = _first_exact_formula_use(text, pieces(text), spelling)
    assert actual is not None
    assert (actual["start"], actual["end"]) == expected
    assert text[actual["start"] : actual["end"]] == spelling == actual["source_piece"]


@pytest.mark.parametrize(
    "text,spelling",
    [
        (r"\lambdax", r"\lambda"),
        (r"\infty+\frac{1}{2}", "f"),
        (r"\omega_{1}", r"\omega_1"),
        (r"\lceil  x\rceil", r"\lceil x\rceil"),
        ("x+x", "x+x"),
    ],
)
def test_no_inside_command_or_normalized_equivalent_use(text, spelling):
    assert _first_exact_formula_use(text, pieces(text), spelling) is None


def test_disjoint_pieces_do_not_invent_a_control_word_before_the_actual_use():
    text = r"\lamXXbda \lambda"
    actual = _first_exact_formula_use(text, pieces(text, [(0, 4), (6, 9), (10, 17)]), r"\lambda")
    assert actual is not None and (actual["start"], actual["end"]) == (10, 17)


def test_unaddressable_first_command_is_not_replaced_with_a_later_occurrence():
    text = r"\lambda + \lambda"
    assert (
        _first_exact_formula_use(text, pieces(text, [(0, 4), (4, 7), (8, 17)]), r"\lambda") is None
    )


@pytest.mark.parametrize(
    "formula,symbol,first",
    [
        (r"\lambdax + \lambda", r"\lambda", (11, 18)),
        (r"\omega_2+\omega_1", r"\omega_1", (9, 17)),
        (r"\lceil x\rceil+1", r"\lceil x\rceil", (0, 14)),
        (r"\lfloor x\rfloor+1", r"\lfloor x\rfloor", (0, 16)),
    ],
)
def test_actual_assembler_retains_tex_binding_with_exact_first_use(formula, symbol, first):
    from corpus_structure.methods.record_assembly import (
        OCCURRENCE_POLICY,
        LiteralSpan,
        NativeRecordGroup,
        RoleInput,
        assemble_native_records,
    )
    from methods.record_assembly_support import fields, release

    text = formula + " " + symbol + " means rate"
    ctx = context(text)
    start = len(formula) + 1
    group = NativeRecordGroup(
        (
            RoleInput("formula", spans=(LiteralSpan(0, len(formula), formula),)),
            RoleInput("scope", native_pointer="#/groups/1"),
            RoleInput("symbol", spans=(LiteralSpan(start, start + len(symbol), symbol),)),
            RoleInput("meaning", spans=(LiteralSpan(len(text) - 4, len(text), "rate"),)),
        ),
        "independently located exact source declaration",
    )
    result = assemble_native_records(
        release(),
        ctx,
        contract="FormulaRecordFields",
        occurrence_roles=("formula",),
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
        groups=(group,),
    )
    assert len(result.records) == 1
    record = result.records[0]
    assert fields(record)["symbol"]["original"] == symbol
    row = record.model_dump()
    actual = next(a for a in row["anchors"] if a["anchor_id"] == row["occurrence_anchors"][1])
    assert (actual["start"], actual["end"], actual["source_piece"]) == (*first, symbol)
