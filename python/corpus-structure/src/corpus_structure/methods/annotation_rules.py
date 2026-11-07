"""Named, source-bound candidate rules over retained linguistic columns.

Pattern matches and their roles remain proposals, never semantic admission.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from spacy.language import Language
from spacy.matcher import DependencyMatcher, Matcher, PhraseMatcher
from spacy.pipeline import SpanRuler
from spacy.pipeline.spancat import build_preset_spans_suggester
from spacy.tokens import Doc, Span
from spacy.vocab import Vocab

from corpus_structure.ingest.annotation_views import AnnotationView

RAW_GROUP = "wce_raw_candidates"
RECONCILED_GROUP = "wce_reconciled_candidates"
CLASSIFIED_GROUP = "wce_classified_candidates"


class RoleBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    node: str = Field(min_length=1)
    expansion: Literal["exact", "subtree", "conjuncts", "noun_chunk"] = "exact"
    max_tokens: int = Field(default=64, ge=1, le=256)
    stop_words: tuple[str, ...] = ("if", "unless", "except")
    nominal_prepositions: tuple[str, ...] = Field(default=(), exclude_if=lambda words: not words)

    @model_validator(mode="after")
    def nominal_complements(self):
        if self.nominal_prepositions and self.expansion != "noun_chunk":
            raise ValueError("nominal complements require a base noun chunk")
        return self


class AnnotationRule(BaseModel):
    """One stable authored variant; role vocabulary belongs to its domain recipe."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    rule: str = Field(min_length=1)
    variant: str = Field(min_length=1)
    mechanism: Literal["token", "phrase", "dependency"]
    pattern: list[dict[str, Any]] | list[str] = Field(min_length=1)
    bindings: dict[str, RoleBinding] = Field(min_length=1)

    @model_validator(mode="after")
    def named_nodes(self):
        if any(not name for name in self.bindings):
            raise ValueError("role identifiers cannot be empty")
        if self.mechanism == "phrase":
            if not all(isinstance(value, str) and value for value in self.pattern):
                raise ValueError("phrase pattern requires explicit token spellings")
            names = {"match", *(str(i) for i in range(len(self.pattern)))}
        elif self.mechanism == "token":
            if not all(isinstance(value, dict) for value in self.pattern):
                raise ValueError("token pattern requires token predicates")
            names = {"match"}
        else:
            names = [value.get("RIGHT_ID") for value in self.pattern if isinstance(value, dict)]
            if len(names) != len(self.pattern) or any(not name for name in names):
                raise ValueError("dependency variant requires named RIGHT_ID nodes")
            if len(set(names)) != len(names):
                raise ValueError("dependency variant repeats RIGHT_ID")
        if any(binding.node not in names for binding in self.bindings.values()):
            raise ValueError("role binding references an unavailable pattern node")
        return self


@dataclass(frozen=True)
class LocatedRole:
    role: str
    node: str
    head: int
    expansion: str
    nodes: tuple[int, ...]
    extents: tuple[tuple[int, int], ...]
    status: str
    reason: str | None = None


@dataclass(frozen=True)
class AnnotationRuleMatch:
    rule: str
    variant: str
    mechanism: str
    nodes: tuple[int, ...]
    extents: tuple[tuple[int, int], ...]
    piece_indices: tuple[int, ...]
    sentences: tuple[int | None, ...]
    dependency_digest: str
    roles: tuple[LocatedRole, ...]
    protocol: str = "named-annotation-match-2"
    negation_extents: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class AnnotationRuleResult:
    matches: tuple[AnnotationRuleMatch, ...]
    availability: tuple[tuple[str, str, str], ...]


class PreparedAnnotationRules:
    """Prepare once; keep each variant's node ordering and explicit role bindings."""

    def __init__(self, vocab: Vocab, *, rules: tuple[AnnotationRule, ...]) -> None:
        self.vocab = vocab
        self.rules = rules
        self.matchers: dict[int, Any] = {}
        self.variants: dict[int, AnnotationRule] = {}
        if len({(r.rule, r.variant) for r in rules}) != len(rules):
            raise ValueError("duplicate authored rule/variant identity")
        for index, rule in enumerate(rules):
            label = f"wce-variant:{index}:{rule.rule}:{rule.variant}"
            self.variants[vocab.strings.add(label)] = rule
            if rule.mechanism == "token":
                matcher = Matcher(vocab, validate=True)
                matcher.add(label, [[part for part in rule.pattern if isinstance(part, dict)]])
            elif rule.mechanism == "phrase":
                matcher = PhraseMatcher(vocab, attr="LOWER", validate=True)
                matcher.add(
                    label,
                    [Doc(vocab, words=[word for word in rule.pattern if isinstance(word, str)])],
                )
            else:
                matcher = DependencyMatcher(vocab, validate=True)
                matcher.add(label, [[part for part in rule.pattern if isinstance(part, dict)]])
            self.matchers[vocab.strings[label]] = matcher
        self.collector = SpanRuler(
            Language(vocab=vocab),
            spans_key=RAW_GROUP,
            spans_filter=None,
            annotate_ents=False,
            overwrite=True,
            validate=True,
        )
        self.candidate_suggester = build_preset_spans_suggester(RAW_GROUP)

    @staticmethod
    def _requirements(rule: AnnotationRule) -> set[str]:
        attributes = {key: key for key in ("LEMMA", "POS", "TAG", "MORPH", "DEP", "SENT_START")}
        attributes.update({"IS_SENT_START": "SENT_START", "IS_SENT_END": "SENT_START"})
        # NER columns are not synthesized from the default values of a restored Doc.
        attributes.update({key: key for key in ("ENT_TYPE", "ENT_IOB", "ENT_ID", "ENT_KB_ID")})
        required = {"DEP"} if rule.mechanism == "dependency" else set()
        for part in rule.pattern:
            if isinstance(part, dict):
                predicates = part.get("RIGHT_ATTRS", part)
                required.update(attributes[key] for key in predicates if key in attributes)
        return required

    @staticmethod
    def _nominal_complements(doc, head, noun_chunks, allowed):
        """Extend a base noun chunk through one explicitly permitted nominal preposition."""
        expanded = set(noun_chunks[head])
        for prep in doc[head].children:
            if prep.dep_ != "prep" or prep.lower_ not in allowed:
                continue
            objects = [child for child in prep.children if child.dep_ == "pobj"]
            if len(objects) != 1 or objects[0].i not in noun_chunks:
                return expanded, "partial", "nominal complement lacks one retained noun chunk"
            expanded.update({prep.i, *noun_chunks[objects[0].i]})
        return expanded, "complete", None

    def match(self, view: AnnotationView) -> AnnotationRuleResult:
        view.check_layout()
        if view.doc.vocab is not self.vocab:
            raise ValueError("prepared rules and native view require the same vocabulary")
        product, doc = view.product, view.doc
        columns = {c.attribute for c in product.availability if c.status == "complete"}
        available = {
            key for key, rule in self.variants.items() if self._requirements(rule) <= columns
        }
        statuses = tuple(
            (rule.rule, rule.variant, "available" if key in available else "unavailable")
            for key, rule in self.variants.items()
        )
        results, spans = [], []
        noun_chunks = {}
        if "DEP" in columns and any(
            binding.expansion == "noun_chunk"
            for rule in self.variants.values()
            for binding in rule.bindings.values()
        ):
            try:
                noun_chunks = {
                    chunk.root.i: set(range(chunk.start, chunk.end)) for chunk in doc.noun_chunks
                }
            except NotImplementedError:
                # A language without a declared syntax iterator has no such expansion.
                noun_chunks = {}

        def add(label: int, nodes: tuple[int, ...]) -> None:
            if label not in available:
                return
            rule = self.variants[label]
            node_map = (
                {
                    part["RIGHT_ID"]: (index,)
                    for part, index in zip(rule.pattern, nodes, strict=True)
                    if isinstance(part, dict)
                }
                if rule.mechanism == "dependency"
                else {"match": nodes, **{str(i): (n,) for i, n in enumerate(nodes)}}
            )
            roles = []
            for name, binding in rule.bindings.items():
                selected = node_map[binding.node]
                head = (
                    selected[0]
                    if len(selected) == 1
                    else doc[min(selected) : max(selected) + 1].root.i
                )
                expanded, status, reason = set(selected), "complete", None
                if binding.expansion != "exact":
                    if "DEP" not in columns or product.tokens[head].sentence is None:
                        expanded, status, reason = (
                            {head},
                            "unavailable",
                            "expansion requires retained DEP and sentence ownership",
                        )
                    else:
                        if binding.expansion == "noun_chunk" and head not in noun_chunks:
                            status, reason = (
                                "unavailable",
                                "no retained base noun phrase for this head",
                            )
                        expanded = (
                            noun_chunks.get(head, {head})
                            if binding.expansion == "noun_chunk"
                            else {t.i for t in doc[head].subtree}
                            if binding.expansion == "subtree"
                            else {head, *(t.i for t in doc[head].conjuncts)}
                        )
                        if binding.nominal_prepositions and head in noun_chunks:
                            expanded, status, reason = self._nominal_complements(
                                doc, head, noun_chunks, binding.nominal_prepositions
                            )
                        scoped = {
                            i
                            for i in expanded
                            if product.tokens[i].sentence == product.tokens[head].sentence
                        }
                        boundaries = [
                            i for i in scoped if i != head and doc[i].lower_ in binding.stop_words
                        ]
                        if boundaries:
                            scoped = {i for i in scoped if i < min(boundaries)}
                        if scoped != expanded:
                            status, reason = (
                                "partial",
                                "expansion stopped at sentence or declared scope boundary",
                            )
                        expanded = scoped | {head}
                if len(expanded) > binding.max_tokens:
                    expanded, status, reason = (
                        {head},
                        "partial",
                        "expansion exceeds declared token limit; head retained",
                    )
                role_nodes = tuple(sorted(expanded))
                extents = tuple(
                    (product.tokens[i].start, product.tokens[i].end) for i in role_nodes
                )
                roles.append(
                    LocatedRole(
                        name,
                        binding.node,
                        head,
                        binding.expansion,
                        role_nodes,
                        extents,
                        status,
                        reason,
                    )
                )
                if role_nodes and role_nodes == tuple(range(role_nodes[0], role_nodes[-1] + 1)):
                    spans.append(
                        Span(
                            doc,
                            role_nodes[0],
                            role_nodes[-1] + 1,
                            label=name,
                            span_id=repr((rule.rule, rule.variant, name)),
                        )
                    )
            rows = [product.tokens[index] for index in nodes]
            selected_role_nodes = {index for role in roles for index in role.nodes}
            negation_extents = tuple(
                (token.start, token.end)
                for index, token in enumerate(product.tokens)
                if token.dependency == "neg"
                and (index in selected_role_nodes or token.head in nodes)
            )
            results.append(
                AnnotationRuleMatch(
                    rule.rule,
                    rule.variant,
                    rule.mechanism,
                    nodes,
                    tuple(sorted({(r.start, r.end) for r in rows})),
                    tuple(sorted({i for r in rows for i in r.piece_indices})),
                    tuple(r.sentence for r in rows),
                    product.dependency_digest,
                    tuple(roles),
                    negation_extents=negation_extents,
                )
            )

        # Each variant is prepared once and runs only when its own columns are available.
        for key, matcher in self.matchers.items():
            if key not in available:
                continue
            for match in matcher(doc):
                if self.variants[key].mechanism == "dependency":
                    label, nodes = match
                    add(label, tuple(nodes))
                else:
                    label, start, end = match
                    add(label, tuple(range(start, end)))
        self.collector.set_annotations(doc, spans)
        doc.spans[RECONCILED_GROUP] = list(doc.spans[RAW_GROUP])
        return AnnotationRuleResult(tuple(results), statuses)
