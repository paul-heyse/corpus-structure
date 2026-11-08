"""Predicate and scope proposals over the unchanged retained English annotation."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import lru_cache
from importlib.resources import files
from typing import Any, Literal

from spacy.lang.en import English
from spacy.matcher import DependencyMatcher, Matcher, PhraseMatcher
from spacy.tokens import Doc, Token
from spacy.vocab import Vocab

from corpus_structure.ingest.annotation_views import AnnotationView, annotation_view
from corpus_structure.ingest.annotations import AnnotationProduct, AnnotationUnavailable

PREDICATE_FRAME_VERSION = "2"
type RoleSpan = tuple[int, int]
type FrameLayout = Literal["prose", "example", "policy", "instruction"]


@lru_cache(maxsize=1)
def interpretation_recipe():
    return json.loads(files(__package__).joinpath("predicate_interpretation.json").read_text())


def source_layout(
    product: AnnotationProduct,
    text: str,
    pieces: Sequence[Mapping[str, Any]],
    items: Mapping[str, Mapping[str, Any]],
) -> FrameLayout:
    """Use only the preceding native heading in the same local structural group."""
    item = next(
        (
            items[piece["item_ref"]]
            for piece in pieces
            if piece.get("item_ref") in items
            and piece["start"] <= product.block_start < piece["end"]
        ),
        {},
    )
    parent = item.get("parent")
    for piece in reversed(pieces):
        if piece["end"] > product.block_start:
            continue
        pointer = piece.get("item_ref")
        candidate = items.get(pointer, {}) if isinstance(pointer, str) else {}
        if candidate.get("parent") != parent or candidate.get("label") not in {
            "title",
            "section_header",
        }:
            continue
        heading = text[piece["start"] : piece["end"]].strip().lower()
        first = heading.split(maxsplit=1)[0].strip(":") if heading else ""
        headings = interpretation_recipe()["layout_headings"]
        for layout in ("example", "policy", "instruction"):
            if first in headings[layout]:
                return layout
        break
    return "prose"


_SUBJECT = tuple(interpretation_recipe()["subject_dependencies"])
_PATIENT = tuple(interpretation_recipe()["patient_dependencies"])
_OBJECT = tuple(interpretation_recipe()["object_dependencies"])
_COMPLEMENT = tuple(interpretation_recipe()["complement_dependencies"])
_AUX = frozenset(interpretation_recipe()["auxiliary_dependencies"])
_CLAUSE = frozenset(interpretation_recipe()["subordinate_dependencies"])
_NOMINAL_EDGE = frozenset(interpretation_recipe()["nominal_dependencies"])
_NOMINAL_PREP = frozenset(interpretation_recipe()["nominal_prepositions"])
_NOMINAL_POS = frozenset(interpretation_recipe()["nominal_positions"])
_REPORT = frozenset(interpretation_recipe()["report_lemmas"])
_ASSUMPTION = frozenset(interpretation_recipe()["assumption_lemmas"])
_ASSUMPTION_WORDS = frozenset(
    f"{lemma[:-1]}{ending}" for lemma in _ASSUMPTION for ending in ("e", "es", "ed", "ing")
)
_NAMING = frozenset(interpretation_recipe()["naming_lemmas"])
_NAMING_COMPLEMENT = frozenset(interpretation_recipe()["naming_complement_required"])
_NAMING_REFERENCE = frozenset(interpretation_recipe()["naming_reference_only"])
_PRESCRIPTIVE_MODALS = frozenset(interpretation_recipe()["prescriptive_modals"])
_CONDITION = frozenset({"if", "when", "provided", "provided that", "as long as"})
_EXCEPTION = frozenset({"unless", "except", "except for"})
_ORDER = frozenset({"before", "after"})
_ALTERNATIVE = frozenset({"or", "nor"})
_REQUIRED = ("DEP", "POS", "SENT_START")


@dataclass(frozen=True, slots=True)
class LocatedFrameSpan:
    tokens: tuple[int, ...]
    extents: tuple[RoleSpan, ...]


@dataclass(frozen=True, slots=True)
class FrameRole:
    name: str
    head: int
    span: LocatedFrameSpan
    status: Literal["located", "partial", "unresolved"]
    inherited_from: int | None = None


@dataclass(frozen=True, slots=True)
class FrameCue:
    block_id: str
    dependency: str
    kind: str
    variant: str
    span: LocatedFrameSpan
    basis: LocatedFrameSpan
    status: Literal["located", "unresolved"]
    hosts: tuple[int, ...]
    origin: int | None
    component: int | None = None


@dataclass(frozen=True, slots=True)
class PredicateFrame:
    block_id: str
    dependency: str
    sentence: int
    predicate: LocatedFrameSpan
    focus: LocatedFrameSpan
    reading: str
    variant: str
    roles: tuple[FrameRole, ...]
    cues: tuple[FrameCue, ...]
    voice: Literal["active", "passive", "copular", "unresolved"]
    polarity: Literal["positive", "negative", "negative_scope_unresolved", "unresolved"]
    interpretation: str


@dataclass(frozen=True, slots=True)
class FrameIssue:
    block_id: str
    dependency: str
    status: Literal["unavailable", "unsupported_alignment"]
    reason: str


@dataclass(frozen=True, slots=True)
class PredicateFrameResult:
    frames: tuple[PredicateFrame, ...]
    issues: tuple[FrameIssue, ...]
    unresolved_cues: tuple[FrameCue, ...] = ()


@lru_cache(maxsize=4)
def _prepared(vocab: Vocab) -> tuple[DependencyMatcher, Matcher, PhraseMatcher]:
    """Compile the bounded named dependency and lexical variants together."""
    direct = DependencyMatcher(vocab, validate=True)
    for variant, dependencies in {
        "active_subject": _SUBJECT,
        "passive_patient": _PATIENT,
        "direct_object": _OBJECT,
        "predicative_complement": _COMPLEMENT,
        "passive_agent": ("agent", "obl:agent"),
        "passive_auxiliary": ("auxpass", "aux:pass"),
        "copular_complement_head": ("cop",),
        "reported_assumption": ("ccomp",),
        "subordinate": ("advcl",),
        "subordinate_marker": ("mark",),
    }.items():
        # spaCy's default English and UD dependency labels differ for some
        # direct arguments. Preserve the named head and member in both cases.
        governor = (
            {"LOWER": {"IN": sorted(_ASSUMPTION_WORDS)}} if variant == "reported_assumption" else {}
        )
        direct.add(
            variant,
            [
                [
                    {"RIGHT_ID": "predicate", "RIGHT_ATTRS": governor},
                    {
                        "LEFT_ID": "predicate",
                        "REL_OP": ">",
                        "RIGHT_ID": "member",
                        "RIGHT_ATTRS": {"DEP": {"IN": list(dependencies)}},
                    },
                ]
            ],
        )
    token = Matcher(vocab, validate=True)
    token.add("modal", [[{"TAG": "MD"}]])
    token.add("negation", [[{"DEP": "neg"}]])
    token.add("marker", [[{"LOWER": {"IN": sorted(_CONDITION | _EXCEPTION | _ORDER)}}]])
    token.add(
        "probability_comparison",
        [
            [
                {"LOWER": "probability"},
                {"LOWER": "that"},
                {"IS_ALPHA": True},
                {"LOWER": {"IN": ["is", "was"]}},
                {"LOWER": {"IN": ["less", "greater"]}},
                {"LOWER": "than"},
                {"IS_ALPHA": True},
            ]
        ],
    )
    phrase = PhraseMatcher(vocab, attr="LOWER", validate=True)
    for words in (
        ("instead", "of"),
        ("for", "example"),
        ("according", "to"),
        ("except", "for"),
        ("provided", "that"),
        ("as", "long", "as"),
    ):
        phrase.add(" ".join(words), [Doc(vocab, words=list(words))])
    return direct, token, phrase


@lru_cache(maxsize=1)
def _frame_vocabulary() -> Vocab:
    return English().vocab


def _available(product: AnnotationProduct) -> set[str]:
    return {column.attribute for column in product.availability if column.status == "complete"}


def predicate_frames(
    text: str, annotations: Iterable[AnnotationProduct], *, layout: FrameLayout = "prose"
) -> PredicateFrameResult:
    """Reconstruct the selected original blocks, with diagnostics per retained block."""
    frames, issues, unresolved = [], [], []
    for product in annotations:
        missing = sorted(set(_REQUIRED) - _available(product))
        if missing:
            issues.append(
                FrameIssue(
                    product.block_id,
                    product.dependency_digest,
                    "unavailable",
                    "required retained columns: " + ", ".join(missing),
                )
            )
            continue
        try:
            if not 0 <= product.block_start < product.block_end <= len(text):
                raise ValueError("annotation block is outside the selected source projection")
            view = annotation_view(
                product,
                text[product.block_start : product.block_end],
                _frame_vocabulary(),
                required=_REQUIRED,
            )
            result = predicate_frame_result(view, layout=layout)
            frames.extend(result.frames)
            issues.extend(result.issues)
            unresolved.extend(result.unresolved_cues)
        except (AnnotationUnavailable, ValueError) as error:
            issues.append(
                FrameIssue(
                    product.block_id, product.dependency_digest, "unsupported_alignment", str(error)
                )
            )
            continue
    return PredicateFrameResult(tuple(frames), tuple(issues), tuple(unresolved))


def frames_from_annotation(
    view: AnnotationView, *, layout: FrameLayout = "prose"
) -> tuple[PredicateFrame, ...]:
    """Use the same cue owner when a named consumer already has a reconstructed block."""
    return predicate_frame_result(view, layout=layout).frames


def predicate_frame_result(
    view: AnnotationView, *, layout: FrameLayout = "prose"
) -> PredicateFrameResult:
    """Include unresolved cue evidence and unavailable columns for a native view."""
    product = view.product
    columns = _available(product)
    missing = sorted(set(_REQUIRED) - columns)
    if missing:
        issue = FrameIssue(
            product.block_id,
            product.dependency_digest,
            "unavailable",
            "required retained columns: " + ", ".join(missing),
        )
        return PredicateFrameResult((), (issue,))
    block = _FrameBlock(view, layout)
    frames = block.frames()
    missing = sorted({"LEMMA", "MORPH", "TAG"} - columns)
    issues = (
        (
            FrameIssue(
                product.block_id,
                product.dependency_digest,
                "unavailable",
                "optional retained columns: " + ", ".join(missing),
            ),
        )
        if missing
        else ()
    )
    return PredicateFrameResult(frames, issues, tuple(block.unowned))


class _FrameBlock:
    def __init__(self, view: AnnotationView, layout: FrameLayout):
        self.doc = view.doc
        self.product = view.product
        self.layout = layout
        self.direct: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
        self.lexical: dict[str, list[tuple[int, ...]]] = defaultdict(list)
        view.check_layout()
        direct, token, phrase = _prepared(self.doc.vocab)
        strings = self.doc.vocab.strings
        for label, (predicate, member) in direct(self.doc):
            if self.same_sentence(predicate, member):
                self.direct[strings[label]][predicate].append(member)
        for label, start, end in (*token(self.doc, allow_missing=True), *phrase(self.doc)):
            nodes = tuple(range(start, end))
            variant = strings[label]
            if (variant != "modal" or "TAG" in _available(self.product)) and self.same_sentence(
                *nodes
            ):
                self.lexical[variant].append(nodes)

        try:
            self.noun_chunks = {
                chunk.root.i: set(range(chunk.start, chunk.end)) for chunk in self.doc.noun_chunks
            }
        except NotImplementedError:
            self.noun_chunks = {}
        self.copular = self.direct["copular_complement_head"]
        self.predicates = {
            token.i for token in self.doc if self.eligible(token) and self.is_predicate(token)
        }
        self.probability: dict[int, tuple[int, ...]] = {}
        self.recover_probability_subject()
        self.pos_ambiguous = self.ambiguous_coordinates()
        self.predicates.update(self.pos_ambiguous)
        self.quotes = self.quoted_tokens()
        self.clause_intro = {
            token.i
            for token in self.doc
            if token.dep_ == "prep"
            and any(
                child.i in self.predicates and child.dep_ == "pcomp" for child in token.children
            )
        }
        self.cues: dict[int, list[FrameCue]] = defaultdict(list)
        self.unowned: list[FrameCue] = []

    def same_sentence(self, first: int, *indices: int) -> bool:
        sentence = self.product.tokens[first].sentence
        return sentence is not None and all(
            self.product.tokens[i].sentence == sentence for i in indices
        )

    def eligible(self, token: Token) -> bool:
        row = self.product.tokens[token.i]
        return row.role == "prose" and row.sentence is not None and token.dep_ not in _AUX

    def is_predicate(self, token: Token) -> bool:
        if token.i in self.copular:
            return True
        if token.pos_ == "AUX":
            return self.lemma(token) == "be" or token.lower_ in {
                "am",
                "is",
                "are",
                "was",
                "were",
                "been",
                "being",
            }
        if token.pos_ == "VERB":
            return token.dep_ not in _NOMINAL_EDGE | {"prep", "agent", "compound", "punct"}
        # A subordinate with a marker and its own subject can be a clause even if
        # the parser labelled its inflected head as nominal.
        return (
            token.dep_ == "advcl"
            and token.i in self.direct["subordinate_marker"]
            and token.i in self.direct["active_subject"]
        )

    @staticmethod
    def lemma(token: Token) -> str:
        return token.lemma_.casefold() or token.lower_

    def span(self, indices: Iterable[int]) -> LocatedFrameSpan:
        tokens = tuple(sorted({i for i in indices if not self.doc[i].is_space}))
        extents: list[RoleSpan] = []
        previous = None
        for index in tokens:
            row = self.product.tokens[index]
            # Coalesce source whitespace only across adjacent retained tokens in
            # the same native piece. An intervening unselected token splits a run.
            if (
                previous is not None
                and row.piece_indices == self.product.tokens[previous].piece_indices
                and len(row.piece_indices) == 1
                and all(self.doc[i].is_space for i in range(previous + 1, index))
            ):
                extents[-1] = (extents[-1][0], row.end)
            else:
                extents.append((row.start, row.end))
            previous = index
        return LocatedFrameSpan(tokens, tuple(extents))

    def recover_probability_subject(self) -> None:
        # The bounded "probability that X is less/greater than Y" construction can
        # remain recognizable when a retained analysis misattaches Y as the passive
        # subject of "is given". Both direct clause evidence and the exact local
        # token pattern are required to replace that particular argument proposal.
        for nodes in self.lexical["probability_comparison"]:
            head, marker, subject, copula, comparison, _than, endpoint = nodes
            nominal = self.doc[head]
            if (
                self.doc[marker].head.i != copula
                or self.doc[subject].head.i != copula
                or self.doc[copula].head.i != head
                or self.doc[comparison].head.i != copula
            ):
                continue
            nominal_nodes = {
                i
                for i in self.noun_chunks.get(head, {head})
                if i <= head and self.doc[i].dep_ != "advmod"
            }
            subject_nodes = tuple(sorted(nominal_nodes | set(nodes)))
            self.probability[head] = subject_nodes
            if endpoint + 2 >= len(self.doc) or nominal.dep_ not in {"ROOT", "appos"}:
                continue
            auxiliary, given = self.doc[endpoint + 1], self.doc[endpoint + 2]
            if (
                self.same_sentence(head, given.i)
                and given.i in self.predicates
                and given.lower_ == "given"
                and auxiliary.i in self.direct["passive_auxiliary"][given.i]
                and endpoint in self.direct["passive_patient"][given.i]
                and given.head.i == comparison
            ):
                self.direct["passive_patient"][given.i] = [head]

    def ambiguous_coordinates(self) -> set[int]:
        negated = {self.doc[i].head.i for (i,) in self.lexical["negation"]}
        return {
            token.i
            for token in self.doc
            if token.dep_ == "conj"
            and token.head.i in negated & self.predicates
            and token.pos_ == "NOUN"
            and token.tag_ == "NN"
            and not any(not child.is_punct for child in token.children)
            and not self.direct["active_subject"][token.head.i]
            and any(child.lower_ == "do" and child.dep_ == "aux" for child in token.head.children)
            and self.connector(token.head.i, token.i) == "and"
        }

    def quoted_tokens(self) -> set[int]:
        result = set()
        closing = {
            '"': '"',
            "“": "”",
            "\N{LEFT SINGLE QUOTATION MARK}": "\N{RIGHT SINGLE QUOTATION MARK}",
        }
        stack = []
        for token in self.doc:
            if stack and token.text == stack[-1][1]:
                opening, _ = stack.pop()
                if self.same_sentence(opening, token.i):
                    result.update(range(opening, token.i + 1))
            elif token.text in closing:
                stack.append((token.i, closing[token.text]))
        return result

    def nominal(self, head: int) -> tuple[set[int], bool]:
        if head in self.probability:
            return set(self.probability[head]), False
        selected = set()
        pending = [(head, 0)]
        partial = False
        while pending:
            index, depth = pending.pop()
            if index in selected:
                continue
            selected.add(index)
            if len(selected) > 64:
                return {head}, True
            for child in self.doc[index].children:
                if not self.same_sentence(head, child.i):
                    partial = True
                    continue
                dep = child.dep_
                if dep in _NOMINAL_EDGE or (
                    dep in {"pobj", "obj"} and self.doc[index].dep_ == "prep"
                ):
                    pending.append((child.i, depth))
                elif dep == "prep" and child.lower_ in _NOMINAL_PREP and depth < 3:
                    pending.append((child.i, depth + 1))
                elif dep in _CLAUSE or dep == "prep":
                    partial = True
        chunk = self.noun_chunks.get(head, {head})
        selected.update(
            i
            for i in chunk
            if self.same_sentence(head, i)
            and not self.doc[i].is_punct
            and self.doc[i].dep_ in _NOMINAL_EDGE
        )
        return selected, partial

    def role(self, name: str, head: int) -> FrameRole:
        if self.doc[head].dep_ in {"csubj", "csubjpass", "csubj:pass"}:
            return FrameRole(name, head, self.focus(head), "located")
        nodes, partial = self.nominal(head)
        span = self.span(nodes)
        return FrameRole(name, head, span, "partial" if partial else "located")

    def voice(self, predicate: int) -> Literal["active", "passive", "copular", "unresolved"]:
        if predicate in self.pos_ambiguous:
            return "unresolved"
        if predicate in self.copular or self.doc[predicate].pos_ == "AUX":
            return "copular"
        if self.has_local_passive(predicate):
            return "passive"
        token = self.doc[predicate]
        if (
            token.tag_ == "VBN"
            and self.has_local_passive(token.head.i)
            and self.shared_coordinate(token.head.i, predicate)
        ):
            return "passive"
        return "active"

    def has_local_passive(self, predicate: int) -> bool:
        return bool(
            self.direct["passive_patient"][predicate] or self.direct["passive_auxiliary"][predicate]
        )

    def own_roles(self, predicate: int) -> tuple[FrameRole, ...]:
        voice = self.voice(predicate)
        subjects = self.direct["active_subject"][predicate]
        objects = self.direct["direct_object"][predicate]
        complements = self.direct["predicative_complement"][predicate]
        if voice == "passive":
            agents = self.direct["passive_agent"][predicate]
            subjects = [
                child.i
                for i in agents
                for child in self.doc[i].children
                if child.dep_ in {"pobj", "obj"} and self.same_sentence(predicate, child.i)
            ] + [i for i in agents if self.doc[i].dep_ == "obl:agent"]
            objects = [*self.direct["passive_patient"][predicate], *objects]
        if predicate in self.copular:
            complements = [*complements, predicate]
        if self.lemma(self.doc[predicate]) in _NAMING:
            complements = [
                *complements,
                *(
                    member.i
                    for child in self.doc[predicate].children
                    if child.dep_ == "prep" and child.lower_ in {"as", "to"}
                    for member in child.children
                    if member.dep_ in {"pobj", "obj"} and self.same_sentence(predicate, member.i)
                ),
            ]
        return tuple(
            self.role(name, index)
            for name, indices in (
                ("subject" if voice == "copular" else "actor", subjects),
                ("object", objects),
                ("complement", complements),
            )
            for index in sorted(
                set(indices)
                | {
                    peer.i
                    for index in indices
                    for peer in self.doc[index].conjuncts
                    if peer.pos_ in _NOMINAL_POS
                    and self.same_sentence(predicate, peer.i)
                    and peer.i not in self.predicates
                }
            )
        )

    def connector(self, first: int, second: int) -> str | None:
        start, end = sorted((first, second))
        words = {
            token.lower_
            for token in self.doc[start + 1 : end]
            if token.dep_ == "cc" and token.head.i in {first, second}
        }
        return next(iter(words)) if len(words) == 1 else None

    def coordinate_group(self, predicate: int) -> tuple[int, ...]:
        return tuple(
            sorted(
                {predicate}
                | {
                    t.i
                    for t in self.doc[predicate].conjuncts
                    if t.i in self.predicates and self.same_sentence(predicate, t.i)
                }
            )
        )

    def shared_coordinate(self, governor: int, peer: int) -> bool:
        return (
            self.doc[peer].dep_ == "conj"
            and self.doc[peer].head.i == governor
            and self.connector(governor, peer) == "and"
            and not self.direct["active_subject"][peer]
            and not self.direct["passive_patient"][peer]
            and not any(child.dep_ in _AUX for child in self.doc[peer].children)
        )

    def focus(self, predicate: int, roles: tuple[FrameRole, ...] = ()) -> LocatedFrameSpan:
        selected = set()
        pending = [predicate]
        while pending:
            index = pending.pop()
            if index in selected:
                continue
            selected.add(index)
            for child in self.doc[index].children:
                if (
                    self.same_sentence(predicate, child.i)
                    and child.i not in self.predicates
                    and child.i not in self.clause_intro
                    and child.dep_ not in _CLAUSE | {"conj", "cc"}
                    and (not child.is_punct or child.i in self.quotes)
                    and not (child.dep_ == "prep" and child.lower_ in _EXCEPTION)
                ):
                    pending.append(child.i)
        selected.update(
            index for role in roles if role.inherited_from is None for index in role.span.tokens
        )
        return self.span(selected)

    def add_cue(
        self, kind, variant, span, basis, hosts, *, origin=None, component=None, unresolved=False
    ) -> None:
        cue = FrameCue(
            self.product.block_id,
            self.product.dependency_digest,
            kind,
            variant,
            span,
            basis,
            "unresolved" if unresolved else "located",
            hosts,
            origin,
            component,
        )
        if not hosts:
            self.unowned.append(cue)
        for host in hosts:
            self.cues[host].append(cue)

    def local_predicate(self, token: int) -> int | None:
        if token in self.predicates:
            return token
        head = self.doc[token].head.i
        return head if head in self.predicates and self.same_sentence(head, token) else None

    def compound_condition(self, marker: int, subordinate: int, origin: int):
        """Recognize a provisional host that lies inside an explicit antecedent."""
        premise = self.doc[origin]
        main = premise.head
        if (
            premise.dep_ != "ccomp"
            or main.i <= origin
            or main.i not in self.predicates
            or not self.same_sentence(marker, subordinate, origin, main.i)
            or not any(
                token.lower_ == "and" and token.dep_ == "cc"
                for token in self.doc[subordinate + 1 : origin]
            )
        ):
            return None
        boundaries = [
            token.i
            for token in main.children
            if origin < token.i < main.i
            and token.lower_ == "then"
            and token.dep_ == "advmod"
            and self.doc[token.i - 1].text == ","
            and token.i not in self.quotes
        ]
        if len(boundaries) != 1:
            return None
        return self.span(range(marker, boundaries[0] - 1)), (origin, main.i)

    def clause_cues(self) -> None:
        fronted = []
        phrases = (
            (variant, nodes)
            for variant in _CONDITION | _EXCEPTION
            if " " in variant
            for nodes in self.lexical[variant]
        )
        matches = {nodes[0]: (variant, nodes) for variant, nodes in phrases}
        for (index,) in self.lexical["marker"]:
            matches.setdefault(index, (self.doc[index].lower_, (index,)))
        # Single-token Matcher and PhraseMatcher evidence can overlap. Prefer the
        # full marker when a separately located token also belongs to that phrase.
        inside = {index for _, nodes in matches.values() for index in nodes[1:]}
        for index, (variant, nodes) in sorted(matches.items()):
            if index in inside or any(i in self.quotes for i in nodes):
                continue
            token = self.doc[index]
            basis = self.span(nodes)
            kind = (
                "condition"
                if variant in _CONDITION
                else "exception"
                if variant in _EXCEPTION
                else "order"
            )
            component = origin = None
            if token.dep_ == "mark" and index in self.direct["subordinate_marker"][token.head.i]:
                candidate = token.head
                if candidate.i in self.direct["subordinate"][candidate.head.i]:
                    component = candidate.i
                    if candidate.head.i in self.predicates:
                        origin = candidate.head.i
                elif candidate.i in self.predicates:
                    origin = candidate.i
            elif token.dep_ in {"prep", "advmod"}:
                dependents = [
                    child.i
                    for child in token.children
                    if child.dep_ in {"pcomp", "advcl"}
                    and child.i in self.predicates
                    and self.same_sentence(index, child.i)
                ]
                if len(dependents) == 1:
                    component = dependents[0]
                    if token.head.i in self.predicates:
                        origin = token.head.i
            if component is not None:
                compound = (
                    self.compound_condition(index, component, origin)
                    if variant == "if" and origin is not None
                    else None
                )
                if compound is not None:
                    span, candidates = compound
                    self.add_cue(
                        kind,
                        "compound_if_then",
                        span,
                        basis,
                        candidates,
                        origin=origin,
                        component=component,
                        unresolved=True,
                    )
                    continue
                span = self.span({*self.focus(component).tokens, *nodes})
                hosts = () if origin is None else (origin,)
                unresolved = origin is None or component not in self.predicates
                self.add_cue(
                    kind,
                    variant,
                    span,
                    basis,
                    hosts,
                    origin=origin,
                    component=component,
                    unresolved=unresolved,
                )
                if (
                    origin is not None
                    and not unresolved
                    and kind == "condition"
                    and max(span.tokens) < origin
                ):
                    fronted.append((origin, self.cues[origin][-1]))
            elif kind == "exception" and variant in {"except", "except for"}:
                self.nominal_exception(token, variant, basis)
            elif token.dep_ in {"mark", "prep"}:
                self.add_cue(kind, variant, basis, basis, (), origin=origin, unresolved=True)

        # An explicit local condition or exception blocks inheritance into
        # that conjunct even when the fronted marker is attached to its peer.
        local = {
            host
            for host, cues in self.cues.items()
            if any(cue.kind in {"condition", "exception"} for cue in cues)
        }
        for origin, cue in fronted:
            inherited = tuple(
                peer
                for peer in self.coordinate_group(origin)
                if peer not in local and self.shared_coordinate(origin, peer)
            )
            if inherited:
                shared = replace(cue, hosts=tuple(sorted((origin, *inherited))))
                self.cues[origin][self.cues[origin].index(cue)] = shared
                for peer in inherited:
                    self.cues[peer].append(shared)

    def nominal_exception(self, token: Token, variant: str, basis: LocatedFrameSpan) -> None:
        argument = {
            child.i
            for child in token.children
            if child.dep_ in {"pobj", "obj", "obl", "prep"} and self.same_sentence(token.i, child.i)
        }
        argument.update(basis.tokens)
        last = max(basis.tokens)
        boundary = next(
            (
                item.i
                for item in self.doc[last + 1 :]
                if not self.same_sentence(token.i, item.i) or item.is_punct
            ),
            len(self.doc),
        )
        selected = {
            i for head in argument for i in self.nominal(head)[0] if token.i <= i < boundary
        }
        span = self.span(selected)
        if token.dep_ != "prep" or token.head.i not in self.predicates:
            # A nominal exception may belong to an argument under a predicate.
            # Preserve that origin when located, while the exact relationship
            # host remains unresolved.
            origin = self.local_predicate(token.head.i) if token.dep_ == "prep" else None
            self.add_cue(
                "exception",
                "nominal_" + variant,
                span,
                basis,
                (),
                origin=origin,
                unresolved=True,
            )
            return
        origin = token.head.i
        self.add_cue(
            "exception",
            "nominal_" + variant,
            span,
            basis,
            (origin,),
            origin=origin,
            unresolved=set(span.tokens) == set(basis.tokens),
        )

    def discourse_cues(self, roles: dict[int, tuple[FrameRole, ...]]) -> None:
        for nodes in self.lexical["instead of"]:
            preposition = self.doc[nodes[-1]]
            for child in preposition.children:
                if (
                    child.dep_ == "pcomp"
                    and child.i in self.predicates
                    and self.same_sentence(*nodes, child.i)
                ):
                    self.add_cue(
                        "contrast",
                        "instead_of",
                        self.focus(child.i, roles[child.i]),
                        self.span(nodes),
                        (child.i,),
                        origin=self.local_predicate(preposition.head.i),
                        component=child.i,
                    )
        for phrase, kind in (("for example", "example"), ("according to", "attribution")):
            for nodes in self.lexical[phrase]:
                following = nodes[-1] + 1
                if kind == "example" and following < len(self.doc):
                    number = self.doc[following]
                    if (
                        number.pos_ == "NUM"
                        and number.dep_ == "nummod"
                        and number.head.i == nodes[-1]
                        and self.same_sentence(*nodes, following)
                    ):
                        continue
                first = self.doc[nodes[0]]
                origin = self.local_predicate(first.head.i) if first.dep_ == "prep" else None
                if origin is None or not self.same_sentence(origin, *nodes):
                    continue
                span = self.span(
                    index
                    for index in {*(token.i for token in first.subtree), *nodes}
                    if self.same_sentence(origin, index) and index not in self.predicates
                )
                self.add_cue(
                    kind, phrase.replace(" ", "_"), span, self.span(nodes), (origin,), origin=origin
                )
        for report in sorted(self.predicates):
            token = self.doc[report]
            lemma = self.lemma(token)
            if lemma not in _REPORT:
                continue
            attribution = self.span(
                {
                    report,
                    *(
                        i
                        for role in roles[report]
                        if role.name == "actor"
                        for i in role.span.tokens
                    ),
                    *(
                        child.i
                        for child in token.children
                        if child.dep_ in _AUX | {"neg"} and self.same_sentence(report, child.i)
                    ),
                }
            )
            unresolved = any(cue.kind == "negation" for cue in self.cues[report])
            for child in token.children:
                if (
                    child.dep_ != "ccomp"
                    or child.i not in self.predicates
                    or not self.same_sentence(report, child.i)
                ):
                    continue
                variant = (
                    "reported_assumption"
                    if child.i in self.direct["reported_assumption"][report]
                    else "reported_complement"
                )
                self.add_cue(
                    "attribution",
                    variant,
                    attribution,
                    self.span((report,)),
                    (child.i,),
                    origin=report,
                    component=child.i,
                    unresolved=unresolved,
                )
                if lemma in _ASSUMPTION:
                    self.add_cue(
                        "assumption",
                        variant,
                        self.focus(child.i, roles[child.i]),
                        self.span((report,)),
                        (report,),
                        origin=report,
                        component=child.i,
                        unresolved=unresolved,
                    )
        for predicate in self.predicates & self.quotes:
            self.add_cue(
                "quotation",
                "quoted_predicate",
                self.focus(predicate, roles[predicate]),
                self.span((predicate,)),
                (predicate,),
                origin=predicate,
            )

    def predicate_cues(self) -> None:
        for (index,) in self.lexical["modal"]:
            token = self.doc[index]
            origin = token.head.i
            if (
                token.dep_ not in _AUX
                or origin not in self.predicates
                or not self.same_sentence(origin, index)
            ):
                continue
            span = self.span((index,))
            hosts = tuple(
                peer
                for peer in self.coordinate_group(origin)
                if peer == origin or self.shared_coordinate(origin, peer)
            )
            self.add_cue("modality", token.lower_, span, span, hosts, origin=origin)
        for (index,) in self.lexical["negation"]:
            token = self.doc[index]
            origin = token.head.i
            if origin not in self.predicates or not self.same_sentence(origin, index):
                continue
            span = self.span((index,))
            hosts = {origin}
            for peer in self.coordinate_group(origin):
                if self.shared_coordinate(origin, peer):
                    hosts.add(peer)
            # Disjunction also leaves negative scope undecided. A contrastive
            # conjunction or a peer with its own subject/auxiliary keeps it local.
            for child in self.doc[origin].children:
                if (
                    child.i in self.predicates
                    and child.dep_ == "conj"
                    and self.connector(origin, child.i) in _ALTERNATIVE
                    and not self.direct["active_subject"][child.i]
                    and not self.direct["passive_patient"][child.i]
                    and not any(member.dep_ in _AUX for member in child.children)
                ):
                    hosts.add(child.i)
            self.add_cue(
                "negation",
                "predicate_negation",
                span,
                span,
                tuple(sorted(hosts)),
                origin=origin,
                unresolved=len(hosts) > 1,
            )

    def roles_for_coordinates(
        self, roles: dict[int, tuple[FrameRole, ...]]
    ) -> dict[int, tuple[FrameRole, ...]]:
        inherited = {}
        for predicate, own in roles.items():
            group = self.coordinate_group(predicate)
            additions = []
            for name in ("actor", "object"):
                if any(role.name == name for role in own):
                    continue
                passive = self.voice(predicate) == "passive"
                sources = {
                    (peer, role)
                    for peer in group
                    if peer != predicate
                    and self.voice(peer) == self.voice(predicate)
                    and self.shared_coordinate(
                        peer if peer < predicate else predicate, max(peer, predicate)
                    )
                    for role in roles[peer]
                    if role.name == name
                    and (
                        (name == "actor" and peer < predicate)
                        or (name == "actor" and passive and predicate < peer < role.head)
                        or (name == "object" and passive and role.head < peer < predicate)
                        or (name == "object" and predicate < peer < role.head)
                    )
                }
                if len(sources) == 1:
                    peer, role = next(iter(sources))
                    additions.append(replace(role, inherited_from=peer))
            inherited[predicate] = (*own, *additions)
        return inherited

    def recipe(self, predicate: int, voice: str, roles: tuple[FrameRole, ...]) -> tuple[str, str]:
        token = self.doc[predicate]
        lemma = self.lemma(token)
        if predicate in self.pos_ambiguous:
            return "unresolved", "unresolved_coordinate_pos"
        if lemma in _ASSUMPTION:
            variant = (
                "reported_assumption"
                if self.direct["reported_assumption"][predicate]
                else "assumption_predicate"
            )
            return "reported_assumption", variant
        if lemma in _NAMING and (
            lemma not in _NAMING_COMPLEMENT or any(role.name == "complement" for role in roles)
        ):
            return "naming", "naming_" + voice
        if voice == "copular":
            return (
                "copular",
                "copular_complement_head"
                if predicate in self.copular
                else "copular_auxiliary_head",
            )
        if self.direct["passive_patient"][predicate] and any(
            head in self.probability for head in self.direct["passive_patient"][predicate]
        ):
            return "passive", "passive_probability_subject"
        if voice == "passive":
            return "passive", "passive_patient"
        if token.pos_ != "VERB":
            return "unresolved", "marked_clause_pos"
        return "active", "active_lexical_predicate"

    def disposition(
        self, predicate: int, reading: str, roles: tuple[FrameRole, ...], polarity: str
    ) -> str:
        token = self.doc[predicate]
        cues = self.cues[predicate]
        kinds = {cue.kind for cue in cues}
        if "contrast" in kinds or "quotation" in kinds:
            return "reference"
        if reading == "reported_assumption":
            return "assumption_restriction" if polarity == "positive" else "unresolved"
        if "attribution" in kinds:
            return "reference"
        if reading == "naming":
            if polarity != "positive":
                return "reference" if polarity == "negative" else "unresolved"
            if self.lemma(token) in _NAMING_REFERENCE:
                return "reference"
            return "definition" if len(roles) >= 2 else "unresolved"
        if self.layout == "example" or "example" in kinds:
            return "example"
        if reading == "copular":
            return "explanation" if len(roles) >= 2 else "unresolved"
        if self.lemma(token) == "give" and any(role.head in self.probability for role in roles):
            return "explanation"
        if (
            reading not in {"active", "passive"}
            or polarity.endswith("unresolved")
            or token.dep_ in _CLAUSE
        ):
            return "unresolved"
        modals = {cue.variant for cue in cues if cue.kind == "modality"}
        if self.layout in {"policy", "instruction"} and modals & _PRESCRIPTIVE_MODALS:
            return "prescribed_action"
        imperative = (token.tag_ == "VB" or "Imp" in token.morph.get("Mood", None)) and not any(
            role.name == "actor" for role in roles
        )
        if imperative and (self.layout == "instruction" or self.product.kind == "list_item"):
            return "prescribed_action"
        if not modals and {role.name for role in roles} >= {"actor", "object"}:
            return "described_process"
        return "unresolved"

    def frames(self) -> tuple[PredicateFrame, ...]:
        own_roles = {predicate: self.own_roles(predicate) for predicate in sorted(self.predicates)}
        roles = self.roles_for_coordinates(own_roles)
        self.clause_cues()
        self.predicate_cues()
        self.discourse_cues(own_roles)
        frames = []
        for predicate in sorted(self.predicates):
            voice = self.voice(predicate)
            reading, variant = self.recipe(predicate, voice, roles[predicate])
            negations = [cue for cue in self.cues[predicate] if cue.kind == "negation"]
            polarity = (
                "negative_scope_unresolved"
                if any(cue.status == "unresolved" for cue in negations)
                else "negative"
                if negations
                else "unresolved"
                if reading == "unresolved"
                else "positive"
            )
            sentence = self.product.tokens[predicate].sentence
            assert sentence is not None  # predicate construction requires retained ownership
            frames.append(
                PredicateFrame(
                    self.product.block_id,
                    self.product.dependency_digest,
                    sentence,
                    self.span((predicate,)),
                    self.focus(predicate, own_roles[predicate]),
                    reading,
                    variant,
                    roles[predicate],
                    tuple(
                        sorted(
                            self.cues[predicate],
                            key=lambda cue: (cue.basis.tokens, cue.kind, cue.variant),
                        )
                    ),
                    voice,
                    polarity,
                    self.disposition(predicate, reading, roles[predicate], polarity),
                )
            )
        return tuple(frames)
