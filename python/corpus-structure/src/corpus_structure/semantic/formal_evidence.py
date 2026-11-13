"""Positioned formal syntax over an immutable source projection.

Lark objects live only during recognition/reduction. Retained inputs distinguish original
source characters from recognized LaTeX; a relation to an opaque atom never fabricates a
character map to the original PDF. Normalized syntax and domain validity are separate fields.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

import lark
from lark import Token, Tree, UnexpectedInput
from lark.exceptions import VisitError

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import grammar as math_grammar
from corpus_structure.semantic.characterization import LayerReport, occurrence_id, validate_layer
from corpus_structure.semantic.formal_forest import recognize_formal
from corpus_structure.semantic.formal_sources import (
    NORMALIZATION_RECIPE,
    mapped_formal_extents,
    nominate_inline_equations,
    normalize_inline_equation,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_views import PreparedSourceView
from corpus_structure.semantic.structural_parsing import (
    COMPARISON_BASIS,
    FIELD_GRAMMAR,
    FIELD_LEXER_GRAMMAR,
    REVISION_DECLARATION,
    REVISION_LINEAGE,
    REVISION_SUCCESSION,
    formal_field_grammar,
    located_tokens,
)
from corpus_structure.semantic.types import PreparedRelease

PROFILE = "positioned-formal-v1"
FAMILIES = (
    "formal.lexical",
    "formal.number",
    "formal.threshold",
    "formal.date",
    "formal.identifier",
    "formal.quantity",
    "formal.interval",
    "formal.math",
)
_CONVENTIONAL_UNITS = frozenset({"%", "$", "€", "£", "USD", "EUR", "kg", "m", "s"})
_UNIT_AFTER = re.compile(r"[ \t]*(?P<unit>[%$€£]|[A-Za-z][A-Za-z0-9_/-]*)")
_LABELED = re.compile(r"(?m)^[ \t]*(?P<field>(Date|Identifier|Quantity|Range):[^\r\n]*)")
_LABEL_START = re.compile(r"(?<!\w)(Date|Identifier|Quantity|Range):")
_DATE = re.compile(r"(?<![\w-])[0-9]{4}-[0-9]{2}-[0-9]{2}(?![\w-])")
_LABEL_FAMILY = {
    "Date": "date",
    "Identifier": "identifier",
    "Quantity": "quantity",
    "Range": "interval",
}
_COMPARATORS = {">": ">", ">=": ">=", "<": "<", "<=": "<=", "=": "=", "≥": ">=", "≤": "<="}
_EMPTY_EXCEPTIONS = re.compile(r"(?<!\w)(?:no exceptions|exceptions: none)(?!\w)", re.I)
_META = {
    "line": "line",
    "column": "column",
    "end_line": "end_line",
    "end_column": "end_column",
    "container_start": "container_start_pos",
    "container_end": "container_end_pos",
    "container_line": "container_line",
    "container_column": "container_column",
    "container_end_line": "container_end_line",
    "container_end_column": "container_end_column",
}


@dataclass(frozen=True, slots=True)
class FieldCandidate:
    family: str
    start: int
    end: int
    start_symbol: str


@dataclass(frozen=True, slots=True)
class FieldNomination:
    """Examined source is recorded even when no candidate was recognized."""

    examined_start: int
    examined_end: int
    tokens: tuple[Token, ...]
    candidates: tuple[FieldCandidate, ...]


def nominate_fields(text: str) -> FieldNomination:
    """One complete lexical scan for the explicitly named nomination profile.

    Arbitrary prose words do not become unit/identifier assertions. Unknown unit codes
    remain supported in explicitly labeled Quantity/Range fields and in whole-field input.
    """
    tokens = located_tokens(text)
    found: dict[tuple[str, int, int], FieldCandidate] = {}
    labeled = []

    def add(family, start, end, entry):
        found[family, start, end] = FieldCandidate(family, start, end, entry)

    for match in _LABELED.finditer(text):
        start, end = match.span("field")
        add(_LABEL_FAMILY[match[2]], start, end, "labeled")
    for marker in _LABEL_START.finditer(text):
        start = marker.start()
        candidate = text[start : start + 256].splitlines()[0]
        interactive = formal_field_grammar("labeled").parse_interactive(candidate)
        try:
            for token in interactive.lexer_thread.lex(interactive.parser_state):
                interactive.feed_token(token)
                if "$END" in interactive.accepts():
                    stop = token.end_pos
                    if type(stop) is not int or stop <= marker.end() - start:
                        continue
                    add(_LABEL_FAMILY[marker[1]], start, start + stop, "labeled")
                    labeled.append((start, start + stop))
        except UnexpectedInput:
            # The complete accepted prefixes remain exact nominated fields; the
            # unsupported suffix stays in the lexical inventory and raw line input.
            pass

    def outside_label(start, end):
        return not any(a <= start and end <= b for a, b in labeled)

    def unit_end(number_end):
        match = _UNIT_AFTER.match(text, number_end)
        if match and all(part in _CONVENTIONAL_UNITS for part in match["unit"].split("/")):
            return match.end()
        return number_end

    for match in _DATE.finditer(text):
        if outside_label(*match.span()):
            add("date", *match.span(), "date")
    for index, token in enumerate(tokens):
        start, end = token.start_pos, token.end_pos
        if start is None or end is None:
            raise ValueError("formal lexer omitted source positions")
        if token.type == "OP" and index + 1 < len(tokens) and tokens[index + 1].type == "NUMBER":
            begin = (
                tokens[index - 1].start_pos if index and tokens[index - 1].type == "WORD" else start
            )
            stop = unit_end(tokens[index + 1].end_pos)
            if outside_label(begin, stop):
                add("threshold", begin, stop, "threshold")
        if token.type == "NUMBER":
            stop = unit_end(end)
            if stop > end and outside_label(start, stop):
                add("quantity", start, stop, "quantity")
        if str(token) in {"[", "("} and index + 4 < len(tokens):
            number, comma, upper, closing = tokens[index + 1 : index + 5]
            if (
                number.type == upper.type == "NUMBER"
                and str(comma) == ","
                and str(closing) in {"]", ")"}
            ):
                stop = unit_end(closing.end_pos)
                if outside_label(start, stop):
                    add("interval", start, stop, "interval")
    return FieldNomination(
        0,
        len(text),
        tokens,
        tuple(sorted(found.values(), key=lambda c: (c.start, c.end, c.family))),
    )


def decimal_value(text: str) -> str:
    """Exact Decimal normalization without context rounding or huge exponent expansion."""
    value = Decimal(text)
    if not value.is_finite():
        raise ValueError("nonfinite decimal")
    if not value:
        return "0"
    if abs(value.adjusted()) <= 100:
        rendered = format(value, "f")
        return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered
    sign, digits, exponent = value.as_tuple()
    assert isinstance(exponent, int)
    coefficient = "".join(str(digit) for digit in digits)
    while coefficient.endswith("0"):
        coefficient = coefficient[:-1]
        exponent += 1
    return ("-" if sign else "") + coefficient + "e" + str(exponent)


def normalized_token(token: Token) -> dict[str, Any] | None:
    value = str(token)
    if token.type == "NUMBER":
        try:
            return dict(kind="decimal", value=decimal_value(value), domain_status="valid")
        except (ValueError, ArithmeticError) as error:
            return dict(kind="decimal", value=value, domain_status="invalid", reason=str(error))
    if token.type == "OP":
        return dict(kind="comparator", value=_COMPARATORS[value], domain_status="not_requested")
    if token.type in {"IDENTIFIER", "SYMBOL"}:
        return dict(kind="identifier", value=value, domain_status="not_requested")
    if token.type == "UNIT":
        return dict(
            kind="unit",
            value=value,
            domain_status="unresolved",
            reason="No unit/dimension vocabulary was requested.",
        )
    if token.type == "DATE":
        try:
            return dict(
                kind="date", value=date.fromisoformat(value).isoformat(), domain_status="valid"
            )
        except ValueError as error:
            return dict(kind="date", value=value, domain_status="invalid", reason=str(error))
    return None


def normalized_field(tree: Tree) -> dict[str, Any] | None:
    tokens = tuple(tree.scan_values(lambda item: isinstance(item, Token)))
    numbers = [token for token in tokens if token.type == "NUMBER"]
    units = [token for token in tokens if token.type == "UNIT"]
    if tree.data == "threshold":
        value = normalized_token(numbers[0])
        assert value is not None
        symbols = [token for token in tokens if token.type == "SYMBOL"]
        comparator = next(token for token in tokens if token.type == "OP")
        valid = value["domain_status"] == "valid"
        return dict(
            kind="threshold",
            value=value["value"],
            comparator=_COMPARATORS[str(comparator)],
            **({"quantity": str(symbols[0])} if symbols else {}),
            **({"unit": str(units[0])} if units else {}),
            domain_status="unresolved" if valid and units else "valid" if valid else "invalid",
            reason=(
                "Scientific quantity and unit/dimension interpretation "
                "are separate from this syntax."
            ),
        )
    if tree.data in {"interval", "bounded_range"}:
        values: list[dict[str, Any]] = []
        for token in numbers:
            value = normalized_token(token)
            assert value is not None
            values.append(value)
        lower_closed = str(next(token for token in tokens if token.type == "OPEN")) == "["
        upper_closed = str(next(token for token in tokens if token.type == "CLOSE")) == "]"
        valid = all(value["domain_status"] == "valid" for value in values)
        if valid:
            lower, upper = (Decimal(str(token)) for token in numbers)
            valid = lower < upper or (lower == upper and lower_closed and upper_closed)
        return dict(
            kind="interval",
            lower=values[0]["value"],
            upper=values[1]["value"],
            lower_closed=lower_closed,
            upper_closed=upper_closed,
            **({"unit": str(units[0])} if units else {}),
            domain_status="valid" if valid else "invalid",
            **(
                {"reason": "Unit resolution is separate from ordered interval syntax."}
                if valid
                else {"reason": "Interval endpoints do not define a nonempty ordered interval."}
            ),
        )
    if tree.data == "quantity":
        value = normalized_token(numbers[0])
        assert value is not None
        if value["domain_status"] == "invalid":
            return {**value, "unit": str(units[0])}
        return {
            **value,
            "unit": str(units[0]),
            "domain_status": "unresolved",
            "reason": "No unit/dimension vocabulary was requested.",
        }
    if tree.data in {"date", "identifier", "number"} and len(tokens) == 1:
        return normalized_token(tokens[0])
    return None


@lru_cache(maxsize=1)
def field_grammar_identity() -> str:
    return (
        "field-lalr-2:"
        + sha256(
            canonical_bytes(
                {
                    "grammar": FIELD_GRAMMAR,
                    "lark": lark.__version__,
                    "parser": "lalr",
                    "lexer": "contextual",
                    "positions": True,
                }
            )
        ).hexdigest()
    )


@lru_cache(maxsize=1)
def lexical_grammar_identity() -> str:
    return (
        "field-basic-1:"
        + sha256(
            canonical_bytes(
                {
                    "grammar": FIELD_LEXER_GRAMMAR,
                    "lark": lark.__version__,
                    "parser": None,
                    "lexer": "basic",
                    "positions": True,
                }
            )
        ).hexdigest()
    )


def macro_identity(macros: Mapping[str, MacroDef] | None = None) -> str:
    return (
        "none"
        if not macros
        else sha256(
            canonical_bytes(
                [
                    [name, value.nargs, value.default, value.body]
                    for name, value in sorted(macros.items())
                ]
            )
        ).hexdigest()
    )


def math_grammar_identity(macros: Mapping[str, MacroDef] | None = None) -> str:
    return _math_grammar_identity(math_grammar.classify(macros or {}))


@lru_cache(maxsize=16)
def _math_grammar_identity(classes: math_grammar.MacroClass) -> str:
    return (
        "math-lark-1:"
        + sha256(
            canonical_bytes(
                {
                    "math": math_grammar.grammar_text(classes),
                    "lark": lark.__version__,
                    "starts": math_grammar.STARTS,
                    "macro_classification": classes.key,
                    "parser": "earley",
                    "lexer": "dynamic",
                    "ambiguity": "forest",
                    "positions": True,
                    "keep_all_tokens": True,
                    "whole_control_words": True,
                    "ordered_sets": True,
                }
            )
        ).hexdigest()
    )


@lru_cache(maxsize=1)
def grammar_identity() -> str:
    """The installed effective grammar family, including the unedited shipped grammar."""
    recipes = {
        name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in (
            "formal_evidence.py",
            "formal_forest.py",
            "formal_sources.py",
            "structural_parsing.py",
        )
    }
    recipes["math_frontend"] = sha256(Path(math_grammar.__file__).read_bytes()).hexdigest()
    recipes["forest_adapter"] = sha256(
        (Path(__file__).with_name("constructions") / "reuse.py").read_bytes()
    ).hexdigest()
    recipes["symbolic_nodes"] = sha256(
        (Path(__file__).with_name("constructions") / "nodes.py").read_bytes()
    ).hexdigest()
    recipes["symbol_spelling"] = sha256(Path(tex.__file__).read_bytes()).hexdigest()
    return sha256(
        canonical_bytes(
            dict(
                field=field_grammar_identity(),
                lexical=lexical_grammar_identity(),
                math=math_grammar_identity(),
                mapping=recipes,
            )
        )
    ).hexdigest()


def _identity(kind: str, *values: Any) -> str:
    return "formal:" + kind + ":" + sha256(canonical_bytes(values)).hexdigest()


def _native_bounds(node: Token | Tree) -> tuple[int, int] | None:
    owner = node if isinstance(node, Token) else node.meta
    start, end = getattr(owner, "start_pos", None), getattr(owner, "end_pos", None)
    return (start, end) if type(start) is int and type(end) is int else None


class FormalSource(Protocol):
    """The recognizer consumes selected immutable source facts, never a reader."""

    @property
    def text(self) -> str: ...
    @property
    def pieces(self) -> tuple[dict[str, Any], ...]: ...
    @property
    def items(self) -> tuple[dict[str, Any], ...]: ...
    @property
    def health(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class FormalIdentity:
    """Explicit identity policy at extraction, distinct from execution custody."""

    source: bytes
    projection: str
    view: str | int
    semantic: bool = False


class _LayerBuilder:
    def __init__(self, view: FormalSource, operation: Mapping[str, Any], identity: FormalIdentity):
        self.view = view
        self.identity = identity
        self.operation = {} if identity.semantic else dict(operation)
        self.occurrences: dict[str, dict[str, Any]] = {}
        self.annotations: list[dict[str, Any]] = []
        self.memberships: list[dict[str, Any]] = []
        self.terms: dict[str, dict[str, Any]] = {}
        self.choices: dict[str, dict[str, Any]] = {}
        self.problems: dict[str, list[str]] = {family: [] for family in FAMILIES}
        self.counts = dict.fromkeys(FAMILIES, 0)
        self.macros: dict[str, MacroDef] = {}
        self.items = {item["self_ref"]: item for item in view.items}

    def occurrence(self, piece: Mapping[str, Any], start: int, end: int) -> str:
        if piece.get("native_atom_only"):
            if start != 0 or end != 0 or piece["item_ref"] not in self.items:
                raise ValueError("formal native atom has no projected character interval")
            extent = dict(
                projection=self.identity.projection,
                **({} if self.identity.semantic else {"source_view_id": self.identity.view}),
                native_pointer=piece["item_ref"],
                synthetic=False,
            )
            local_id = occurrence_id(json.loads(self.identity.source), [extent])
            self.occurrences[local_id] = {"local_id": local_id, "extents": [extent]}
            return local_id
        if not piece["start"] <= start < end <= piece["end"]:
            raise ValueError("formal source extent exceeds its exact native piece")
        extent = dict(
            projection=self.identity.projection,
            **({} if self.identity.semantic else {"source_view_id": self.identity.view}),
            native_pointer=piece["item_ref"],
            start=start,
            end=end,
            text=self.view.text[start:end],
            synthetic=False,
        )
        pages = {
            entry.get("page_no") for entry in self.items.get(piece["item_ref"], {}).get("prov", ())
        }
        pages.discard(None)
        if len(pages) == 1:
            extent["page"] = next(iter(pages))
        local_id = occurrence_id(json.loads(self.identity.source), [extent])
        self.occurrences[local_id] = {"local_id": local_id, "extents": [extent]}
        return local_id

    def source_fact(self, piece, start, end, kind, value, *, scheme="formal-source-field-1"):
        occurrence = self.occurrence(piece, start, end)
        key = _identity("source-fact", self.operation, occurrence, kind, value)
        self.annotations.append(
            dict(
                local_id=key,
                kind=kind,
                family="formal.lexical",
                vocabulary="formal-source-fields-1",
                native_scheme=scheme,
                native_label=value,
                rule_id=_identity("source-field-policy", kind)
                if self.identity.semantic
                else _identity("source-field-policy", kind, grammar_identity()),
                occurrences=[occurrence],
                status="native_evidence",
            )
        )
        self.counts["formal.lexical"] += 1
        return key, occurrence

    def input(
        self,
        piece: Mapping[str, Any],
        start: int,
        end: int,
        *,
        text: str,
        family: str,
        grammar: str,
        entry: str,
        syntax: str = "complete",
        original: str | None = None,
        representation: str = "source_text",
        exact: bool = True,
        diagnostic: Mapping[str, Any] | None = None,
        correspondence=None,
        normalization_recipe=None,
        macros=None,
    ) -> str:
        parent = self.occurrence(piece, start, end)
        if self.identity.semantic:
            grammar = (
                "formal-math"
                if family == "formal.math"
                else "formal-lexical"
                if family == "formal.lexical"
                else "formal-field"
            )
        identity = _identity(
            "input",
            self.operation,
            parent,
            text,
            grammar,
            entry,
            representation,
            macro_identity(macros),
        )
        formal_input: dict[str, Any] = dict(
            parent_occurrence=parent,
            representation=representation,
            text=text,
            grammar=grammar,
            start_symbol=entry,
            macro_identity=macro_identity(macros),
            syntax_outcome=syntax,
            interpretation_outcome="not_requested",
            symbol_outcome="not_requested",
            correspondence=[
                dict(
                    input_start=0,
                    input_end=len(text),
                    relation="exact" if exact else "contained_in_atom",
                    source_occurrences=[parent],
                )
            ],
        )
        if original is not None:
            formal_input["original_text"] = original
        if correspondence is not None:
            formal_input["correspondence"] = correspondence
        if normalization_recipe is not None:
            formal_input["normalization_recipe"] = normalization_recipe
        if diagnostic is not None:
            formal_input["diagnostic"] = dict(diagnostic)
        self.annotations.append(
            dict(
                local_id=identity,
                kind="formal.input",
                vocabulary="formal-syntax-v1",
                occurrences=[parent],
                native_scheme="lark:" + grammar,
                native_label=entry,
                status="native_evidence",
                family=family,
                formal_input=formal_input,
            )
        )
        self.counts[family] += 1
        return identity

    def formula(
        self,
        piece,
        start,
        end,
        *,
        text,
        representation,
        entry,
        seconds,
        max_nodes,
        exact=True,
        original=None,
        healthy=True,
        diagnostic: dict[str, Any] | None = None,
        correspondence=None,
        normalization_recipe=None,
        inline=False,
        check_active=lambda: None,
    ):
        recognized = None
        syntax = "failed"
        if healthy:
            recognized = recognize_formal(
                text,
                entry,
                region=_identity(
                    "region",
                    self.operation,
                    self.identity.view,
                    self.identity.projection,
                    piece["item_ref"],
                    start,
                    end,
                    representation,
                    text,
                    normalization_recipe,
                    macro_identity(self.macros),
                ),
                seconds=seconds,
                max_nodes=max_nodes,
                check_active=check_active,
                macros=self.macros,
            )
            result = recognized.reading
            syntax = {
                ParseOutcome.OK: "complete",
                ParseOutcome.PARTIAL: "partial",
                ParseOutcome.AMBIGUOUS: "ambiguous",
                ParseOutcome.FAILED: "failed",
            }[result.status]
            if result.failure is not None:
                diagnostic = dict(
                    category=result.failure.category,
                    message=result.failure.detail or result.failure.error,
                    **(
                        {"position": result.failure.position}
                        if result.failure.position is not None and result.failure.position >= 0
                        else {}
                    ),
                )
            if recognized.diagnostic is not None:
                diagnostic = recognized.diagnostic
            if (
                recognized.reducer is not None
                and recognized.reducer.choices
                and syntax == "complete"
            ):
                syntax = "ambiguous"
            if result.tail:
                diagnostic = dict(
                    category=result.failure.category if result.failure else "trimmed_retry",
                    message=(diagnostic["message"] + "; " if diagnostic else "")
                    + (
                        f"Trimmed retry excluded input[{len(text) - len(result.tail)}:"
                        f"{len(text)}] = {result.tail!r}"
                    ),
                    position=len(text) - len(result.tail),
                )
        key = self.input(
            piece,
            start,
            end,
            text=text,
            family="formal.math",
            grammar=math_grammar_identity(self.macros),
            entry=entry,
            syntax=syntax,
            original=original,
            representation=representation,
            exact=exact,
            diagnostic=diagnostic,
            correspondence=correspondence,
            normalization_recipe=normalization_recipe,
            macros=self.macros,
        )
        annotation = next(
            annotation for annotation in self.annotations if annotation["local_id"] == key
        )
        if inline:
            annotation["native_label"] = "introduced_inline_equation"
        if recognized is not None:
            self.packed(key, recognized, piece, start, exact=exact)
            annotation["formal_input"]["interpretation_outcome"] = recognized.interpretation
        if syntax != "complete" or (recognized is not None and recognized.diagnostic is not None):
            self.problems["formal.math"].append(
                "Formula syntax is "
                + syntax
                + (": " + diagnostic["category"] if diagnostic else "")
            )
        return key

    def nodes(
        self,
        root_id: str,
        nodes: Sequence[Token | Tree],
        piece: Mapping[str, Any],
        source_start: int,
        source_end: int,
        *,
        exact: bool,
        family: str,
        normalize: bool,
    ) -> None:
        root = next(
            annotation for annotation in self.annotations if annotation["local_id"] == root_id
        )
        input_text = root["formal_input"]["text"]
        parent_occurrence = root["formal_input"]["parent_occurrence"]
        # Postorder computes spans of positionless _ambig wrappers without recursion.
        bounds: dict[int, tuple[int, int]] = {}
        work = [(node, False) for node in reversed(nodes)]
        while work:
            node, visited = work.pop()
            if isinstance(node, Tree) and not visited:
                work.append((node, True))
                work.extend((child, False) for child in reversed(node.children))
                continue
            span = _native_bounds(node)
            children = (
                [bounds[id(child)] for child in node.children] if isinstance(node, Tree) else []
            )
            if span is None and children:
                span = min(value[0] for value in children), max(value[1] for value in children)
            if span is None:
                raise ValueError("formal syntax node has no source or insertion position")
            bounds[id(node)] = span
        ordinal = 0
        pending = [
            (node, root_id, index, False) for index, node in reversed(tuple(enumerate(nodes)))
        ]
        while pending:
            node, parent_id, order, alternative = pending.pop()
            start, end = bounds[id(node)]
            if not 0 <= start <= end <= len(input_text):
                raise ValueError("formal parser returned out-of-input positions")
            rule = node.type if isinstance(node, Token) else node.data
            identity = _identity("node", root_id, ordinal, rule, start, end)
            ordinal += 1
            formal: dict[str, Any] = dict(
                input_id=root_id,
                node_kind="token" if isinstance(node, Token) else "rule",
                rule=rule,
                start=start,
                end=end,
            )
            meta = node if isinstance(node, Token) else node.meta
            for field, native in _META.items():
                value = getattr(meta, native, None)
                if type(value) is int:
                    formal[field] = value
            normalized = None
            if normalize:
                try:
                    normalized = (
                        normalized_token(node)
                        if isinstance(node, Token)
                        else normalized_field(node)
                    )
                except Exception as error:
                    cause = error.orig_exc if isinstance(error, VisitError) else error
                    root["formal_input"]["interpretation_outcome"] = "failed"
                    root["formal_input"]["diagnostic"] = dict(
                        category="semantic_callback",
                        message=f"{type(cause).__name__}: {cause}",
                        rule=rule,
                    )
                    self.problems[family].append(
                        "Positioned syntax succeeded but normalization failed."
                    )
            if normalized is not None:
                formal["normalized"] = normalized
                outcome = {
                    "not_requested": "not_requested",
                    "valid": "resolved",
                    "invalid": "invalid",
                    "unresolved": "unresolved",
                }[normalized["domain_status"]]
                priority = {
                    "not_requested": 0,
                    "resolved": 1,
                    "unresolved": 2,
                    "invalid": 3,
                    "failed": 4,
                }
                if priority[outcome] > priority[root["formal_input"]["interpretation_outcome"]]:
                    root["formal_input"]["interpretation_outcome"] = outcome
            occurrence = (
                self.occurrence(piece, source_start + start, source_start + end)
                if exact and start < end
                else parent_occurrence
            )
            selected_family = (
                "formal.number"
                if family == "formal.lexical" and isinstance(node, Token) and node.type == "NUMBER"
                else family
            )
            self.annotations.append(
                dict(
                    local_id=identity,
                    kind="formal.token" if isinstance(node, Token) else "formal.rule",
                    vocabulary="formal-syntax-v1",
                    occurrences=[occurrence],
                    native_scheme=root["native_scheme"],
                    native_label=rule,
                    status="native_evidence",
                    family=selected_family,
                    formal=formal,
                )
            )
            self.counts[selected_family] += 1
            self.memberships.append(
                dict(
                    local_id=_identity("member", root_id, parent_id, identity, order),
                    group=parent_id,
                    member=identity,
                    role="alternative" if alternative else "child",
                    order=order,
                    occurrences=[occurrence],
                    scope=root_id,
                    structural=True,
                    family=selected_family,
                )
            )
            if isinstance(node, Tree):
                pending.extend(
                    (child, identity, index, node.data == "_ambig")
                    for index, child in reversed(tuple(enumerate(node.children)))
                )

    def packed(self, root_id, recognized, piece, source_start, *, exact):
        reducer = recognized.reducer
        if reducer is None:
            return
        root = next(
            annotation for annotation in self.annotations if annotation["local_id"] == root_id
        )
        root["formal_input"]["symbol_outcome"] = reducer.symbol_outcome
        parent = root["formal_input"]["parent_occurrence"]

        def located(start, end):
            if root["formal_input"]["representation"] == "normalized_latex" and start < end:
                extents = mapped_formal_extents(root["formal_input"], start, end, self.occurrences)
                if len(extents) != 1:
                    raise ValueError(
                        "normalized formal constituent has discontinuous native support"
                    )
                return self.occurrence(piece, extents[0]["start"], extents[0]["end"])
            return (
                self.occurrence(piece, source_start + start, source_start + end)
                if exact and start < end
                else parent
            )

        for key, syntax in reducer.syntax.items():
            formal = {**syntax["formal"], "input_id": root_id}
            occurrence = located(formal["start"], formal["end"])
            self.annotations.append(
                dict(
                    local_id=key,
                    kind="formal.token" if formal["node_kind"] == "token" else "formal.rule",
                    vocabulary="formal-syntax-v1",
                    native_scheme=root["native_scheme"],
                    native_label=syntax["native_label"],
                    status="native_evidence",
                    family="formal.math",
                    occurrences=[occurrence],
                    formal=formal,
                    **({"rule_id": syntax["rule_id"]} if "rule_id" in syntax else {}),
                )
            )
            self.memberships.append(
                dict(
                    local_id=_identity("packed-member", root_id, key),
                    group=root_id,
                    member=key,
                    role="formal_constituent",
                    order=len(self.memberships),
                    occurrences=[occurrence],
                    scope=root_id,
                    structural=True,
                    family="formal.math",
                )
            )
        self.choices.update(reducer.choices)
        for key, term in reducer.terms.items():
            start, end = reducer.positions.get(key, (0, len(root["formal_input"]["text"])))
            self.terms[key] = {**term, "occurrences": [located(start, end)]}
        for group in reducer.choices.values():
            for member in group["members"]:
                required = self.terms[member["root"]].setdefault("required_choices", [])
                if member["local_id"] not in required:
                    required.append(member["local_id"])
        for key, symbol in reducer.symbols.items():
            formal = {**symbol["formal"], "input_id": root_id}
            if formal.get("symbol_parent") not in reducer.symbols:
                formal.pop("symbol_parent", None)
            occurrence = located(formal["start"], formal["end"])
            self.annotations.append(
                dict(
                    local_id=key,
                    kind="formal.symbol",
                    vocabulary="math-source-symbol-1",
                    native_scheme="math-positioned-symbol-1",
                    native_label=formal["normalized"]["value"],
                    status="native_evidence",
                    family="formal.math",
                    occurrences=[occurrence],
                    formal=formal,
                    premises=symbol["premises"],
                    required_choices=symbol["required_choices"],
                )
            )
            self.memberships.append(
                dict(
                    local_id=_identity("symbol-member", root_id, key),
                    group=root_id,
                    member=key,
                    role="symbol_occurrence",
                    order=len(self.memberships),
                    occurrences=[occurrence],
                    scope=root_id,
                    structural=True,
                    family="formal.math",
                    required_choices=symbol["required_choices"],
                )
            )
            for support in symbol["supports"]:
                self.memberships.append(
                    dict(
                        local_id=_identity("symbol-support", key, support),
                        group=key,
                        member=support["member"],
                        role="symbol_derivation_support",
                        order=len(self.memberships),
                        occurrences=[occurrence],
                        scope=root_id,
                        structural=False,
                        family="formal.math",
                        premises=support["premises"],
                        required_choices=support["required_choices"],
                    )
                )
        for key, syntax in reducer.syntax.items():
            for index, child in enumerate(syntax["children"]):
                target = child.target or child.choice_group
                start, end = reducer.positions.get(
                    target, (syntax["formal"]["start"], syntax["formal"]["end"])
                )
                self.memberships.append(
                    dict(
                        local_id=_identity("packed-part", key, target, index),
                        group=key,
                        member=target,
                        role="part",
                        order=index,
                        occurrences=[located(start, end)],
                        scope=root_id,
                        structural=True,
                        family="formal.math",
                    )
                )
        if recognized.root is not None:
            key = _identity("packed-reading", root_id)
            self.terms[key] = dict(
                local_id=key,
                kind="unknown",
                family="formal.math",
                vocabulary="formal-math-symbolic-1",
                value="formal-reading",
                status="unknown",
                occurrences=[parent],
                children=[recognized.root.edge("reading")],
                premises=[root_id],
            )


def extract_formal_facts(
    builder: _LayerBuilder,
    selected: Sequence[Mapping[str, Any]],
    *,
    math_start: math_grammar.Kind,
    parse_seconds: float,
    max_forest_nodes: int,
    max_inline_chars: int,
    check_active: Callable[[], None],
) -> list[dict[str, Any]]:
    """One actual nomination/parser/reducer implementation shared by both projections."""
    view = builder.view
    for selector in selected:
        a, b = selector.get("start", 0), selector.get("end", len(view.text))
        if not 0 <= a <= b <= len(view.text):
            raise ValueError("formal selected source bounds exceed the actual projection")
        if selector.get("native_pointer") and selector["native_pointer"] not in builder.items:
            raise ValueError("formal selector does not name a selected native source atom")

    def matches(piece, selector):
        selected_pointer = selector.get("native_pointer")
        pointer = piece.get("item_ref")
        seen = set()
        while selected_pointer and pointer != selected_pointer and pointer not in seen:
            seen.add(pointer)
            parent = builder.items.get(pointer, {}).get("parent")
            pointer = parent.get("$ref") if isinstance(parent, dict) else parent
        if selected_pointer and pointer != selected_pointer:
            return False
        if "page" in selector:
            pages = {
                prov.get("page_no")
                for prov in builder.items.get(piece["item_ref"], {}).get("prov", ())
            }
            if pages != {selector["page"]}:
                return False
        return True

    selectors = []
    formula_health = {
        item["pointer"]: item["outcome"] for item in view.health.get("formula_outcomes", ())
    }
    pieces = []
    for piece in view.pieces:
        if piece["kind"] != "native_text":
            continue
        intervals = sorted(
            (
                max(piece["start"], selector.get("start", 0)),
                min(piece["end"], selector.get("end", len(view.text))),
            )
            for selector in selected
            if matches(piece, selector)
            and max(piece["start"], selector.get("start", 0))
            < min(piece["end"], selector.get("end", len(view.text)))
        )
        merged = []
        for a, b in intervals:
            if merged and a <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
            else:
                merged.append((a, b))
        pieces.extend(
            dict(piece, start=a, end=b, complete_atom=(a, b) == (piece["start"], piece["end"]))
            for a, b in merged
        )
    for piece in pieces:
        check_active()
        if piece["kind"] != "native_text":
            continue
        start, end = piece["start"], piece["end"]
        if start == end:
            continue
        text = view.text[start:end]
        selectors.append(
            dict(
                projection=builder.identity.projection,
                native_pointer=piece["item_ref"],
                start=start,
                end=end,
            )
        )
        nomination = nominate_fields(text)
        lexical_id = builder.input(
            piece,
            start,
            end,
            text=text,
            family="formal.lexical",
            grammar=lexical_grammar_identity(),
            entry="lex",
        )
        builder.nodes(
            lexical_id,
            nomination.tokens,
            piece,
            start,
            end,
            exact=True,
            family="formal.lexical",
            normalize=True,
        )
        for basis in COMPARISON_BASIS.finditer(text):
            if not basis[1].strip():
                continue
            occurrence = builder.occurrence(piece, start + basis.start(), start + basis.end())
            builder.annotations.append(
                dict(
                    local_id=_identity("comparison-basis", builder.operation, occurrence),
                    kind="formal.comparison_basis",
                    family="formal.lexical",
                    vocabulary="formal-source-fields-1",
                    native_scheme="source-comparison-basis-1",
                    native_label=basis[1].strip(),
                    rule_id=_identity(
                        "comparison-basis-rule", COMPARISON_BASIS.pattern, COMPARISON_BASIS.flags
                    ),
                    occurrences=[occurrence],
                    status="native_evidence",
                )
            )
            builder.counts["formal.lexical"] += 1
        for token in nomination.tokens:
            if token.type == "WORD" and str(token).casefold() in {"and", "or"}:
                a, b = token.start_pos, token.end_pos
                assert type(a) is int and type(b) is int
                builder.source_fact(
                    piece, start + a, start + b, "formal.coordination_cue", str(token).casefold()
                )
        for marker in _EMPTY_EXCEPTIONS.finditer(text):
            builder.source_fact(
                piece,
                start + marker.start(),
                start + marker.end(),
                "formal.exception_empty",
                "empty",
            )
        for pattern, kind in (
            (REVISION_DECLARATION, "formal.revision_declaration"),
            (REVISION_LINEAGE, "formal.clause_lineage"),
        ):
            for marker in pattern.finditer(text):
                builder.source_fact(
                    piece, start + marker.start(), start + marker.end(), kind, marker[1]
                )
        for marker in REVISION_SUCCESSION.finditer(text):
            group, _ = builder.source_fact(
                piece,
                start + marker.start(),
                start + marker.end(),
                "formal.revision_succession",
                "supersedes",
            )
            for index, role in ((1, "newer_revision"), (2, "older_revision")):
                member, occurrence = builder.source_fact(
                    piece,
                    start + marker.start(index),
                    start + marker.end(index),
                    "formal.version_identifier",
                    marker[index],
                )
                builder.memberships.append(
                    dict(
                        local_id=_identity("revision-member", group, member, role),
                        group=group,
                        member=member,
                        role=role,
                        order=index - 1,
                        scope=group,
                        structural=True,
                        family="formal.lexical",
                        occurrences=[occurrence],
                        premises=[group],
                    )
                )
        item = builder.items.get(piece["item_ref"], {})
        if item.get("label") == "formula":
            if not piece["complete_atom"]:
                builder.problems["formal.math"].append(
                    "Selected source cuts a protected formula atom; "
                    "complete recognition was not attempted."
                )
                continue
            latex = item.get("text", "")
            healthy = formula_health.get(piece["item_ref"]) == "succeeded" and bool(latex.strip())
            builder.formula(
                piece,
                start,
                end,
                text=text,
                representation="source_text",
                entry=math_start,
                original=text,
                seconds=parse_seconds,
                max_nodes=max_forest_nodes,
                check_active=check_active,
            )
            builder.formula(
                piece,
                start,
                end,
                text=latex,
                representation="recognized_latex",
                entry=math_start,
                original=item.get("orig", text),
                seconds=parse_seconds,
                max_nodes=max_forest_nodes,
                exact=piece.get("source_field") == "text" and latex == text,
                healthy=healthy,
                diagnostic=None
                if healthy
                else dict(
                    category="recognition_unavailable",
                    message="The source formula has no attributable successful LaTeX recognition.",
                ),
                check_active=check_active,
            )
            continue
        for equation in nominate_inline_equations(
            view.text, [piece], builder.items, max_chars=max_inline_chars
        ):
            check_active()
            surface = view.text[equation.start : equation.end]
            normalized = (
                normalize_inline_equation(surface) if equation.status == "captured" else None
            )
            correspondence = None
            if normalized is not None:
                correspondence = []
                for part in normalized.pieces:
                    row = dict(
                        input_start=part.input_start,
                        input_end=part.input_end,
                        relation=part.relation,
                        source_occurrences=[]
                        if part.relation == "synthetic"
                        else [
                            builder.occurrence(
                                piece,
                                equation.start + part.source_start,
                                equation.start + part.source_end,
                            )
                        ],
                    )
                    if part.relation == "synthetic":
                        row["boundary"] = equation.start + part.source_start
                    correspondence.append(row)
            healthy_inline = normalized is not None
            category = (
                "inline_nomination_limited"
                if equation.status == "limited"
                else "inline_nomination_unsupported"
            )
            root = builder.formula(
                piece,
                equation.start,
                equation.end,
                text=normalized.text if normalized is not None else surface,
                representation="normalized_latex" if normalized is not None else "source_text",
                entry="formula",
                original=surface,
                seconds=parse_seconds,
                max_nodes=max_forest_nodes,
                exact=normalized is None,
                healthy=healthy_inline,
                diagnostic=None
                if healthy_inline
                else dict(
                    category=category,
                    message=(
                        "Introduced inline equation is outside "
                        "the selected literal normalization contract."
                    ),
                ),
                correspondence=correspondence,
                normalization_recipe=NORMALIZATION_RECIPE,
                inline=True,
                check_active=check_active,
            )
            annotation = next(
                annotation for annotation in builder.annotations if annotation["local_id"] == root
            )
            for a, b in (
                (equation.support_start, equation.start),
                (equation.end, equation.support_end),
            ):
                if a is not None and b is not None and a < b:
                    annotation["occurrences"].append(builder.occurrence(piece, a, b))
        for candidate in nomination.candidates:
            check_active()
            surface = text[candidate.start : candidate.end]
            family = "formal." + candidate.family
            diagnostic = None
            try:
                tree = formal_field_grammar(candidate.start_symbol).parse(surface)
            except UnexpectedInput as error:
                tree = None
                diagnostic = dict(
                    category=type(error).__name__,
                    message=error.get_context(surface),
                    **(
                        {"position": error.pos_in_stream}
                        if error.pos_in_stream is not None and error.pos_in_stream >= 0
                        else {}
                    ),
                )
                builder.problems[family].append("A nominated whole field has unsupported syntax.")
            root = builder.input(
                piece,
                start + candidate.start,
                start + candidate.end,
                text=surface,
                family=family,
                grammar=field_grammar_identity(),
                entry=candidate.start_symbol,
                syntax="complete" if tree is not None else "failed",
                diagnostic=diagnostic,
            )
            if tree is not None:
                builder.nodes(
                    root,
                    [tree],
                    piece,
                    start + candidate.start,
                    start + candidate.end,
                    exact=True,
                    family=family,
                    normalize=True,
                )
    # Recognized formula bytes belong to the native document even when the source
    # view has no readable original characters. Keep syntax anchored to that item;
    # never fabricate a literal projection or an exact character correspondence.
    projected = {piece["item_ref"] for piece in pieces}
    for pointer, item in builder.items.items():
        if item.get("label") != "formula" or pointer in projected:
            continue
        selected_atom = any(
            selector.get("native_pointer", pointer) == pointer
            and (
                "start" not in selector
                or (selector["start"], selector["end"]) == (0, len(view.text))
            )
            and (
                "page" not in selector
                or selector["page"] in {p.get("page_no") for p in item.get("prov", ())}
            )
            for selector in selected
        )
        if not selected_atom:
            continue
        piece = dict(item_ref=pointer, start=0, end=0, native_atom_only=True)
        builder.problems["formal.math"].append(
            "Selected native formula has no exact projected source-character correspondence."
        )
        for representation, surface in (
            ("source_text", item.get("orig", "")),
            ("recognized_latex", item.get("text", "")),
        ):
            healthy = representation == "source_text" or formula_health.get(pointer) == "succeeded"
            if not surface.strip() and representation == "source_text":
                continue
            builder.formula(
                piece,
                0,
                0,
                text=surface,
                representation=representation,
                entry=math_start,
                original=item.get("orig", ""),
                seconds=parse_seconds,
                max_nodes=max_forest_nodes,
                exact=False,
                healthy=healthy and bool(surface.strip()),
                diagnostic=dict(
                    category="source_correspondence_unavailable"
                    if healthy
                    else "recognition_unavailable",
                    message="Native formula retained without projected literal correspondence."
                    if healthy
                    else "Native formula has no attributable successful recognition.",
                ),
                check_active=check_active,
            )
    if not selectors:
        selectors = [dict(projection=builder.identity.projection, start=0, end=0)]
    return selectors


def build_formal_layer(
    view: PreparedSourceView,
    prepared: PreparedRelease,
    operation: Mapping[str, Any],
    *,
    math_start: math_grammar.Kind = "any_value",
    parse_seconds: float = math_grammar.PARSE_SECONDS,
    max_forest_nodes: int = 20000,
    check_active: Callable[[], None] = lambda: None,
    source_scope: Mapping[str, Any] | None = None,
    max_inline_chars: int = 2048,
    macros: Mapping[str, MacroDef] | None = None,
) -> LayerReport:
    """Recognize privately, then validate one detached publishable source-bound layer.

    ``operation`` comes from the execution owner's immutable task determinants. This
    function never invents runtime/model/input identity and performs no native algebra.
    """
    required = {
        "key",
        "version",
        "runtime",
        "configuration",
        "input",
        "model",
        "grammar",
        "context",
    }
    if not required <= operation.keys() or any(not operation[key] for key in required):
        raise ValueError("formal producer requires authoritative operation determinants")
    if math_start not in math_grammar.STARTS or parse_seconds <= 0 or max_forest_nodes < 1:
        raise ValueError("invalid formal parser request")
    builder = _LayerBuilder(
        view,
        operation,
        FormalIdentity(
            canonical_bytes(view.ref.native_product.values()),
            view.ref.projection_digest,
            view.ref.id,
        ),
    )
    builder.macros = dict(macros or {})
    selected: list[dict[str, Any]]
    if source_scope is not None:
        expected = dict(
            source_view_id=view.ref.id,
            key=view.ref.key,
            base_document=view.ref.native_product.values(),
            section_pointer=view.ref.section_pointer,
            membership=view.ref.membership,
            projection_digest=view.ref.projection_digest,
            recipe_digest=view.ref.recipe_digest,
        )
        if source_scope["source_view_ids"] != [view.ref.id] or source_scope["source_views"] != [
            expected
        ]:
            raise ValueError(
                "formal source selection differs from the actual immutable source view"
            )
        selected = list(source_scope["selectors"])
        if any(selector["projection"] != view.ref.projection_digest for selector in selected):
            raise ValueError("formal selected source has a different projection")
    else:
        selected = [dict(projection=view.ref.projection_digest, start=0, end=len(view.text))]
    selectors = extract_formal_facts(
        builder,
        selected,
        math_start=math_start,
        parse_seconds=parse_seconds,
        max_forest_nodes=max_forest_nodes,
        max_inline_chars=max_inline_chars,
        check_active=check_active,
    )
    scope = dict(
        source_view_ids=[view.ref.id],
        source_views=[
            dict(
                source_view_id=view.ref.id,
                key=view.ref.key,
                base_document=view.ref.native_product.values(),
                section_pointer=view.ref.section_pointer,
                membership=view.ref.membership,
                projection_digest=view.ref.projection_digest,
                recipe_digest=view.ref.recipe_digest,
            )
        ],
        profile=PROFILE,
        selectors=selectors,
    )
    if source_scope is not None:
        scope = dict(source_scope)
        selectors = list(scope["selectors"])
    coverage = [
        dict(
            family=family,
            operation=operation["key"],
            eligible=selectors,
            examined=selectors,
            availability="available",
            outcome="partial"
            if builder.problems[family]
            else "complete"
            if builder.counts[family]
            else "empty",
            profile=PROFILE,
            **(
                {"reason": "; ".join(dict.fromkeys(builder.problems[family]))}
                if builder.problems[family]
                else {}
            ),
        )
        for family in FAMILIES
    ]
    partial = any(builder.problems.values())
    return validate_layer(
        prepared,
        dict(
            format="characterization-layer-v1",
            base_document=view.ref.native_product.values(),
            release_id=prepared.release_id,
            operation={
                **operation,
                "produced_families": list(FAMILIES),
                "outcomes": ["complete", "partial", "failed"],
                "result_determinants": sorted(required),
                "preconditions": [
                    (
                        "positioned-formal-v1 nomination: lexical numbers, comparison operators, "
                        "ISO dates, explicit labeled literals, conventional quantities "
                        "and intervals; "
                        "recognized formulas require attributable recognition"
                    )
                ],
                "effects": [
                    (
                        "immutable positioned formal syntax and packed symbolic structure; "
                        "no native symbolic evaluation"
                    )
                ],
            },
            source_scope=scope,
            outcome="partial" if partial else "complete",
            occurrences=list(builder.occurrences.values()),
            annotations=builder.annotations,
            memberships=builder.memberships,
            terms=list(builder.terms.values()),
            choices=list(builder.choices.values()),
            coverage=coverage,
        ),
    )
