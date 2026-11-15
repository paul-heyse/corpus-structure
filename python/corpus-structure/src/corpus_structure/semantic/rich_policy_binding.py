"""Resolve rich policy references to their single captured preparation owners."""

from hashlib import sha256

from pydantic import TypeAdapter

from .analysis_contracts import AnalysisContextProfile
from .identity import canonical_bytes
from .rich_knowledge_sources import RULE_INPUT
from .scientific_evidence import SCIENTIFIC_POLICY_INPUT, scientific_policy_recipe

RICH_CONTEXT_INPUT = "operation/rich-analysis-context.json"


def _artifact(prepared, name):
    values = [item for item in prepared.artifacts if item.kind == name]
    if len(values) != 1:
        raise ValueError("rich policy requires its exact captured owner: " + name)
    return values[0].content


def rich_context_profile(prepared) -> AnalysisContextProfile:
    profile = TypeAdapter(AnalysisContextProfile).validate_json(
        _artifact(prepared, RICH_CONTEXT_INPUT)
    )
    if canonical_bytes(scientific_policy_recipe(context_profile=profile)) != _artifact(
        prepared, SCIENTIFIC_POLICY_INPUT
    ):
        raise ValueError("rich analysis context differs from its actual captured scientific policy")
    return profile


def rich_policy_value(prepared, model, *, allowed_domain_contracts=None):
    from .rich_knowledge_contracts import DdoRichConsolidationPolicy
    from .statement_types import effective_bindings

    selected = effective_bindings(prepared)
    qualification = prepared.qualification_definition(selected["qualification"])
    statement = selected["statement"]
    if statement is None:
        raise ValueError("rich knowledge requires its actual checked statement binding")
    # Effective bindings are serialized immutable records, not runtime type labels.
    statement_name = statement["class_name"]
    definition = prepared.index.definitions[statement_name]
    contracts = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    classes = {
        contracts[definition.iri]: definition
        for definition in prepared.definitions
        if (definition.name == "Entity" or "Entity" in definition.ancestors)
        and definition.name != "SourceReading"
        and "SourceReading" not in definition.ancestors
        and definition.iri in contracts
    }
    if allowed_domain_contracts is None:
        allowed_domain_contracts = tuple(sorted(classes))
    if (
        not allowed_domain_contracts
        or len(set(allowed_domain_contracts)) != len(allowed_domain_contracts)
        or any(contract not in classes for contract in allowed_domain_contracts)
    ):
        raise ValueError(
            "rich domain policy requires its actual checked Entity-class contract universe"
        )
    return DdoRichConsolidationPolicy(
        version="rich-consolidation-policy-1",
        qualification_contract=contracts[qualification.iri],
        statement_contract=contracts[definition.iri],
        allowed_domain_contracts=tuple(sorted(allowed_domain_contracts)),
        rules_digest=sha256(_artifact(prepared, RULE_INPUT)).hexdigest(),
        scientific_digest=sha256(_artifact(prepared, SCIENTIFIC_POLICY_INPUT)).hexdigest(),
        analysis_profile_digest=rich_context_profile(prepared).model_id,
    )


def require_rich_policy(prepared, model, value):
    from .rich_knowledge_contracts import DdoRichConsolidationPolicy

    actual = DdoRichConsolidationPolicy.model_validate(value)
    if actual != rich_policy_value(
        prepared, model, allowed_domain_contracts=actual.allowed_domain_contracts
    ):
        raise ValueError(
            "rich interpretation policy differs from its actual checked captured owners"
        )
    return actual


def rich_eligibility_policy_digest(checked_policy, model) -> str:
    """Actual checked policy and the selected consolidation implementation recipe."""
    from .data_operation_identity import semantic_value
    from .refusals import SemanticRefusal

    recipes = tuple(identity.key for identity in model.identities
                    if identity.domain == "recipe" and identity.owner == "rich.consolidate")
    if len(recipes) != 1 or not any(operation.semantic_id == "rich.consolidate" for operation in model.operations):
        raise SemanticRefusal("rich eligibility requires its actual bound consolidation recipe")
    return sha256(canonical_bytes(semantic_value({
        "policy": checked_policy.model_dump(mode="python"), "recipe": recipes[0],
    }))).hexdigest()
