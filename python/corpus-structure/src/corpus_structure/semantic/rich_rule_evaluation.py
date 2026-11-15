"""Typed rule decisions over the actual current rich occurrence and value graph.

Occurrence addresses stay distinct from canonical proposition references. Pure
rule/scientific selections grant no native knowledge admission by themselves.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

import networkx as nx
import pyarrow as pa
from pydantic import BaseModel

from .analysis_contracts import AnalysisContextProfile, prepare_interpretation_context
from .analytical_kernels import (
    VIEW_ALTERNATIVES,
    VIEW_CLAIMS,
    VIEW_ENTITIES,
    VIEW_IDENTITY,
    ViewSpec,
)
from .data_operation_identity import canonical_identity
from .data_operation_model import EffectiveDataOperationModel, SubjectContext
from .identity import canonical_bytes
from .refusals import SemanticReason, SemanticRefusal, semantic_reason_identity
from .rich_decisions import OccurrenceStatus, RuleOutcome, RuleSeverity
from .rich_graph_validation import RichWholeInput, read_rich_graph
from .rich_knowledge_contracts import (
    DdoRichAlternative,
    DdoRichAssessment,
    DdoRichConsolidation,
    DdoRichConsolidationPolicy,
    DdoRichEntity,
    DdoRichFact,
    DdoRichOccurrence,
    DdoRichSelectedMember,
    RichGraphAssembly,
    rich_reference_key,
)
from .rich_policy_binding import (
    require_rich_policy,
    rich_context_profile,
    rich_eligibility_policy_digest,
)
from .rich_relations import RichRelationKernel
from .rich_rules import RichRulePolicy
from .rich_scientific import (
    RichScientificSourceContext,
    checked_rich_operand_macros,
    checked_rich_source_contexts,
)
from .rule_views import (
    BindingView,
    EntityView,
    NodeView,
    QualifiersView,
    Reading,
    StatementView,
    binding_symbols,
    project_rule_value,
)
from .types import PreparationError, PreparedRelease
from .value_codec import value_meaning


@dataclass(frozen=True)
class RichRuleFinding:
    rule: str
    outcome: RuleOutcome
    severity: RuleSeverity
    assessment_id: str | None


@dataclass(frozen=True)
class RichRuleDecision:
    occurrence_id: str
    fact_id: str
    status: OccurrenceStatus
    findings: tuple[RichRuleFinding, ...]


@dataclass(frozen=True)
class RichScientificRepresentative:
    fact_id: str
    representative_fact_id: str
    component_id: str
    policy: Literal["min-fact-id-1"] = "min-fact-id-1"


@dataclass(frozen=True)
class RichRuleEvaluation:
    assessments: tuple[DdoRichAssessment, ...]
    decisions: tuple[RichRuleDecision, ...]
    selected_fact_ids: frozenset[str]
    selected_occurrence_ids: frozenset[str]
    scientific_representatives: tuple[RichScientificRepresentative, ...]
    eligibility_policy_digest: str


class RichRuleEvaluationRefused(SemanticRefusal):
    """The selected graph or captured rule basis cannot support this evaluation."""


@dataclass(frozen=True)
class _Unavailable:
    reason: SemanticReason


class _ProjectionUnavailable(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason.render())


class _ClaimView(Mapping[str, Any]):
    """The declared logical OBJECT view, with explicit unavailable projections.

    The existing rule-engine accessors validate every returned field. An unknown
    condition is never an empty condition list and cannot establish a rule pass.
    """

    def __init__(self, values: Mapping[str, Any]):
        self._fields = values

    def __getitem__(self, name):
        value = self._fields[name]
        if isinstance(value, _Unavailable):
            raise _ProjectionUnavailable(value.reason)
        return value

    def __iter__(self):
        return iter(self._fields)

    def __len__(self):
        return len(self._fields)


def _plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _plain(value.model_dump(mode="python", exclude_unset=True))
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(_plain(item) for item in value)
    return value


def _statement(reference):
    return (
        None
        if reference is None
        else canonical_bytes([reference.product_id, reference.member_id]).decode()
    )


def _condition_nodes(value, occurrence, prepared):
    if value is None:
        return ()
    kind = value["kind"]
    if kind in {"all", "any"}:
        return (
            NodeView("and" if kind == "all" else "or", None, None, None, None),
            *(
                node
                for term in value["terms"]
                for node in _condition_nodes(term, occurrence, prepared)
            ),
        )
    if kind == "not":
        return (
            NodeView("not", None, None, None, None),
            *_condition_nodes(value["term"], occurrence, prepared),
        )
    if kind == "claim":
        return (NodeView("claim", value["ref"], None, None, None),)
    if kind == "member":
        return (NodeView("member", None, None, None, value["x"]["expression"]),)
    if kind == "compare":
        return (NodeView("cmp", None, None, value["relation"], value["lhs"]["expression"]),)
    if kind == "forall":
        return (
            NodeView("forall", None, value["variable"], None, None),
            *_condition_nodes(value["body"], occurrence, prepared),
        )
    if kind == "atomic":
        return (NodeView("pred", None, value["predicate"], None, None),)
    raise _ProjectionUnavailable(
        SemanticReason(
            "unsupported_interpretation",
            "rich-rules",
            prepared.release_id,
            (occurrence,),
            expected="admitted condition projection",
            actual=kind,
            detail="source condition remains uninterpreted: " + value.get("reason", kind),
        )
    )


def _entity_view(state, entity, policy):
    identities = {}
    symbols = set()
    labels = set()
    for basis in entity.identities:
        definition = state.definition(basis.class_contract)
        if basis.label is not None:
            labels.add(basis.label)
        for field in basis.fields:
            _, prop, _ = state.property(field.property_contract, definition.iri)
            value = state.property_value(field.value_id, definition, prop)
            lexical = value if isinstance(value, str) else value_meaning(value)[1]
            lexical = (
                ("true" if lexical else "false") if isinstance(lexical, bool) else str(lexical)
            )
            name = policy.compact(prop.iri)
            if name in identities and identities[name] != lexical:
                raise RichRuleEvaluationRefused(
                    "rich rule identity projection has conflicting actual property values"
                )
            identities[name] = lexical
            if prop.name == "symbol":
                symbols.add(lexical)
    if len(symbols) > 1:
        raise RichRuleEvaluationRefused(
            "rich rule symbol projection has conflicting actual symbol properties"
        )
    return EntityView(
        entity.entity_id,
        entity.entity_id,
        tuple(
            sorted(
                policy.compact(state.definition(contract).iri)
                for contract in entity.class_contracts
            )
        ),
        min(labels, default=""),
        next(iter(symbols), None),
        identities,
    )


def _reading(prepared, profile, occurrence, value, qualification, source, readings):
    lexical = value.get("expression") if isinstance(value, Mapping) else None
    if lexical is None:
        return None, None
    if source is None or value.get("language") not in {"latex", "tex"}:
        return None, SemanticReason(
            "unsupported_interpretation" if source is not None else "missing_operands",
            "rich-rules",
            prepared.release_id,
            (occurrence.occurrence_id,),
            expected="actual selected mathematical source context",
            actual=value.get("language")
            if source is not None
            else "missing selected source context",
            detail="mathematical rule reading requires an explicit source context and admitted language",
        )
    from corpus_structure.methods.math.prepared import PreparedMathInput

    from .grammar_profile import GRAMMAR_KINDS

    macros = checked_rich_operand_macros((value, qualification), source)
    try:
        context = prepare_interpretation_context(
            prepared,
            context_profile=profile,
            macros=macros,
            bindings=value.get("bindings", ()),
            kind="set_expr" if value.get("kind") == "set" else "any_value",
            demand="symbolic",
        )
        key = (lexical, value.get("kind"), context.key())
        if key not in readings:
            result = PreparedMathInput(context, lexical).symbolic_reading()
            context.validate_result(
                produced=("lexical", "syntax", "occurrences", "interpretation", "symbolic"),
                interpretation=result.status.value,
                completeness="failed" if result.failure else "complete",
            )
            readings[key] = Reading(
                result.status.value,
                GRAMMAR_KINDS.get(result.kind or ""),
                tuple(sorted({item.name for item in result.occurrences if not item.constant})),
            )
        reading = readings[key]
    except PreparationError as error:
        source_codes = {
            "analysis_binding_kind",
            "analysis_declaration",
            "analysis_declaration_authority",
        }
        if not error.diagnostics or any(
            item.code not in source_codes for item in error.diagnostics
        ):
            raise
        return None, SemanticReason(
            "preparation_failed",
            "rich-rules",
            prepared.release_id,
            (occurrence.occurrence_id,),
            detail=str(error),
        )
    if reading.status != "ok":
        return reading, SemanticReason(
            "preparation_failed" if reading.status == "failed" else "unsupported_interpretation",
            "rich-rules",
            prepared.release_id,
            (occurrence.occurrence_id,),
            expected="ok",
            actual=reading.status,
            detail="mathematical reading " + reading.status,
        )
    return reading, None


def evaluate_rich_rules(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    *,
    context: SubjectContext,
    graph: RichGraphAssembly | DdoRichConsolidation,
    inputs: tuple[DdoRichSelectedMember, ...],
    policy: RichRulePolicy,
    relations: RichRelationKernel,
    context_profile: AnalysisContextProfile,
    consolidation_policy: DdoRichConsolidationPolicy,
    source_contexts: tuple[RichScientificSourceContext, ...],
    scientific_assessments: tuple[DdoRichAssessment, ...] = (),
    whole_inputs: tuple[RichWholeInput, ...] = (),
    retained_graphs: tuple[RichWholeInput, ...] = (),
) -> RichRuleEvaluation:
    """Evaluate actual occurrence views; publication and complete-reading grading stay separate."""
    relations.check_active()
    if policy.prepared != prepared:
        raise RichRuleEvaluationRefused(
            "rich rule policy differs from its actual prepared interpretation"
        )
    checked_policy = require_rich_policy(prepared, model, consolidation_policy)
    if context_profile != rich_context_profile(prepared):
        raise RichRuleEvaluationRefused(
            "rich rule analysis context differs from its actual captured owner"
        )
    policy_digest = rich_eligibility_policy_digest(checked_policy)
    state = read_rich_graph(
        prepared,
        model,
        context=context,
        graph=graph,
        inputs=inputs,
        whole_inputs=whole_inputs,
        retained_graphs=retained_graphs,
    )
    for retained in state.retained_admissions:
        if retained.eligibility_policy_digest != policy_digest:
            raise RichRuleEvaluationRefused(
                "rich known eligibility has a different actual policy basis; regenerate"
            )
    contexts = checked_rich_source_contexts(
        prepared, state, source_contexts=source_contexts, whole_inputs=whole_inputs
    )
    if any(
        not set(body.class_contracts) <= set(checked_policy.allowed_domain_contracts)
        for body in state.members.values()
        if isinstance(body, DdoRichEntity)
    ):
        raise RichRuleEvaluationRefused(
            "rich entity memberships exceed the actual checked domain policy"
        )
    entities = {
        identifier: _entity_view(state, body, policy)
        for identifier, body in state.members.items()
        if isinstance(body, DdoRichEntity)
    }
    occurrences = {
        identifier: body
        for identifier, body in state.members.items()
        if isinstance(body, DdoRichOccurrence)
    }
    facts = {
        identifier: body
        for identifier, body in state.members.items()
        if isinstance(body, DdoRichFact)
    }
    terms = {}
    for identifier, occurrence in occurrences.items():
        fact = facts[occurrence.fact_id]
        definition, prop, _ = state.property(fact.property_contract)
        qualification = _plain(state.value(occurrence.observed_qualification_value))
        value = _plain(
            state.property_value(fact.object_value, definition, prop, item=prop.multivalued)
        )
        terms[identifier] = (fact, definition, prop, qualification, value)
    if any(
        identifier not in state.retained_member_ids
        and isinstance(values[4], Mapping)
        and values[4].get("expression") is not None
        and values[4].get("language") in {"latex", "tex"}
        and rich_reference_key(occurrences[identifier].original) in contexts
        for identifier, values in terms.items()
    ):
        from .scientific_evidence import require_scientific_policy

        require_scientific_policy(prepared, context_profile=context_profile)
    predicate_occurrences = {
        identifier: occurrence
        for identifier, occurrence in occurrences.items()
        if policy.metadata.get((terms[identifier][1].name, terms[identifier][2].iri), {}).get(
            "cs:role"
        )
        == "predicate"
    }
    gives, premises, global_premises, symbol_owners = {}, defaultdict(set), set(), defaultdict(set)
    for identifier, occurrence in predicate_occurrences.items():
        _, definition, prop, qualification, _ = terms[identifier]
        metadata = policy.metadata.get((definition.name, prop.iri), {})
        param_map = metadata.get("cs:param_map")
        symbols = frozenset()
        if param_map and prepared.member_has_behavior(
            "StatementRole", occurrence.statement_role, "supplies_binding_symbol"
        ):
            entries = qualification.get(param_map, ())
            members = entries.values() if isinstance(entries, Mapping) else entries
            binding = prepared.index.properties[policy.qprops[param_map].range, "value"]
            symbols = binding_symbols(
                prepared, binding, (entry.get("value", entry) for entry in members)
            )
        gives[identifier] = symbols
        for symbol in symbols:
            symbol_owners[symbol].add(identifier)
        if prepared.member_has_behavior(
            "StatementRole", occurrence.statement_role, "participates_as_premise"
        ):
            if occurrence.statement is not None:
                premises[_statement(occurrence.statement)].add(occurrence.fact_id)
            if prepared.member_has_behavior(
                "StatementKind", occurrence.statement_kind, "global_premise_context"
            ):
                global_premises.add(occurrence.fact_id)
    specs = tuple(
        ViewSpec.from_declaration(
            name,
            {**raw, "source": prepared.expand_name(raw["source"])},
            {
                terms[identifier][2].iri
                for identifier in predicate_occurrences
                if policy.applies(
                    {"applies_to": raw["applies_to"]},
                    class_name=terms[identifier][1].name,
                    predicate=terms[identifier][2].iri,
                )
            },
        )
        for name, raw in policy.source.get("views", {}).items()
    )
    alternatives = {
        identifier: body
        for identifier, body in state.members.items()
        if isinstance(body, DdoRichAlternative)
    }
    tables = dict(
        claims=pa.Table.from_pylist(
            [
                {
                    "claim": identifier,
                    "predicate": terms[identifier][2].iri,
                    "subject": terms[identifier][0].subject_entity,
                    "object": terms[identifier][4]
                    if isinstance(terms[identifier][4], str) and terms[identifier][4] in entities
                    else None,
                    "statement": _statement(occurrence.statement),
                }
                for identifier, occurrence in predicate_occurrences.items()
            ],
            schema=VIEW_CLAIMS,
        ),
        entities=pa.Table.from_pylist(
            [
                {
                    "entity": entity.id,
                    "key": entity.key,
                    "class_id": class_id,
                    "label": entity.label,
                    "symbol": entity.symbol,
                }
                for entity in entities.values()
                for class_id in entity.types
            ],
            schema=VIEW_ENTITIES,
        ),
        identity=pa.Table.from_pylist(
            [
                {"entity": entity.id, "slot": slot, "value": value}
                for entity in entities.values()
                for slot, value in entity.identity.items()
            ],
            schema=VIEW_IDENTITY,
        ),
        alternatives=pa.Table.from_pylist(
            [
                {"group": identifier, "claim": occurrence.occurrence_id}
                for identifier, alternative in alternatives.items()
                for occurrence in predicate_occurrences.values()
                if occurrence.fact_id in alternative.fact_ids
            ],
            schema=VIEW_ALTERNATIVES,
        ),
    )
    view_rows = {
        (row["claim"], row["view"]): tuple(row["facts"])
        for row in relations.views(**tables, specs=specs).to_pylist()
    }
    by_occurrence = {
        identifier: occurrence.fact_id for identifier, occurrence in predicate_occurrences.items()
    }
    guideline_ids = {raw["id"] for raw in policy.source.get("guideline", ())}
    assessments, decisions, readings = list(scientific_assessments), [], {}
    unresolved = {
        identifier
        for assessment in scientific_assessments
        if assessment.outcome == "undecided"
        for identifier in assessment.occurrences
    }
    if len({item.assessment_id for item in scientific_assessments}) != len(scientific_assessments):
        raise RichRuleEvaluationRefused(
            "rich scientific assessment population repeats an actual assessment"
        )
    for assessment in scientific_assessments:
        if (
            assessment.rule != "scientific.value_equivalence"
            or assessment.severity is not None
            or assessment.outcome not in {"equivalent", "different", "undecided"}
            or len(set(assessment.occurrences)) != 2
            or any(identifier not in occurrences for identifier in assessment.occurrences)
        ):
            raise RichRuleEvaluationRefused(
                "rich rules require actual scientific occurrence assessments"
            )
    for identifier, occurrence in sorted(predicate_occurrences.items()):
        relations.check_active()
        if identifier in state.retained_member_ids:
            continue
        fact, definition, prop, qualification, raw_value = terms[identifier]
        findings, unknown = [], identifier in unresolved
        severity: RuleSeverity
        evidence = tuple(
            sorted(
                {
                    rich_reference_key(ref): ref
                    for ref in (
                        occurrence.original,
                        *((occurrence.statement,) if occurrence.statement else ()),
                    )
                }.values(),
                key=rich_reference_key,
            )
        )

        def assess(rule, outcome, severity, reason, semantic_reason=None):
            identity = canonical_identity(
                "rich-rule-assessment",
                [
                    policy.version,
                    policy_digest,
                    identifier,
                    rule,
                    severity,
                    semantic_reason_identity(semantic_reason)
                    if semantic_reason is not None
                    else reason,
                ],
            ).key
            assessments.append(
                DdoRichAssessment(
                    member_type="assessment",
                    assessment_id=identity,
                    occurrences=(identifier,),
                    rule=rule,
                    outcome=outcome,
                    severity=severity,
                    reason=reason,
                    evidence_members=evidence,
                )
            )
            return identity

        reading, reading_reason = _reading(
            prepared,
            context_profile,
            occurrence,
            raw_value,
            qualification,
            contexts.get(rich_reference_key(occurrence.original)),
            readings,
        )
        if reading_reason is not None:
            unknown = True
            finding_id = assess(
                "operation.not_checkable",
                "undecided",
                "warning",
                reading_reason.render(),
                reading_reason,
            )
            findings.append(
                RichRuleFinding("operation.not_checkable", "not-checkable", "warning", finding_id)
            )
        try:
            nodes = _condition_nodes(qualification.get("condition"), identifier, prepared)
            claim_refs = tuple(sorted({node.ref for node in nodes if node.ref is not None}))
        except _ProjectionUnavailable as error:
            nodes = claim_refs = _Unavailable(error.reason)
            unknown = True
            finding_id = assess(
                "operation.not_checkable",
                "undecided",
                "warning",
                error.reason.render(),
                error.reason,
            )
            findings.append(
                RichRuleFinding("operation.not_checkable", "not-checkable", "warning", finding_id)
            )
        bindings = (
            tuple(
                BindingView(
                    row["symbol"],
                    row["kind"],
                    row.get("entity"),
                    row.get("claim"),
                    row.get("parameter"),
                )
                for row in raw_value.get("bindings", ())
            )
            if isinstance(raw_value, Mapping)
            else ()
        )
        same = tuple(
            sorted(
                {
                    by_occurrence[item]
                    for item in view_rows.get((identifier, "same_slot"), ())
                    if by_occurrence[item] != fact.fact_id
                }
            )
        )
        other = tuple(
            sorted(
                {
                    by_occurrence[item]
                    for item in view_rows.get((identifier, "alternative_of"), ())
                    if by_occurrence[item] != fact.fact_id
                }
            )
        )
        qvalues = {name: qualification.get(name) for name in policy.qprops}
        statement_id = _statement(occurrence.statement)
        view = _ClaimView(
            dict(
                id=identifier,
                key=identifier,
                predicate=policy.compact(prop.iri),
                groups=tuple(
                    policy.metadata.get((definition.name, prop.iri), {}).get("groups", ())
                ),
                subject=entities[fact.subject_entity],
                object=entities.get(raw_value) if isinstance(raw_value, str) else None,
                value=project_rule_value(prepared, prop, raw_value, reading),
                qualifiers=QualifiersView(qvalues),
                qualification_values={
                    name: project_rule_value(prepared, policy.qprops[name], value)
                    for name, value in qvalues.items()
                    if value is not None
                    and not policy.qprops[name].multivalued
                    and (
                        policy.qprops[name].range not in prepared.index.definitions
                        or policy.qprops[name].range == "Value"
                        or "Value"
                        in prepared.index.definitions[policy.qprops[name].range].ancestors
                    )
                },
                statement=StatementView(statement_id, statement_id, occurrence.statement_kind or "")
                if statement_id is not None
                else None,
                statement_kind=occurrence.statement_kind,
                statement_role=occurrence.statement_role,
                establishment=occurrence.establishment,
                bindings=bindings,
                condition_nodes=nodes,
                claim_refs=claim_refs,
                statement_premises=tuple(
                    sorted(
                        (premises.get(_statement(occurrence.statement), set()) | global_premises)
                        - {fact.fact_id}
                    )
                ),
                gives_symbols=tuple(sorted(gives[identifier])),
                given_by_others=tuple(
                    sorted(
                        symbol for symbol, owners in symbol_owners.items() if owners - {identifier}
                    )
                ),
                same_slot=same,
                alternative_of=other,
                evidence_count=occurrence.evidence_count,
                unresolved_symbols=sum(binding.bind == "unresolved" for binding in bindings),
                **{
                    name: view_rows.get((identifier, name), ())
                    for name in policy.source.get("views", {})
                },
            )
        )
        errors = False
        for raw, when, check in policy.rules:
            relations.check_active()
            severity = "warning" if raw["id"] in guideline_ids else raw.get("severity", "error")
            if not policy.applies(raw, class_name=definition.name, predicate=prop.iri):
                findings.append(RichRuleFinding(raw["id"], "not-applicable", severity, None))
                continue
            try:
                if not when.evaluate({"claim": view}):
                    findings.append(RichRuleFinding(raw["id"], "not-applicable", severity, None))
                elif check.evaluate({"claim": view}):
                    findings.append(RichRuleFinding(raw["id"], "passed", severity, None))
                else:
                    finding_id = assess(
                        raw["id"], "invalid", severity, raw.get("description", raw["id"])
                    )
                    findings.append(RichRuleFinding(raw["id"], "failed", severity, finding_id))
                    errors |= severity == "error"
            except _ProjectionUnavailable as error:
                unknown = True
                finding_id = assess(
                    raw["id"], "undecided", severity, error.reason.render(), error.reason
                )
                findings.append(RichRuleFinding(raw["id"], "not-checkable", severity, finding_id))
        status: OccurrenceStatus = (
            "rejected"
            if errors
            else "ambiguous"
            if other
            else "candidate"
            if unknown
            else "accepted"
        )
        decisions.append(RichRuleDecision(identifier, fact.fact_id, status, tuple(findings)))
    selected_facts = {
        identifier
        for identifier, fact in facts.items()
        if identifier not in state.retained_member_ids
        and policy.metadata.get(
            (state.property(fact.property_contract)[0].name, fact.predicate), {}
        ).get("cs:role")
        != "predicate"
    }
    # Display representatives are observable presentation choices, not equality
    # rewrites or evidence that other spellings were absent.
    display = defaultdict(list)
    for identifier in selected_facts:
        fact = facts[identifier]
        definition, prop, _ = state.property(fact.property_contract)
        if (
            not prop.multivalued
            and policy.metadata.get((definition.name, prop.iri), {}).get("cs:role") == "display"
        ):
            display[fact.subject_entity, fact.property_contract].append(identifier)
    for members in display.values():
        keep = min(
            members,
            key=lambda identifier: (str(state.value(facts[identifier].object_value)), identifier),
        )
        selected_facts.difference_update(set(members) - {keep})
    selected_occurrences = {
        identifier
        for identifier, occurrence in occurrences.items()
        if occurrence.fact_id in selected_facts and identifier not in state.retained_member_ids
    }
    selected_facts.update(
        decision.fact_id for decision in decisions if decision.status == "accepted"
    )
    selected_occurrences.update(
        decision.occurrence_id for decision in decisions if decision.status == "accepted"
    )
    equivalence = nx.Graph()
    equivalence.add_nodes_from(facts)
    retained_fact_ids = state.retained_member_ids.intersection(facts)
    retained_occurrence_ids = state.retained_member_ids.intersection(occurrences)
    for retained in state.retained_admissions:
        if (
            not set(retained.selected_fact_ids) <= retained_fact_ids
            or not set(retained.selected_occurrence_ids) <= retained_occurrence_ids
        ):
            raise RichRuleEvaluationRefused(
                "rich known eligibility lacks its exact unchanged graph members"
            )
        selected_facts.update(retained.selected_fact_ids)
        selected_occurrences.update(retained.selected_occurrence_ids)
        for representative in retained.scientific_representatives:
            equivalence.add_edge(representative.fact_id, representative.representative_fact_id)
    for assessment in scientific_assessments:
        if assessment.outcome == "equivalent":
            members = tuple(
                occurrences[identifier].fact_id for identifier in assessment.occurrences
            )
            equivalence.add_edges_from((members[0], other) for other in members[1:])
    representatives = []
    for component in nx.connected_components(equivalence):
        accepted = sorted(component & selected_facts)
        if accepted:
            component_id = canonical_identity("rich-scientific-component", sorted(component)).key
            representatives.extend(
                RichScientificRepresentative(identifier, accepted[0], component_id)
                for identifier in accepted
            )
    relations.check_active()
    return RichRuleEvaluation(
        tuple(sorted(assessments, key=lambda item: item.assessment_id)),
        tuple(decisions),
        frozenset(selected_facts),
        frozenset(selected_occurrences),
        tuple(sorted(representatives, key=lambda item: item.fact_id)),
        policy_digest,
    )
