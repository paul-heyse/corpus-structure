r"""S5-A grammar variants over the frozen I-R2 ``mathgrammar`` (which stays unedited: the
instruments score against it, plan §3.5).

- ``spike``: ``mathgrammar.build.parser_for`` as it stands (shipped grammar + regex-generated
  whole-name ``%override`` lines + ``mathgrammar/extension.lark`` + generated blocks).
- ``edited`` (V1): the same grammar text with Lark's ``edit_terminals`` making every control-word
  literal whole-name (``"\\left"`` never matches the start of ``\leftarrow``; this reaches the
  anonymous ``%ignore`` terminals no ``%override`` can) and ``ordered_sets=True`` explicit
  (text-math note §3.1, ``p4_edit_terminals.py``).
- ``edited-noovr``: ``edited`` without the regex-generated ``%override`` lines (the port form, in
  which ``edit_terminals`` is the only whole-name rule).
- ``extended``: ``edited-noovr`` with ``s5grammar/extension.lark`` (the S5 extensions) in place of
  ``mathgrammar/extension.lark``.
- ``ext:01,02,...``: ``edited-noovr`` with ``mathgrammar/extension.lark`` followed by the named
  candidate blocks of ``s5grammar/ext/`` (step 3's trials; ``s5_extensions.py`` assembles the kept
  ones into ``extension.lark``).

``install(variant)`` points ``mathgrammar.api`` at the variant's parsers (per process).
"""

from __future__ import annotations

from pathlib import Path

import lark
import regex
from lark.lexer import PatternRE, PatternStr

from mathgrammar import api, build

HERE = Path(__file__).resolve().parent
EXTENSION = HERE / "extension.lark"
EXT_DIR = HERE / "ext"
VARIANTS = ("spike", "edited", "edited-noovr", "extended")


def block_files(ids: list[str]) -> list[Path]:
    out = []
    for i in ids:
        hits = sorted(EXT_DIR.glob(f"{i}_*.lark"))
        if len(hits) != 1:
            raise ValueError(f"extension block {i!r}: {hits}")
        out.append(hits[0])
    return out


def extension_text(ids: list[str]) -> str:
    """mathgrammar/extension.lark followed by the named S5 blocks."""
    text = build.EXTENSION.read_text(encoding="utf-8")
    for f in block_files(ids):
        text += "\n" + f.read_text(encoding="utf-8")
    return text

_CW = regex.compile(r"\\[A-Za-z]+")
_ALT = regex.compile(r"\(\?:((?:[^()|]+\|)*[^()|]+)\)")  # a flat (?:a|b|c), as Lark builds for "a" | "b"
_RE_CW = regex.compile(r"\\\\[A-Za-z]+")  # an escaped control word inside a regex: \\left


def whole_name(t) -> None:
    """``edit_terminals``: every control-word literal matches whole command names only."""
    p = t.pattern
    if isinstance(p, PatternStr) and _CW.fullmatch(p.value):
        t.pattern = PatternRE(regex.escape(p.value) + r"(?![A-Za-z])", p.flags)
    elif isinstance(p, PatternRE) and (m := _ALT.fullmatch(p.value)):
        alts = m.group(1).split("|")
        if any(_RE_CW.fullmatch(a) for a in alts):
            t.pattern = PatternRE("(?:" + "|".join(a + "(?![A-Za-z])" if _RE_CW.fullmatch(a) else a for a in alts) + ")",
                                  p.flags)


def grammar_text(variant: str, mc: build.MacroClass) -> str:
    if variant in ("spike", "edited"):
        return build.grammar_text(mc)
    if variant.startswith("ext:"):
        ext = extension_text([x for x in variant[4:].split(",") if x])
    else:
        ext = (EXTENSION if variant == "extended" else build.EXTENSION).read_text(encoding="utf-8")
    text = (build.BASE_GRAMMAR.read_text(encoding="utf-8") + "\n" + ext
            + "\n// ---- generated from the token form's drop list (printer.DROP_LIST)\n" + build.drop_list_ignores()
            + "\n" + build.generated_block(mc))
    build.check_ignores(text)
    return text


_PARSERS: dict[tuple[str, str], lark.Lark] = {}


def build_parser(variant: str, mc: build.MacroClass) -> lark.Lark:
    if variant not in VARIANTS and not variant.startswith("ext:"):
        raise ValueError(variant)
    k = (variant, mc.key)
    p = _PARSERS.get(k)
    if p is None:
        if variant == "spike":
            p = build.parser_for(mc)
        else:
            p = lark.Lark(grammar_text(variant, mc), source_path=str(build.GRAMMAR_DIR) + "/", parser="earley",
                          start=list(build.STARTS), lexer="dynamic", ambiguity="explicit", propagate_positions=True,
                          maybe_placeholders=False, keep_all_tokens=True, ordered_sets=True, edit_terminals=whole_name)
        _PARSERS[k] = p
    return p


def install(variant: str) -> None:
    api.parser_for = lambda mc: build_parser(variant, mc)
    api._CACHE.clear()
