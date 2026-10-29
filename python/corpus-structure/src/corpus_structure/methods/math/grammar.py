"""The one math grammar (ADR-0012; D4 M11; ingest and math §3.7, P0-I-2a).

Every reader of math in the product parses with this module. Ported from the spike's frozen
`mathgrammar` as S5-A extended it (records `s5.coverage`, `s5.keys-property`), rewritten against
`core/tex.py`.

**Assembly.** The grammar text is SymPy 1.14's shipped `latex.lark`, read unedited from the
installed package; `extension.lark` (`%extend`/`%override`, typed start symbols, sub- and
superscripts as rules, set constructs, S5's additions); the `%ignore` of `core/tex.py`'s drop-list
commands the shipped grammar lacks; and a block generated from the rendition's macro classification
(`GEN_SET`, `GEN_OP`, `GEN_STYLE`). Assembly fails if any `%ignore` of the text is not on the drop
list (D1 §6.2). Lark's `edit_terminals` makes every control-word literal whole-name, including the
anonymous terminals of the shipped string `%ignore` lines, so `x \\leftarrow y` fails as an unknown
command instead of reading `\\left` and `arrow`.

**Parsers.** One Earley parser per macro classification, built lazily in a per-process dictionary
(Earley parsers cannot be saved or pickled; one builds in about 0.05 s). A macro reads, from its
body: `\\mathbb{R|N|Z|Q|C}` as a set, another `\\mathbb{X}` or `\\text`/`\\operatorname`/`\\textrm`/
`\\mathrm` of two or more letters as an operator, a bare typeface wrapper as a style; anything else
is not in the grammar (and is expanded only in token forms).

**`parse(latex, kind, macros, context)`** reads `latex` under a typed start symbol (`any_value`
by default) with the rendition's effective macro table (`core/tex.py` `effective_macros`) and the
declared context. The result holds a `ParseOutcome` (`partial` when only trailing `.`, `,`, `;`
was dropped), the detected kind, the tree, the failure with its category, notes, and the symbol
occurrences with offsets into `latex`.

- **Ambiguity** is resolved only from declared context: a symbol before `(...)` is applied only if
  declared a function, multiplied only if declared a variable; a definition `g(x) = ...` declares
  `g` a function; a lone symbol under `any_value` is a formula; a list before `\\in` is a
  membership of each element; a bare `(a, b)` under `any_value` is ambiguous; readings with equal
  SymPy values collapse to the first, which `ordered_sets` keeps stable. Anything else is
  `ambiguous`, never picked silently.
- **Failure categories** are derived from the exception class, the TeX token at the error position
  (`core/tex.py` `token_at`) and the parser's terminals, as S5 derived them;
  `UnexpectedInput.match_examples` is not used (S5 measured its categories without it).
- **Deadline.** One `SIGALRM` timer bounds the whole read: the parse, the trimmed retry, the
  ambiguity resolver's SymPy conversions and the occurrences (S5-A: the spike's resolver ran
  unbounded and once hung for over eleven minutes). Expiry gives category `timeout`. The timer works
  only on a process's main thread, so `parse` raises `OffMainThread` anywhere else: a misplaced
  caller fails loudly instead of running without a limit.
- **Memo.** A bounded per-process memo keyed by (latex, kind, macro table, context) lets M09 and
  M11 share a parse in one process. Timeouts are not memoized.
"""

from __future__ import annotations

import codecs
import dataclasses
import functools
import hashlib
import json
import re
import signal
import threading
from collections import OrderedDict
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import Any, Literal

import lark
import sympy
import sympy.parsing.latex.lark as _sympy_lark
from lark import Token, Tree
from lark.exceptions import (
    UnexpectedCharacters,
    UnexpectedEOF,
    UnexpectedInput,
    UnexpectedToken,
    VisitError,
)
from lark.lexer import PatternRE, PatternStr, TerminalDef

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import _tree
from corpus_structure.methods.math.transform import (
    KNOWN_FUNCTIONS,
    NotRepresentable,
    bare,
    symbol_name,
    transform,
)

SHIPPED = Path(_sympy_lark.__file__).parent / "grammar" / "latex.lark"
EXTENSION = Path(__file__).with_name("extension.lark")

type Kind = Literal["formula", "relation", "member", "set_expr", "any_value"]
STARTS: tuple[Kind, ...] = ("formula", "relation", "member", "set_expr", "any_value")
PARSE_SECONDS = 2.0  # the default deadline; M11's `Config` sets it
MEMO_SIZE = 8192

_SET_ROOTS = frozenset(
    {
        "set_const",
        "interval",
        "set_list",
        "set_builder",
        "empty_set",
        "set_named",
        "set_group",
        "set_minus",
        "set_union",
        "set_intersection",
        "set_product",
        "set_expr",
        "set_power",
    }
)
_SYMBOL_TOKENS = frozenset({"SYMBOL", "GREEK_SYMBOL_WITH_PRIMES"})
_TRAILING = ".,;"


class GrammarError(ValueError):
    """The assembled grammar breaks a build rule (an `%ignore` off the drop list)."""


class OffMainThread(RuntimeError):
    """`parse` was called off a process's main thread, where its deadline cannot run."""


class NotParsed(Exception):
    """The value did not parse (`to_sympy`)."""


class Ambiguous(Exception):
    """The value has more than one reading the context does not settle (`to_sympy`)."""


# ============================================================================ macro classification

_SPACING = re.compile(r"\\[,;:! ]|\s+")
_CONTROL_WORD = re.compile(r"\\[A-Za-z]+")
_WRAPPERS = frozenset(
    {
        "\\mathscr",
        "\\mathcal",
        "\\mathbf",
        "\\boldsymbol",
        "\\bm",
        "\\mathsf",
        "\\mathfrak",
        "\\mathrm",
    }
)
_SET_LETTERS = frozenset("RNZQC")


@dataclass(frozen=True, slots=True)
class MacroClass:
    """Which argument-free macros read as sets, operators or style wrappers (from their bodies)."""

    sets: tuple[tuple[str, str], ...] = ()  # (macro, letter in RNZQC)
    ops: tuple[tuple[str, str], ...] = ()  # (macro, operator name)
    styles: tuple[tuple[str, str], ...] = ()  # (macro, wrapper command)

    @property
    def key(self) -> str:
        """The parser's key: the classification, not the whole table."""
        payload = json.dumps([self.sets, self.ops, self.styles])
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def classify(macros: Mapping[str, MacroDef]) -> MacroClass:
    """Classify a macro table; spacing and whitespace in a body are ignored (`\\,\\text{sgn}`)."""
    return _classify(tuple(sorted(macros.items())))


@functools.cache
def _classify(items: tuple[tuple[str, MacroDef], ...]) -> MacroClass:
    sets: list[tuple[str, str]] = []
    ops: list[tuple[str, str]] = []
    styles: list[tuple[str, str]] = []
    for name, definition in items:
        if definition.nargs or not _CONTROL_WORD.fullmatch(name):
            continue
        body = _SPACING.sub("", definition.body)
        if m := re.fullmatch(r"\\mathbb\{?([A-Z])\}?", body):
            (sets if m.group(1) in _SET_LETTERS else ops).append((name, m.group(1)))
        elif m := re.fullmatch(r"\\(?:text|operatorname|textrm|mathrm)\{([A-Za-z]{2,})\}", body):
            ops.append((name, m.group(1)))
        elif body in _WRAPPERS:
            styles.append((name, body))
    return MacroClass(tuple(sets), tuple(ops), tuple(styles))


def _table_key(macros: Mapping[str, MacroDef]) -> str:
    rows = sorted((n, d.nargs, d.default, d.body) for n, d in macros.items())
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16]


# ============================================================================ grammar text

_WHITESPACE_IGNORE = "/[ \\t\\n\\r]+/"  # the shipped first line; the token form drops whitespace
_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _whole_name_regex(names: Sequence[str]) -> str:
    """A Lark regex matching exactly these commands as whole names; never matching when empty."""
    if not names:
        return "/(?!)x/"
    ordered = sorted(set(names), key=lambda s: (-len(s), s))
    body = "|".join(re.escape(n[1:]) for n in ordered)
    return "/\\\\(?:" + body.replace("/", "\\/") + ")(?![A-Za-z])/"


def _ignore_literals(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        if line.startswith("%ignore"):
            out += [codecs.decode(lit, "unicode_escape") for lit in _LITERAL.findall(line)]
    return out


@functools.cache
def _shipped() -> str:
    text = SHIPPED.read_text(encoding="utf-8")
    if frozenset(_ignore_literals(text)) != tex.SYMPY_IGNORE:
        raise GrammarError("SymPy's %ignore literals differ from core/tex.py's SYMPY_IGNORE")
    return text


@functools.cache
def drop_ignore() -> str:
    """One `%ignore` for the drop-list commands the shipped grammar does not ignore."""
    extra = sorted(tex.DROP - frozenset(_ignore_literals(_shipped())))
    if any(not _CONTROL_WORD.fullmatch(c) for c in extra):
        raise GrammarError(f"drop-list additions must be control words: {extra}")
    return "%ignore " + _whole_name_regex(extra)


def check_ignores(text: str) -> None:
    """Refuse a grammar with an `%ignore` that is not on `core/tex.py`'s drop list."""
    generated = drop_ignore()
    for line in text.splitlines():
        if not line.startswith("%ignore"):
            continue
        body = line[len("%ignore") :].strip()
        if line.strip() == generated or body == _WHITESPACE_IGNORE:
            continue
        literals = [codecs.decode(lit, "unicode_escape") for lit in _LITERAL.findall(body)]
        rest = _LITERAL.sub("", body).replace("|", "").strip()
        if rest or not literals or any(lit not in tex.DROP for lit in literals):
            raise GrammarError(f"%ignore not on the drop list: {line}")


def generated_block(classes: MacroClass) -> str:
    return (
        "// ---- generated from the rendition's macro classification (methods.math.grammar)\n"
        f"GEN_SET: {_whole_name_regex([n for n, _ in classes.sets])}\n"
        f"GEN_OP: {_whole_name_regex([n for n, _ in classes.ops])}\n"
        f"GEN_STYLE: {_whole_name_regex([n for n, _ in classes.styles])}\n"
    )


def grammar_text(classes: MacroClass) -> str:
    text = "\n".join(
        [
            _shipped(),
            EXTENSION.read_text(encoding="utf-8"),
            "// ---- generated from core/tex.py's drop list",
            drop_ignore(),
            generated_block(classes),
        ]
    )
    check_ignores(text)
    return text


_FLAT_ALTERNATION = re.compile(r"\(\?:((?:[^()|]+\|)*[^()|]+)\)")  # Lark's (?:a|b|c) for "a" | "b"
_ESCAPED_WORD = re.compile(r"\\\\[A-Za-z]+")  # an escaped control word inside a regex: \\left


def whole_name(terminal: TerminalDef) -> None:
    """`edit_terminals`: every control-word literal matches whole command names only."""
    pattern = terminal.pattern
    if isinstance(pattern, PatternStr) and _CONTROL_WORD.fullmatch(pattern.value):
        terminal.pattern = PatternRE(re.escape(pattern.value) + r"(?![A-Za-z])", pattern.flags)
    elif isinstance(pattern, PatternRE) and (m := _FLAT_ALTERNATION.fullmatch(pattern.value)):
        alternatives = m.group(1).split("|")
        if any(_ESCAPED_WORD.fullmatch(a) for a in alternatives):
            joined = "|".join(
                a + "(?![A-Za-z])" if _ESCAPED_WORD.fullmatch(a) else a for a in alternatives
            )
            terminal.pattern = PatternRE("(?:" + joined + ")", pattern.flags)


_NO_COMMAND = "\\zqxjkvw"  # a command no grammar defines


@dataclass(frozen=True, slots=True)
class Parser:
    lark: lark.Lark
    terminals: tuple[re.Pattern[str], ...]  # the command terminals' patterns ("unknown-command")


_PARSERS: dict[str, Parser] = {}


def parser_for(classes: MacroClass) -> Parser:
    """The Earley parser of a macro classification, built once per process."""
    parser = _PARSERS.get(classes.key)
    if parser is None:
        built = lark.Lark(
            grammar_text(classes),
            source_path=str(SHIPPED),
            parser="earley",
            lexer="dynamic",
            ambiguity="explicit",
            propagate_positions=True,
            maybe_placeholders=False,
            keep_all_tokens=True,
            ordered_sets=True,
            start=list(STARTS),
            edit_terminals=whole_name,
        )
        patterns = [re.compile(t.pattern.to_regexp()) for t in built.terminals]
        # A terminal that reads any text (S5-18's TEXT_BODY) names no command.
        commands = tuple(p for p in patterns if not p.fullmatch(_NO_COMMAND))
        parser = _PARSERS[classes.key] = Parser(built, commands)
    return parser


# ============================================================================ results


@dataclass(frozen=True, slots=True)
class MathContext:
    """Declared context: symbols applied as functions, symbols that are variables (both written as
    the symbol, a lone control word with or without its backslash), and the pack's constants
    (`math.constants`, D2 §12.1)."""

    functions: frozenset[str] = frozenset()
    variables: frozenset[str] = frozenset()
    constants: frozenset[str] = frozenset()

    def key(self) -> str:
        return json.dumps([sorted(self.functions), sorted(self.variables), sorted(self.constants)])


@dataclass(frozen=True, slots=True)
class Occurrence:
    """A symbol occurrence; `start`/`end` index the parsed text. `name`, `base`, `sub` and `sup`
    are token forms (`sub` and `sup` of the script's content without its braces)."""

    name: str
    base: str
    sub: str | None
    sup: str | None
    start: int
    end: int
    constant: bool = False
    in_subscript_of: str | None = None


@dataclass(frozen=True, slots=True)
class Failure:
    """Why a value did not parse whole: the category, the exception, the position and TeX token
    there, and the terminals allowed there."""

    category: str
    error: str
    position: int | None = None
    token: str = ""
    allowed: tuple[str, ...] = ()
    detail: str | None = None


@dataclass(frozen=True)
class MathResult:
    latex: str  # the parsed text
    requested: Kind
    status: ParseOutcome
    kind: str | None = None  # formula | relation | member | set_expr | list | ambiguous | None
    tree: Tree[Token] | None = None
    failure: Failure | None = None  # failed; or the whole input's failure behind a trimmed reading
    notes: tuple[str, ...] = ()
    occurrences: tuple[Occurrence, ...] = ()
    tail: str = ""  # trailing punctuation dropped before the reading (T1)
    macros: Mapping[str, MacroDef] = field(default_factory=dict)
    classes: MacroClass = field(default_factory=MacroClass)
    context: MathContext = field(default_factory=MathContext)


# ============================================================================ the deadline


class _Expired(BaseException):
    """Raised by the timer. A BaseException, so no `except Exception` inside Lark, SymPy or the
    resolver swallows it."""


@contextmanager
def _deadline(seconds: float) -> Generator[None]:
    armed = [True]

    def expire(signum: int, frame: FrameType | None) -> None:
        if armed[0]:
            raise _Expired

    previous = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        armed[0] = False
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


# ============================================================================ failures

_ENVIRONMENT = frozenset({"\\begin", "\\end"})
_TEXT = frozenset({"\\text", "\\mbox", "\\textrm"})
_LIMIT = frozenset({"\\lim", "\\to"})
_INTEGRAL = frozenset({"\\int", "\\iint", "\\oint"})
_SUM = frozenset({"\\sum", "\\prod"})
_UNSUPPORTED_RELATION = frozenset(
    {
        "\\mapsto",
        "\\Rightarrow",
        "\\iff",
        "\\implies",
        "\\Leftrightarrow",
        "\\Longrightarrow",
        "\\leftarrow",
        "\\rightarrow",
        "\\longrightarrow",
        "\\Leftarrow",
        "\\leftrightarrow",
    }
)


def _known(word: str, parser: Parser) -> bool:
    return word in tex.DROP or any(p.fullmatch(word) for p in parser.terminals)


def _failure(error: Exception, source: str, parser: Parser) -> Failure:
    position: int | None = None
    allowed: frozenset[str] | set[str] = frozenset()
    if isinstance(error, UnexpectedCharacters):
        position, allowed = error.pos_in_stream, error.allowed or frozenset()
    elif isinstance(error, UnexpectedToken):
        position, allowed = error.token.start_pos, error.expected or frozenset()
    elif isinstance(error, UnexpectedEOF):
        position, allowed = len(source), frozenset(error.expected or ())
    found = tex.token_at(source, position) if position is not None else None
    token = found.text if found is not None else ""
    if not isinstance(error, UnexpectedInput):
        category = "internal"
    elif (
        isinstance(error, UnexpectedEOF)
        or (isinstance(error, UnexpectedToken) and error.token.type == "$END")
        or position == len(source)
    ):
        category = "incomplete"
    elif found is not None and found.kind == "word":
        if token in _ENVIRONMENT:
            category = "environment"
        elif token in _TEXT:
            category = "text-in-math"
        elif token in _LIMIT:
            category = "limit-arrow"
        elif token in _INTEGRAL:
            category = "integral-bounds"
        elif token in _SUM:
            category = "sum-bounds"
        elif token in _UNSUPPORTED_RELATION:
            category = "unsupported-relation"
        elif not _known(token, parser):
            category = "unknown-command"
        else:
            category = "unexpected-command"
    elif token in ("&", "\\\\"):
        category = "alignment"
    elif token in (",", ";", ".", ":"):
        category = "punctuation-or-list"
    else:
        category = "unexpected-token"
    detail = (
        None if isinstance(error, UnexpectedInput) else f"{type(error).__name__}: {error}"[:160]
    )
    return Failure(
        category, type(error).__name__, position, token, tuple(sorted(allowed))[:12], detail
    )


# ============================================================================ ambiguity


def _unbrace(node: _tree.Node) -> _tree.Node:
    if (
        isinstance(node, Tree)
        and node.data == "group_curly_parentheses"
        and len(node.children) == 3
    ):
        return node.children[1]
    return node


def _leftmost(node: _tree.Node) -> Token | None:
    while isinstance(node, Tree):
        if not node.children:
            return None
        node = node.children[0]
    return node


def _is_symbol(node: _tree.Node) -> bool:
    return (isinstance(node, Token) and node.type in _SYMBOL_TOKENS) or (
        isinstance(node, Tree) and node.data == "sub_symbol"
    )


class _Resolver:
    def __init__(
        self, source: str, macros: Mapping[str, MacroDef], classes: MacroClass, context: MathContext
    ) -> None:
        self.source = source
        self.macros = macros
        self.sets = dict(classes.sets)
        self.ops = dict(classes.ops)
        self.functions = {bare(x) for x in context.functions} | set(KNOWN_FUNCTIONS)
        self.variables = {bare(x) for x in context.variables}
        self.notes: list[str] = []
        self.unresolved = 0

    def name(self, node: _tree.Node) -> str:
        return bare(symbol_name(node, self.source, self.macros))

    def flags(self, node: _tree.Node) -> tuple[set[str], set[str]]:
        """(symbols applied as functions, symbols multiplied by a following parenthesized group)."""
        applied: set[str] = set()
        multiplied: set[str] = set()
        if isinstance(node, Token):
            return applied, multiplied
        if node.data == "function_applied":
            applied.add(self.name(node.children[0]))
        elif node.data == "adjacent_expressions" and len(node.children) == 2:
            first, second = node.children
            leftmost = _leftmost(second)
            if leftmost is not None and leftmost.type == "L_PAREN":
                if _is_symbol(first):
                    multiplied.add(self.name(first))
                elif (
                    isinstance(first, Tree)
                    and first.data == "superscript"
                    and len(first.children) == 3
                    and _is_symbol(first.children[0])
                    and _tree.form(_unbrace(first.children[2]), self.source, self.macros) == "-1"
                ):  # F^{-1}(p): inverse-function notation the grammar reads as a product
                    multiplied.add(self.name(first.children[0]))
        if node.data != "_ambig":
            for child in node.children:
                a, m = self.flags(child)
                applied |= a
                multiplied |= m
        return applied, multiplied

    def declare_definitions(self, tree: Tree[Token]) -> None:
        """`g(x) = ...`: the left side applies g to symbols, so g is a function here."""
        for node in tree.iter_subtrees():
            if node.data not in ("eq", "rel_chain") or not node.children:
                continue
            left = node.children[0]
            readings = left.children if isinstance(left, Tree) and left.data == "_ambig" else [left]
            for reading in readings:
                if not (isinstance(reading, Tree) and reading.data == "function_applied"):
                    continue
                arguments = [t for t in _tree.leaves(reading.children[2]) if t.type != "COMMA"]
                if arguments and all(t.type in _SYMBOL_TOKENS for t in arguments):
                    name = self.name(reading.children[0])
                    if name not in self.variables and name not in self.functions:
                        self.functions.add(name)
                        self.notes.append(f"{name} declared a function by its definition")

    def lone_symbol_formula(self, node: _tree.Node) -> _tree.Node | None:
        """`any_value` over [formula(symbol), set_named(symbol)] -> the formula reading; over
        [member, value_list] (`a, b \\in S`) -> the membership of every element."""
        if not (isinstance(node, Tree) and node.data == "_ambig"):
            return None
        alternatives = node.children

        def readings(kind: str) -> list[Tree[Token]]:
            return [
                a
                for a in alternatives
                if isinstance(a, Tree)
                and a.data == "any_value"
                and isinstance(a.children[0], Tree)
                and a.children[0].data == kind
            ]

        formulas, named = readings("formula"), readings("set_named")
        if len(formulas) == 1 and named and len(formulas) + len(named) == len(alternatives):
            self.notes.append("a lone symbol: read as a formula (a named set needs a set position)")
            return formulas[0]
        members, lists = readings("member"), readings("value_list")
        if len(members) == 1 and lists and len(members) + len(lists) == len(alternatives):
            self.notes.append("a comma list before \\in: every listed element is a member")
            return members[0]
        return None

    def admissible(self, reading: _tree.Node) -> bool:
        applied, multiplied = self.flags(reading)
        return applied <= self.functions and multiplied <= self.variables

    def value(self, reading: _tree.Node) -> Any:
        try:
            return transform(reading, self.source, self.macros, self.sets, self.ops)
        except Exception:  # a reading without a value is not comparable
            return None

    def resolve(self, node: _tree.Node) -> _tree.Node:
        if isinstance(node, Token):
            return node
        children = [self.resolve(c) for c in node.children]
        if node.data != "_ambig":
            return Tree(node.data, children, node.meta)
        keep = [a for a in children if self.admissible(a)]
        if len(keep) == 1:
            return keep[0]
        candidates = keep or children
        values = [self.value(a) for a in candidates]
        if all(v is not None for v in values) and all(v == values[0] for v in values[1:]):
            return candidates[0]
        self.unresolved += 1
        applied: set[str] = set()
        multiplied: set[str] = set()
        for a in children:
            f, p = self.flags(a)
            applied |= f
            multiplied |= p
        if applied | multiplied:
            what = f"application or product: {', '.join(sorted(applied | multiplied))}"
        else:
            what = f"{len(candidates)} readings"
        self.notes.append(f"unresolved ambiguity ({what})")
        return Tree("_ambig", candidates, node.meta)

    def residual_products(self, node: _tree.Node) -> set[str]:
        """Product readings of `symbol(...)` with an undeclared symbol, left in the tree."""
        return self.flags(node)[1] - self.variables


def _detect(tree: _tree.Node) -> str | None:
    node = tree
    if isinstance(node, Tree) and node.data == "_ambig":
        kinds = {_detect(c) for c in node.children}
        return kinds.pop() if len(kinds) == 1 else "ambiguous"
    if isinstance(node, Tree) and node.data == "any_value":
        node = node.children[0]
        if isinstance(node, Tree) and node.data == "_ambig":
            kinds = {_detect(Tree("any_value", [c])) for c in node.children}
            return kinds.pop() if len(kinds) == 1 else "ambiguous"
    if isinstance(node, Tree):
        if node.data in ("formula", "relation", "member"):
            return node.data
        if node.data == "value_list":
            return "list"
        if node.data in _SET_ROOTS:
            return "set_expr"
    return None


def _bare_interval(tree: Tree[Token]) -> bool:
    node = tree.children[0] if tree.data == "any_value" else tree
    return isinstance(node, Tree) and node.data == "interval"


# ============================================================================ occurrences


def occurrences(
    tree: _tree.Node, source: str, macros: Mapping[str, MacroDef], constants: frozenset[str]
) -> tuple[Occurrence, ...]:
    """Symbol occurrences of a reading, by position; a subscript's symbols name what they index."""
    found: dict[tuple[int, int, str], Occurrence] = {}

    def form(node: _tree.Node, braced: bool = False) -> str:
        return _tree.form(node, source, macros, braced)

    def add(node: _tree.Node, sup: str | None = None, parent: str | None = None) -> None:
        where = _tree.span(node)
        if where is None:
            return
        sub: str | None = None
        if isinstance(node, Tree) and node.data == "sub_symbol":
            base = form(node.children[0])
            sub = form(node.children[2], braced=True)
        else:
            base = form(node)
        name = form(node)
        key = (where[0], where[1], name)
        if key not in found:
            constant = name in constants and sub is None
            found[key] = Occurrence(name, base, sub, sup, where[0], where[1], constant, parent)

    def walk(node: _tree.Node, parent: str | None = None) -> None:
        if isinstance(node, Token):
            if node.type in _SYMBOL_TOKENS:
                add(node, parent=parent)
            return
        rule = node.data
        if rule == "op_name":
            return
        if rule in ("multi_letter_symbol", "styled"):
            add(node, parent=parent)
            return
        if rule == "superscript" and len(node.children) >= 3:
            base = node.children[0]
            exponent = node.children[2] if len(node.children) == 3 else node.children[3]
            if _is_symbol(base) or (isinstance(base, Tree) and base.data == "styled"):
                add(base, sup=form(exponent, braced=True), parent=parent)
                if isinstance(base, Tree) and base.data == "sub_symbol":
                    walk(base.children[2], parent=form(base))
                walk(exponent, parent)
                return
        if rule == "sup_sub":
            base, _caret, exponent, underscore, argument = node.children
            sub = Tree("sub_symbol", [base, underscore, argument])
            add(sub, sup=form(exponent, braced=True), parent=parent)
            walk(argument, parent=form(sub))
            walk(exponent, parent)
            return
        if rule == "sub_symbol":
            add(node, parent=parent)
            walk(node.children[2], parent=form(node))
            return
        if rule == "pi_constant":
            where = _tree.span(node)
            if where is not None:
                found[(where[0], where[1], "\\pi")] = Occurrence(
                    "\\pi", "\\pi", None, None, where[0], where[1], constant=True
                )
            return
        for child in node.children:
            walk(child, parent)

    walk(tree)
    return tuple(sorted(found.values(), key=lambda o: (o.start, o.end)))


# ============================================================================ parse

_MEMO: OrderedDict[tuple[str, str, str, str], MathResult] = OrderedDict()


def parse(
    latex: str,
    kind: Kind = "any_value",
    macros: Mapping[str, MacroDef] | None = None,
    context: MathContext | None = None,
    *,
    seconds: float = PARSE_SECONDS,
) -> MathResult:
    """Read `latex` under the start symbol `kind` with the effective macro table `macros`."""
    if threading.current_thread() is not threading.main_thread():
        raise OffMainThread("the math grammar runs only on a process's main thread (its deadline)")
    if kind not in STARTS:
        raise ValueError(f"kind {kind!r} is not one of {STARTS}")
    table: Mapping[str, MacroDef] = macros or {}
    ctx = context or MathContext()
    key = (latex, kind, _table_key(table), ctx.key())
    hit = _MEMO.get(key)
    if hit is not None:
        _MEMO.move_to_end(key)
        return hit
    result = _read(latex, kind, table, ctx, seconds)
    if result.failure is None or result.failure.category != "timeout":
        _MEMO[key] = result
        if len(_MEMO) > MEMO_SIZE:
            _MEMO.popitem(last=False)
    return result


def _read(
    latex: str, kind: Kind, table: Mapping[str, MacroDef], ctx: MathContext, seconds: float
) -> MathResult:
    classes = classify(table)
    parser = parser_for(classes)
    constants = frozenset(tex.token_form(c, table) for c in ctx.constants)
    base = MathResult(latex, kind, ParseOutcome.FAILED, macros=table, classes=classes, context=ctx)
    try:
        with _deadline(seconds):
            return _reading(base, parser, constants)
    except _Expired:
        return dataclasses.replace(base, failure=Failure("timeout", "Timeout"))


def _reading(base: MathResult, parser: Parser, constants: frozenset[str]) -> MathResult:
    source, kind = base.latex, base.requested
    tree: Tree[Token] | None = None
    failure: Failure | None = None
    tail = ""
    try:
        tree = parser.lark.parse(source, start=kind)
    except Exception as error:  # every failure gets a category
        failure = _failure(error, source, parser)
        trimmed = source.rstrip().rstrip(_TRAILING).rstrip()
        if trimmed and trimmed != source.strip():
            try:
                tree = parser.lark.parse(trimmed, start=kind)
                tail = source[len(trimmed) :]
            except Exception:  # the whole input's failure stands
                tree = None
    if tree is None:
        return dataclasses.replace(base, failure=failure)
    try:
        resolver = _Resolver(source, base.macros, base.classes, base.context)
        resolver.declare_definitions(tree)
        node: _tree.Node = resolver.lone_symbol_formula(tree) or tree
        node = resolver.resolve(node)
        node = resolver.lone_symbol_formula(node) or node
        if not isinstance(node, Tree):
            raise TypeError("a reading resolved to a token")
        found = occurrences(node, source, base.macros, constants)
    except Exception as error:  # a crash after parsing is reported, not raised
        return dataclasses.replace(base, failure=_failure(error, source, parser))
    notes = list(resolver.notes)
    residual = resolver.residual_products(node) if not resolver.unresolved else set()
    if residual:
        notes.append(
            f"product or application: {', '.join(sorted(residual))} (undeclared symbol before '(')"
        )
    if resolver.unresolved or residual:
        status = ParseOutcome.AMBIGUOUS
    elif kind == "any_value" and _bare_interval(node):
        status = ParseOutcome.AMBIGUOUS
        notes.append("interval or pair: a bare (a, b) without a declared set kind")
    elif tail:
        status = ParseOutcome.PARTIAL
        notes.append("trailing punctuation dropped")
    else:
        status = ParseOutcome.OK
    return dataclasses.replace(
        base,
        status=status,
        kind=_detect(node) if kind == "any_value" else kind,
        tree=node,
        failure=failure if tail else None,
        notes=tuple(notes),
        occurrences=found,
        tail=tail,
    )


# ============================================================================ SymPy


def to_sympy(result: MathResult) -> Any:
    """The SymPy value of a parsed value (evaluation's value equivalence; M11 from phase 1).

    Raises `NotParsed`, `Ambiguous` or `NotRepresentable`; transformer failures are unwrapped from
    `VisitError`. The pack's constants named `e` read as Euler's number (`\\pi` has its own rule).
    """
    if result.tree is None:
        raise NotParsed(result.failure)
    if result.status is ParseOutcome.AMBIGUOUS:
        raise Ambiguous("; ".join(result.notes))
    sets, ops = dict(result.classes.sets), dict(result.classes.ops)
    try:
        value = transform(result.tree, result.latex, result.macros, sets, ops)
    except VisitError as error:
        cause = error.orig_exc
        if isinstance(cause, NotRepresentable):
            raise cause from error
        raise NotRepresentable(f"{type(cause).__name__}: {cause}") from error
    if not isinstance(value, sympy.Basic) or _holds_tree(value):
        raise NotRepresentable("a construct without a SymPy value")
    if "e" in {tex.token_form(c, result.macros) for c in result.context.constants}:
        euler = {
            s: sympy.E for s in value.free_symbols if isinstance(s, sympy.Symbol) and s.name == "e"
        }
        value = value.xreplace(euler)
    return value


def _holds_tree(value: Any) -> bool:
    if isinstance(value, Tree):
        return True
    if isinstance(value, sympy.Basic):
        return any(_holds_tree(a) for a in value.args)
    return False
