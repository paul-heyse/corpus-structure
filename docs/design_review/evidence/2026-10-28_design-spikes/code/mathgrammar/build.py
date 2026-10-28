"""Grammar assembly and parser cache (ADR-0009).

grammar = SymPy's shipped latex.lark (read unedited from the installed package, as
LarkLaTeXParser does)
        + generated whole-name overrides of SymPy's command terminals
        + extension.lark (ours)
        + the %ignore of the drop-list commands the shipped grammar lacks (printer.DROP_LIST)
        + a block generated from the rendition's macro table (GEN_SET, GEN_OP, GEN_STYLE).

Building fails if an %ignore of the assembled grammar is not covered by the drop list (or the
whitespace rule), so the grammar and the token form never drop different sets (D1 §6.2).

One Earley parser is built per macro-table classification and cached (construction is costly).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import lark
import sympy.parsing.latex.lark as _slark

HERE = Path(__file__).resolve().parent
GRAMMAR_DIR = Path(_slark.__file__).parent / "grammar"
BASE_GRAMMAR = GRAMMAR_DIR / "latex.lark"
EXTENSION = HERE / "extension.lark"
STARTS = ("formula", "relation", "member", "set_expr", "any_value")

_SET_LETTERS = {"R": "Reals", "N": "Naturals0", "Z": "Integers", "Q": "Rationals", "C": "Complexes"}
_WRAPPERS = {"\\mathscr", "\\mathcal", "\\mathbf", "\\boldsymbol", "\\bm", "\\mathsf", "\\mathfrak", "\\mathrm"}
_SPACING = re.compile(r"\\[,;:! ]|\s+")


# ============================================================================ macro classification


@dataclass(frozen=True)
class MacroClass:
    """How a nargs-0 macro reads, from its body (source data, never grammar text)."""

    sets: tuple[tuple[str, str], ...] = ()  # (macro name, letter in RNZQC)
    ops: tuple[tuple[str, str], ...] = ()  # (macro name, operator name)
    styles: tuple[tuple[str, str], ...] = ()  # (macro name, wrapper command)
    other: tuple[tuple[str, str], ...] = ()  # (macro name, body): not classified, not in the grammar
    bodies: tuple[tuple[str, str], ...] = ()  # (macro name, body) for every nargs-0 macro
    with_args: tuple[tuple[str, int, str], ...] = ()  # (macro name, nargs, body): canonical form only

    @property
    def key(self) -> str:
        return hashlib.sha256(json.dumps([self.sets, self.ops, self.styles], sort_keys=True).encode()).hexdigest()[:16]

    @property
    def full_key(self) -> str:
        """Identity of the whole table (parser key plus bodies), for result caches."""
        return hashlib.sha256(json.dumps([self.key, self.bodies, self.with_args], sort_keys=True).encode()).hexdigest()[:16]

    def set_letter(self, name: str) -> str | None:
        return dict(self.sets).get(name)

    def op(self, name: str) -> str | None:
        return dict(self.ops).get(name)

    def body(self, name: str) -> str | None:
        return dict(self.bodies).get(name)

    def table(self) -> dict[str, tuple[int, str]]:
        """Every macro as name -> (nargs, body), for expansion in the canonical form."""
        out = {n: (0, b) for n, b in self.bodies}
        out.update({n: (k, b) for n, k, b in self.with_args})
        return out


def classify(macros: dict | None) -> MacroClass:
    """Classify a macro table ``{"\\\\R": {"nargs": 0, "body": "\\\\mathbb{R}"}, ...}``.

    - ``\\mathbb{R|N|Z|Q|C}`` -> set constant; other ``\\mathbb{X}`` -> operator ``X``;
    - ``\\text{w}``, ``\\operatorname{w}``, ``\\textrm{w}``, ``\\mathrm{w}`` (two or more letters)
      -> operator ``w``;
    - a bare typeface wrapper (``\\mathscr``, ``\\boldsymbol``, ...) -> transparent wrapper;
    - anything else is recorded as ``other`` (not added to the grammar).
    Spacing commands and whitespace in a body are ignored (``\\,\\text{sgn}``). Macros with
    arguments are not classified.
    """
    sets, ops, styles, other, bodies, with_args = [], [], [], [], [], []
    for name, spec in sorted((macros or {}).items()):
        if isinstance(spec, str):
            spec = {"nargs": 0, "body": spec}
        name = name.strip()
        if not re.fullmatch(r"\\[A-Za-z]+", name):
            continue
        if int(spec.get("nargs") or 0) != 0:
            with_args.append((name, int(spec["nargs"]), spec.get("body", "")))
            continue
        raw = spec.get("body", "")
        body = _SPACING.sub("", raw)
        bodies.append((name, raw))
        if m := re.fullmatch(r"\\mathbb\{?([A-Z])\}?", body):
            (sets if m.group(1) in _SET_LETTERS else ops).append((name, m.group(1)))
        elif m := re.fullmatch(r"\\(?:text|operatorname|textrm|mathrm)\{([A-Za-z]{2,})\}", body):
            ops.append((name, m.group(1)))
        elif body in _WRAPPERS:
            styles.append((name, body))
        else:
            other.append((name, raw))
    return MacroClass(tuple(sets), tuple(ops), tuple(styles), tuple(other), tuple(bodies), tuple(with_args))


# ============================================================================ grammar text


def _alt(names: list[str]) -> str:
    """A whole-name regex alternation of command names (longest first); never-matching if empty."""
    if not names:
        return "/(?!)x/"
    body = "|".join(re.escape(n[1:]) for n in sorted(set(names), key=lambda s: (-len(s), s)))
    return "/\\\\(?:" + body.replace("/", "\\/") + ")(?![A-Za-z])/"


_TERMINAL_LINE = re.compile(r'^([A-Z][A-Z0-9_]*):\s*((?:"\\\\[A-Za-z]+"\s*\|?\s*)+)$')


@lru_cache(maxsize=1)
def whole_name_overrides() -> str:
    """``%override`` lines making SymPy's command terminals (``FUNC_SIN: "\\\\sin"``,
    ``LTE: "\\\\leq" | "\\\\le" | ...``) match whole names only, so ``\\\\sinh`` cannot lex as
    ``\\\\sin`` + ``h``. Derived from the shipped grammar's own definitions."""
    out = []
    for line in BASE_GRAMMAR.read_text(encoding="utf-8").splitlines():
        m = _TERMINAL_LINE.match(line.split("//")[0].rstrip())
        if not m:
            continue
        names = re.findall(r'"\\\\([A-Za-z]+)"', m.group(2))
        out.append(f"%override {m.group(1)}: {_alt(['\\' + n for n in names])}")
    return "\n".join(out) + "\n"


def generated_block(mc: MacroClass) -> str:
    return (
        "// ---- generated from the rendition's macro table (classification in mathgrammar.build)\n"
        f"GEN_SET: {_alt([n for n, _ in mc.sets])}\n"
        f"GEN_OP: {_alt([n for n, _ in mc.ops])}\n"
        f"GEN_STYLE: {_alt([n for n, _ in mc.styles])}\n"
    )


_WHITESPACE_IGNORE = "/[ \\t\\n\\r]+/"  # shipped line 1; the token form removes whitespace itself (rule 5)


def _shipped_literals(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        if line.startswith("%ignore"):
            out += ["\\" + m for m in re.findall(r'"\\\\([^"]+)"', line)]
    return out


@lru_cache(maxsize=1)
def drop_list_ignores() -> str:
    """``%ignore`` for the drop-list commands the shipped grammar does not already ignore,
    as one whole-name terminal (``\\big`` never matches inside ``\\bigcup``)."""
    from .printer import DROP_LIST

    shipped = set(_shipped_literals(BASE_GRAMMAR.read_text(encoding="utf-8")))
    extra = [c for c in DROP_LIST if c not in shipped]
    if any(not re.fullmatch(r"\\[A-Za-z]+", c) for c in extra):
        raise ValueError(f"drop-list additions must be control words: {extra}")
    return "%ignore " + _alt(extra) + "\n"


def check_ignores(text: str) -> None:
    """Every %ignore of the assembled grammar is on the drop list (literals), is the shipped
    whitespace rule, or is the generated drop-list terminal; the shipped literals equal
    printer.SYMPY_IGNORE_LITERALS."""
    from .printer import DROP, SYMPY_IGNORE_LITERALS

    shipped = _shipped_literals(BASE_GRAMMAR.read_text(encoding="utf-8"))
    if tuple(shipped) != SYMPY_IGNORE_LITERALS:
        raise ValueError(f"SymPy's %ignore literals changed: {shipped}")
    generated = drop_list_ignores().strip()
    for line in text.splitlines():
        if not line.startswith("%ignore"):
            continue
        body = line[len("%ignore"):].strip()
        if line.strip() == generated or body == _WHITESPACE_IGNORE:
            continue
        lits = re.findall(r'"\\\\([^"]+)"', body)
        rest = re.sub(r'"\\\\[^"]+"|\|', "", body).strip()
        if rest or not lits or any("\\" + x not in DROP for x in lits):
            raise ValueError(f"%ignore not covered by the drop list: {line}")


def grammar_text(mc: MacroClass) -> str:
    text = (BASE_GRAMMAR.read_text(encoding="utf-8") + "\n// ---- whole-name overrides of the shipped command terminals\n"
            + whole_name_overrides() + EXTENSION.read_text(encoding="utf-8")
            + "\n// ---- generated from the token form's drop list (printer.DROP_LIST)\n" + drop_list_ignores()
            + "\n" + generated_block(mc))
    check_ignores(text)
    return text


_PARSERS: dict[str, lark.Lark] = {}


def parser_for(mc: MacroClass) -> lark.Lark:
    p = _PARSERS.get(mc.key)
    if p is None:
        p = lark.Lark(grammar_text(mc), source_path=str(GRAMMAR_DIR) + "/", parser="earley", start=list(STARTS),
                      lexer="dynamic", ambiguity="explicit", propagate_positions=True, maybe_placeholders=False,
                      keep_all_tokens=True)
        _PARSERS[mc.key] = p
    return p
