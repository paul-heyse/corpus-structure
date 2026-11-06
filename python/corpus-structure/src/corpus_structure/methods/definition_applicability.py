"""Located target extraction and separately justified usage applicability.

The extraction task retains target-local products independently of downstream
linking. Neither returned model attributes nor deterministic compatibility confer
independent assessment or publication standing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from types import SimpleNamespace
from typing import Any, Literal, Self

from pydantic import Field, JsonValue, RootModel, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.methods.annotation_rules import AnnotationRule
from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile, GlinerRefused
from corpus_structure.methods.gliner_worker import GlinerWorker, GlinerWorkerError
from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import (
    ApplicabilityPremise,
    DefinitionComponentsProduct,
    DefinitionProduct,
    DefinitionStage,
    LocatedDefinitionComponent,
    LocatedDefinitionSpan,
    RetainedComponentRef,
    StructuralDefinitionReading,
    StructuralInput,
    StructuralPassage,
    StructuralProductReport,
    StructuralValue,
    definition_component,
)


class DefinitionComponentsConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    target_ids: tuple[str, ...] = ()
    profile: GlinerProfile | None = None
    term_entity: str = Field(default="defined term or expression", min_length=1)
    content_entity: str = Field(default="defining text or formula", min_length=1)
    attachment_relation: str = Field(default="term is defined or explained by", min_length=1)
    threshold: float = Field(default=0.5, gt=0, lt=1)
    term_role: str = Field(default="defined_term", min_length=1)
    content_role: str = Field(default="defining_content", min_length=1)
    use_named_candidates: bool = True
    use_model: bool = True
    annotation_rules: tuple[AnnotationRule, ...] = ()

    @model_validator(mode="after")
    def bound_inputs(self) -> Self:
        if self.inputs is None:
            if self.target_ids or self.profile or self.structural_input_digest:
                raise ValueError("absent definition extraction cannot carry partial inputs")
            return self
        if (self.use_model and self.profile is None) or self.structural_input_digest != self.inputs.identity:
            raise ValueError("definition extraction requires selected producer inputs and exact input digest")
        if not self.use_model and (self.profile is not None or not self.use_named_candidates):
            raise ValueError("linguistic-only extraction requires named candidates and no model profile")
        passages = {p.passage_id for p in self.inputs.passages}
        if (
            not self.target_ids
            or len(set(self.target_ids)) != len(self.target_ids)
            or not set(self.target_ids) <= passages
        ):
            raise ValueError("definition targets must be unique selected passages")
        if self.term_entity == self.content_entity:
            raise ValueError("term and defining content need distinct entity roles")
        return self


def definition_pack(release: str, cfg: DefinitionComponentsConfig) -> GlinerPack:
    return GlinerPack.from_declaration(
        release,
        {
            "entities": [cfg.term_entity, cfg.content_entity],
            "entity_attributes": {
                "interpretation": {
                    "labels": ["definition", "explanation", "unresolved"],
                    "applies_to": [cfg.term_entity],
                    "qualify_labels": True,
                }
            },
            "relations": [cfg.attachment_relation],
        },
        version="native-local-v1",
    )


def _located(passage: StructuralPassage, raw: Any) -> LocatedDefinitionSpan:
    if not isinstance(raw, dict):
        raise GlinerRefused("located definition endpoint must be an object")
    start, end, text = raw.get("start"), raw.get("end"), raw.get("text")
    if (
        type(start) is not int
        or type(end) is not int
        or not isinstance(text, str)
        or not 0 <= start < end <= len(passage.text)
        or passage.text[start:end] != text
    ):
        raise GlinerRefused("definition endpoint differs from exact original input slice")
    return LocatedDefinitionSpan(
        passage_id=passage.passage_id,
        start=passage.start + start,
        end=passage.start + end,
        text=text,
    )


def decode_definition_components(
    raw: Any, passage: StructuralPassage, cfg: DefinitionComponentsConfig
) -> tuple[LocatedDefinitionComponent, ...]:
    """Require both independently located endpoint roles and a returned attachment.

    Equal strings never reconcile endpoints; the complete source interval does.
    Unattached decoded entities stay in the immutable raw report, not invented edges.
    """
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("entities"), dict)
        or not isinstance(raw.get("relation_extraction"), dict)
    ):
        raise GlinerRefused("located extraction did not return declared entity/relation channels")
    entities = raw["entities"]
    term_spans = {}
    for term in entities.get(cfg.term_entity, ()):
        span = _located(passage, term)
        interpretation = term.get("interpretation")
        if isinstance(interpretation, dict):
            interpretation = interpretation.get("label")
        if interpretation not in {"definition", "explanation", "unresolved"}:
            raise GlinerRefused("decoded term has no supported span-conditioned interpretation")
        term_spans[span.identity] = (span, interpretation)
    content_spans = {
        _located(passage, c).identity: _located(passage, c)
        for c in entities.get(cfg.content_entity, ())
    }
    components = {}
    for relation in raw["relation_extraction"].get(cfg.attachment_relation, ()):
        if not isinstance(relation, dict):
            raise GlinerRefused("attachment has no located endpoints")
        term, content = (
            _located(passage, relation.get("head")),
            _located(passage, relation.get("tail")),
        )
        if term.identity not in term_spans or content.identity not in content_spans:
            raise GlinerRefused("attachment endpoints lack the declared decoded roles")
        component = definition_component(
            term=term,
            content=content,
            interpretation=term_spans[term.identity][1],
            basis="model_reading",
            scope=passage.scope,
            effective_version=passage.effective_version,
            evidence=(passage.passage_id,),
            reason=(
                "Target-local decoded span roles and directed attachment; "
                "independent support unassessed."
            ),
        )
        components[component.component_id] = component
    return tuple(components[key] for key in sorted(components))


def located_entity_count(raw, passage, cfg):
    """Count actual source-validated entity proposals independently of attachments."""
    if not isinstance(raw, dict) or not isinstance(raw.get("entities"), dict):
        raise GlinerRefused("located extraction returned no declared entity channel")
    located = set()
    for role, values in raw["entities"].items():
        if role not in {cfg.term_entity, cfg.content_entity} or not isinstance(values, list):
            raise GlinerRefused("located extraction returned an undeclared entity population")
        for value in values:
            located.add((role, _located(passage, value).identity))
    return len(located)


def components_from_named_matches(
    passage: StructuralPassage, matches, *, term_role: str, content_role: str
) -> tuple[LocatedDefinitionComponent, ...]:
    """Consume WCE03 named role expansions; never infer a role from node order.

    Only exact contiguous available roles can form this attachment. Raw matches,
    alternatives and discontinuous roles remain retained in their source producer.
    """
    components = {}
    for match in matches:
        if match.negation_extents:
            continue
        roles = {role.role: role for role in match.roles}
        selected = []
        for name in (term_role, content_role):
            role = roles.get(name)
            if (
                role is None
                or role.status != "complete"
                or not role.extents
                or role.nodes != tuple(range(role.nodes[0], role.nodes[-1] + 1))
            ):
                break
            start, end = role.extents[0][0], role.extents[-1][1]
            if not passage.start <= start < end <= passage.end:
                break
            selected.append(
                LocatedDefinitionSpan(
                    passage_id=passage.passage_id,
                    start=start,
                    end=end,
                    text=passage.text[start - passage.start : end - passage.start],
                )
            )
        if len(selected) != 2:
            continue
        component = definition_component(
            term=selected[0],
            content=selected[1],
            interpretation="definition",
            basis="matched_cue",
            scope=passage.scope,
            effective_version=passage.effective_version,
            evidence=(passage.passage_id,),
            reason=(
                f"Named rule {match.rule}/{match.variant} binds explicit "
                f"{term_role}/{content_role} roles; semantic attachment remains "
                "independently unassessed."
            ),
        )
        components[component.component_id] = component
    return tuple(components[key] for key in sorted(components))


def components_from_following_display(passage, matches, display_spans, *, term_role):
    """Join an explicit named following-content cue to its adjacent native display.

    Source-owned display geometry supplies the defining element, not a model score.
    Only punctuation/whitespace may separate the cue from that exact element.
    """
    found = []
    for match in matches:
        if match.negation_extents:
            continue
        roles = {role.role: role for role in match.roles}
        term = roles.get(term_role)
        cue = roles.get("following_content_cue")
        if (
            term is None
            or cue is None
            or term.status != "complete"
            or cue.status != "complete"
            or not term.extents
            or not cue.extents
        ):
            continue
        if term.nodes != tuple(range(term.nodes[0], term.nodes[-1] + 1)):
            continue
        term_start, term_end = term.extents[0][0], term.extents[-1][1]
        cue_end = cue.extents[-1][1]
        if not passage.start <= term_start < term_end <= cue_end <= passage.end:
            continue
        for start, end in sorted(set(display_spans)):
            if not cue_end <= start < end <= passage.end:
                continue
            gap = passage.text[cue_end - passage.start : start - passage.start]
            if any(character not in ": \t\r\n" for character in gap):
                continue

            def span(a, b):
                return LocatedDefinitionSpan(
                    passage_id=passage.passage_id,
                    start=a,
                    end=b,
                    text=passage.text[a - passage.start : b - passage.start],
                )

            found.append(
                definition_component(
                    term=span(term_start, term_end),
                    content=span(start, end),
                    interpretation="definition",
                    basis="native_geometry",
                    scope=passage.scope,
                    effective_version=passage.effective_version,
                    evidence=(passage.passage_id,),
                    reason=(
                        f"Named rule {match.rule}/{match.variant} following-content cue "
                        "joined to the adjacent source-owned display element; "
                        "semantic support unassessed."
                    ),
                )
            )
            break
    return tuple(found)


@dataclass(frozen=True)
class NamedDefinitionResult:
    components: tuple[LocatedDefinitionComponent, ...]
    available: bool
    operations: tuple[dict[str, Any], ...]
    reason: str


def retained_annotation_components(reader, inputs, passage, cfg, *, retained=None):
    from spacy.lang.en import English

    from corpus_structure.ingest.annotation_views import annotation_view
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.annotation_rules import AnnotationRule, PreparedAnnotationRules

    if retained is None:
        retained = reader.structural_source_annotations(
            inputs, passage.source_ref, AnnotationProfile(SentenceConfig(exclude=("ner",)))
        )
    frame, products, errors = retained.source, retained.annotations, retained.errors
    if errors:
        return NamedDefinitionResult((), False, (), "; ".join(errors))
    rules = tuple(AnnotationRule.model_validate(rule) for rule in cfg.annotation_rules)
    prepared = PreparedAnnotationRules(English().vocab, rules=rules)
    found, operations = [], []
    for product in products:
        if product.block_start >= passage.end or product.block_end <= passage.start:
            continue
        restored = annotation_view(
            product,
            frame.text[product.block_start : product.block_end],
            prepared.vocab,
            required=(),
        )
        result = prepared.match(restored)
        matches = result.matches
        for rule, variant, state in result.availability:
            selected = [
                match for match in matches if (match.rule, match.variant) == (rule, variant)
            ]
            operations.append(
                dict(
                    passage_id=passage.passage_id,
                    source_ref=passage.source_ref,
                    annotation_task_id=retained.annotation_task_id,
                    block_id=product.block_id,
                    rule=rule,
                    variant=variant,
                    availability=state,
                    matched_count=len(selected),
                    negation_extents=[extent for match in selected for extent in match.negation_extents],
                    role_outcomes=[
                        dict(role=role.role, outcome=role.status)
                        for match in selected
                        for role in match.roles
                    ],
                )
            )
        found.extend(
            components_from_named_matches(
                passage, matches, term_role=cfg.term_role, content_role=cfg.content_role
            )
        )
        display_spans = tuple(
            span
            for retained in products
            for span in retained.display_spans
            if passage.start <= span[0] < span[1] <= passage.end
        )
        found.extend(
            components_from_following_display(
                passage, matches, display_spans, term_role=cfg.term_role
            )
        )
    available = any(operation["availability"] == "available" for operation in operations)
    return NamedDefinitionResult(
        tuple(found),
        available,
        tuple(operations),
        "Current named rules executed on authenticated retained annotation columns."
        if available
        else ("No selected retained linguistic rule operation is executable; "
              "no source absence is established."),
    )


def retained_named_components(
    reader, inputs: StructuralInput, passage: StructuralPassage, cfg: DefinitionComponentsConfig
):
    """Consume the selected actual WCE03 producer, never caller-supplied role labels."""
    from corpus_structure.semantic.observations import source_python

    source = next(ref for ref in inputs.sources if ref.identity == passage.source_ref)
    result = reader.source_result(source.source_view_id, "extract.m1_candidates")
    if result is None:
        return NamedDefinitionResult((), False, (), "selected named-candidate producer unavailable")
    matches = []
    for row in result.get("contributions", ()):
        if not row.get("semantic_type", "").startswith("source_rule."):
            continue
        pin = row.get("pin", {})
        expected = {
            "source_view_id": source.source_view_id,
            "native_product_task_id": source.native_task_id,
            "product_key": source.native_product_key,
            "product_digest": source.native_content_digest,
            "projection_digest": source.projection_digest,
            "recipe_digest": source.recipe_digest,
        }
        if any(pin.get(key) != value for key, value in expected.items()):
            raise ValueError("named candidate differs from original source custody")
        match = source_python(row["value"])
        if "negation_extents" not in match:
            return NamedDefinitionResult((), False, (), "Selected named candidates lack current polarity evidence.")
        if match.get("protocol") != "named-annotation-match-2":
            raise ValueError("named candidate requires current role contract")
        roles = tuple(
            SimpleNamespace(
                **{
                    **role,
                    "nodes": tuple(role["nodes"]),
                    "extents": tuple(tuple(v) for v in role["extents"]),
                }
            )
            for role in match["roles"]
        )
        matches.append(SimpleNamespace(**{**match, "roles": roles}))
    operations = tuple(dict(operation) for operation in result.get("contribution_operations", ()))
    available = any(
        operation.get("outcome") in {"succeeded", "empty", "limited"} for operation in operations
    )
    return NamedDefinitionResult(
        components_from_named_matches(
            passage, matches, term_role=cfg.term_role, content_role=cfg.content_role
        ),
        available,
        operations,
        "Consumed selected source-authenticated named candidates.",
    )


_DEFINITION_WINDOW_CHARS = 1536
_DEFINITION_WINDOW_OVERLAP = 256
_DEFINITION_MAX_WINDOWS = 64


def definition_windows(passage: StructuralPassage, cfg: DefinitionComponentsConfig):
    """Bound model contexts while preserving original offsets and overlap provenance."""
    # Operational resource choices belong to the archived runtime, not the semantic
    # configuration ABI. Tuning these bounds does not redefine the output data model.
    max_chars = (
        min(_DEFINITION_WINDOW_CHARS, max(1, cfg.profile.max_input_bytes // 4))
        if cfg.profile is not None
        else _DEFINITION_WINDOW_CHARS
    )
    overlap = min(_DEFINITION_WINDOW_OVERLAP, max_chars // 4)
    start = 0
    windows = []
    while start < len(passage.text) and len(windows) < _DEFINITION_MAX_WINDOWS:
        end = min(len(passage.text), start + max_chars)
        if end < len(passage.text):
            boundary = passage.text.rfind(" ", start + max_chars // 2, end)
            if boundary > start:
                end = boundary
        windows.append(
            StructuralPassage(
                passage_id=passage.passage_id,
                source_ref=passage.source_ref,
                start=passage.start + start,
                end=passage.start + end,
                text=passage.text[start:end],
                scope=passage.scope,
                effective_version=passage.effective_version,
                parent=passage.parent,
            )
        )
        if end == len(passage.text):
            break
        start = max(start + 1, end - overlap)
        while start < end and not passage.text[start - 1].isspace():
            start += 1
    return tuple(windows)


class DefinitionComponentsMethod:
    name = "structure.definition_components"
    version = "4"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.ENCODER
    confidence_source = None
    Config = DefinitionComponentsConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def __init__(self):
        self._worker: GlinerWorker | None = None

    def close(self):
        if self._worker is not None:
            self._worker.close()
        self._worker = None

    def select(self, run, cfg):
        return (
            (UnitRef(TaskUnitType.RUN, unit_key="definition-components:" + cfg.inputs.identity),)
            if cfg.inputs is not None
            else ()
        )

    def input_digest(self, unit, cfg):
        return Digest(canonical_bytes(cfg.model_dump(mode="json", exclude_none=True)))

    def run(self, units, cfg, ctx):
        if cfg.inputs is None or (cfg.use_model and cfg.profile is None):
            raise ValueError("definition extraction needs complete configured inputs")
        ctx.check_active()
        ctx.reader.validate_structural_inputs(cfg.inputs)
        pack = definition_pack(ctx.reader.prepared.release_id, cfg) if cfg.use_model else None
        if cfg.use_model:
            if cfg.profile is None:
                raise GlinerRefused("model execution requires its exact declared profile")
            if self._worker is None:
                self._worker = GlinerWorker(cfg.profile)
            elif self._worker.profile.fingerprint != cfg.profile.fingerprint:
                raise GlinerRefused("definition worker cannot switch model profile")
        passages = {p.passage_id: p for p in cfg.inputs.passages}
        components, stages, raw_reports = [], [], []
        named_rule_operations = []
        annotation_sources = {}
        if cfg.use_named_candidates and cfg.annotation_rules:
            from corpus_structure.ingest.annotations import AnnotationProfile
            from corpus_structure.ingest.sentences import SentenceConfig

            for source_ref in dict.fromkeys(passages[p].source_ref for p in cfg.target_ids):
                annotation_sources[source_ref] = ctx.reader.structural_source_annotations(
                    cfg.inputs, source_ref, AnnotationProfile(SentenceConfig(exclude=("ner",)))
                )
        # Detach all selected source products before the owned encoder starts.
        if cfg.use_named_candidates:
            for passage_id in cfg.target_ids:
                named = (
                    retained_annotation_components(
                        ctx.reader,
                        cfg.inputs,
                        passages[passage_id],
                        cfg,
                        retained=annotation_sources[passages[passage_id].source_ref],
                    )
                    if cfg.annotation_rules
                    else retained_named_components(
                        ctx.reader, cfg.inputs, passages[passage_id], cfg
                    )
                )
                components.extend(named.components)
                named_rule_operations.extend(named.operations)
                stages.append(
                    DefinitionStage(
                        passage_id=passage_id,
                        operation="attachment",
                        outcome="succeeded"
                        if named.components
                        else "empty"
                        if named.available
                        else "unavailable",
                        reason=named.reason,
                    )
                )
        if not cfg.use_model:
            stages.extend(DefinitionStage(passage_id=passage_id,operation="located_extraction",outcome="not_run",reason="Explicit registered linguistic-only composition; no model extraction requested.") for passage_id in cfg.target_ids)
        for passage_id in cfg.target_ids if cfg.use_model else ():
            if self._worker is None or pack is None:
                raise GlinerRefused("model execution owner is unavailable")
            passage = passages[passage_id]
            windows = definition_windows(passage, cfg)
            for window in windows:
                ctx.check_active()
                request = GlinerInput(
                    "definition-target:" + window.identity, window.identity, window.text
                )
                try:
                    (reply,) = self._worker.extract(
                        pack,
                        (request,),
                        threshold=cfg.threshold,
                        overlap_policy="flat",
                        check_active=ctx.check_active,
                    )
                    raw_reports.append(
                        dict(
                            passage_id=passage_id,
                            window_start=window.start,
                            window_end=window.end,
                            **asdict(reply),
                        )
                    )
                    locations = located_entity_count(reply.raw, window, cfg)
                except (
                    GlinerRefused,
                    GlinerWorkerError,
                    ValueError,
                    TimeoutError,
                    OSError,
                ) as error:
                    stages.append(
                        DefinitionStage(
                            passage_id=passage_id,
                            operation="located_extraction",
                            outcome="failed",
                            reason=(
                                f"Window {window.start}:{window.end}: "
                                f"{type(error).__name__}: {error}"
                            ),
                        )
                    )
                    stages.append(
                        DefinitionStage(
                            passage_id=passage_id,
                            operation="attachment",
                            outcome="not_run",
                            reason=(
                                f"Window {window.start}:{window.end}: "
                                "located extraction unavailable."
                            ),
                        )
                    )
                    continue
                raw_reports[-1]["located_proposal_count"] = locations
                stages.append(
                    DefinitionStage(
                        passage_id=passage_id,
                        operation="located_extraction",
                        outcome="succeeded" if locations else "empty",
                        reason=(
                            f"Window {window.start}:{window.end}: {locations} "
                            "source-validated entity proposals retained; "
                            "role/support remains unassessed."
                        ),
                    )
                )
                try:
                    decoded = decode_definition_components(reply.raw, window, cfg)
                except (GlinerRefused, ValueError) as error:
                    stages.append(
                        DefinitionStage(
                            passage_id=passage_id,
                            operation="attachment",
                            outcome="failed",
                            reason=(
                                f"Window {window.start}:{window.end}: "
                                f"{type(error).__name__}: {error}; located proposals retained."
                            ),
                        )
                    )
                    continue
                components.extend(decoded)
                stages.append(
                    DefinitionStage(
                        passage_id=passage_id,
                        operation="attachment",
                        outcome="succeeded" if decoded else "empty",
                        reason=(
                            f"Window {window.start}:{window.end}: {len(decoded)} "
                            "decoded role-and-attachment components; "
                            "no absence or semantic correctness claim."
                        ),
                    )
                )
            if windows and windows[-1].end < passage.end:
                stages.append(
                    DefinitionStage(
                        passage_id=passage_id,
                        operation="located_extraction",
                        outcome="not_run",
                        reason=(
                            "Model window bound reached; original source tail "
                            f"{windows[-1].end}:{passage.end} uninspected by this producer."
                        ),
                    )
                )
        components = list({component.component_id: component for component in components}.values())
        ctx.check_active()
        report = StructuralProductReport(
            kind="definition_components",
            inputs=cfg.inputs,
            definition_components=DefinitionComponentsProduct(
                components=tuple(components), stages=tuple(stages)
            ),
        )
        detail = (
            RootModel[dict[str, JsonValue]]
            .model_validate_json(
                canonical_bytes(
                    dict(
                        version="located-definition-extraction-1",
                        raw_reports=raw_reports,
                        named_rule_operations=named_rule_operations,
                        annotation_inputs=[
                            dict(
                                source_ref=source_ref,
                                task_id=retained.annotation_task_id,
                                input_hash=retained.annotation_input_hash,
                                errors=retained.errors,
                            )
                            for source_ref, retained in annotation_sources.items()
                        ],
                        pack_fingerprint=pack.fingerprint if pack else None,
                        schema_declaration=pack.declaration_json if pack else None,
                        profile_fingerprint=cfg.profile.fingerprint if cfg.profile else None,
                        profile=cfg.model_dump(mode="json")["profile"],
                    )
                )
            )
            .root
        )
        return tuple(
            UnitResult(
                ref=unit.ref,
                outcome=ObservationOutcome.PRODUCED,
                structural_product=report.model_dump(mode="json"),
                parse_detail=detail,
            )
            for unit in units
        )


class ApplicabilityCandidate(StructuralValue):
    target_id: str = Field(min_length=1)
    reference: RetainedComponentRef
    link_ref: RetainedRelationshipDecisionRef
    component: LocatedDefinitionComponent
    premises: tuple[ApplicabilityPremise, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def component_binding(self) -> Self:
        if self.reference.component_id != self.component.component_id:
            raise ValueError("applicability candidate substitutes its component")
        return self


class DefinitionApplicabilityConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    usage_id: str | None = None
    selection_refs: tuple[RetainedRelationshipDecisionRef, ...] = ()
    applicability_scope: Literal["contextual_usage", "defining_occurrence"] = "contextual_usage"

    @model_validator(mode="after")
    def bound_inputs(self) -> Self:
        if self.inputs is None:
            if self.structural_input_digest or self.usage_id or self.selection_refs:
                raise ValueError("absent applicability cannot carry partial inputs")
            return self
        if (
            self.structural_input_digest != self.inputs.identity
            or not self.selection_refs
            or self.usage_id not in {p.passage_id for p in self.inputs.passages}
        ):
            raise ValueError("applicability requires exact inputs and usage/candidate selection")
        if (
            self.applicability_scope == "defining_occurrence"
            and self.inputs.policy_id != "definition-introduction-1"
        ):
            raise ValueError("defining-occurrence scope requires its declared introduction policy")
        return self


def is_defining_occurrence(inputs, usage, component, relation):
    """An introduction is not a transfer to another occurrence or parameter context."""
    term = component.term
    target = next(p for p in inputs.passages if p.passage_id == term.passage_id)
    return (
        relation == "defined-by"
        and usage.source_ref == target.source_ref
        and (usage.start, usage.end, usage.text) == (term.start, term.end, term.text)
        and usage.parent == target.parent
        and usage.scope == component.scope
        and usage.effective_version == component.effective_version
    )


def assess_applicability(
    inputs: StructuralInput,
    usage_id: str,
    candidate: ApplicabilityCandidate,
    *,
    defining_occurrence: bool = False,
) -> StructuralDefinitionReading:
    usage = next(p for p in inputs.passages if p.passage_id == usage_id)
    component = candidate.component
    dimensions = {p.dimension for p in candidate.premises}
    if dimensions != {"sense", "parameterization", "convention"}:
        raise ValueError(
            "usage binding requires explicit sense, parameterization and convention premises"
        )
    target = next(p for p in inputs.passages if p.passage_id == component.term.passage_id)
    same_introduction = defining_occurrence and is_defining_occurrence(
        inputs, usage, component, "defined-by"
    )
    parent_state: Literal["compatible", "incompatible", "unknown", "inapplicable"] = (
        "inapplicable"
        if same_introduction and usage.parent is None and target.parent is None
        else "unknown"
        if usage.parent is None or target.parent is None
        else "compatible"
        if usage.parent == target.parent
        else "incompatible"
    )
    premises = (
        *candidate.premises,
        ApplicabilityPremise(
            dimension="parent",
            state=parent_state,
            evidence=(usage_id, component.term.passage_id),
            reason="Compare declared parent contexts; missing transfer premises remain unknown.",
        ),
        ApplicabilityPremise(
            dimension="scope",
            state="compatible" if usage.scope == component.scope else "incompatible",
            evidence=(usage_id, component.term.passage_id),
            reason="Compare original usage and component scope.",
        ),
        ApplicabilityPremise(
            dimension="version",
            state="unknown"
            if usage.effective_version is None and component.effective_version is not None
            else (
                "compatible"
                if usage.effective_version == component.effective_version
                else "incompatible"
            ),
            evidence=(usage_id, component.term.passage_id),
            reason="Compare declared original effective versions; unknown is not compatible.",
        ),
    )
    states = {p.state for p in premises}
    if "incompatible" in states:
        outcome = "incompatible"
    elif "unknown" in states or component.interpretation == "unresolved":
        outcome = "unresolved"
    else:
        outcome = (
            "applicable_definition"
            if component.interpretation == "definition"
            else "applicable_explanation"
        )
    return StructuralDefinitionReading(
        target_id=candidate.target_id,
        component_ref=candidate.reference,
        link_ref=candidate.link_ref,
        component=component,
        outcome=outcome,
        evidence=(usage_id, component.term.passage_id, component.content.passage_id),
        premises=premises,
        reason=(
            "Applicability derived from explicit usage binding and compatibility "
            "premises; independent support unassessed."
        ),
    )


class DefinitionApplicabilityMethod:
    name = "structure.definitions"
    version = "2"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = DefinitionApplicabilityConfig
    resources = Resources()

    def select(self, run, cfg):
        return (
            (
                UnitRef(
                    TaskUnitType.RUN,
                    unit_key="definition-applicability:" + cfg.inputs.identity + ":" + cfg.usage_id,
                ),
            )
            if cfg.inputs is not None
            else ()
        )

    def input_digest(self, unit, cfg):
        return Digest(canonical_bytes(cfg.model_dump(mode="json", exclude_none=True)))

    def run(self, units, cfg, ctx):
        if cfg.inputs is None or cfg.usage_id is None or not cfg.selection_refs:
            raise ValueError("applicability requires selected retained relationship bindings")
        ctx.check_active()
        ctx.reader.validate_structural_inputs(cfg.inputs)
        usage = next(p for p in cfg.inputs.passages if p.passage_id == cfg.usage_id)
        readings, candidate_lists = [], set()
        for reference in cfg.selection_refs:
            ctx.check_active()
            selected = ctx.reader.retained_relationship_decision(reference)
            decision, edge, occurrence = (
                selected["decision"],
                selected["edge"],
                selected["occurrence"],
            )
            if edge["relation"] not in {"denotes", "defined-by"}:
                raise ValueError(
                    "applicability requires a selected usage-sense or defining relationship"
                )
            if (
                decision["scope"] != usage.scope
                or decision.get("effective_version") != usage.effective_version
            ):
                raise ValueError("selected usage relationship differs from scope/version")
            _validate_usage_occurrence(ctx.reader, cfg.inputs, usage, occurrence)
            target = selected["component_target"]
            component_ref = RetainedComponentRef.model_validate(target["reference"])
            component = LocatedDefinitionComponent.model_validate(
                ctx.reader.resolve_definition_component(component_ref)
            )
            from corpus_structure.methods.contextual_embeddings import identity

            if component_ref.component_id not in edge["member_target_ids"] or edge[
                "target_id"
            ] != identity("semantic-target", selected["semantic_target"]):
                raise ValueError(
                    "selected relationship substitutes its semantic target or proof carrier"
                )
            introduction = (
                cfg.applicability_scope == "defining_occurrence"
                and is_defining_occurrence(cfg.inputs, usage, component, edge["relation"])
            )
            candidate_lists.add(decision["candidate_list_id"])
            candidate = ApplicabilityCandidate(
                target_id=edge["target_id"],
                reference=component_ref,
                link_ref=reference,
                component=component,
                premises=(
                    ApplicabilityPremise(
                        dimension="sense",
                        state="compatible",
                        evidence=(usage.passage_id, component.term.passage_id),
                        reason=(
                            "Actual selected usage relationship; "
                            "independent semantic support remains separate."
                        ),
                    ),
                    ApplicabilityPremise(
                        dimension="parameterization",
                        state="inapplicable" if introduction else "unknown",
                        evidence=(usage.passage_id, component.term.passage_id),
                        reason=(
                            "Same defining occurrence under the introduction policy; "
                            "no parameter transfer is asserted."
                            if introduction
                            else "No authenticated parameter correspondence has been established."
                        ),
                    ),
                    ApplicabilityPremise(
                        dimension="convention",
                        state="inapplicable" if introduction else "unknown",
                        evidence=(usage.passage_id, component.term.passage_id),
                        reason=(
                            "Same defining occurrence under the introduction policy; "
                            "no convention transfer is asserted."
                            if introduction
                            else "No authenticated convention correspondence has been established."
                        ),
                    ),
                ),
            )
            readings.append(
                assess_applicability(
                    cfg.inputs, cfg.usage_id, candidate, defining_occurrence=introduction
                )
            )
        if len(candidate_lists) != 1:
            raise ValueError(
                "applicability bindings must share the exact usage candidate population"
            )
        targets = tuple(dict.fromkeys(r.target_id for r in readings))
        report = StructuralProductReport(
            kind="definition_applicability",
            inputs=cfg.inputs,
            definition=DefinitionProduct(
                usage_id=cfg.usage_id,
                candidate_list_id=next(iter(candidate_lists)),
                eligible_targets=targets,
                candidate_targets=targets,
                readings=tuple(readings),
            ),
        )
        return tuple(
            UnitResult(
                ref=unit.ref,
                outcome=ObservationOutcome.PRODUCED,
                structural_product=report.model_dump(mode="json"),
            )
            for unit in units
        )


def _validate_usage_occurrence(reader, inputs, usage, occurrence):
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import (
        NativeSourceContext,
        SourceSlice,
        evidence_anchor,
    )

    source = next(ref for ref in inputs.sources if ref.identity == usage.source_ref)
    view = reader.source_view(source.source_view_id)
    frame = native_source_frame(view, ())
    if (
        frame.projection_digest != source.projection_digest
        or frame.native_product.content_digest != source.native_content_digest
    ):
        raise ValueError("usage occurrence source differs from original projection")
    context = NativeSourceContext(
        frame,
        (),
        (SourceSlice(source.source_view_id, usage.start, usage.end),),
        "usage occurrence",
        "witnessed-applicability-1",
        "exact selected physical occurrence",
        max_chars=len(usage.text),
        max_pieces=256,
    )
    mapped = tuple(
        evidence_anchor(context, piece, native=True)[0]
        for piece in context.map_span(0, len(usage.text), literal=usage.text, allow_multiple=True)
    )

    def physical(anchor):
        return canonical_bytes(
            {key: anchor[key] for key in ("pin", "pointer", "start", "end", "source_piece")}
        )

    if {physical(anchor) for anchor in mapped} != {
        physical(anchor) for anchor in occurrence["anchors"]
    }:
        raise ValueError("usage passage is not the exact selected physical occurrence")
