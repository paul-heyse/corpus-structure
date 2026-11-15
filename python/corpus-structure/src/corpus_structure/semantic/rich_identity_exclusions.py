"""Materialized source declarations and their explicit current resolution outcome."""

from .data_operation_identity import canonical_identity, semantic_value
from .data_operation_model import SubjectContext
from .identity import canonical_bytes
from .rich_knowledge_contracts import DdoRichIdentityExclusion, DdoRichLocatedEvidence


def rich_identity_exclusion_id(context: SubjectContext, *, declaration, left_entity_id, right_entity_id,
                               outcome, reason, source_members) -> str:
    """Identity of this exact computed constraint, never a source-declaration match key."""
    return canonical_identity("rich-identity-exclusion", [context.identity_record, semantic_value(declaration.model_dump(mode="python")),
        left_entity_id, right_entity_id, outcome, reason,
        [semantic_value(item.model_dump(mode="python")) for item in source_members],
    ]).key


def rich_located_evidence(prepared, value) -> DdoRichLocatedEvidence:
    """Project an already captured source boundary; None means an absent optional slot."""
    checked = prepared.validate_python("AgentLocatedEvidence", value)
    return DdoRichLocatedEvidence.model_validate(checked.model_dump(mode="python", exclude_unset=True))


def validate_rich_identity_exclusion(prepared, context: SubjectContext, value: DdoRichIdentityExclusion):
    """Reuse the actual captured source/evidence boundary; grant no native standing."""
    declaration = value.declaration
    source, pin = declaration.source, declaration.context
    expected_context = (source.project_id, source.subject, source.subject_definition, source.original_source, source.analyzed_scope_meaning)
    actual_context = (pin.project_id, pin.subject, pin.subject_definition, pin.original_source, pin.analyzed_scope_meaning)
    if expected_context != actual_context or pin.project_id != context.project_id:
        raise ValueError("rich identity exclusion declaration differs from its actual source context")
    reference = value.source_members[0]
    if reference.member_id != "identity_exclusion:" + declaration.local_id:
        raise ValueError("rich identity exclusion differs from its actual source-local declaration address")
    primary = False
    for evidence in declaration.evidence:
        original = evidence.model_dump(mode="python", exclude_none=True)
        checked = prepared.validate_python("AgentLocatedEvidence", original)
        if canonical_bytes(semantic_value(checked.model_dump(mode="python", exclude_unset=True))) != canonical_bytes(semantic_value(original)):
            raise ValueError("rich identity exclusion evidence changed at its captured source boundary")
        if evidence.outcome == "located":
            if not evidence.locator or evidence.start is None or evidence.end is None or evidence.end <= evidence.start:
                raise ValueError("located identity exclusion evidence lacks its actual bounded source extent")
            if evidence.role == "primary":
                primary = True
    expected = "unlocated" if not primary else "unresolved-endpoint" if None in (value.left_entity_id, value.right_entity_id) else "located"
    if value.outcome != expected:
        raise ValueError("rich identity exclusion outcome differs from actual evidence and endpoint resolution")
    for endpoint, entity in ((declaration.left, value.left_entity_id), (declaration.right, value.right_entity_id)):
        if endpoint.kind == "known" and entity is not None and entity != endpoint.target:
            raise ValueError("rich identity exclusion known endpoint changed its actual entity")
    if value.outcome == "located" and value.left_entity_id == value.right_entity_id:
        raise ValueError("located identity exclusion contradicts its actual resolved identity")
    identifier = rich_identity_exclusion_id(context, declaration=declaration, left_entity_id=value.left_entity_id, right_entity_id=value.right_entity_id,
                                            outcome=value.outcome, reason=value.reason, source_members=value.source_members)
    if identifier != value.exclusion_id:
        raise ValueError("rich identity exclusion identity differs from its exact declaration and resolution meaning")
