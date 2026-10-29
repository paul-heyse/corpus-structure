"""The rule-language helper: typed rule-engine contexts with compile-time literal checks (P0-S-2).

Schema and rules §3.5; schema-rules note L-04, L-05 (P8); D2 §7.4; ADR-0018. One helper serves the
pack rules and orchestration's policies, so both share one compile discipline.

**A language** declares its OBJECT types and root symbols in a small type notation (`string`,
`number`, `boolean`, `list[T]`, `map[T]` for string keys, an OBJECT name, a trailing `?` for
nullable, and `function(T, …)->T` for builtins), plus its `$` builtins and, per attribute, the
closed vocabulary its values (or, for a list, its elements; for a map, its keys) come from.
`Language.compile(rule_id, text)` builds a rule-engine `Context` with `type_resolver_from_dict`,
`mapping_attribute_lookup=False` and `default_timezone="utc"`, a fresh context per expression (a
shared context accumulates symbols across rules), and returns the `Rule`. Structured symbols are
OBJECTs read through `getattr` over plain view objects.

**Compile-time error classes** (`RuleErrorCode`), each a `RuleError` at construction:
- rule-engine's own: a syntax error, an unknown symbol, an unknown (misspelled) attribute,
  attribute access on a nullable value, a wrong function argument type, an operand type mismatch;
- `$now`, `$today` and `$random`, refused from the context's symbol set (determinism);
- an attribute the language declares absent with a reason: at the batch site, a reading of the
  math grammar (`at: [finalize]` rules only); an ambiguous qualifier identifier;
- a regular expression (`=~`, `=~~`, `!~`, `!~~`) over formula text, which runs Python `re` with
  no timeout;
- a string literal outside its vocabulary (coordinator decision 23, DA-012).

**The literal walk.** After construction the helper walks the reduced tree (`Rule.statement`; a
private rule-engine surface, so constant folding has already happened) for equality comparisons,
memberships, subscripts and function arguments that meet a vocabulary-typed operand and a string
literal. A vocabulary-typed operand is an attribute of a declared OBJECT (its type name and the
attribute name identify it, so comprehension variables are covered) or a `$` builtin; a coalesce
`x ?? 'default'` keeps `x`'s vocabulary and admits its own default. The walk is the built option;
the `$enums` membership fallback of §3.5 is not needed (settled by the tests over the pack's rules).
"""

from __future__ import annotations

import difflib
import enum
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, ClassVar

import rule_engine
from rule_engine import Context, DataType, Rule, errors
from rule_engine.ast import (
    ArrayExpression,
    CoalesceExpression,
    ComparisonExpression,
    ContainsExpression,
    ExpressionBase,
    FunctionCallExpression,
    FuzzyComparisonExpression,
    GetAttributeExpression,
    GetItemExpression,
    SetExpression,
    StringExpression,
    SymbolExpression,
)
from rule_engine.builtins import Builtins

NONDETERMINISTIC = frozenset({"now", "today", "random"})
BUILTIN = "$"  # the owner part of a builtin's reference, `("$", name)`

Ref = tuple[str, str]  # (OBJECT type name, attribute) or ("$", builtin name)


class RuleErrorCode(enum.StrEnum):
    """The compile-time error classes of a rule or policy expression (module doc)."""

    SYNTAX = "syntax"
    UNKNOWN_SYMBOL = "unknown_symbol"
    UNKNOWN_ATTRIBUTE = "unknown_attribute"
    NULLABLE_ACCESS = "nullable_access"
    ARGUMENT_TYPE = "argument_type"
    TYPE_MISMATCH = "type_mismatch"
    NONDETERMINISTIC_BUILTIN = "nondeterministic_builtin"
    READING_AT_BATCH = "reading_at_batch"
    AMBIGUOUS_QUALIFIER = "ambiguous_qualifier"
    REGEX_ON_FORMULA_TEXT = "regex_on_formula_text"
    LITERAL_OUTSIDE_VOCABULARY = "literal_outside_vocabulary"
    # rules-file errors the rules compiler adds (schema.rules)
    UNKNOWN_APPLIES_TO = "unknown_applies_to"
    DUPLICATE_RULE_ID = "duplicate_rule_id"
    RULE_ID_PREFIX = "rule_id_prefix"
    BAD_TABLE = "bad_table"
    BAD_VIEW = "bad_view"


@dataclass(frozen=True)
class RuleProblem:
    rule: str
    code: RuleErrorCode
    message: str

    def __str__(self) -> str:
        return f"{self.rule}: [{self.code}] {self.message}"


class RuleError(ValueError):
    """Expressions that do not compile; `problems` lists each with its rule and code."""

    def __init__(self, problems: Sequence[RuleProblem]) -> None:
        self.problems = tuple(problems)
        super().__init__("rules refused:\n  " + "\n  ".join(str(p) for p in self.problems))

    @property
    def codes(self) -> set[RuleErrorCode]:
        return {p.code for p in self.problems}


@dataclass(frozen=True)
class Vocabulary:
    """A closed set of strings a typed operand takes (a generated closed set, a pack enum, a
    version-scoped set, or names of the schema version)."""

    name: str
    members: frozenset[str]

    def nearest(self, literal: str) -> str:
        close = difflib.get_close_matches(literal, sorted(self.members), n=1, cutoff=0.0)
        return close[0] if close else ""

    def admit(self, extra: str) -> Vocabulary:
        return Vocabulary(self.name, self.members | {extra})


@dataclass(frozen=True)
class Builtin:
    """A `$` builtin: its Python value and its declared type (in the module's notation)."""

    value: Any
    type: str


# --- The type notation ------------------------------------------------------------------------


def _split_args(text: str) -> list[str]:
    out, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch in "[(":
            depth += 1
        elif ch in "])":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append(text[start:i].strip())
            start = i + 1
    if text[start:].strip():
        out.append(text[start:].strip())
    return out


class _Types:
    """Type texts -> rule-engine data types, OBJECTs built once each with a `getattr` accessor."""

    SCALARS: ClassVar[dict[str, Any]] = {
        "string": DataType.STRING,
        "number": DataType.FLOAT,
        "boolean": DataType.BOOLEAN,
    }

    def __init__(self, objects: Mapping[str, Mapping[str, str]]) -> None:
        self.objects = objects
        self.built: dict[str, Any] = {}

    def object(self, name: str) -> Any:
        if name not in self.built:
            attributes = {a: self.parse(t) for a, t in self.objects[name].items()}
            self.built[name] = DataType.OBJECT(name, attributes=attributes, accessor=getattr)
        return self.built[name]

    def parse(self, text: str) -> Any:
        text = text.strip()
        if text.endswith("?"):
            return DataType.NULLABLE(self.parse(text[:-1]))
        if text.startswith("function(") and ")->" in text:
            args, ret = text[len("function(") :].rsplit(")->", 1)
            return DataType.FUNCTION(
                "function",
                return_type=self.parse(ret),
                argument_types=tuple(self.parse(a) for a in _split_args(args)),
            )
        if text.startswith("list[") and text.endswith("]"):
            return DataType.ARRAY(self.parse(text[5:-1]))
        if text.startswith("map[") and text.endswith("]"):
            return DataType.MAPPING(DataType.STRING, self.parse(text[4:-1]))
        if text in self.SCALARS:
            return self.SCALARS[text]
        if text in self.objects:
            return self.object(text)
        raise ValueError(f"unknown type {text!r}")


# --- The language -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Language:
    """One typed rule language (module doc). Immutable; each `compile` builds its own context."""

    objects: Mapping[str, Mapping[str, str]]
    symbols: Mapping[str, str]
    builtins: Mapping[str, Builtin] = field(default_factory=dict)
    values: Mapping[Ref, Vocabulary] = field(default_factory=dict)
    keys: Mapping[Ref, Vocabulary] = field(default_factory=dict)
    arguments: Mapping[str, tuple[Vocabulary | None, ...]] = field(default_factory=dict)
    absent: Mapping[Ref, tuple[RuleErrorCode, str]] = field(default_factory=dict)
    no_regex: frozenset[Ref] = frozenset()

    @cached_property
    def _types(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        types = _Types(self.objects)
        symbols = {name: types.parse(t) for name, t in self.symbols.items()}
        values = {name: b.value for name, b in self.builtins.items()}
        value_types = {name: types.parse(b.type) for name, b in self.builtins.items()}
        return symbols, values, value_types

    def context(self) -> Context:
        symbols, values, value_types = self._types
        ctx = Context(
            type_resolver=rule_engine.type_resolver_from_dict(symbols),
            mapping_attribute_lookup=False,
            default_timezone="utc",
        )
        ctx.builtins = Builtins.from_defaults(
            values=values, value_types=value_types, timezone=ctx.default_timezone
        )
        return ctx

    def compile(self, rule_id: str, text: str) -> Rule:
        """The compiled expression, or a `RuleError` naming the rule and the error class."""
        ctx = self.context()
        try:
            rule = Rule(text, context=ctx)
        except errors.EngineError as error:
            # the symbols seen before the error are recorded, so a banned builtin is named too
            raise RuleError([self._classify(rule_id, error), *_banned(rule_id, ctx)]) from None
        problems = _banned(rule_id, ctx)
        problems += _Walk(self, rule_id).problems(rule.statement.expression)
        if problems:
            raise RuleError(problems)
        return rule

    def _classify(self, rule_id: str, error: errors.EngineError) -> RuleProblem:
        message = str(getattr(error, "message", "") or error)
        if isinstance(error, errors.ObjectAttributeError):
            owner = getattr(error.object, "name", "")
            declared = self.absent.get((owner, error.attribute_name))
            if declared is not None:
                return RuleProblem(rule_id, declared[0], declared[1])
            hint = f" (did you mean {error.suggestion!r}?)" if error.suggestion else ""
            return RuleProblem(
                rule_id,
                RuleErrorCode.UNKNOWN_ATTRIBUTE,
                f"{owner} has no attribute {error.attribute_name!r}{hint}",
            )
        if isinstance(error, errors.SyntaxError):
            return RuleProblem(rule_id, RuleErrorCode.SYNTAX, message)
        if isinstance(error, errors.SymbolResolutionError):
            hint = f" (did you mean {error.suggestion!r}?)" if error.suggestion else ""
            return RuleProblem(
                rule_id,
                RuleErrorCode.UNKNOWN_SYMBOL,
                f"unknown symbol {error.symbol_name!r}{hint}",
            )
        if isinstance(error, errors.FunctionCallError):
            return RuleProblem(rule_id, RuleErrorCode.ARGUMENT_TYPE, message)
        if "nullable" in message:
            return RuleProblem(rule_id, RuleErrorCode.NULLABLE_ACCESS, message)
        return RuleProblem(rule_id, RuleErrorCode.TYPE_MISMATCH, message)


def _banned(rule_id: str, ctx: Context) -> list[RuleProblem]:
    banned = sorted(ctx.symbols & NONDETERMINISTIC)
    if not banned:
        return []
    names = ", ".join(f"${b}" for b in banned)
    message = f"{names} is not deterministic; rules and policies may not read it"
    return [RuleProblem(rule_id, RuleErrorCode.NONDETERMINISTIC_BUILTIN, message)]


# --- The literal walk -------------------------------------------------------------------------


def _children(node: Any) -> Iterator[ExpressionBase]:
    names = set(getattr(node, "__dict__", {}))
    for cls in type(node).__mro__:
        slots = getattr(cls, "__slots__", ())
        names.update((slots,) if isinstance(slots, str) else slots)
    for name in sorted(names - {"context"}):
        yield from _expressions(getattr(node, name, None))


def _expressions(value: Any) -> Iterator[ExpressionBase]:
    if isinstance(value, ExpressionBase):
        yield value
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _expressions(item)


def _ref(expr: Any) -> Ref | None:
    if isinstance(expr, CoalesceExpression):
        return _ref(expr.left)
    if isinstance(expr, GetAttributeExpression):
        owner = getattr(expr, "_object_type", None)
        return (owner.name, expr.name) if owner is not None else None
    if isinstance(expr, SymbolExpression) and expr.scope == "built-in":
        return (BUILTIN, expr.name)
    return None


def _text(expr: Any) -> str:
    """The operand as written, for messages."""
    if isinstance(expr, CoalesceExpression):
        return f"{_text(expr.left)} ?? …"
    if isinstance(expr, GetAttributeExpression):
        return f"{_text(expr.object)}{'&.' if expr.safe else '.'}{expr.name}"
    if isinstance(expr, SymbolExpression):
        return ("$" if expr.scope == "built-in" else "") + expr.name
    if isinstance(expr, GetItemExpression):
        return f"{_text(expr.container)}[…]"
    return type(expr).__name__


def _strings(expr: Any) -> list[str]:
    """The string literals of a literal string, list or set."""
    if isinstance(expr, StringExpression):
        return [expr.value]
    if isinstance(expr, (ArrayExpression, SetExpression)):
        return [m.value for m in expr.value if isinstance(m, StringExpression)]
    return []


class _Walk:
    def __init__(self, language: Language, rule_id: str) -> None:
        self.language = language
        self.rule_id = rule_id
        self.found: list[RuleProblem] = []

    def problems(self, root: ExpressionBase) -> list[RuleProblem]:
        stack = [root]
        while stack:
            node = stack.pop()
            self.visit(node)
            stack.extend(_children(node))
        return self.found

    def vocabulary(self, expr: Any, table: Mapping[Ref, Vocabulary]) -> Vocabulary | None:
        ref = _ref(expr)
        vocab = table.get(ref) if ref is not None else None
        if vocab is not None and isinstance(expr, CoalesceExpression):
            for default in _strings(expr.right):
                vocab = vocab.admit(default)
        return vocab

    def check(self, operand: Any, literals: list[str], vocab: Vocabulary | None) -> None:
        if vocab is None:
            return
        for literal in literals:
            if literal not in vocab.members:
                self.found.append(
                    RuleProblem(
                        self.rule_id,
                        RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY,
                        f"{literal!r} is not a member of {vocab.name}, which {_text(operand)} "
                        f"takes; the nearest member is {vocab.nearest(literal)!r}",
                    )
                )

    def visit(self, node: Any) -> None:
        values, keys = self.language.values, self.language.keys
        if isinstance(node, FuzzyComparisonExpression):
            for side in (node.left, node.right):
                if _ref(side) in self.language.no_regex:
                    self.found.append(
                        RuleProblem(
                            self.rule_id,
                            RuleErrorCode.REGEX_ON_FORMULA_TEXT,
                            f"a regular expression over formula text ({_text(side)}) runs without "
                            "a timeout; read the view's token-derived attributes instead",
                        )
                    )
        elif isinstance(node, ComparisonExpression) and node.type in ("eq", "ne"):
            self.check(node.left, _strings(node.right), self.vocabulary(node.left, values))
            self.check(node.right, _strings(node.left), self.vocabulary(node.right, values))
        elif isinstance(node, ContainsExpression):
            # a typed member in a literal list, or a literal in a typed list or map
            self.check(node.member, _strings(node.container), self.vocabulary(node.member, values))
            container = self.vocabulary(node.container, values) or self.vocabulary(
                node.container, keys
            )
            if isinstance(node.member, StringExpression):
                self.check(node.container, [node.member.value], container)
        elif isinstance(node, GetItemExpression) and isinstance(node.item, StringExpression):
            self.check(node.container, [node.item.value], self.vocabulary(node.container, keys))
        elif isinstance(node, FunctionCallExpression):
            ref = _ref(node.function)
            declared = self.language.arguments.get(ref[1]) if ref and ref[0] == BUILTIN else None
            for arg, vocab in zip(node.arguments, declared or (), strict=False):
                if isinstance(arg, StringExpression):
                    self.check(node.function, [arg.value], vocab)
