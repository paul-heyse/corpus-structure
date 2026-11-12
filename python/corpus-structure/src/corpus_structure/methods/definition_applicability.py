"""Located target extraction and separately justified usage applicability.

The extraction task retains target-local products independently of downstream
linking. Neither returned model attributes nor deterministic compatibility confer
independent assessment or publication standing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import pairwise
from typing import Any, Literal, Self

from pydantic import Field, JsonValue, RootModel, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.methods.annotation_rules import AnnotationRule, AnnotationRuleMatch
from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile, GlinerRefused
from corpus_structure.methods.gliner_worker import GlinerWorker, GlinerWorkerError
from corpus_structure.methods.native_host_clients import HostedGliner
from corpus_structure.methods.predicate_frames import (
    PREDICATE_FRAME_VERSION,
    FrameCue,
    PredicateFrameResult,
    interpretation_recipe,
    predicate_frames,
)
from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import (
    ApplicabilityPremise,
    DefinitionBasisWitness,
    DefinitionComponentsProduct,
    DefinitionProduct,
    DefinitionRoleCandidate,
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
    native_execution_profile: dict[str, Any] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    target_ids: tuple[str, ...] = ()
    profile: GlinerProfile | None = None
    term_entity: str = Field(default="defined term or expression", min_length=1)
    content_entity: str = Field(default="defining text or formula", min_length=1)
    attachment_relation: str = Field(default="term is defined or explained by", min_length=1)
    threshold: float = Field(default=0.5, gt=0, lt=1)
    description_arm: Literal["bare", "described"] = "bare"
    evaluation_overlap: Literal["flat", "nested", "allow"] | None = None
    term_role: str = Field(default="defined_term", min_length=1)
    content_role: str = Field(default="defining_content", min_length=1)
    use_named_candidates: bool = True
    use_model: bool = True
    annotation_rules: tuple[AnnotationRule, ...] = ()
    characterization_layers: tuple[dict, ...] = ()

    @model_validator(mode="after")
    def bound_inputs(self) -> Self:
        if self.inputs is None:
            if self.target_ids or self.profile or self.structural_input_digest:
                raise ValueError("absent definition extraction cannot carry partial inputs")
            return self
        if (
            self.use_model and self.profile is None
        ) or self.structural_input_digest != self.inputs.identity:
            raise ValueError(
                "definition extraction requires selected producer inputs and exact input digest"
            )
        if not self.use_model and (self.profile is not None or not self.use_named_candidates):
            raise ValueError(
                "linguistic-only extraction requires named candidates and no model profile"
            )
        if not self.use_model and (
            self.description_arm != "bare" or self.evaluation_overlap is not None
        ):
            raise ValueError("model experiments require enabled model extraction")
        if self.use_named_candidates and self.annotation_rules and not self.characterization_layers:
            raise ValueError("named definition extraction requires frozen primary layers")
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
    entities: list[str] | dict[str, str] = [cfg.term_entity, cfg.content_entity]
    relations: list[str] | dict[str, str] = [cfg.attachment_relation]
    if cfg.description_arm == "described":
        entities = {
            cfg.term_entity: (
                "The exact term or expression whose meaning is stated, distinct from "
                "neighboring examples, subjects of historical reports, and incidental symbols."
            ),
            cfg.content_entity: (
                "The complete text or formula conveying that meaning, including complements "
                "and restrictions needed to state it."
            ),
        }
        relations = {
            cfg.attachment_relation: (
                "Directed from the exact term occurrence to the text or formula that defines "
                "or explains that occurrence in its local scope."
            ),
        }
    return GlinerPack.from_declaration(
        release,
        {
            "entities": entities,
            "entity_attributes": {
                "interpretation": {
                    "labels": ["definition", "explanation", "unresolved"],
                    "applies_to": [cfg.term_entity],
                    "qualify_labels": True,
                }
            },
            "relations": relations,
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
    raw: Any,
    passage: StructuralPassage,
    cfg: DefinitionComponentsConfig,
    *,
    candidate_errors: list[dict[str, JsonValue]] | None = None,
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

    def rejected(channel: str, index: int, error: ValueError) -> None:
        if candidate_errors is None:
            raise error
        candidate_errors.append(
            dict(channel=channel, index=index, type=type(error).__name__, reason=str(error))
        )

    entities = raw["entities"]
    relations = raw["relation_extraction"].get(cfg.attachment_relation, [])
    if not isinstance(relations, list):
        raise GlinerRefused("declared definition attachment channel is not a candidate list")
    term_spans = {}
    for index, term in enumerate(entities.get(cfg.term_entity, ())):
        try:
            span = _located(passage, term)
            interpretation = term.get("interpretation")
            if isinstance(interpretation, dict):
                interpretation = interpretation.get("label")
            if interpretation not in {"definition", "explanation", "unresolved"}:
                raise GlinerRefused("decoded term has no supported span-conditioned interpretation")
            term_spans[span.identity] = (span, interpretation)
        except ValueError as error:
            rejected("term", index, error)
    content_spans = {}
    for index, content in enumerate(entities.get(cfg.content_entity, ())):
        try:
            span = _located(passage, content)
            content_spans[span.identity] = span
        except ValueError as error:
            rejected("content", index, error)
    components = {}
    for index, relation in enumerate(relations):
        try:
            if not isinstance(relation, dict):
                raise GlinerRefused("attachment has no located endpoints")
            term, content = (
                _located(passage, relation.get("head")),
                _located(passage, relation.get("tail")),
            )
            if term.identity not in term_spans or content.identity not in content_spans:
                raise GlinerRefused("attachment endpoints lack the declared decoded roles")
        except ValueError as error:
            rejected("attachment", index, error)
            continue
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


def located_definition_roles(raw, passage, cfg, *, envelope, errors=None):
    """Read each authenticated entity candidate independently of its group and relation."""
    if not isinstance(raw, dict) or not isinstance(raw.get("entities"), dict):
        raise GlinerRefused("located extraction returned no declared entity channel")
    entities = raw["entities"]
    if set(entities) - {cfg.term_entity, cfg.content_entity} or any(
        not isinstance(values, list) for values in entities.values()
    ):
        raise GlinerRefused("located extraction returned an undeclared entity population")
    candidates = []
    for role, channel in (("term", cfg.term_entity), ("content", cfg.content_entity)):
        for index, value in enumerate(entities.get(channel, ())):
            try:
                span = _located(passage, value)
            except GlinerRefused as error:
                if errors is None:
                    raise
                errors.append(
                    dict(channel=role, index=index, type=type(error).__name__, reason=str(error))
                )
                continue
            candidates.append(
                DefinitionRoleCandidate(
                    role=role,
                    span=span,
                    window_start=passage.start,
                    window_end=passage.end,
                    envelope=envelope,
                    index=index,
                )
            )
    return tuple(candidates)


def located_entity_count(raw, passage, cfg):
    """Count distinct exact proposals without requiring attachment or interpretation."""
    return len(
        {
            (r.role, r.span.identity)
            for r in located_definition_roles(raw, passage, cfg, envelope="count")
        }
    )


type DefinitionDisposition = Literal[
    "supported", "negated", "contrasted", "attributed", "qualified", "unresolved"
]


@dataclass(frozen=True)
class DefinitionScope:
    act_host: int
    act_polarity: Literal["positive", "negative", "unresolved"]
    disposition: DefinitionDisposition
    act_cues: tuple[FrameCue, ...] = ()
    content_cues: tuple[FrameCue, ...] = ()
    probability_subject: tuple[int, int] | None = None
    primary_scope: tuple[Any, ...] = ()


_SCOPE_CUES = frozenset(
    {
        "negation",
        "condition",
        "exception",
        "modality",
        "attribution",
        "contrast",
        "quotation",
        "assumption",
        "example",
        "order",
    }
)
_DEFINITION_SCOPE = interpretation_recipe()["definition_scope"]
_CONTENT_CUES = frozenset(_DEFINITION_SCOPE["content_cues"])
_WITNESS_COLUMNS = frozenset({"DEP", "POS", "SENT_START", "LEMMA", "TAG"})


def definition_scopes(
    matches: tuple[AnnotationRuleMatch, ...],
    result: PredicateFrameResult,
    *,
    content_role: str,
) -> dict[AnnotationRuleMatch, DefinitionScope]:
    """Assess exact predicate ownership before projecting a definition pair."""
    if result.issues:
        # Incomplete primary coverage cannot establish that an act is unqualified.
        return {
            match: DefinitionScope(act.head, "unresolved", "unresolved")
            for match in matches
            if (
                act := next(
                    (role for role in match.roles if role.role in {"defining_cue", "copular_cue"}),
                    None,
                )
            )
            is not None
        }
    by_head: dict[int, dict[FrameCue, None]] = {}
    probability_subjects = {}
    for frame in result.frames:
        head = frame.predicate.tokens[0]
        by_head.setdefault(head, {}).update(
            dict.fromkeys(cue for cue in frame.cues if cue.kind in _SCOPE_CUES)
        )
        if frame.variant == "passive_probability_subject":
            subjects = {
                role.span.extents[0]
                for role in frame.roles
                if role.name == "object"
                and role.status == "located"
                and len(role.span.extents) == 1
            }
            if len(subjects) == 1:
                probability_subjects[head] = next(iter(subjects))
    unowned = tuple(cue for cue in result.unresolved_cues if cue.kind in _SCOPE_CUES)
    for cue in unowned:
        origin = cue.origin
        if origin is not None and origin in by_head:
            by_head[origin][cue] = None
    scopes = {}
    for match in matches:
        roles = {role.role: role for role in match.roles}
        act = roles.get("defining_cue") or roles.get("copular_cue")
        if act is None:
            continue
        if act.status != "complete" or act.head not in by_head:
            scopes[match] = DefinitionScope(act.head, "unresolved", "unresolved")
            continue

        content = roles.get(content_role)
        content_nodes = set(content.nodes) if content else set()
        content_predicate = roles.get("defining_content_predicate")
        scope_guard = roles.get("definition_scope_guard")
        content_heads = content_nodes & by_head.keys()
        if content_predicate is not None:
            content_heads.add(content_predicate.head)
        elif scope_guard is not None:
            # A retained recipe may request the broader defining subtree. Its
            # bounds remain conservative until it names a content predicate.
            content_heads.update(set(scope_guard.nodes) & by_head.keys())
        content_heads.discard(act.head)
        act_cues = tuple(by_head[act.head])
        content_candidates = (
            *(cue for head in sorted(content_heads & by_head.keys()) for cue in by_head[head]),
            *(
                cue
                for cue in unowned
                if cue.basis.tokens and set(cue.basis.tokens) <= content_nodes
            ),
        )
        content_cues = tuple(
            dict.fromkeys(cue for cue in content_candidates if cue not in act_cues)
        )
        act_negation = tuple(cue for cue in act_cues if cue.kind == "negation")
        polarity: Literal["positive", "negative", "unresolved"] = (
            "unresolved"
            if any(cue.status != "located" for cue in act_negation)
            else "negative"
            if act_negation
            else "positive"
        )
        act_kinds = {cue.kind for cue in act_cues}
        disposition: DefinitionDisposition
        if (
            any(cue.status != "located" for cue in (*act_cues, *content_cues))
            or (
                content_predicate is not None
                and (
                    content_predicate.status != "complete" or content_predicate.head not in by_head
                )
            )
            or (scope_guard is not None and scope_guard.status != "complete")
        ):
            disposition = "unresolved"
        elif polarity == "negative":
            disposition = "negated"
        elif "contrast" in act_kinds:
            disposition = "contrasted"
        elif "attribution" in act_kinds:
            disposition = "attributed"
        elif act_cues or any(
            cue.kind not in _CONTENT_CUES or not set(cue.span.tokens) <= content_nodes
            for cue in content_cues
        ):
            # The pair cannot carry a qualification outside its exact content.
            disposition = "qualified"
        else:
            disposition = "supported"
        scopes[match] = DefinitionScope(
            act.head,
            polarity,
            disposition,
            act_cues,
            content_cues,
            probability_subjects.get(act.head),
            tuple(
                dict.fromkeys(
                    [
                        frame.primary_ref
                        for frame in result.frames
                        if frame.predicate.tokens[0] in {act.head, *content_heads}
                        and frame.primary_ref is not None
                    ]
                    + [
                        reference
                        for cue in (*act_cues, *content_cues)
                        for reference in (cue.primary_ref, cue.primary_marker_ref)
                        if reference is not None
                    ]
                )
            ),
        )
    return scopes


def components_from_named_matches(
    passage: StructuralPassage,
    matches: tuple[AnnotationRuleMatch, ...],
    *,
    scopes: Mapping[AnnotationRuleMatch, DefinitionScope],
    term_role: str,
    content_role: str,
    antecedents: Mapping[AnnotationRuleMatch, LocatedDefinitionSpan] | None = None,
    witnesses: Mapping[AnnotationRuleMatch, DefinitionBasisWitness] | None = None,
) -> tuple[LocatedDefinitionComponent, ...]:
    """Consume WCE03 named role expansions; never infer a role from node order.

    Only exact contiguous available roles can form this attachment. Raw matches,
    alternatives and discontinuous roles remain retained in their source producer.
    """
    components = {}
    readings = {}
    for match in matches:
        roles = {role.role: role for role in match.roles}
        cue, term, content = (
            roles.get("defining_cue"),
            roles.get(term_role),
            roles.get(content_role),
        )
        if cue is not None and term is not None and content is not None:
            key = (match.rule, match.variant, cue.extents)
            readings.setdefault(key, set()).add((term.extents, content.extents))
    for match in matches:
        scope = scopes.get(match)
        if scope is None or scope.disposition != "supported":
            continue
        roles = {role.role: role for role in match.roles}
        cue = roles.get("defining_cue")
        if cue is None or cue.status != "complete":
            continue
        if len(readings.get((match.rule, match.variant, cue.extents), ())) > 1:
            # A competing retained binding is not resolved by surface order.
            continue
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
        antecedent = antecedents.get(match) if antecedents is not None else None
        qualified = witnesses is None or (match in witnesses and antecedent is None)
        component = definition_component(
            term=selected[0],
            content=antecedent if antecedent is not None else selected[1],
            interpretation=(
                ("explanation" if match.rule in {"naming", "explanation"} else "definition")
                if qualified
                else "unresolved"
            ),
            basis="matched_cue" if qualified else "unqualified",
            witness=witnesses[match] if qualified and witnesses is not None else None,
            scope=passage.scope,
            effective_version=passage.effective_version,
            evidence=(passage.passage_id,),
            reason=(
                f"Named rule {match.rule}/{match.variant} binds explicit "
                f"{term_role}/{content_role} roles; semantic attachment remains "
                "independently unassessed."
                + (
                    " The demonstrative refers to the unique preceding restricted nominal "
                    "in the same retained source piece."
                    if antecedent is not None
                    else ""
                )
            ),
        )
        components[component.component_id] = component
    return tuple(components[key] for key in sorted(components))


def components_from_following_display(
    passage: StructuralPassage,
    matches: tuple[AnnotationRuleMatch, ...],
    display_spans: tuple[tuple[int, int], ...],
    *,
    scopes: Mapping[AnnotationRuleMatch, DefinitionScope],
    term_role: str,
    witnesses: Mapping[AnnotationRuleMatch, DefinitionBasisWitness] | None = None,
) -> tuple[LocatedDefinitionComponent, ...]:
    """Join an explicit named following-content cue to its adjacent native display.

    Source-owned display geometry supplies the defining element, not a model score.
    Only punctuation/whitespace may separate the cue from that exact element.
    """
    found = []
    labels = [
        (match, role)
        for match in matches
        for role in match.roles
        if role.role == "definition_label" and role.status == "complete" and role.extents
    ]
    for match in matches:
        scope = scopes.get(match)
        if scope is None or scope.disposition != "supported":
            continue
        roles = {role.role: role for role in match.roles}
        labelled = "definition_label_required" in roles
        term = roles.get("nominal_subject" if labelled else term_role)
        cue = roles.get("copular_cue" if labelled else "following_content_cue")
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
        nominal = (term_start, term_end)
        if match.rule == "explanation" and scope.probability_subject is not None:
            subject_start, subject_end = scope.probability_subject
            if subject_start <= term_start < term_end <= subject_end:
                term_start, term_end = subject_start, subject_end
        cue_end = cue.extents[-1][1]
        if not passage.start <= term_start < term_end <= cue_end <= passage.end:
            continue
        label_match = next(
            (
                candidate
                for candidate, label in labels
                if passage.start <= label.extents[0][0] < label.extents[-1][1] <= term_start
            ),
            None,
        )
        if labelled and label_match is None:
            # Labels and cue matches are supplied from this one retained native block.
            # A bare copula in another block does not inherit definition standing.
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

            qualified = witnesses is None or (
                match in witnesses
                and nominal == (term_start, term_end)
                and (not labelled or label_match in witnesses)
            )
            witness = witnesses[match] if qualified and witnesses is not None else None
            if witness is not None and labelled and label_match is not None:
                witness = witness.model_copy(update={"label_nodes": label_match.nodes})
            found.append(
                definition_component(
                    term=span(term_start, term_end),
                    content=span(start, end),
                    interpretation=(
                        ("explanation" if match.rule == "explanation" else "definition")
                        if qualified
                        else "unresolved"
                    ),
                    basis="native_geometry" if qualified else "unqualified",
                    witness=witness,
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


def retained_annotation_components(
    reader, inputs, passage, cfg, *, retained=None, witness_policy: Mapping[str, Any]
):
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.semantic.constructions.named import RetainedNamedRules

    if retained is None:
        retained = reader.structural_source_annotations(
            inputs, passage.source_ref, AnnotationProfile(SentenceConfig(exclude=("ner",)))
        )
    frame, products, errors = retained.source, retained.annotations, retained.errors
    if errors:
        return NamedDefinitionResult((), False, (), "; ".join(errors))
    layers = {
        pin: report
        for product in products
        for pin, report in getattr(product, "primary_layers", {}).items()
    }
    if not layers:
        return NamedDefinitionResult(
            (), False, (), "Exact retained primary named-rule inputs are unavailable."
        )
    named = RetainedNamedRules(layers)
    qualified_rules = (
        witness_policy.get("rules", {})
        if witness_policy.get("scope") == _DEFINITION_SCOPE["version"]
        and cfg.term_role == witness_policy.get("term_role")
        and cfg.content_role == witness_policy.get("content_role")
        else {}
    )
    reviewed = {
        (rule.rule, rule.variant)
        for rule in cfg.annotation_rules
        if qualified_rules.get(f"{rule.rule}/{rule.variant}")
        == sha256(canonical_bytes(rule.model_dump(mode="json"))).hexdigest()
    }
    found, operations = [], []
    display_spans = tuple(
        span
        for product in products
        for span in product.display_spans
        if passage.start <= span[0] < span[1] <= passage.end
    )
    for product in products:
        if product.block_start >= passage.end or product.block_end <= passage.start:
            continue
        try:
            result = named.match(product, rules=cfg.annotation_rules)
            references = named.references(product, rules=cfg.annotation_rules)
            nominations = named.nominations(product, rules=cfg.annotation_rules)
        except ValueError as error:
            return NamedDefinitionResult((), False, tuple(operations), str(error))
        matches = tuple(
            match
            for match in result.matches
            if all(passage.start <= start < end <= passage.end for start, end in match.extents)
        )
        scopes = (
            definition_scopes(
                matches, predicate_frames(frame.text, (product,)), content_role=cfg.content_role
            )
            if matches
            else {}
        )
        antecedents = {}
        for match in matches:
            nomination = nominations.get(match, {}).get(cfg.content_role)
            if (
                nomination is None
                or nomination.status != "resolved"
                or not nomination.antecedent_extents
            ):
                continue
            extents = nomination.antecedent_extents
            first, last = extents[0][0], extents[-1][1]
            if (
                nomination.context_start is not None
                and passage.start <= nomination.context_start <= first < last <= passage.end
                and all(a <= b for (_x, a), (b, _y) in pairwise(extents))
            ):
                antecedents[match] = LocatedDefinitionSpan(
                    passage_id=passage.passage_id,
                    start=first,
                    end=last,
                    text=passage.text[first - passage.start : last - passage.start],
                )
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
                    dependency_digest=product.dependency_digest,
                    rule=rule,
                    variant=variant,
                    availability=state,
                    matched_count=len(selected),
                    matches=[
                        dict(
                            nodes=match.nodes,
                            roles=[asdict(role) for role in match.roles],
                            definition_scope=asdict(scopes[match]) if match in scopes else None,
                            **(
                                {"content_antecedent": antecedents[match].model_dump(mode="json")}
                                if match in antecedents
                                else {}
                            ),
                        )
                        for match in selected
                    ],
                )
            )
        complete_witness_columns = {
            column.attribute for column in product.availability if column.status == "complete"
        } >= _WITNESS_COLUMNS
        witnesses = {
            match: DefinitionBasisWitness(
                annotation_task_id=retained.annotation_task_id,
                block_id=product.block_id,
                dependency_digest=product.dependency_digest,
                rule=match.rule,
                variant=match.variant,
                nodes=match.nodes,
                primary_match=references[match],
                primary_scope=scopes[match].primary_scope,
            )
            for match in matches
            if retained.annotation_task_id is not None
            and complete_witness_columns
            and (match.rule, match.variant) in reviewed
            and match in scopes
            and scopes[match].primary_scope
            and (
                cfg.content_role not in nominations.get(match, {})
                or nominations[match][cfg.content_role].demonstrative is False
            )
        }
        found.extend(
            components_from_named_matches(
                passage,
                matches,
                scopes=scopes,
                term_role=cfg.term_role,
                content_role=cfg.content_role,
                antecedents=antecedents,
                witnesses=witnesses,
            )
        )
        found.extend(
            components_from_following_display(
                passage,
                matches,
                display_spans,
                scopes=scopes,
                term_role=cfg.term_role,
                witnesses=witnesses,
            )
        )
    available = any(operation["availability"] == "available" for operation in operations)
    return NamedDefinitionResult(
        tuple(found),
        available,
        tuple(operations),
        "Exact retained primary named-rule assignments projected onto the selected domain passage."
        if available
        else (
            "No selected retained linguistic rule operation is executable; "
            "no source absence is established."
        ),
    )


_DEFINITION_WINDOW_CHARS = 1536
_DEFINITION_WINDOW_OVERLAP = 256
_DEFINITION_MAX_WINDOWS = 64


def definition_windows(passage: StructuralPassage, cfg: DefinitionComponentsConfig, policy=None):
    """Bound model contexts while preserving original offsets and overlap provenance."""
    # Operational resource choices belong to the archived runtime, not the semantic
    # configuration ABI. Tuning these bounds does not redefine the output data model.
    bound = policy["chars"] if policy else _DEFINITION_WINDOW_CHARS
    limit = policy["limit"] if policy else _DEFINITION_MAX_WINDOWS
    max_chars = min(bound, max(1, cfg.profile.max_input_bytes // 4)) if cfg.profile else bound
    overlap = min(policy["overlap"] if policy else _DEFINITION_WINDOW_OVERLAP, max_chars // 4)
    start = 0
    windows = []
    while start < len(passage.text) and len(windows) < limit:
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
    version = "10"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.ENCODER
    confidence_source = None
    Config = DefinitionComponentsConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def __init__(self):
        self._worker: HostedGliner | None = None

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
        from .model_observation import (
            released_pack,
            released_policy,
            report_observation_digest,
            request_digest,
        )

        if cfg.inputs is None or (cfg.use_model and cfg.profile is None):
            raise ValueError("definition extraction needs complete configured inputs")
        ctx.check_active()
        ctx.reader.validate_structural_inputs(cfg.inputs)
        policy = released_policy(ctx.reader.prepared)
        pack = (
            released_pack(ctx.reader.prepared.release_id, policy, config=cfg.model_dump())
            if cfg.use_model
            else None
        )
        if cfg.use_model:
            if cfg.profile is None:
                raise GlinerRefused("model execution requires its exact declared profile")
            if self._worker is None:
                providers = getattr(ctx.reader, "provider_execution", None)
                if providers is not None:
                    self._worker = HostedGliner(
                        cfg.profile,
                        group=providers.native_group,
                        native_profile=cfg.native_execution_profile,
                    )
                else:
                    self._worker = GlinerWorker(cfg.profile)
            elif self._worker.profile.fingerprint != cfg.profile.fingerprint:
                raise GlinerRefused("definition worker cannot switch model profile")
        passages = {p.passage_id: p for p in cfg.inputs.passages}
        components, stages, raw_reports, window_outcomes = [], [], [], []
        role_candidates = []
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
                        witness_policy=policy.get("definition_witness", {}),
                    )
                    if cfg.annotation_rules
                    else NamedDefinitionResult(
                        (), False, (), "No exact rule recipe was selected for annotation replay."
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
            stages.extend(
                DefinitionStage(
                    passage_id=passage_id,
                    operation="located_extraction",
                    outcome="not_run",
                    reason=(
                        "Explicit registered linguistic-only composition; "
                        "no model extraction requested."
                    ),
                )
                for passage_id in cfg.target_ids
            )
        for passage_id in cfg.target_ids if cfg.use_model else ():
            if self._worker is None or pack is None:
                raise GlinerRefused("model execution owner is unavailable")
            passage = passages[passage_id]
            windows = definition_windows(passage, cfg, policy["definition_windows"])
            for window in windows:
                ctx.check_active()
                request = GlinerInput(
                    "definition-target:" + window.identity,
                    window.identity,
                    window.text,
                    f"{self.name}/{self.version}",
                )
                expected = request_digest(
                    pack,
                    asdict(cfg.profile),
                    (request,),
                    cfg.threshold,
                    cfg.evaluation_overlap or "flat",
                    cfg.evaluation_overlap is not None,
                    policy["inference"],
                )
                outcome = dict(
                    passage_id=passage_id,
                    start=window.start,
                    end=window.end,
                    request_digest=expected,
                    status="failed",
                )
                window_outcomes.append(outcome)
                try:
                    (reply,) = self._worker.extract(
                        pack,
                        (request,),
                        threshold=cfg.threshold,
                        overlap_policy=cfg.evaluation_overlap or "flat",
                        **({"evaluation": True} if cfg.evaluation_overlap is not None else {}),
                        check_active=ctx.check_active,
                    )
                    if (
                        reply.computation != expected
                        or reply.request_digest != expected
                        or reply.observation_digest != report_observation_digest(asdict(reply))
                    ):
                        raise GlinerWorkerError("provider reply differs from the selected request")
                    outcome["status"] = "returned"
                    raw_reports.append(
                        dict(
                            passage_id=passage_id,
                            window_start=window.start,
                            window_end=window.end,
                            **asdict(reply),
                        )
                    )
                    role_errors: list[dict[str, JsonValue]] = []
                    roles = located_definition_roles(
                        reply.raw, window, cfg, envelope=reply.computation, errors=role_errors
                    )
                    role_candidates.extend(roles)
                    locations = len({(r.role, r.span.identity) for r in roles})
                except (
                    GlinerRefused,
                    GlinerWorkerError,
                    ValueError,
                    TimeoutError,
                    OSError,
                ) as error:
                    if isinstance(error, GlinerRefused) and outcome["status"] != "returned":
                        outcome["status"] = "refused"
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
                raw_reports[-1]["role_errors"] = role_errors
                stages.append(
                    DefinitionStage(
                        passage_id=passage_id,
                        operation="located_extraction",
                        outcome="failed" if role_errors else "succeeded" if locations else "empty",
                        reason=(
                            f"Window {window.start}:{window.end}: {locations} "
                            "source-validated entity proposals retained; "
                            "role/support remains unassessed."
                        ),
                    )
                )
                try:
                    candidate_errors: list[dict[str, JsonValue]] = []
                    decoded = decode_definition_components(
                        reply.raw, window, cfg, candidate_errors=candidate_errors
                    )
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
                raw_reports[-1]["decoded_attachment_count"] = len(decoded)
                raw_reports[-1]["candidate_errors"] = candidate_errors
                stages.append(
                    DefinitionStage(
                        passage_id=passage_id,
                        operation="attachment",
                        outcome="failed"
                        if candidate_errors
                        else "succeeded"
                        if decoded
                        else "empty",
                        reason=(
                            f"Window {window.start}:{window.end}: {len(decoded)} "
                            "individually decoded role-and-attachment components retained; "
                            f"{len(candidate_errors)} rejected candidates retained "
                            "with indexed reasons; "
                            "no absence or semantic correctness claim."
                        ),
                    )
                )
            if windows and windows[-1].end < passage.end:
                window_outcomes.append(
                    dict(
                        passage_id=passage_id,
                        start=windows[-1].end,
                        end=passage.end,
                        status="uninspected",
                    )
                )
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
                components=tuple(components),
                stages=tuple(stages),
                role_candidates=tuple(role_candidates),
            ),
        )
        detail = (
            RootModel[dict[str, JsonValue]]
            .model_validate_json(
                canonical_bytes(
                    dict(
                        version="located-definition-extraction-5",
                        predicate_frame_version=PREDICATE_FRAME_VERSION,
                        raw_reports=raw_reports,
                        window_outcomes=window_outcomes,
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
                        description_arm=cfg.description_arm,
                        overlap_policy=cfg.evaluation_overlap or "flat",
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
