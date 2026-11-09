"""Compose private record candidates from exact, independently declared source rules."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict
from hashlib import sha256
from itertools import pairwise

from pydantic import BaseModel, ConfigDict, Field, model_validator
from spacy.vocab import Vocab

from corpus_structure.ingest.annotation_views import AnnotationView, annotation_view
from corpus_structure.ingest.annotations import AnnotationProduct, TokenAnnotation
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_contexts import NativeSourceContext, NativeSourcePin
from corpus_structure.semantic.types import PreparedRelease

from .annotation_rules import (
    AnnotationRule,
    AnnotationRuleMatch,
    LocatedRole,
    PreparedAnnotationRules,
)
from .pm2_products import CueView, FrameView, ParserProducts
from .pm2_source import MappedSource, PM2TokenMap, SourceMapSegment
from .record_assembly import LiteralSpan, NativeRecordGroup, RoleInput
from .record_packs import classification, family_roles, field_kind


class ClassifiedCapture(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(min_length=1)
    cues: tuple[str, ...] = Field(min_length=1)


class RecordCaptureRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract: str = Field(min_length=1)
    match: AnnotationRule
    literals: dict[str, tuple[str, ...]] = Field(min_length=1)
    classifications: dict[str, ClassifiedCapture] = Field(default_factory=dict)

    @model_validator(mode="after")
    def role_bindings(self):
        if self.literals.keys() & self.classifications.keys():
            raise ValueError("a captured role cannot be both literal and classified")
        roles = self.match.bindings.keys()
        inputs = [*self.literals.values(), *(field.cues for field in self.classifications.values())]
        if any(not bindings or len(set(bindings)) != len(bindings) or set(bindings) - roles
               for bindings in inputs):
            raise ValueError("record capture requires distinct declared source bindings")
        return self


def _extent(
    names: tuple[str, ...], roles: Mapping[str, LocatedRole],
    tokens: tuple[TokenAnnotation, ...], offset: int, text: str,
) -> LiteralSpan | None:
    nodes = tuple(node for name in names for node in roles[name].nodes)
    if not nodes or any(left + 1 != right for left, right in pairwise(nodes)):
        return None
    start, end = tokens[nodes[0]].start, tokens[nodes[-1]].end
    return LiteralSpan(start + offset, end + offset, text[start:end])


def hanlp_condition_groups(
    mapping: PM2TokenMap, products: ParserProducts, *, request_digest: str,
) -> tuple[NativeRecordGroup, ...]:
    """Compose a private assertion from a unique, exactly located HanLP condition and host."""
    source_map = mapping.mapping
    context = source_map.context
    if source_map.segments != (SourceMapSegment(0, len(context.text), 0),):
        return ()  # This adapter consumes the exact-copy HanLP character map only.
    pin = NativeSourcePin.from_source(context.primary)

    def spans(key: str) -> tuple[LiteralSpan, ...]:
        location = products.locations.get(key)
        if (
            not isinstance(location, MappedSource)
            or (location.scope_digest, location.source_map_digest, location.input_digest)
            != (source_map.scope_digest, source_map.input_digest, mapping.input_digest)
            or not location.pieces
            or any(piece.source != pin for piece in location.pieces)
        ):
            return ()
        return tuple(LiteralSpan(s.start, s.end, s.literal) for s in location.provider_spans)

    frames = {
        row.key: row
        for row in products.products
        if row.semantic_type == "linguistic.predicate_frame"
    }
    selected = []
    candidate_counts: Counter[str] = Counter()
    for row in products.products:
        if (
            row.semantic_type != "linguistic.qualifier_cue"
            or row.value.get("kind") != "condition"
        ):
            continue
        cue = CueView.model_validate_json(canonical_bytes(row.value))
        candidate_counts.update(cue.candidates)
        if len(cue.candidates) != 1:
            continue
        (host_key,) = cue.candidates
        host = frames.get(host_key)
        if (
            host is None
            or host.value.get("voice") != "active"
            or row.value.get("sentence") != host.value.get("sentence")
            or not {cue.location, cue.marker, host_key} <= set(row.members)
        ):
            continue
        frame = FrameView.model_validate_json(canonical_bytes(host.value))
        subject = [a.location for a in frame.dependency_arguments if a.role == "nsubj"]
        object_ = [a.location for a in frame.dependency_arguments if a.role == "obj"]
        if len(subject) != 1 or len(object_) != 1:
            continue
        locations = (subject[0], frame.predicate, object_[0], cue.location)
        if not {subject[0], frame.predicate, object_[0]} <= set(host.members):
            continue
        fields = tuple(spans(key) for key in locations)
        marker = spans(cue.marker)
        if any(not field for field in fields) or not marker or any(
            not any(start.start <= part.start < part.end <= start.end for start in fields[-1])
            for part in marker
        ):
            continue
        ordered = sorted((span.start, span.end) for field in fields for span in field)
        if any(left[1] > right[0] for left, right in pairwise(ordered)):
            continue
        selected.append((host_key, NativeRecordGroup(
            tuple(RoleInput(role, spans=field) for role, field in zip(
                ("subject", "predicate", "object", "condition"), fields, strict=True,
            )),
            "one HanLP condition cue and its uniquely located active host",
            (
                "source-parser-input:" + mapping.input_digest,
                "source-parser-request:" + request_digest,
                "source-parser-products:"
                + sha256(canonical_bytes([asdict(row), asdict(host)])).hexdigest(),
            ),
        )))
    return tuple(group for key, group in selected if candidate_counts[key] == 1)


class SourceRecordCapture:
    """Reuse retained token/dependency columns and the released record field vocabulary."""

    def __init__(
        self, prepared: PreparedRelease, vocab: Vocab, rules: tuple[RecordCaptureRule, ...]
    ):
        self._rules = {(r.match.rule, r.match.variant): r for r in rules}
        self._digests = {
            key: sha256(canonical_bytes(rule.model_dump(mode="json"))).hexdigest()
            for key, rule in self._rules.items()
        }
        for rule in rules:
            _, declared = family_roles(prepared, rule.contract)
            fields = {field.name: field for field in declared}
            if (rule.literals.keys() | rule.classifications.keys()) - fields.keys():
                raise ValueError("source capture names an unreleased role")
            if any(field_kind(prepared, fields[name]) != "literal" for name in rule.literals):
                raise ValueError("source capture literal must target a released literal role")
            for name, binding in rule.classifications.items():
                field = fields[name]
                if (
                    field_kind(prepared, field) != "classified"
                    or binding.label not in classification(prepared, field)[1]
                ):
                    raise ValueError("source capture classification must use a released label")
        self._matcher = PreparedAnnotationRules(vocab, rules=tuple(r.match for r in rules))
        self._matches: dict[str, tuple[AnnotationRuleMatch, ...]] = {}
        self._contracts = {rule.contract for rule in rules}

    def capture(
        self, context: NativeSourceContext, contract: str,
        blocks: tuple[AnnotationProduct, ...], start: int, end: int,
    ) -> tuple[NativeRecordGroup, ...]:
        if contract not in self._contracts:
            return ()
        return tuple(
            result
            for block in blocks
            if block.block_start < end and block.block_end > start
            for result in self.candidates(block, context, contract, start, end)
        )

    def candidates(
        self, block: AnnotationProduct, context: NativeSourceContext, contract: str,
        start: int, end: int,
    ) -> tuple[NativeRecordGroup, ...]:
        """Only exact, ordered spans inside one inspected primary-source sentence may bind."""
        from .assertion_qualification import _sentence_model_start

        pin = NativeSourcePin.from_source(context.primary)
        if block.source != pin:
            return ()
        if block.dependency_digest not in self._matches:
            text = context.primary.text[block.block_start : block.block_end]
            view: AnnotationView = annotation_view(block, text, self._matcher.vocab, required=())
            self._matches[block.dependency_digest] = self._matcher.match(view).matches
        candidates = []
        for match in self._matches[block.dependency_digest]:
            key = (match.rule, match.variant)
            rule = self._rules[key]
            if rule.contract != contract or match.negation_extents:
                continue
            roles = {role.role: role for role in match.roles}
            if any(role.status != "complete" for role in roles.values()):
                continue
            tokens = block.tokens
            nodes = (*match.nodes, *(i for role in roles.values() for i in role.nodes))
            if any(tokens[node].role != "prose" for node in nodes):
                continue
            owned_sentences = {tokens[node].sentence for node in nodes}
            if len(owned_sentences) != 1 or None in owned_sentences:
                continue
            (sentence_index,) = owned_sentences
            assert sentence_index is not None
            sentence = block.sentences[sentence_index]
            if not start <= sentence.start < sentence.end <= end:
                continue
            model_start = _sentence_model_start(context, pin, sentence)
            if model_start is None:
                continue
            offset = model_start - sentence.start

            fields = []
            for name, bindings in rule.literals.items():
                literal = _extent(bindings, roles, tokens, offset, context.primary.text)
                if literal is None:
                    break
                fields.append(RoleInput(name, spans=(literal,)))
            else:
                for name, binding in rule.classifications.items():
                    cue = _extent(binding.cues, roles, tokens, offset, context.primary.text)
                    if cue is None:
                        break
                    fields.append(RoleInput(
                        name, label=binding.label, cues=(cue,),
                        reason="explicit source cue in the matched dependency construction",
                    ))
                else:
                    candidates.append(NativeRecordGroup(
                        tuple(fields),
                        "exact primary source spans in one declared annotation construction",
                        (
                            "annotation:" + match.dependency_digest,
                            "source-record-capture:" + self._digests[key],
                        ),
                    ))
        return tuple(candidates)
