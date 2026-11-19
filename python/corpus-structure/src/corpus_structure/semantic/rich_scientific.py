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
from corpus_structure.model.compiled import annotation_boolean

from .data_operation_identity import canonical_identity, semantic_value
from .data_operation_model import EffectiveDataOperationModel, SubjectContext
from .expression_context import bind_expression_context
from .identity import canonical_bytes
from .math_context import AnalysisContextProfile
from .observations import source_python
from .refusals import SemanticReason
from .rich_graph_validation import (
    RichGraphState,
    RichWholeInput,
    checked_stage_index,
    read_rich_graph,
)
from .rich_knowledge_contracts import (
    DdoRichAssessment,
    DdoRichAuthoredPropositions,
    DdoRichConsolidation,
    DdoRichFact,
    DdoRichOccurrence,
    DdoRichQualificationMeaning,
    DdoRichSelectedMember,
    RichGraphAssembly,
    rich_reference_key,
)
from .rich_rules import RichRulePolicy
from .scientific_evidence import (
    CONSOLIDATION_PROFILE,
    SCIENTIFIC_POLICY_INPUT,
    EvidenceTier,
    ScientificInterpretationUnavailable,
    SemanticComparator,
    require_scientific_policy,
    scientific_assessment_reason,
)
from .types import PreparedRelease

_RULE = "scientific.value_equivalence"
_AUTHORED = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/DdoRichAuthoredPropositions"
_PACKET = "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket"


class RichScientificSourceContext(BaseModel):
    """Actual proposition member and its selected interpretation owner's explicit macros."""

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


def checked_rich_operand_macros(
    value: Any, context: RichScientificSourceContext
) -> dict[str, MacroDef]:
    """Verify the fact's referenced macro meaning against its actual source packet."""
    projected = bind_expression_context(value, context.macros)
    for actual, expected in zip(
        _expression_contexts(value), _expression_contexts(projected), strict=True
    ):
        observed = actual.get("macro_context", {})
        required = expected.get("macro_context", {})
        if canonical_bytes(observed) != canonical_bytes(required):
            raise ValueError("rich scientific operand lacks its exact source-bound macro context")
    names = {
        name
        for expression in _expression_contexts(projected)
        for name in expression.get("macro_context", {})
    }
    return {name: context.macros[name] for name in sorted(names)}


def checked_rich_source_contexts(
    prepared: PreparedRelease,
    state: RichGraphState,
    *,
    source_contexts: tuple[RichScientificSourceContext, ...],
    whole_inputs: tuple[RichWholeInput, ...],
) -> dict[bytes, RichScientificSourceContext]:
    """Check actual selected packet/authored macros once for scientific and rule consumers."""
    packet_inputs = {rich_reference_key(item.reference): item.value for item in whole_inputs}
    if len(packet_inputs) != len(whole_inputs):
        raise ValueError("rich scientific context repeats an actual whole input")
    contexts = {}
    for source in source_contexts:
        state.occurrence_source(source.original)
        state.external(source.context)
        owner = state.kind(source.context.kind_contract).semantic_id
        if source.context.member_id is not None or owner not in {_PACKET, _AUTHORED}:
            raise ValueError(
                "rich scientific context is not its actual selected extraction packet or authored propositions"
            )
        packet = packet_inputs.get(rich_reference_key(source.context))
        if packet is None:
            raise ValueError("rich scientific context lacks its actual selected packet body")
        if owner == _PACKET:
            from .data_operation_json import json_bytes

            # The packet owns lexical SourceValue floats and exact scope-meaning
            # text. Its JSON wire arrays are realized by the captured adapter;
            # actual rich graph contexts stay on their lossless Python route.
            checked_packet = prepared.validate_json(
                "DdoExternalExtractionPacket", json_bytes(_plain(packet))
            )
            actual_macros = source_python(_plain(checked_packet)["macros"])
        else:
            from corpus_structure.semantic.input_values import _untrusted_value

            authored = DdoRichAuthoredPropositions.model_validate(_untrusted_value(packet))
            actual_macros = _plain(authored.macros)
        if not isinstance(actual_macros, dict):
            raise ValueError("rich scientific packet macros are not an explicit source mapping")
        parsed_macros = {
            name: MacroDef.model_validate(value) for name, value in actual_macros.items()
        }
        if parsed_macros != source.macros:
            raise ValueError("rich scientific macros differ from the actual selected packet")
        key = rich_reference_key(source.original)
        if key in contexts:
            raise ValueError("rich scientific source context repeats an actual proposal member")
        contexts[key] = source
    return contexts


def _compare_partitioned_values(
    comparator, operands, compared, conditions, *, common_condition=True
):
    """A supported difference decides the pair; equivalence requires every component."""
    if not common_condition:
        return None, "scientific comparison requires a common condition"
    pending = [("value", operands[0], operands[1])]
    unresolved = []
    for name in sorted(compared[0].keys() | compared[1].keys()):
        if name not in compared[0] or name not in compared[1]:
            unresolved.append("compared qualification is absent on one side: " + name)
        elif semantic_value(compared[0][name]) != semantic_value(compared[1][name]):
            pending.append(("qualification " + name, compared[0][name], compared[1][name]))
    results = []
    for name, left, right in pending:
        try:
            result = comparator.compare(left, right, conditions, ref_eq=lambda a, b: a == b)
        except ScientificInterpretationUnavailable as error:
            unresolved.append(name + ": " + str(error))
            continue
        if result.tier is EvidenceTier.UNDECIDED:
            unresolved.append(name + ": " + result.detail)
        elif not result.equal:
            return result, name + ": " + result.detail
        else:
            results.append(result)
    if unresolved:
        return None, "; ".join(unresolved)
    # All component comparisons succeeded. Retain the weakest supporting tier.
    rank = {EvidenceTier.CANONICAL: 0, EvidenceTier.SYMBOLIC: 1, EvidenceTier.NUMERIC: 2}
    result = max(results, key=lambda item: rank[item.tier])
    return result, result.detail


def assess_rich_scientific(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    *,
    context: SubjectContext,
    graph: RichGraphAssembly | DdoRichConsolidation,
    inputs: tuple[DdoRichSelectedMember, ...],
    policy: RichRulePolicy,
    context_profile: AnalysisContextProfile,
    source_contexts: tuple[RichScientificSourceContext, ...],
    whole_inputs: tuple[RichWholeInput, ...] = (),
    retained_graphs: tuple[RichWholeInput, ...] = (),
    _index: RichGraphState | None = None,
) -> tuple[DdoRichAssessment, ...]:
    """Compare distinct functional accepted-value facts within exact qualification slots.

    The selected closed graph owns fact/entity/value meaning. Explicit packet inputs own
    source interpretation. This pure kernel grants neither accepted standing nor native
    custody; its output and input basis must be retained by the actual CPU executor.
    """
    if policy.prepared != prepared:
        raise ValueError("rich scientific policy differs from its actual prepared interpretation")
    require_scientific_policy(prepared, context_profile=context_profile)
    state = (
        read_rich_graph(
            prepared,
            model,
            context=context,
            graph=graph,
            inputs=inputs,
            whole_inputs=whole_inputs,
            retained_graphs=retained_graphs,
        )
        if _index is None
        else checked_stage_index(
            _index, prepared, model, context, graph, inputs, whole_inputs, retained_graphs
        )
    )
    contexts = checked_rich_source_contexts(
        prepared, state, source_contexts=source_contexts, whole_inputs=whole_inputs
    )
    groups = defaultdict(list)
    partitions = {}
    for occurrence in state.members.values():
        if not isinstance(occurrence, DdoRichOccurrence):
            continue
        fact = state.member(occurrence.fact_id, DdoRichFact)
        definition, prop, _ = state.property(fact.property_contract)
        metadata = policy.metadata.get((definition.name, prop.iri), {})
        if not (
            prop.constraint_scope == "accepted_value"
            and metadata.get("cs:role") == "predicate"
            and (
                not prop.multivalued
                or annotation_boolean(metadata.get("cs:functional", False), "cs:functional")
            )
        ):
            continue
        observed = state.value(occurrence.observed_qualification_value)
        _, comparison_context, compared = policy.comparison_projection.partition(
            definition.name, prop.iri, type(observed).__name__, _plain(observed)
        )
        meaning = state.member(fact.qualification_meaning, DdoRichQualificationMeaning)
        qualification_definition = state.definition(meaning.qualification_contract)
        context_fields = [
            field.model_dump(mode="python")
            for field in meaning.fields
            if state.property(field.property_contract, qualification_definition.iri)[1].name
            in comparison_context
        ]
        partitions[occurrence.occurrence_id] = compared
        groups[
            (
                fact.subject_entity,
                fact.property_contract,
                canonical_bytes([meaning.qualification_contract, context_fields]),
            )
        ].append(occurrence)
    results = []
    policy_digest = next(
        item.digest for item in prepared.artifacts if item.kind == SCIENTIFIC_POLICY_INPUT
    )
    comparators = {}
    for slot in sorted(groups):
        members = sorted(groups[slot], key=lambda item: item.occurrence_id)
        for left_occurrence, right_occurrence in combinations(members, 2):
            if left_occurrence.fact_id == right_occurrence.fact_id:
                continue
            if {
                left_occurrence.occurrence_id,
                right_occurrence.occurrence_id,
            } <= state.retained_member_ids:
                continue
            operands, qualifiers, source_pair, macros = [], [], [], []
            for occurrence in (left_occurrence, right_occurrence):
                source = contexts.get(rich_reference_key(occurrence.original))
                if source is None:
                    raise ValueError(
                        "rich scientific occurrence lacks its explicit selected source context"
                    )
                source_pair.append(source)
                fact = state.member(occurrence.fact_id, DdoRichFact)
                definition, prop, _ = state.property(fact.property_contract)
                value = _plain(
                    state.property_value(fact.object_value, definition, prop, item=prop.multivalued)
                )
                if prop.range in prepared.index.definitions and not prop.inlined:
                    value = {"kind": "entity", "target": value}
                qualification = _plain(state.value(occurrence.observed_qualification_value))
                operands.append(value)
                qualifiers.append(qualification)
                macros.append(checked_rich_operand_macros((value, qualification), source))
            conflict = set(macros[0]) & set(macros[1])
            incompatible = any(macros[0][name] != macros[1][name] for name in conflict)
            comparison, semantic_reason = None, None
            detail = "incompatible referenced source macro definitions" if incompatible else ""
            try:
                if not incompatible:
                    operative = {**macros[0], **macros[1]}
                    key = canonical_bytes(_plain(operative))
                    if key not in comparators:
                        comparators[key] = SemanticComparator(
                            operative, prepared=prepared, context_profile=context_profile
                        )
                    condition = qualifiers[0].get("condition")
                    common_condition = semantic_value(condition) == semantic_value(
                        qualifiers[1].get("condition")
                    )
                    comparison, detail = _compare_partitioned_values(
                        comparators[key],
                        operands,
                        [
                            partitions[item.occurrence_id]
                            for item in (left_occurrence, right_occurrence)
                        ],
                        (condition,) if condition is not None else (),
                        common_condition=common_condition,
                    )
            except ScientificInterpretationUnavailable as error:
                detail = str(error)
            outcome = (
                "undecided"
                if comparison is None or comparison.tier is EvidenceTier.UNDECIDED
                else "equivalent"
                if comparison.equal
                else "different"
            )
            occurrences = (left_occurrence.occurrence_id, right_occurrence.occurrence_id)
            if outcome == "undecided":
                semantic_reason = SemanticReason(
                    "incompatible_bindings" if incompatible else "unsupported_interpretation",
                    "scientific_policy",
                    None,
                    occurrences,
                    detail=detail or "no faithful comparison operand",
                )
            evidence = comparison.evidence if comparison is not None else None
            reason = scientific_assessment_reason(
                evidence,
                detail=detail or f"{outcome} under {CONSOLIDATION_PROFILE}",
                semantic_reason=semantic_reason,
                context=semantic_value(
                    {
                        "left": operands[0],
                        "right": operands[1],
                        "qualification": qualifiers,
                        "macros": [_plain(item) for item in macros],
                    }
                ),
            )
            references = {}
            for occurrence, source in zip(
                (left_occurrence, right_occurrence), source_pair, strict=True
            ):
                retained = state.retained_sources(occurrence.occurrence_id)
                source_refs = (
                    (*retained, source.context)
                    if retained
                    else (occurrence.original, occurrence.statement, source.context)
                )
                for reference in source_refs:
                    if reference is not None:
                        references[rich_reference_key(reference)] = reference
            evidence_members = tuple(references[key] for key in sorted(references))
            identity = canonical_identity(
                "rich-assessment",
                [
                    context.identity_record,
                    _RULE,
                    policy_digest,
                    occurrences,
                    outcome,
                    reason,
                    [item.model_dump(mode="python") for item in evidence_members],
                ],
            ).key
            results.append(
                DdoRichAssessment(
                    severity=None,
                    member_type="assessment",
                    assessment_id=identity,
                    occurrences=occurrences,
                    rule=_RULE,
                    outcome=outcome,
                    reason=reason,
                    evidence_members=evidence_members,
                )
            )
    return tuple(sorted(results, key=lambda item: item.assessment_id))
