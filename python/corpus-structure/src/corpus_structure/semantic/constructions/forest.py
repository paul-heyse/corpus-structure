"""Direct immutable, factorized SPPF reduction; no parse-tree conversion."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import copy
from dataclasses import dataclass
from functools import cache, lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any

from lark import Lark, UnexpectedInput
from lark.parser_frontends import ParsingFrontend
from lark.parsers.xearley import Parser as DynamicEarleyParser

from corpus_structure.semantic.file_custody import observed_file

from .declarations import DECLARATIONS, MODAL_FORCES, REVISION
from .lexical import LEXICAL, PositionedTerminal, ProtectedAtom, classify
from .nodes import Reference, identity
from .reuse import ReusingForestTransformer

_POSITIONED_NAMES = frozenset((*LEXICAL, "ATOM", "WS"))


def terminal_guard(start: int, end: int, atoms: tuple[ProtectedAtom, ...], *, atom: bool) -> None:
    intersecting = [a for a in atoms if start < a.end and a.start < end]
    if atom:
        if len(intersecting) != 1 or (start, end) != (intersecting[0].start, intersecting[0].end):
            raise ValueError("atom derivation is not one whole protected occurrence")
    elif intersecting:
        raise ValueError("prose terminal splits or crosses a protected occurrence")


@cache
def _grammar_resource(path: Path):
    return observed_file(path)


def prepared_parser(
    text: str,
    atoms: tuple[ProtectedAtom, ...],
    grammar: str | None = None,
    *,
    terminals: tuple[PositionedTerminal, ...] | None = None,
) -> Lark:
    resource = _grammar_resource(Path(__file__).with_name("grammars").joinpath("prose.lark"))
    resource.check()
    return _prepared_parser(text, atoms, grammar, resource.digest, terminals)


@dataclass(frozen=True, slots=True)
class _PositionedMatch:
    text: str
    endpoint: int

    def group(self, index: int = 0) -> str:
        if index != 0:
            raise IndexError("positioned terminal has only the whole match")
        return self.text

    def end(self) -> int:
        return self.endpoint


@dataclass(frozen=True, slots=True)
class _RegionMatcher:
    source: str
    values: Mapping[tuple[str, int], _PositionedMatch]
    native_match: Callable

    def match(self, term, text, index=0):
        if text is not self.source and text != self.source:
            raise ValueError("positioned parser belongs to a different source region")
        if term.name in _POSITIONED_NAMES:
            return self.values.get((term.name, index))
        # An authored grammar may contain ordinary native terminals in addition
        # to the positioned names. Their original matcher remains authoritative.
        return self.native_match(term, text, index)


@lru_cache(maxsize=64)
def _grammar_prototype(grammar: str | None, resource_digest: str) -> Lark:
    """Prepare grammar analysis once; no source text or region matcher is cached."""
    if grammar is None:
        imports = ", ".join(["clause", *LEXICAL, "ATOM"])
        grammar = f"%import .prose ({imports})\nstart: clause PUNCT?"
    # Dynamic Earley requires positive regexp width even though supplied matches
    # replace these terminals. The existing absent-terminal spelling has width 1.
    declarations = "\n".join(f"%override {name}: /(?!)x/" for name in (*LEXICAL, "ATOM"))
    parser = Lark(
        grammar + "\n" + declarations + "\nWS: /(?!)x/\n%ignore WS",
        import_paths=[str(Path(__file__).with_name("grammars"))],
        parser="earley",
        lexer="dynamic",
        ambiguity="forest",
        priority=None,
        ordered_sets=True,
        start=["start"],
        keep_all_tokens=True,
    )
    _grammar_resource(Path(__file__).with_name("grammars").joinpath("prose.lark")).check()
    return parser


def _prepared_parser(
    text: str,
    atoms: tuple[ProtectedAtom, ...],
    grammar: str | None,
    resource_digest: str,
    terminals: tuple[PositionedTerminal, ...] | None = None,
) -> Lark:
    previous = 0
    for atom in sorted(atoms, key=lambda a: a.start):
        if not previous <= atom.start < atom.end <= len(text):
            raise ValueError("protected atoms overlap or lie outside their source region")
        previous = atom.end
    values = classify(text, atoms) if terminals is None else terminals
    starts = {}
    for row in values:
        key = row.terminal, row.start
        if key in starts and starts[key] != row:
            raise ValueError(
                "same-terminal same-start alternatives exceed dynamic Earley lexical support"
            )
        starts[key] = row
        terminal_guard(row.start, row.end, atoms, atom=False)
        if (
            row.terminal not in {*LEXICAL, "WS"}
            or not 0 <= row.start < row.end <= len(text)
            or text[row.start : row.end] != row.text
        ):
            raise ValueError("retained lexical observation differs from exact original source")
    matches = {key: _PositionedMatch(row.text, row.end) for key, row in starts.items()}
    for atom in atoms:
        matches["ATOM", atom.start] = _PositionedMatch(text[atom.start : atom.end], atom.end)
    prototype = _grammar_prototype(grammar, resource_digest)
    frontend = prototype.parser
    if not isinstance(frontend, ParsingFrontend) or not isinstance(
        frontend.parser, DynamicEarleyParser
    ):
        raise RuntimeError(
            "prepared prose grammar requires its captured dynamic Earley implementation"
        )
    parser = copy(prototype)
    region_frontend = copy(frontend)
    scanner = copy(frontend.parser)
    # Lark 1.3.1 keeps its grammar analysis on the parser and parse state in local
    # columns/scanner buffers. Copy only the three owners along this binding path;
    # shared rules/configuration stay immutable and no parser holds another run's
    # text. Never mutate the cached scanner or serialize access through a lock.
    scanner.term_matcher = _RegionMatcher(
        text, MappingProxyType(matches), frontend.parser.term_matcher
    ).match
    region_frontend.parser = scanner
    parser.parser = region_frontend
    return parser


class PackedReducer(ReusingForestTransformer):
    """Native traversal with an explicit completed immutable result for every parent.

    Keep single_visit False: callbacks skip descent when a completed result exists,
    but the native out callback still delivers that result to the active parent.
    """

    def __init__(
        self,
        text: str,
        atoms: tuple[ProtectedAtom, ...],
        *,
        region: str = "region",
        offset: int = 0,
        check_active=lambda: None,
        max_nodes: int = 20000,
    ):
        super().__init__(check_active=check_active, max_nodes=max_nodes)
        self.text, self.atoms, self.region, self.offset = text, atoms, region, offset
        self.terms: dict[str, dict[str, Any]] = {}
        self.choices: dict[str, dict[str, Any]] = {}
        self.syntax: dict[str, dict[str, Any]] = {}
        self.positions: dict[str, tuple[int, int]] = {}
        self.uninterpreted: set[str] = set()
        self.sequences: dict[str, tuple[Reference, ...]] = {}

    def _term(
        self,
        value: str,
        kind: str,
        family: str,
        children: list[dict[str, Any]],
        start: int,
        end: int,
        *,
        status: str = "interpreted",
        premises=(),
        provenance=(),
    ) -> Reference:
        payload = dict(
            kind=kind,
            family=family,
            vocabulary=REVISION,
            value=value,
            status=status,
            children=children,
            premises=list(premises),
            **({"provenance": list(provenance)} if provenance else {}),
        )
        key = identity("term", [self.region, start, end, payload])
        self.positions[key] = (start + self.offset, end + self.offset)
        self.terms.setdefault(key, dict(local_id=key, **payload))
        return Reference(target=key)

    def _semantic_options(self, values, family, start, end, production):
        roots = [
            self._term(
                value,
                "participant",
                family,
                [],
                start,
                end,
                status="private_proposal",
                premises=[production],
            )
            for value in values
        ]
        if len(roots) == 1:
            return roots[0]
        key = identity("semantic-choice", [self.region, production, values, start, end])
        self.choices[key] = dict(
            local_id=key,
            family=family,
            compatibility="exclusive",
            members=[
                dict(local_id=identity("semantic-option", [key, root.target]), root=root.target)
                for root in roots
            ],
        )
        self.positions[key] = (start + self.offset, end + self.offset)
        return Reference(choice_group=key)

    def transform_token_node(self, node):
        token = node
        start, end = token.start_pos, token.end_pos
        terminal_guard(start, end, self.atoms, atom=token.type == "ATOM")
        annotation = identity("terminal", [self.region, token.type, start, end, str(token)])
        self.syntax.setdefault(
            annotation,
            dict(
                local_id=annotation,
                kind="grammar.terminal",
                native_label=token.type,
                start=start + self.offset,
                end=end + self.offset,
            ),
        )
        spelling = str(token)
        label = " ".join(spelling.split()) or " "
        return self._term(
            label,
            "participant",
            "construction.predication",
            [],
            start,
            end,
            premises=[annotation],
            provenance=(
                ["lexical-normalization:whitespace-folding-1"] if label != spelling else []
            ),
        )

    def transform_packed_node(self, node, data):
        alias = str(node.rule.alias or node.rule.origin.name)
        name = alias.removeprefix("prose__")
        declaration = DECLARATIONS.get(name)
        partial = node.parent.is_intermediate
        # LR prefixes remain explicit structural sequences. This retains correlations
        # when the prefix itself is ambiguous rather than multiplying alternatives.
        if partial:
            value, kind, family = "@sequence", "unknown", "construction.predication"
        elif declaration:
            value, kind, family = name, declaration.kind, declaration.family
            if kind == "binder":
                # A noun-phrase quantifier does not yet establish its sentential body.
                kind = "operator"
        else:
            value, kind, family = alias, "unknown", "construction.predication"
            if name not in {"start", "clause", "nominal", "predication"}:
                self.uninterpreted.add(alias)
        expanded = list(data)
        if expanded and expanded[0].target in self.sequences:
            expanded = [*self.sequences[expanded[0].target], *expanded[1:]]
        roles = []
        expansion = node.rule.expansion
        authored_roles = declaration.roles if declaration else ()
        if name in {"conditional", "quotation", "passive_predication"}:
            authored_roles = []
            counts = {}
            for symbol in expansion:
                label = str(symbol.name).removeprefix("prose__")
                counts[label] = counts.get(label, 0) + 1
                if name == "conditional":
                    role = {"IF": "cue", "COMMA": "punctuation", "THEN": "consequent_cue"}.get(
                        label, "antecedent" if counts[label] == 1 else "consequent"
                    )
                elif name == "quotation":
                    role = (
                        "open_quote"
                        if label == "QUOTE" and counts[label] == 1
                        else "close_quote"
                        if label == "QUOTE"
                        else "punctuation"
                        if label == "PUNCT"
                        else "content"
                    )
                else:
                    role = {
                        "COPULA": "auxiliary",
                        "AUX": "aspect",
                        "WORD": "predicate",
                        "PREP": "agent_cue",
                    }.get(label, "grammatical_subject" if counts[label] == 1 else "agent")
                authored_roles.append(role)
        pointer = node.parent.s[1] if partial else len(expansion)
        for index, child in enumerate(expanded):
            role = (
                "prefix"
                if len(expanded) < pointer and index == 0
                else (
                    authored_roles[pointer - len(expanded) + index]
                    if declaration and pointer - len(expanded) + index < len(authored_roles)
                    else f"part_{index}"
                )
            )
            roles.append(child.edge(role, index))
        child_positions = []
        for reference in expanded:
            position_key = reference.target or reference.choice_group
            if position_key is None:
                raise ValueError("forest child requires a term or analytical site")
            child_positions.append(self.positions[position_key])
        start = (
            min((p[0] for p in child_positions), default=node.parent.start + self.offset)
            - self.offset
        )
        end = (
            max((p[1] for p in child_positions), default=node.parent.end + self.offset)
            - self.offset
        )
        production = identity("production", [self.region, alias, str(node.rule), start, end, roles])
        self.syntax.setdefault(
            production,
            dict(
                local_id=production,
                kind="grammar.production",
                native_label=alias,
                start=start + self.offset,
                end=end + self.offset,
                premises=[r.target for r in expanded if r.target],
                rule_id=declaration.rule_id if declaration else None,
                complete=not partial,
            ),
        )
        if (
            name == "quantified_predication"
            and not partial
            and len(expanded) >= 3
            and all(r.target for r in expanded)
        ):
            variable = self._term(
                "bound-occurrence", "participant", family, [], start, start, status="implicit"
            )
            body = self._term(
                "verbal_predication",
                "predicate",
                family,
                [
                    expanded[2].edge("predicate"),
                    variable.edge("grammatical_subject"),
                    *([expanded[3].edge("grammatical_object")] if len(expanded) > 3 else []),
                ],
                start,
                end,
                premises=[production],
            )
            kind = "binder"
            roles = [
                variable.edge("variable"),
                expanded[1].edge("restrictor"),
                body.edge("body"),
                expanded[0].edge("cue"),
            ]
        if name == "relative" and not partial and expanded:
            gap = self._term(
                "relative-gap",
                "participant",
                family,
                [expanded[0].edge("antecedent")],
                start,
                start,
                status="implicit",
                premises=[production],
            )
            roles.append(gap.edge("gap"))
        if (
            name
            in {
                "negative_predication",
                "quantified_negative_predication",
                "negative_quantified_predication",
            }
            and not partial
            and all(r.target for r in expanded)
        ):
            quantified = name != "negative_predication"
            subject_index, predicate_index, neg_index = (1, 4, 3) if quantified else (0, 3, 2)
            subject = expanded[subject_index]
            variable = (
                self._term(
                    "bound-occurrence", "participant", family, [], start, start, status="implicit"
                )
                if quantified
                else subject
            )
            body = self._term(
                "verbal_predication",
                "predicate",
                family,
                [
                    expanded[predicate_index].edge("predicate"),
                    variable.edge("grammatical_subject"),
                    *(
                        [expanded[predicate_index + 1].edge("grammatical_object")]
                        if len(expanded) > predicate_index + 1
                        else []
                    ),
                ],
                start,
                end,
                premises=[production],
            )
            if quantified:
                negative = self._term(
                    "negation",
                    "operator",
                    family,
                    [expanded[neg_index].edge("cue"), body.edge("target")],
                    start,
                    end,
                    premises=[production],
                )
                binder = self._term(
                    "quantification",
                    "binder",
                    family,
                    [
                        variable.edge("variable"),
                        subject.edge("restrictor"),
                        (body if name == "negative_quantified_predication" else negative).edge(
                            "body"
                        ),
                        expanded[0].edge("cue"),
                    ],
                    start,
                    end,
                    premises=[production],
                )
                if name == "negative_quantified_predication":
                    roles, kind = (
                        [expanded[neg_index].edge("cue"), binder.edge("target")],
                        "operator",
                    )
                else:
                    roles, kind = (
                        [
                            variable.edge("variable"),
                            subject.edge("restrictor"),
                            negative.edge("body"),
                            expanded[0].edge("cue"),
                        ],
                        "binder",
                    )
            else:
                roles, kind = [expanded[neg_index].edge("cue"), body.edge("target")], "operator"
        if name == "clause_relation" and not partial:
            cue = next(
                (edge for edge in roles if edge["role"] == "cue" and edge.get("target")), None
            )
            if cue:
                wording = self.terms[cue["target"]]["value"].lower()
                relation = {
                    "because": "causal",
                    "although": "concessive",
                    "before": "temporal",
                    "after": "temporal",
                    "until": "temporal",
                    "while": "temporal",
                    "than": "comparative",
                    "except": "exception",
                    "without": "exception",
                }.get(wording)
                if relation:
                    a, b = self.positions[cue["target"]]
                    proposal = self._term(
                        relation,
                        "participant",
                        family,
                        [],
                        a - self.offset,
                        b - self.offset,
                        premises=[production],
                    )
                    roles.append(proposal.edge("relation_type"))
        if name == "passive_predication" and not partial:
            passive = self._term(
                "voice:passive", "participant", family, [], start, end, premises=[production]
            )
            roles.append(passive.edge("voice"))
        if name == "coordination" and not partial and expanded and expanded[-1].target:
            right = self.terms[expanded[-1].target]
            if right["value"] == "nominal_predication":
                gap = self._term(
                    "unresolved-ellipsis",
                    "predicate",
                    family,
                    [],
                    end,
                    end,
                    status="unknown",
                    premises=[production],
                )
                roles.append(gap.edge("ellipsis_gap"))
        if (
            name in {"coordination", "nominal_coordination"}
            and not partial
            and len(expanded) == 3
            and expanded[1].target
        ):
            cue = self.terms[expanded[1].target]["value"].lower()
            connective = self._term(
                cue,
                "operator",
                family,
                [expanded[0].edge("left"), expanded[2].edge("right"), expanded[1].edge("cue")],
                start,
                end,
                premises=[production],
            )
            roles.append(connective.edge("semantic_connective"))
            if name == "nominal_coordination":
                distribution = self._semantic_options(
                    ("collective", "distributive"), family, start, end, production
                )
                roles.append(distribution.edge("distribution"))
        if name == "modal_predication" and not partial and len(expanded) >= 3:
            body = self._term(
                "verbal_predication",
                "predicate",
                family,
                [
                    expanded[0].edge("grammatical_subject"),
                    expanded[2].edge("predicate"),
                    *([expanded[3].edge("grammatical_object")] if len(expanded) > 3 else []),
                ],
                start,
                end,
                premises=[production],
            )
            roles = [expanded[1].edge("cue"), body.edge("target")]
        if (
            name in {"modality", "modal_predication"}
            and not partial
            and expanded
            and expanded[1 if name == "modal_predication" else 0].target
        ):
            cue_ref = expanded[1 if name == "modal_predication" else 0]
            cue_target = cue_ref.target
            assert cue_target is not None
            cue = self.terms[cue_target]["value"].lower()
            if cue in MODAL_FORCES:
                a, b = self.positions[cue_target]
                force = self._semantic_options(
                    MODAL_FORCES[cue], family, a - self.offset, b - self.offset, production
                )
                roles.append(force.edge("force"))
            if name == "modal_predication":
                modal = self._term(
                    "modality", "operator", family, roles, start, end, premises=[production]
                )
                roles = [modal.edge("meaning")]
        result = self._term(
            value,
            kind,
            family,
            roles,
            start,
            end,
            status="unknown" if kind == "unknown" else "interpreted",
            premises=[production],
        )
        if partial and result.target:
            self.sequences[result.target] = tuple(expanded)
        return result

    def _symbol(self, node, data):
        unique = tuple(dict.fromkeys(data))
        if len(unique) == 1:
            return unique[0]
        key = identity(
            "choice",
            [self.region, node.start, node.end, [(r.target, r.choice_group) for r in unique]],
        )
        if any(not r.target for r in unique):
            raise ValueError("packed production must produce a term root")
        self.choices.setdefault(
            key,
            dict(
                local_id=key,
                compatibility="exclusive",
                family="construction.predication",
                members=[
                    dict(local_id=identity("alternative", [key, r.target]), root=r.target)
                    for r in unique
                ],
            ),
        )
        positions = [self.positions[r.target] for r in unique]
        self.positions[key] = (min(p[0] for p in positions), max(p[1] for p in positions))
        return Reference(choice_group=key)

    transform_symbol_node = _symbol
    transform_intermediate_node = _symbol


@dataclass(frozen=True)
class Recognition:
    outcome: str
    root: Reference | None
    reducer: PackedReducer | None
    reason: str | None = None


def recognize(
    text: str,
    atoms: tuple[ProtectedAtom, ...] = (),
    *,
    region: str = "region",
    offset: int = 0,
    terminals: tuple[PositionedTerminal, ...] | None = None,
    max_chars: int = 4096,
    parse_seconds: float = 2.0,
    check_active=lambda: None,
) -> Recognition:
    check_active()
    if len(text) > max_chars:
        return Recognition(
            "unsupported", None, None, "source region exceeds declared grammar character bound"
        )
    from corpus_structure.methods.math.grammar import Expired, OffMainThread, deadline

    reducer = None
    try:
        with deadline(parse_seconds):
            forest = prepared_parser(text, atoms, terminals=terminals).parse(text)
            check_active()
            reducer = PackedReducer(
                text, atoms, region=region, offset=offset, check_active=check_active
            )
            root = reducer.transform(forest)
    except UnexpectedInput:
        return Recognition("empty", None, None)
    except Expired:
        check_active()
        return Recognition(
            "partial",
            None,
            reducer,
            "source grammar deadline expired during preparation/recognition/reduction",
        )
    except OffMainThread:
        return Recognition(
            "unsupported",
            None,
            None,
            "source grammar deadline requires the managed worker process main thread",
        )
    except ValueError as error:
        check_active()
        return Recognition("partial", None, reducer, str(error))
    return Recognition(
        "partial" if reducer.uninterpreted else "complete",
        root,
        reducer,
        "unhandled grammar productions retained" if reducer.uninterpreted else None,
    )
