"""Scientific comparisons over the closed current rich graph and captured source contexts.

Assessments compare domain fact meanings. A source-reading assertion never becomes a
scientific proposition, and an undecided comparison never becomes inequality.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from itertools import combinations
from typing import Any

from pydantic import BaseModel, ConfigDict

from corpus_structure.core.evidence import MacroDef

from .analysis_contracts import AnalysisContextProfile
from .data_operation_identity import canonical_identity, semantic_value
from .data_operation_model import EffectiveDataOperationModel, SubjectContext
from .expression_context import bind_expression_context
from .identity import canonical_bytes
from .observations import source_python
from .refusals import SemanticReason
from .rich_graph_validation import RichWholeInput, read_rich_graph
from .rich_knowledge_contracts import (
    DdoRichAssessment, DdoRichConsolidation, DdoRichFact, DdoRichOccurrence,
    DdoRichSelectedMember, rich_reference_key,
)
from .rich_rules import RichRulePolicy
from .scientific_evidence import (
    CONSOLIDATION_PROFILE, SCIENTIFIC_POLICY_INPUT, EvidenceTier,
    ScientificInterpretationUnavailable, SemanticComparator,
    require_scientific_policy, scientific_assessment_reason,
)
from .types import PreparedRelease

_RULE = "scientific.value_equivalence"
_PACKET = "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket"


class RichScientificSourceContext(BaseModel):
    """Actual proposal member and its selected extraction packet's explicit macros."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    original: DdoRichSelectedMember
    context: DdoRichSelectedMember
    macros: dict[str, MacroDef]


def _plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _plain(value.model_dump(mode="python", exclude_unset=True))
    if isinstance(value, Mapping):
        return {name: _plain(item) for name, item in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(_plain(item) for item in value)
    return value


def _expression_contexts(value: Any):
    if isinstance(value, Mapping):
        if value.get("kind") in {"expression", "formula", "set"}:
            yield value
        for item in value.values():
            yield from _expression_contexts(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _expression_contexts(item)


def _macros(value: Any, context: RichScientificSourceContext) -> dict[str, MacroDef]:
    """Verify the fact's referenced macro meaning against its actual source packet."""
    projected = bind_expression_context(value, context.macros)
    for actual, expected in zip(_expression_contexts(value), _expression_contexts(projected), strict=True):
        observed = actual.get("macro_context", {})
        required = expected.get("macro_context", {})
        if canonical_bytes(observed) != canonical_bytes(required):
            raise ValueError("rich scientific operand lacks its exact source-bound macro context")
    names = {name for expression in _expression_contexts(projected) for name in expression.get("macro_context", {})}
    return {name: context.macros[name] for name in sorted(names)}


def assess_rich_scientific(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    *,
    context: SubjectContext,
    graph: DdoRichConsolidation,
    inputs: tuple[DdoRichSelectedMember, ...],
    policy: RichRulePolicy,
    context_profile: AnalysisContextProfile,
    source_contexts: tuple[RichScientificSourceContext, ...],
    whole_inputs: tuple[RichWholeInput, ...] = (),
) -> tuple[DdoRichAssessment, ...]:
    """Compare distinct functional accepted-value facts within exact qualification slots.

    The selected closed graph owns fact/entity/value meaning. Explicit packet inputs own
    source interpretation. This pure kernel grants neither accepted standing nor native
    custody; its output and input basis must be retained by the actual CPU executor.
    """
    if policy.prepared != prepared:
        raise ValueError("rich scientific policy differs from its actual prepared interpretation")
    require_scientific_policy(prepared, context_profile=context_profile)
    state = read_rich_graph(prepared, model, context=context, graph=graph, inputs=inputs, whole_inputs=whole_inputs)
    packet_inputs = {rich_reference_key(item.reference): item.value for item in whole_inputs}
    contexts = {}
    for source in source_contexts:
        state.external(source.original)
        state.external(source.context)
        if source.context.member_id is not None or state.kind(source.context.kind_contract).semantic_id != _PACKET:
            raise ValueError("rich scientific context is not its actual selected extraction packet")
        packet = packet_inputs.get(rich_reference_key(source.context))
        if packet is None:
            raise ValueError("rich scientific context lacks its actual selected packet body")
        checked_packet = prepared.validate_python("DdoExternalExtractionPacket", packet)
        actual_macros = source_python(_plain(checked_packet)["macros"])
        if not isinstance(actual_macros, dict):
            raise ValueError("rich scientific packet macros are not an explicit source mapping")
        parsed_macros = {name: MacroDef.model_validate(value) for name, value in actual_macros.items()}
        if parsed_macros != source.macros:
            raise ValueError("rich scientific macros differ from the actual selected packet")
        key = rich_reference_key(source.original)
        if key in contexts:
            raise ValueError("rich scientific source context repeats an actual proposal member")
        contexts[key] = source
    groups = defaultdict(list)
    for occurrence in state.members.values():
        if not isinstance(occurrence, DdoRichOccurrence):
            continue
        fact = state.member(occurrence.fact_id, DdoRichFact)
        definition, prop, _ = state.property(fact.property_contract)
        metadata = policy.metadata.get((definition.name, prop.iri), {})
        if not (
            prop.constraint_scope == "accepted_value" and metadata.get("cs:role") == "predicate"
            and (not prop.multivalued or str(metadata.get("cs:functional", "")).lower() == "true")
        ):
            continue
        # Provenance is excluded by the checked qualification-meaning owner. Scope,
        # modality, conditions and time remain exact boundaries of the comparison.
        groups[(fact.subject_entity, fact.property_contract, fact.qualification_meaning)].append(occurrence)
    results = []
    policy_digest = next(item.digest for item in prepared.artifacts if item.kind == SCIENTIFIC_POLICY_INPUT)
    comparators = {}
    for slot in sorted(groups):
        members = sorted(groups[slot], key=lambda item: item.occurrence_id)
        for left_occurrence, right_occurrence in combinations(members, 2):
            if left_occurrence.fact_id == right_occurrence.fact_id:
                continue
            operands, qualifiers, source_pair, macros = [], [], [], []
            for occurrence in (left_occurrence, right_occurrence):
                source = contexts.get(rich_reference_key(occurrence.original))
                if source is None:
                    raise ValueError("rich scientific occurrence lacks its explicit selected source context")
                source_pair.append(source)
                fact = state.member(occurrence.fact_id, DdoRichFact)
                definition, prop, _ = state.property(fact.property_contract)
                value = _plain(state.property_value(fact.object_value, definition, prop, item=prop.multivalued))
                if prop.range in prepared.index.definitions and not prop.inlined:
                    value = {"kind": "entity", "target": value}
                qualification = _plain(state.value(occurrence.observed_qualification_value))
                operands.append(value)
                qualifiers.append(qualification)
                macros.append(_macros((value, qualification), source))
            conflict = set(macros[0]) & set(macros[1])
            incompatible = any(macros[0][name] != macros[1][name] for name in conflict)
            comparison, semantic_reason = None, None
            detail = "incompatible referenced source macro definitions" if incompatible else ""
            try:
                if not incompatible:
                    operative = {**macros[0], **macros[1]}
                    key = canonical_bytes(_plain(operative))
                    if key not in comparators:
                        comparators[key] = SemanticComparator(operative, prepared=prepared, context_profile=context_profile)
                    condition = qualifiers[0].get("condition")
                    comparison = comparators[key].compare(
                        operands[0], operands[1], (condition,) if condition is not None else (), ref_eq=lambda a, b: a == b,
                    )
                    detail = comparison.detail
            except ScientificInterpretationUnavailable as error:
                detail = str(error)
            outcome = "undecided" if comparison is None or comparison.tier is EvidenceTier.UNDECIDED else "equivalent" if comparison.equal else "different"
            occurrences = (left_occurrence.occurrence_id, right_occurrence.occurrence_id)
            if outcome == "undecided":
                semantic_reason = SemanticReason(
                    "incompatible_bindings" if incompatible else "unsupported_interpretation", "scientific_policy",
                    None, occurrences, detail=detail or "no faithful comparison operand",
                )
            evidence = comparison.evidence if comparison is not None else None
            reason = scientific_assessment_reason(
                evidence, detail=detail or f"{outcome} under {CONSOLIDATION_PROFILE}", semantic_reason=semantic_reason,
                context=semantic_value({"left": operands[0], "right": operands[1], "qualification": qualifiers,
                                        "macros": [_plain(item) for item in macros]}),
            )
            references = {}
            for occurrence, source in zip((left_occurrence, right_occurrence), source_pair, strict=True):
                for reference in (occurrence.original, occurrence.statement, source.context):
                    if reference is not None:
                        references[rich_reference_key(reference)] = reference
            evidence_members = tuple(references[key] for key in sorted(references))
            identity = canonical_identity("rich-assessment", [
                context.identity_record, _RULE, policy_digest, occurrences, outcome, reason,
                [item.model_dump(mode="python") for item in evidence_members],
            ]).key
            results.append(DdoRichAssessment(
                member_type="assessment", assessment_id=identity, occurrences=occurrences,
                rule=_RULE, outcome=outcome, reason=reason, evidence_members=evidence_members,
            ))
    return tuple(sorted(results, key=lambda item: item.assessment_id))
