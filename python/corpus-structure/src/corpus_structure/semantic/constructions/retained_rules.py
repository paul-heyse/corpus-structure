"""Owned finite linguistic recognition over retained native working columns.

These rules run only while producing the common construction layer. Downstream
consumers project retained primary nodes; they do not rerun these recognizers.
"""

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
type FrameLayout = Literal["prose", "example", "policy", "instruction", "unknown"]


@lru_cache(maxsize=1)
def interpretation_recipe():
    return json.loads(files(__package__).joinpath("retained_rules.json").read_text())


def source_layout(
    product: AnnotationProduct,
    text: str,
    pieces: Sequence[Mapping[str, Any]],
    items: Mapping[str, Mapping[str, Any]],
    *,
    with_context=False,
):
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
    examined_heading = None
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
        examined_heading = dict(
            projection=product.source.projection_digest,
            native_pointer=pointer,
            start=piece["start"],
            end=piece["end"],
        )
        heading = text[piece["start"] : piece["end"]].strip().lower()
        first = heading.split(maxsplit=1)[0].strip(":") if heading else ""
        headings = interpretation_recipe()["layout_headings"]
        for layout in ("example", "policy", "instruction"):
            if first in headings[layout]:
                return (layout, examined_heading) if with_context else layout
        break
    return ("prose", examined_heading) if with_context else "prose"


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
_CONDITION = frozenset(interpretation_recipe()["definition_scope"]["condition_markers"])
_EXCEPTION = frozenset(interpretation_recipe()["definition_scope"]["exception_markers"])
_ORDER = frozenset(interpretation_recipe()["definition_scope"]["order_markers"])
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
    primary_ref: Any = None


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
    primary_ref: Any = None
    primary_marker_ref: Any = None


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
    primary_ref: Any = None
    clause_role: str = "unresolved"
    negation_examined: bool = False
    modality_examined: bool = False


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


def recognize_frames(
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
            result = recognize_frame_result(view, layout=layout)
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
    return recognize_frame_result(view, layout=layout).frames


def recognize_frame_result(
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
                span = self.span((index,))
                self.add_cue("modality", token.lower_, span, span, (), unresolved=True)
                continue
            span = self.span((index,))
            hosts = tuple(
                peer
                for peer in self.coordinate_group(origin)
                if peer == origin or self.shared_coordinate(origin, peer)
            )
            self.add_cue("modality", token.lower_, span, span, hosts, origin=origin)
        negative = set(self.lexical["negation"])
        negative.update(
            (token.i,) for token in self.doc
            if {"Polarity=Neg", "PronType=Neg"}.intersection(str(token.morph).split("|"))
        )
        for (index,) in sorted(negative):
            token = self.doc[index]
            origin = token.head.i
            if origin not in self.predicates or not self.same_sentence(origin, index):
                span = self.span((index,))
                self.add_cue("negation", "predicate_negation", span, span, (), unresolved=True)
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


_SYMBOL = object()


@lru_cache(maxsize=4)
def _qualifier_patterns(vocab: Vocab) -> Matcher:
    matcher = Matcher(vocab, validate=True)
    for name, words in (
        (
            "variance",
            (
                "let",
                _SYMBOL,
                "and",
                _SYMBOL,
                "be",
                "random",
                "variables",
                "with",
                "positive",
                "variance",
                ".",
            ),
        ),
        (
            "correlation",
            ("the", "correlation", "of", _SYMBOL, "and", _SYMBOL, "is", "defined", "as"),
        ),
        (
            "parameters",
            ("with", "parameters", _SYMBOL, "and", _SYMBOL, "is", "defined", "as", "follows", ":"),
        ),
        (
            "population",
            (
                "counting",
                "the",
                "waiting",
                "time",
                "of",
                "all",
                "customers",
                ",",
                "even",
                "those",
                "that",
                "do",
                "not",
                "have",
                "to",
                "wait",
                "at",
                "all",
            ),
        ),
    ):
        matcher.add(
            name,
            [
                [
                    {"IS_ALPHA": True, "LENGTH": 1} if word is _SYMBOL else {"LOWER": word}
                    for word in words
                ]
            ],
        )
    return matcher


def _arc(child: Token, parent: Token, dependency: str) -> bool:
    return child.head.i == parent.i and child.dep_ == dependency


def _one_piece(view: AnnotationView, start: int, end: int) -> bool:
    rows = view.product.tokens[start:end]
    if not rows:
        return False
    piece = rows[0].piece_indices
    return len(piece) == 1 and all(row.piece_indices == piece for row in rows)


def _unquoted_sentence(view: AnnotationView, start: int, end: int) -> bool:
    rows = view.product.tokens
    sentence = rows[start].sentence
    return (
        sentence is not None
        and rows[end - 1].sentence == sentence
        and not any(token.is_quote for token in view.doc[start].sent)
    )


def _span(view: AnnotationView, start: int, end: int) -> LocatedFrameSpan:
    rows = view.product.tokens
    indices = tuple(token.i for token in view.doc[start:end] if not token.is_space)
    return LocatedFrameSpan(indices, ((rows[indices[0]].start, rows[indices[-1]].end),))


def _local_qualifier_cue(
    view: AnnotationView,
    kind: str,
    variant: str,
    start: int,
    end: int,
    marker: int,
    origin: int,
    component: int,
    host: int | None,
) -> FrameCue:
    return FrameCue(
        view.product.block_id,
        view.product.dependency_digest,
        kind,
        variant,
        _span(view, start, end),
        _span(view, marker, marker + 1),
        "located" if host is not None else "unresolved",
        () if host is None else (host,),
        origin,
        component,
    )


def _compound_event(view: AnnotationView, candidate: FrameCue) -> FrameCue | None:
    """Resolve the provisional inner host only when 'then' owns the main predicate."""
    if candidate.variant != "compound_if_then" or len(candidate.hosts) != 2:
        return None
    doc = view.doc
    marker = doc[candidate.basis.tokens[0]]
    if candidate.origin is None or candidate.component is None:
        return None
    first, second = doc[candidate.component], doc[candidate.origin]
    main = second.head
    end = candidate.span.tokens[-1] + 1
    if not marker.i + 2 <= first.i < second.i - 2 < end - 1 < main.i - 1:
        return None
    comma, then = doc[end : end + 2]
    conjunction, second_subject = doc[second.i - 2 : second.i]
    prefix = doc[marker.sent.start : marker.i]
    declared_prefix = len(prefix) == 2 and prefix[0].lower_ == "definition" and prefix[1].like_num
    if (
        marker.lower_ != "if"
        or (len(prefix) and not declared_prefix)
        or main.i not in candidate.hosts
        or second.i not in candidate.hosts
        or main.dep_ != "ROOT"
        or first.lemma_ != "be"
        or second.lemma_ != "be"
        or comma.text != ","
        or then.lower_ != "then"
        or conjunction.lower_ != "and"
        or conjunction.dep_ != "cc"
        or not _arc(marker, first, "mark")
        or not _arc(doc[marker.i + 1], first, "nsubj")
        or not _arc(first, second, "advcl")
        or not _arc(second, main, "ccomp")
        or not _arc(then, main, "advmod")
        or sum(t.lower_ == "then" for t in marker.sent) != 1
        or sum(t.lower_ == "and" and t.dep_ == "cc" for t in doc[first.i + 1 : second.i]) != 1
        or doc[marker.i + 1].text == second_subject.text
        or not _one_piece(view, marker.i, main.i + 1)
        or not _unquoted_sentence(view, marker.i, main.i + 1)
    ):
        return None
    attribute = _arc(conjunction.head, first, "attr")
    if not (
        (
            _arc(second_subject, second, "nsubj")
            and (attribute or conjunction.head in (first, second))
        )
        or (attribute and _arc(second_subject, conjunction.head, "conj"))
    ):
        return None
    return _local_qualifier_cue(
        view, "condition", "event_compound_then", marker.i, end, marker.i, main.i, second.i, main.i
    )


def _variance(view: AnnotationView, start: int, end: int, hosts: set[int]) -> FrameCue | None:
    doc = view.doc
    let, a, and_, b, be, _, variables, with_, positive, variance, _ = doc[start:end]
    prefix = doc[let.sent.start : let.i]
    if (
        view.product.kind != "list_item"
        or (len(prefix) and not (len(prefix) == 1 and prefix[0].text.rstrip(".").isdigit()))
        or a.text == b.text
        or let.dep_ != "ROOT"
        or not _unquoted_sentence(view, start, end)
        or not _one_piece(view, start, end)
        or not all(
            (
                _arc(be, let, "ccomp"),
                _arc(a, be, "nsubj"),
                _arc(and_, a, "cc"),
                _arc(b, a, "conj"),
                _arc(variables, be, "attr"),
                _arc(with_, variables, "prep"),
                _arc(variance, with_, "pobj"),
                _arc(positive, variance, "amod"),
            )
        )
    ):
        return None
    host = end + 7 if end + 7 in hosts else None
    return _local_qualifier_cue(
        view, "assumption", "adjacent_variance_premise", start, end - 1, start, start, be.i, host
    )


def _correlation_hosts(view: AnnotationView, pairs: dict[int, int]) -> set[int]:
    doc = view.doc
    hosts = set()
    for start, end in pairs.items():
        article, correlation, of, a, and_, b, is_, defined, _ = doc[start:end]
        if start < 11:
            continue
        previous = doc[start - 11]
        if (
            previous.lower_ == "let"
            and article.is_sent_start
            and doc[start - 1].sent.end == article.i
            and (a.text, b.text) == (doc[start - 10].text, doc[start - 8].text)
            and _one_piece(view, start - 11, end)
            and _unquoted_sentence(view, start, end)
            and defined.dep_ == "ROOT"
            and all(
                (
                    _arc(correlation, defined, "nsubjpass"),
                    _arc(of, correlation, "prep"),
                    _arc(a, of, "pobj"),
                    _arc(and_, a, "cc"),
                    _arc(b, a, "conj"),
                    _arc(is_, defined, "auxpass"),
                )
            )
        ):
            hosts.add(defined.i)
    return hosts


def _parameter_pair(view: AnnotationView, start: int, end: int) -> FrameCue | None:
    doc = view.doc
    with_, parameters, a, and_, b, is_, defined, as_, follows, colon = doc[start:end]
    if (
        not start
        or a.text == b.text
        or not _one_piece(view, start - 1, end)
        or not _unquoted_sentence(view, start - 1, end)
    ):
        return None
    nominal = doc[start - 1]
    shared = (
        nominal.pos_ in {"NOUN", "PROPN"}
        and _arc(with_, nominal, "prep")
        and _arc(is_, defined, "auxpass")
        and _arc(as_, follows, "mark")
        and _arc(follows, defined, "advcl")
        and _arc(colon, defined, "punct")
    )
    split_subject = (
        nominal.dep_ == "ROOT"
        and _arc(parameters, a, "compound")
        and _arc(a, with_, "pobj")
        and _arc(and_, nominal, "cc")
        and _arc(b, defined, "nsubjpass")
        and _arc(defined, nominal, "conj")
    )
    attached_nominal = (
        defined.dep_ == "ROOT"
        and _arc(nominal, defined, "nsubjpass")
        and _arc(parameters, with_, "pobj")
        and _arc(a, parameters, "appos")
        and _arc(and_, a, "cc")
        and _arc(b, a, "conj")
    )
    host = defined.i if shared and (split_subject or attached_nominal) else None
    return _local_qualifier_cue(
        view,
        "parameterization",
        "nominal_parameter_pair",
        start,
        start + 5,
        start,
        defined.i,
        nominal.i,
        host,
    )


def _population(view: AnnotationView, start: int, end: int) -> FrameCue | None:
    doc = view.doc
    (
        counting,
        _,
        _,
        time,
        of,
        all_,
        customers,
        _,
        even,
        those,
        that,
        do,
        not_,
        have,
        to,
        wait,
        _,
        _,
    ) = doc[start:end]
    if not _one_piece(view, start, end) or not _unquoted_sentence(view, start, end):
        return None
    ending = doc[end : counting.sent.end]
    attached = (
        (not len(ending) or (len(ending) == 1 and ending[0].text == "."))
        and those.dep_ == "appos"
        and (those.head in (customers, time) or _arc(those.head, counting, "nsubj"))
        and all(
            (
                _arc(time, counting, "dobj"),
                _arc(of, time, "prep"),
                _arc(all_, customers, "det"),
                _arc(customers, of, "pobj"),
                _arc(even, those, "advmod"),
                _arc(that, have, "nsubj"),
                _arc(do, have, "aux"),
                _arc(not_, have, "neg"),
                _arc(have, those, "relcl"),
                _arc(to, wait, "aux"),
                _arc(wait, have, "xcomp"),
            )
        )
    )
    return _local_qualifier_cue(
        view,
        "population_inclusion",
        "customer_population_inclusion",
        even.i,
        end,
        even.i,
        counting.i,
        customers.i,
        counting.i if attached else None,
    )


def recognize_local_qualifiers(
    view: AnnotationView, result: PredicateFrameResult
) -> PredicateFrameResult:
    """Extend a base frame result while leaving its replay recipe unchanged."""
    if not result.frames:
        return result
    view.check_layout()
    doc = view.doc
    frames = {frame.predicate.tokens[0] for frame in result.frames}
    found: dict[str, dict[int, int]] = {}
    for match, start, end in _qualifier_patterns(doc.vocab)(doc):
        found.setdefault(doc.vocab.strings[match], {})[start] = end
    correlations = _correlation_hosts(view, found.get("correlation", {}))
    candidates = [
        *(
            _variance(view, start, end, correlations)
            for start, end in found.get("variance", {}).items()
        ),
        *(_parameter_pair(view, start, end) for start, end in found.get("parameters", {}).items()),
        *(_population(view, start, end) for start, end in found.get("population", {}).items()),
    ]
    resolved = {}
    for cue in dict.fromkeys(cue for frame in result.frames for cue in frame.cues):
        replacement = _compound_event(view, cue)
        if replacement is not None and replacement.hosts[0] in frames:
            resolved[cue] = replacement
    if not resolved and not any(candidates):
        return result
    assigned: dict[int, list[FrameCue]] = {}
    unresolved = list(result.unresolved_cues)
    for cue in (*resolved.values(), *candidates):
        if cue is None:
            continue
        if cue.hosts and cue.hosts[0] in frames:
            assigned.setdefault(cue.hosts[0], []).append(cue)
        else:
            unresolved.append(replace(cue, hosts=(), status="unresolved"))
    return replace(
        result,
        frames=tuple(
            replace(
                frame,
                cues=tuple(cue for cue in frame.cues if cue not in resolved)
                + tuple(assigned.get(frame.predicate.tokens[0], ())),
            )
            for frame in result.frames
        ),
        unresolved_cues=tuple(unresolved),
    )


@dataclass(frozen=True, slots=True)
class CrossBlockTarget:
    frame: str
    reading: str
    interpretation: str
    polarity: str
    annotation: AnnotationProduct
    predicate: int
    primary_ref: Any = None


@dataclass(frozen=True, slots=True)
class CrossBlockQualifier:
    source: AnnotationProduct
    cue: FrameCue
    targets: tuple[CrossBlockTarget, ...]
    witness: dict[str, str] | None


def _cross_block_cue(product, variant, start, stop, marker):
    tokens = product.tokens

    def span(first, end):
        return LocatedFrameSpan(
            tuple(range(first, end)),
            ((tokens[first].start, tokens[end - 1].end),),
        )

    return FrameCue(
        product.block_id,
        product.dependency_digest,
        "assumption",
        variant,
        span(start, stop),
        span(marker, marker + 1),
        "located",
        (),
        None,
    )


def _sentences(product):
    by_sentence = defaultdict(list)
    for index, token in enumerate(product.tokens):
        if token.sentence is not None:
            by_sentence[token.sentence].append(index)
    return tuple(tuple(indices) for indices in by_sentence.values())


def _whole_piece(product, piece):
    return piece is not None and (product.block_start, product.block_end) == (
        piece["start"],
        piece["end"],
    )


def _siblings(items, node):
    parent = items.get((node.get("parent") or {}).get("$ref"), {})
    children = tuple(ref["$ref"] for ref in parent.get("children", ()))
    pointer = node["self_ref"]
    if children.count(pointer) != 1:
        return (), -1
    return children, children.index(pointer)


def recognize_cross_block(frame, annotations, selected, hosts, population, native, pieces):
    """Return one local cue with exact frame references per authenticated layout route."""
    items = {item["self_ref"]: item for item in (*native["ancestors"], *native["items"])}
    selected_items = {item["self_ref"] for item in native["items"]}
    by_piece = {piece.get("item_ref"): piece for piece in pieces if "cell_index" not in piece}
    position = {piece.get("item_ref"): i for i, piece in enumerate(pieces)}
    by_block = defaultdict(list)
    for host in hosts:
        by_block[host.annotation.block_id].append(host)
    text = frame.text

    def complete_block(product):
        return (
            product.block_id in selected_items
            and selected.start <= product.block_start < product.block_end <= selected.end
            and _whole_piece(product, by_piece.get(product.block_id))
            and items[product.block_id].get("content_layer") == "body"
        )

    def words(product):
        return tuple(text[token.start : token.end] for token in product.tokens)

    def list_intro(product, node, spelling, sentences):
        prefix = ("for", "each", "of", "the", "following", ",", "assume", "that")
        tokens = product.tokens
        if (
            product.kind != "paragraph"
            or len(sentences) != 1
            or tuple(s.lower() for s in spelling[:8]) != prefix
            or len(spelling) < 11
            or spelling[-1] != ":"
            or tokens[6].dependency != "ROOT"
            or sum(t.head == 6 and t.dependency == "ccomp" for t in tokens[8:-1]) != 1
        ):
            return None
        cue = _cross_block_cue(product, "list_assumption", 6, len(tokens) - 1, 6)
        siblings, index = _siblings(items, node)
        if index < 0 or index + 1 == len(siblings):
            return CrossBlockQualifier(product, cue, (), None)
        group = siblings[index + 1]
        group_node = items.get(group, {})
        children = tuple(ref["$ref"] for ref in group_node.get("children", ()))
        following = position[product.block_id] + 1
        if (
            group not in selected_items
            or siblings.count(group) != 1
            or group_node.get("label") != "list"
            or group_node.get("content_layer") != "body"
            or group_node.get("parent") != node.get("parent")
            or not children
            or len(set(children)) != len(children)
            or following == len(pieces)
            or pieces[following].get("item_ref") != children[0]
        ):
            return CrossBlockQualifier(product, cue, (), None)
        targets = []
        for pointer in children:
            candidates = [
                target
                for target in by_block[pointer]
                if target.annotation.tokens[target.predicate].dependency == "ROOT"
                and target.annotation.tokens[target.predicate].pos in {"VERB", "AUX"}
            ]
            if len(candidates) != 1:
                continue
            (host,) = candidates
            if (
                sum(
                    t.dependency == "ROOT" and t.pos in {"VERB", "AUX"}
                    for t in host.annotation.tokens
                )
                != 1
            ):
                continue
            child = items.get(pointer, {})
            if (
                host.annotation.kind == "list_item"
                and child.get("label") == "list_item"
                and child.get("parent") == {"$ref": group}
                and complete_block(host.annotation)
            ):
                targets.append(host)
        return CrossBlockQualifier(
            product, cue, tuple(targets), dict(kind="list_intro", list_group=group)
        )

    def parameter_note(product, node, spelling, sentences):
        suffix = ("and", "thus", "it", "is", "assumed", "to", "be", "positive", ".")
        tokens = product.tokens
        for indices in sentences:
            a, b = indices[0], indices[-1] + 1
            folded = tuple(s.lower() for s in spelling[a:b])
            if (
                b - a < 13
                or folded[:2] != ("the", "parameter")
                or sum(folded[i : i + 2] == ("the", "parameter") for i in range(len(folded) - 1))
                != 1
                or folded[-9:] != suffix
                or len(spelling[a + 2]) != 1
                or not spelling[a + 2].isalpha()
            ):
                continue
            assumed = b - 5
            if (
                tokens[b - 7].head != assumed
                or tokens[b - 7].dependency != "nsubjpass"
                or tokens[b - 6].head != assumed
                or tokens[b - 6].dependency != "auxpass"
                or tokens[b - 4].head != b - 3
                or tokens[b - 4].dependency != "aux"
                or tokens[b - 3].head != assumed
                or tokens[b - 3].dependency != "xcomp"
                or tokens[b - 2].head != b - 3
                or tokens[b - 2].dependency != "acomp"
            ):
                continue
            cue = _cross_block_cue(product, "parameter_positive", b - 7, b - 1, assumed)
            siblings, index = _siblings(items, node)
            targets = []
            if index >= 2:
                origin, display = siblings[index - 2 : index]
                host_candidates = by_block[origin]
                if (
                    items.get(display, {}).get("label") == "formula"
                    and display in selected_items
                    and items[display].get("content_layer") == "body"
                    and items.get(origin, {}).get("label") == "text"
                    and items[display].get("parent") == node.get("parent")
                    and items.get(origin, {}).get("parent") == node.get("parent")
                    and position.get(origin) == position[product.block_id] - 2
                    and position.get(display) == position[product.block_id] - 1
                ):
                    for host in host_candidates:
                        if not complete_block(host.annotation):
                            continue
                        for target_frame, qualifier, indices in population:
                            if target_frame != host.frame:
                                continue
                            symbol = host.annotation.tokens[indices[-1]]
                            if text[symbol.start : symbol.end] == spelling[a + 2]:
                                targets.append((host, qualifier))
            if len(targets) == 1:
                host, predecessor = targets[0]
                yield CrossBlockQualifier(
                    product,
                    cue,
                    (host,),
                    dict(kind="parameter_note", parameterization=predecessor),
                )
            else:
                yield CrossBlockQualifier(product, cue, (), None)

    for product in annotations:
        if not complete_block(product):
            continue
        node = items[product.block_id]
        if node.get("label") != "text":
            continue
        spelling = words(product)
        sentences = _sentences(product)
        intro = list_intro(product, node, spelling, sentences)
        if intro is not None:
            yield intro
        yield from parameter_note(product, node, spelling, sentences)


PRIMARY_RULE_FAMILY = "construction.source_readings"
PRIMARY_RULE_VOCABULARY = "source-linguistic-rules-1"


def populate(
    layer,
    view,
    native_pin,
    native_layer,
    *,
    check_active=lambda: None,
    admitted=lambda start, end: True,
):
    """Recognize finite source-language readings once and retain ordinary primary nodes.

    Native working columns are restored without tokenization/inference. Every emitted
    member cites exact native token annotations. Scientific numeric lowering is not
    performed here; a condition retains its located source and operator meaning.
    """
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.native_evidence_layers import retained_annotation_products

    from .forest import identity

    family = PRIMARY_RULE_FAMILY
    if family not in layer.operation["produced_families"]:
        layer.operation["produced_families"].append(family)
    native_runs = [
        row for row in native_layer.payload.get("native_runs", ()) if row["provider"] == "spacy"
    ]
    if len(native_runs) != 1:
        raise ValueError("source readings require one exact retained spaCy producer")
    run = native_runs[0]
    profile = AnnotationProfile(
        SentenceConfig(
            spacy_version=run["runtime_version"],
            model=run["model"],
            model_version=run["model_version"],
            exclude=("ner",),
        )
    )
    native_products = retained_annotation_products({native_pin: native_layer}, view, profile)
    products = tuple(
        product for product in native_products if admitted(product.block_start, product.block_end)
    )
    for product in native_products:
        if product not in products and any(
            admitted(token.start, token.end) for token in product.tokens
        ):
            for selector in layer.scope["selectors"]:
                if selector["projection"] == view.ref.projection_digest:
                    layer.record(
                        family,
                        selector,
                        "unsupported",
                        "selected source scope cuts a whole native block; no silent linguistic cut",
                    )
    native_annotations = {
        (a["native_token"]["container"], a["native_token"]["index"]): a
        for a in native_layer.payload["annotations"]
        if a.get("native_token", {}).get("native_run") == run["local_id"]
    }
    results, frame_ids, cue_ids = [], {}, {}
    layout_contexts = {}

    def located(product, span, label):
        key = identity("source-role", [native_pin.values(), product.block_id, span.tokens, label])
        if key not in layer.terms:
            occurrences = [layer.occurrence(view, a, b) for a, b in span.extents]
            container = f"spacy/{view.ref.id}/{product.block_id}/block"
            premises = [
                dict(
                    layer=native_pin.values(),
                    local_id=native_annotations[container, index]["local_id"],
                )
                for index in span.tokens
            ]
            layer.terms[key] = dict(
                local_id=key,
                family=family,
                kind="participant",
                vocabulary=PRIMARY_RULE_VOCABULARY,
                value=label,
                status="interpreted" if occurrences else "unknown",
                occurrences=occurrences,
                external_premises=premises,
            )
        return key

    def construction(product, key, variant, occurrences, meaning):
        annotation = identity("source-construction", [key, variant])
        layer.annotations[annotation] = dict(
            local_id=annotation,
            kind="construction",
            family=family,
            vocabulary=PRIMARY_RULE_VOCABULARY,
            rule_id="tc.source." + variant,
            native_scheme="retained-spacy-source-rules-1",
            native_label=variant,
            status="interpreted",
            occurrences=occurrences,
            external_premises=[
                dict(
                    layer=native_pin.values(),
                    local_id=f"spacy/{view.ref.id}/{product.block_id}/block",
                )
            ],
            context=layout_contexts[product.block_id],
        )
        heading = next(
            (
                selector
                for selector in layout_contexts[product.block_id]["examined"]
                if selector.get("native_pointer")
            ),
            None,
        )
        if heading is not None:
            layer.annotations[annotation]["premises"] = [
                layer.occurrence(view, heading["start"], heading["end"])
            ]
        membership = identity("source-meaning", [annotation, meaning])
        layer.memberships[membership] = dict(
            local_id=membership,
            group=annotation,
            member=meaning,
            role="meaning",
            order=0,
            structural=False,
            scope=annotation,
            family=family,
            occurrences=occurrences,
            premises=[annotation],
        )
        return annotation

    def token_span(product, index):
        token = product.tokens[index]
        return LocatedFrameSpan((index,), ((token.start, token.end),))

    def cue(product, candidate):
        key = identity(
            "source-cue",
            [
                native_pin.values(),
                product.block_id,
                candidate.kind,
                candidate.variant,
                candidate.span.tokens,
                candidate.basis.tokens,
            ],
        )
        if key in cue_ids:
            return key
        occurrences = [layer.occurrence(view, a, b) for a, b in candidate.span.extents]
        annotation = construction(product, key, candidate.variant, occurrences, key)
        children = [
            dict(role="cue", target=located(product, candidate.span, "cue"), structural=True),
            dict(role="basis", target=located(product, candidate.basis, "basis"), structural=True),
        ]
        formal_operator = (
            (
                "not_compare"
                if candidate.variant == "unless"
                else "compare"
                if candidate.variant in {"if", "when"}
                else "escape"
            )
            if candidate.kind in {"condition", "assumption"}
            else "escape"
        )
        formal_metadata = identity(
            "source-property", [key, "formal_condition_operator", formal_operator]
        )
        layer.terms[formal_metadata] = dict(
            local_id=formal_metadata,
            family=family,
            kind="operator",
            vocabulary=PRIMARY_RULE_VOCABULARY,
            value=formal_operator,
            status="interpreted",
            occurrences=[],
            children=[],
        )
        children.append(
            dict(role="formal_condition_operator", target=formal_metadata, structural=True)
        )
        if candidate.origin is not None:
            children.append(
                dict(
                    role="origin",
                    target=located(product, token_span(product, candidate.origin), "origin"),
                    structural=True,
                )
            )
        if candidate.component is not None:
            children.append(
                dict(
                    role="component",
                    target=located(product, token_span(product, candidate.component), "component"),
                    structural=True,
                )
            )
        layer.terms[key] = dict(
            local_id=key,
            family=family,
            kind="operator",
            vocabulary=PRIMARY_RULE_VOCABULARY,
            value=candidate.kind,
            status="interpreted" if candidate.status == "located" else "unknown",
            occurrences=occurrences,
            children=children,
            premises=[annotation],
        )
        cue_ids[key] = (product, candidate)
        return key

    for product in products:
        check_active()
        layout, heading = source_layout(
            product,
            view.text,
            view.pieces,
            {node["self_ref"]: node for node in view.items},
            with_context=True,
        )
        focal = dict(
            projection=view.ref.projection_digest, start=product.block_start, end=product.block_end
        )
        layout_contexts[product.block_id] = dict(
            focal=[focal], examined=[heading, focal] if heading is not None else [focal], gaps=[]
        )
        try:
            restored = annotation_view(
                product,
                view.text[product.block_start : product.block_end],
                _frame_vocabulary(),
                required=_REQUIRED,
            )
            result = recognize_local_qualifiers(
                restored, recognize_frame_result(restored, layout=layout)
            )
        except (AnnotationUnavailable, ValueError) as error:
            issue = FrameIssue(
                product.block_id, product.dependency_digest, "unavailable", str(error)
            )
            result = PredicateFrameResult((), (issue,))
        results.append((product, result))
        negation_examined = {"DEP", "MORPH"} <= _available(product)
        modality_examined = {"DEP", "TAG"} <= _available(product)
        for frame in result.frames:
            key = identity(
                "source-predication",
                [native_pin.values(), product.block_id, frame.predicate.tokens],
            )
            frame_ids[product.block_id, frame.predicate.tokens[0]] = key
            occurrences = [layer.occurrence(view, a, b) for a, b in frame.focus.extents]
            annotation = construction(product, key, frame.variant, occurrences, key)
            children: list[dict[str, Any]] = [
                dict(
                    role="predicate",
                    target=located(product, frame.predicate, "predicate"),
                    structural=True,
                ),
                dict(role="focus", target=located(product, frame.focus, "focus"), structural=True),
            ]
            for name, value in (
                ("voice", frame.voice),
                ("polarity", "unresolved" if frame.polarity == "positive" and not negation_examined else frame.polarity),
                ("interpretation", frame.interpretation if negation_examined and modality_examined else "unresolved"),
                ("layout", layout),
                ("negation_examination", "complete" if negation_examined else "unavailable"),
                ("modality_examination", "complete" if modality_examined else "unavailable"),
                (
                    "clause_role",
                    "subordinate"
                    if product.tokens[frame.predicate.tokens[0]].dependency == "advcl"
                    else "main_or_coordinate",
                ),
            ):
                metadata = identity("source-property", [key, name, value])
                layer.terms[metadata] = dict(
                    local_id=metadata,
                    family=family,
                    kind="operator",
                    vocabulary=PRIMARY_RULE_VOCABULARY,
                    value=value,
                    status="interpreted",
                    occurrences=[],
                    children=[],
                )
                children.append(dict(role=name, target=metadata, structural=True))
            for order, role in enumerate(frame.roles):
                member = located(product, role.span, role.name)
                if role.inherited_from is not None:
                    origin = located(
                        product, token_span(product, role.inherited_from), "inherited_from"
                    )
                    layer.terms[member].setdefault("children", []).append(
                        dict(role="inherited_from", target=origin, structural=True)
                    )
                if role.head is not None:
                    head = located(product, token_span(product, role.head), "head")
                    if head != member:
                        layer.terms[member].setdefault("children", []).append(
                            dict(role="head", target=head, structural=True)
                        )
                layer.terms[member]["status"] = (
                    "interpreted" if role.status == "located" else "unknown"
                )
                children.append(dict(role=role.name, target=member, structural=True, order=order))
            layer.terms[key] = dict(
                local_id=key,
                family=family,
                kind="predicate",
                vocabulary=PRIMARY_RULE_VOCABULARY,
                value=frame.reading,
                status="interpreted",
                occurrences=occurrences,
                children=children,
                premises=[annotation],
            )
            for candidate in frame.cues:
                cue(product, candidate)
        for candidate in result.unresolved_cues:
            cue(product, candidate)
        selector = dict(
            projection=view.ref.projection_digest, start=product.block_start, end=product.block_end
        )
        blocking = tuple(issue for issue in result.issues
                         if not issue.reason.startswith("optional retained columns:"))
        layer.record(
            family,
            selector,
            "partial" if blocking else "complete",
            "; ".join(issue.reason for issue in blocking) if blocking else None,
        )
    # Hosting is relational. It never makes an operator point back through its own DAG.
    for key, (product, candidate) in cue_ids.items():
        for host in candidate.hosts:
            target = frame_ids.get((product.block_id, host))
            if target is None:
                continue
            relation = identity("source-host", [key, target])
            layer.roles[relation] = dict(
                local_id=relation,
                owner=key,
                member=target,
                role="host",
                scheme=PRIMARY_RULE_VOCABULARY,
                family=family,
                occurrences=layer.terms[key]["occurrences"],
                basis=dict(
                    kind="contextual_proposal",
                    status="private_proposal",
                    rule_id="tc.source." + candidate.variant,
                    premises=[*layer.terms[key]["premises"], *layer.terms[target]["premises"]],
                ),
            )
    from types import SimpleNamespace

    host_rows = [
        CrossBlockTarget(
            frame_ids[product.block_id, frame.predicate.tokens[0]],
            frame.reading,
            frame.interpretation,
            frame.polarity,
            product,
            frame.predicate.tokens[0],
        )
        for product, result in results
        for frame in result.frames
    ]
    parameters = [
        (frame_ids[product.block_id, host], key, candidate.span.tokens)
        for key, (product, candidate) in cue_ids.items()
        if candidate.variant == "nominal_parameter_pair"
        for host in candidate.hosts
        if (product.block_id, host) in frame_ids
    ]
    selected = SimpleNamespace(start=0, end=len(view.text))
    native = dict(items=view.items, ancestors=view.ancestors)
    pieces = tuple(piece for piece in view.pieces if piece["kind"] == "native_text")
    for entry in recognize_cross_block(
        SimpleNamespace(text=view.text), products, selected, host_rows, parameters, native, pieces
    ):
        check_active()
        key = cue(entry.source, entry.cue)
        witness = entry.witness or {}
        if witness.get("parameterization"):
            layer.terms[key]["children"].append(
                dict(role="prior_qualifier", target=witness["parameterization"], structural=True)
            )
        if witness.get("list_group"):
            metadata = identity(
                "source-property", [key, "native_list_group", witness["list_group"]]
            )
            layer.terms[metadata] = dict(
                local_id=metadata,
                family=family,
                kind="operator",
                vocabulary=PRIMARY_RULE_VOCABULARY,
                value=witness["list_group"],
                status="interpreted",
                occurrences=[],
                children=[],
            )
            layer.terms[key]["children"].append(
                dict(role="native_list_group", target=metadata, structural=True)
            )
        for target in entry.targets:
            relation = identity("source-cross-host", [key, target.frame])
            layer.roles[relation] = dict(
                local_id=relation,
                owner=key,
                member=target.frame,
                role="cross_block_host",
                scheme=PRIMARY_RULE_VOCABULARY,
                family=family,
                occurrences=layer.terms[key]["occurrences"],
                basis=dict(
                    kind="contextual_proposal",
                    status="private_proposal",
                    rule_id="tc.source." + entry.cue.variant,
                    premises=[
                        *layer.terms[key]["premises"],
                        *layer.terms[target.frame]["premises"],
                    ],
                ),
            )
    if not products and not any(row["family"] == family for row in layer.coverage):
        for selector in layer.scope["selectors"]:
            if selector["projection"] == view.ref.projection_digest:
                layer.record(
                    family, selector, "failed", "no retained whole-block native population"
                )
    return tuple(results)
