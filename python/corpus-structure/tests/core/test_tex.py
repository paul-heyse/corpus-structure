"""The TeX tokenizer and the token form (D1 §6.2; ADR-0012; foundations §3.4, §6 F2a).

Expectations are written by hand from D1 §6.2's rules, never by calling the module twice; the
metamorphic properties compare the form of a formula with the form of its rewrite. The parity
fixture (`fixtures/tex/`) is the independent spike implementation's output.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.tex import (
    DROP,
    MAX_TOKENS,
    OUTER_ENVIRONMENTS,
    SIZING,
    SYMPY_IGNORE,
    TEXT_MODE,
    effective_macros,
    expand,
    normalize,
    strip_delimiters,
    token_at,
    token_form,
    tokens,
)

REPO = Path(__file__).resolve().parents[4]
PARITY = REPO / "fixtures" / "tex" / "token_form_spike_pages.jsonl"

R = {"\\R": MacroDef(body="\\mathbb{R}")}


def tf(latex: str, table: dict[str, MacroDef] | None = None) -> str:
    return token_form(latex, table or {})


# --- Tokenizer -------------------------------------------------------------------------------


def kinds(latex: str) -> list[tuple[str, str]]:
    return [(t.kind, t.text) for t in tokens(latex)]


def test_control_words_never_take_a_star() -> None:
    assert kinds("a\\cmd*") == [("char", "a"), ("word", "\\cmd"), ("char", "*")]


def test_token_kinds() -> None:
    assert kinds("\\mu  x") == [("word", "\\mu"), ("space", "  "), ("char", "x")]
    assert kinds("\\\\\\{\\ ") == [("symbol", "\\\\"), ("symbol", "\\{"), ("symbol", "\\ ")]
    assert kinds("{#1}#a%") == [
        ("open", "{"), ("param", "#1"), ("close", "}"), ("char", "#"), ("char", "a"),
        ("char", "%"),
    ]  # fmt: skip
    assert kinds("\\mu\u00e9\\\u00e9") == [("word", "\\mu"), ("char", "é"), ("symbol", "\\é")]
    assert kinds("a\\") == [("char", "a"), ("char", "\\")]
    assert kinds("") == []


@given(st.text(max_size=40))
def test_tokens_cover_the_string_in_order(latex: str) -> None:
    toks = tokens(latex)
    assert "".join(t.text for t in toks) == latex
    position = 0
    for token in toks:
        assert token.start == position and token.end == position + len(token.text)
        position = token.end


def test_token_at() -> None:
    latex = "a \\mu b"
    found = token_at(latex, 3)
    assert found is not None and (found.text, found.start, found.end) == ("\\mu", 2, 5)
    assert token_at(latex, 7) is None
    assert token_at(latex, -1) is None


# --- Declared sets ---------------------------------------------------------------------------


def test_drop_list() -> None:
    # D1 §6.2: SymPy 1.14's `%ignore` literals and the sizing commands with l/r/m forms.
    assert len(SYMPY_IGNORE) == 29 and len(SIZING) == 16 and DROP == SYMPY_IGNORE | SIZING
    for name in (
        "\\,", "\\thinspace", "\\qquad", "\\negthickspace", "\\vspace", "\\hfill", "\\left",
        "\\right", "\\limits", "\\nolimits", "\\displaystyle", "\\big", "\\Bigl", "\\biggr",
        "\\Biggm", "\\(",
    ):  # fmt: skip
        assert name in DROP, name
    assert "\\)" not in DROP and "\\[" not in DROP and "\\bigcup" not in DROP


def test_declared_text_mode_and_environments() -> None:
    assert {"\\text", "\\mathrm", "\\textrm", "\\mbox", "\\operatorname"} == TEXT_MODE
    names = ("equation", "align", "alignat", "flalign", "gather", "multline", "eqnarray")
    assert {*names, *(n + "*" for n in names), "displaymath", "math"} == OUTER_ENVIRONMENTS


# --- D1 rule cases (ported from the spike's test_values) -------------------------------------


@pytest.mark.parametrize(
    ("latex", "form"),
    [
        ("b^{2}", "b^2"),
        ("b^{2} \\sigma^2", "b^2\\sigma^2"),
        ("b^2\\sigma^{2}", "b^2\\sigma^2"),
        ("\\left( x \\right)", "(x)"),
        ("a + b \\, Z", "a+bZ"),
        ("a\\;+\\!b", "a+b"),
        ("e^{\\mu}", "e^\\mu"),
        ("\\(x\\)", "x"),
        ("$x$", "$x$"),  # `$` is prose on Siegrist, never a delimiter (the spike stripped it)
        ("\\mu  x", "\\mu x"),
        ("\\frac{1}{2}", "\\frac12"),
        ("\\mathrm {d} x", "\\mathrm dx"),
        ("{a", "{a"),  # unbalanced: the brace step is skipped, the form stays total
    ],
)
def test_d1_rules(latex: str, form: str) -> None:
    assert tf(latex) == form


def test_page_macros_over_the_fallback() -> None:
    pack = {"\\R": MacroDef(body="\\mathbb{R}"), "\\var": MacroDef(body="\\text{var}")}
    page = {"\\R": MacroDef(body="\\mathbf{R}")}
    table = effective_macros(page, pack)
    assert tf("\\R", effective_macros({}, pack)) == "\\mathbb R"
    assert tf("\\R", table) == "\\mathbf R"
    assert tf("\\var(X)", table) == "\\text{var}(X)"
    assert tf("\\R \\setminus \\{0\\}", R) == "\\mathbb R\\setminus\\{0\\}"
    assert effective_macros(page, pack) == {"\\R": page["\\R"], "\\var": pack["\\var"]}


# --- Revealing cases (foundations §5) --------------------------------------------------------


def test_sizing_commands_are_dropped() -> None:
    assert tf("a \\big/ b") == "a/b"
    assert tf("\\Bigl( x \\Bigr) \\biggm| y") == "(x)|y"


def test_text_mode_keeps_collapsed_whitespace() -> None:
    assert tf("\\text{ for all }") == "\\text{ for all }"
    assert tf("\\text{for   all}\\;x") == "\\text{for all}x"
    assert tf("\\text{a \\, b}") == "\\text{a b}"  # the drop leaves two spaces; they collapse
    assert tf("\\operatorname*{arg max}") == "\\operatorname*{arg max}"
    assert tf("\\text {a b} c d") == "\\text{a b}cd"
    assert tf("\\text{ }x") == "\\text{ }x"
    assert tf("a b") == "ab"


# --- Delimiters ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("latex", "form"),
    [
        ("\\[ x \\]", "x"),
        ("  \\( x \\)  ", "x"),
        ("\\begin{align} a &= b \\\\ c \\end{align}", "a&=b\\\\c"),
        ("\\begin{align*}x\\end{align*}", "x"),
        ("\\begin{equation}x\\end{equation}", "x"),
        ("\\begin{alignat*}{2} x &= 1 \\end{alignat*}", "x&=1"),  # the column count is layout
        ("\\begin{alignat} {2} x &= 1 \\end{alignat}", "x&=1"),
        ("\\begin{align} 2x &= 1 \\end{align}", "2x&=1"),  # no longer equal to the alignat
        ("\\begin{math}x\\end{math}", "x"),
        ("\\begin{cases}x\\end{cases}", "\\begin{cases}x\\end{cases}"),  # not a delimiter
        ("\\begin{align}x\\end{align} + y", "\\begin{align}x\\end{align}+y"),
        ("\\begin{equation}x\\end{align}", "\\begin{equation}x\\end{align}"),
        (
            "\\begin{align}\\begin{align}x\\end{align}\\end{align}",
            "\\begin{align}x\\end{align}",
        ),
        ("\\[\\[x\\]\\]", "\\[x\\]"),  # one pair only
        ("\\[x", "\\[x"),
        ("$$x$$", "$$x$$"),
        # The drop list is literal (operator ruling 2026-10-28): an inner `\(` is dropped and its
        # `\)` kept. M01's delimiting never leaves an inner delimiter inside a span.
        ("\\(a\\) + \\(b\\)", "a\\)+b\\)"),
        ("\\(\\(x\\)\\)", "x\\)"),
    ],
)
def test_one_outer_delimiter_pair(latex: str, form: str) -> None:
    assert tf(latex) == form


def test_inline_and_display_key_alike() -> None:
    forms = {tf("\\(a^{2}\\)"), tf("\\[ a^2 \\]"), tf("\\begin{gather*} a^2 \\end{gather*}")}
    assert forms == {"a^2"}
    assert strip_delimiters(["\\(", "x", "\\)"]) == ["x"]


# --- Macros ----------------------------------------------------------------------------------

F = {"\\f": MacroDef(nargs=2, body="#1/#2")}


def test_macros_expand_by_whole_name() -> None:
    table = {"\\P": MacroDef(body="\\mathbb{P}")}
    assert tf("\\P", table) == "\\mathbb P"
    assert tf("\\Phi", table) == "\\Phi"
    assert tf("\\P hi", table) == "\\mathbb Phi"
    assert tf("\\Phi", table) != tf("\\P hi", table)


def test_arguments_as_tex_reads_them() -> None:
    assert tf("\\f{a}{b}", F) == "a/b"
    assert tf("\\f ab", F) == "a/b"
    assert tf("\\f  {a} \\mu", F) == "a/\\mu"
    # arguments are substituted without their braces (operator ruling 2026-10-28)
    assert tf("\\f {a+b} c", F) == "a+b/c"
    abs_ = {"\\abs": MacroDef(nargs=1, body="\\lvert #1 \\rvert"), **R}
    assert tf("\\abs{x}", abs_) == "\\lvert x\\rvert"
    assert tf("\\abs{\\R}", abs_) == "\\lvert\\mathbb R\\rvert"


def test_optional_first_argument() -> None:
    g = {"\\g": MacroDef(nargs=2, default="0", body="#1:#2")}
    assert tf("\\g{x}", g) == "0:x"
    assert tf("\\g[1]{x}", g) == "1:x"
    assert tf("\\g [a{]}b] {x}", g) == "a]b:x"  # a `]` inside braces does not close it
    assert tf("\\g[1{x}", g) == "0:[1x"  # no closing bracket: not an optional argument


def test_missing_and_extra_arguments() -> None:
    assert tf("\\f{a}", F) == "a/"
    assert tf("{\\f}x", F) == "/x"  # the group's `}` is not taken as an argument
    assert tf("\\h{a}", {"\\h": MacroDef(nargs=1, body="#1#3")}) == "a#3"


def test_an_expansion_reads_the_arguments_that_follow_it() -> None:
    table = {"\\pa": MacroDef(body="\\p"), "\\p": MacroDef(nargs=1, body="(#1)")}
    assert tf("\\pa{x}", table) == "(x)"


def test_dropped_commands_never_become_arguments() -> None:
    q = {"\\q": MacroDef(nargs=1, body="[#1]")}
    assert tf("\\q\\,{x}", q) == "[x]"
    assert tf("\\q \\big {x}", q) == "[x]"
    k = {"\\k": MacroDef(body="\\,\\f"), **F}
    assert tf("\\k{a}{b}", k) == "a/b"


def chain(n: int) -> dict[str, MacroDef]:
    names = [f"\\c{'a' * (i + 1)}" for i in range(n)]
    table = {name: MacroDef(body=nxt) for name, nxt in itertools.pairwise(names)}
    table[names[-1]] = MacroDef(body="z")
    return table


def test_depth_bound_is_sixteen() -> None:
    assert normalize("\\ca", chain(16)).form == "z"
    assert normalize("\\ca", chain(16)).unexpanded == ()
    deeper = normalize("\\ca", chain(17))
    assert deeper.form == "\\c" + "a" * 17 and deeper.unexpanded == ("\\c" + "a" * 17,)
    looped = normalize("\\x+1", {"\\x": MacroDef(body="\\x")})
    assert looped.form == "\\x+1" and looped.unexpanded == ("\\x",)


def test_size_bound_keeps_the_macro_and_its_arguments() -> None:
    triple = normalize("\\t", {"\\t": MacroDef(body="\\t\\t\\t")})
    assert triple.unexpanded == ("\\t",)
    assert len(tokens(triple.form)) <= MAX_TOKENS
    grow = normalize("\\x{a}", {"\\x": MacroDef(nargs=1, body="\\x{#1#1}")})
    assert grow.unexpanded == ("\\x",)
    assert grow.form.startswith("\\x{") and set(grow.form[3:-1]) == {"a"}


def test_expand_alone() -> None:
    out = expand(["\\f", "{", "a", "}", " ", "b"], F)
    assert out.tokens == ("a", "/", "b") and out.unexpanded == ()


# --- Metamorphic properties (D1 §6.2) --------------------------------------------------------

ATOMS = ["a", "b", "x", "1", "2", "+", "=", "(", ")", "^", "_", ",", "|", "\\mu", "\\alpha",
         "\\Phi", "\\P", "\\sum", "\\{", "\\}", "\\frac", "\\leftarrow", "\\setminus"]  # fmt: skip
INSERTS = ["\\,", "\\;", "\\!", "\\quad", "\\big", "\\Bigl", "\\biggr", "\\left", "\\right",
           " ", "  ", "\n"]  # fmt: skip


def formula() -> st.SearchStrategy[list[str]]:
    """Balanced token lists over math atoms (no macros, no text mode)."""
    return st.recursive(
        st.lists(st.sampled_from(ATOMS), min_size=1, max_size=5),
        lambda inner: st.lists(
            st.sampled_from(ATOMS).map(lambda a: [a]) | inner.map(lambda g: ["{", *g, "}"]),
            min_size=1,
            max_size=4,
        ).map(lambda parts: [t for part in parts for t in part]),
        max_leaves=12,
    )


def join(toks: list[str]) -> str:
    """Write tokens so that they re-tokenize as written (a space after a word before a letter)."""
    out = []
    for i, text in enumerate(toks):
        out.append(text)
        word = text[:1] == "\\" and text[1:2].isalpha()
        if word and i + 1 < len(toks) and toks[i + 1][:1].isalpha():
            out.append(" ")
    return "".join(out)


@given(st.text(max_size=60))
def test_total_on_any_string(latex: str) -> None:
    tf(latex)
    tf(latex, {"\\a": MacroDef(nargs=2, default="x", body="#2#1\\a"), **F})


PIECES = [*"ab {}^\\()[]$#1*,;! ", "\\text", "\\mu", "\\left", "\\big", "\\(", "\\)",
          "\\begin{align}", "\\end{align}"]  # fmt: skip


@given(st.lists(st.sampled_from(PIECES), max_size=30).map("".join) | st.text(max_size=20))
def test_idempotent(latex: str) -> None:
    once = tf(latex)
    texts = [t.text for t in tokens(once)]
    assume(strip_delimiters(texts) == texts)  # a delimited output would be stripped again
    assert tf(once) == once


@given(formula(), st.data())
def test_insertions_leave_the_form_unchanged(toks: list[str], data: st.DataObject) -> None:
    base = tf(join(toks))
    at = data.draw(st.integers(0, len(toks)))
    insert = data.draw(st.sampled_from(INSERTS))
    rewritten = [*toks[:at], insert, *toks[at:]]
    assert tf(join(rewritten)) == base


@given(formula(), st.data())
def test_braces_around_a_single_token_leave_the_form_unchanged(
    toks: list[str], data: st.DataObject
) -> None:
    at = data.draw(st.integers(0, len(toks) - 1))
    assume(toks[at] not in ("{", "}"))
    wrapped = [*toks[:at], "{", toks[at], "}", *toks[at + 1 :]]
    assert tf(join(wrapped)) == tf(join(toks))


def test_never_merges_distinct_names() -> None:
    assert tf("\\mu x") != tf("\\mux")
    assert tf("x \\leftarrow y") == "x\\leftarrow y" != tf("xarrowy")
    assert tf("\\P", {"\\P": MacroDef(body="\\mathbb{P}")}) != tf("\\Phi")


# --- Parity with the spike's I-R2 output -----------------------------------------------------


def parity_rows() -> list[dict]:
    with PARITY.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def test_parity_fixture_reproduced_in_full() -> None:
    rows = parity_rows()
    assert len(rows) == 918
    differ = []
    for row in rows:
        table = {name: MacroDef.model_validate(d) for name, d in row["macros"].items()}
        if token_form(row["latex"], table) != row["token_form"]:
            differ.append((row["page"], row["start"], row["latex"], row["token_form"]))
    assert differ == []


def test_canonically_equivalent_input_has_one_form() -> None:
    decomposed = "\\alpha e\u0301 \\text{caf e\u0301}"
    composed = "\\alpha \u00e9 \\text{caf \u00e9}"
    assert tf(decomposed) == tf(composed) == "\\alpha\u00e9\\text{caf \u00e9}"
    # composition can change the tokens (`\\R` + U+0301 is `\\Ŕ`); both spellings agree
    assert tf("\\R\u0301", R) == tf("\\\u0154", R)


CONTROL_SPACES = ["\\ ", "\\\t", "\\\n", "\\\r\n"]  # TeX reads every one as a control space


@given(formula(), st.data())
def test_every_control_space_spelling_gives_one_form(toks: list[str], data: st.DataObject) -> None:
    """IR-15: `\\ `, `\\` + tab and `\\` + end of line are one control space (D1 §6.2)."""
    at = data.draw(st.integers(0, len(toks)))
    text_mode = data.draw(st.booleans())
    forms = set()
    for spelling in CONTROL_SPACES:
        inserted = [*toks[:at], spelling, *toks[at:]]
        latex = join(inserted)
        forms.add(tf(f"\\text{{{latex}}}" if text_mode else latex))
    assert len(forms) == 1


def test_control_space_spellings_in_text_and_macro_bodies() -> None:
    assert {tf(f"a{s}b") for s in CONTROL_SPACES} == {"a\\ b"}
    assert {tf(f"\\text{{for{s}all}}") for s in CONTROL_SPACES} == {"\\text{for\\ all}"}
    bodies = {tf("\\q", {"\\q": MacroDef(body=f"x{s}y")}) for s in CONTROL_SPACES}
    assert bodies == {"x\\ y"}
    assert tf("a\\ b") != tf("ab") and tf("a\\ b") != tf("a\\,b")  # a control space is content
    assert [t.text for t in tokens("a\\\nb")] == ["a", "\\\n", "b"]  # tokens keep the source


def test_a_control_space_absorbs_the_blanks_a_dropped_command_leaves() -> None:
    # Found by a 20,000-example idempotence probe: dropping `\,` must not leave a second space.
    once = tf("\\operatorname{\\ \\, ")
    assert once == "\\operatorname{\\ " and tf(once) == once
    assert tf("\\text{a\\ \\, b}") == tf("\\text{a\\ b}") == "\\text{a\\ b}"
