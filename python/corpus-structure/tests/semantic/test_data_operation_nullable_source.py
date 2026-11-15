"""Source-free project subjects retain a checked scope and an explicit null identity."""

from dataclasses import replace

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_compilation import compile_data_operations, project_operation_binding
from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand
from corpus_structure.semantic.data_operation_identity import body_identity, contextual_product_identity
from corpus_structure.semantic.data_operation_model import SubjectContext, validate_subject_context
from corpus_structure.semantic.data_operation_service import DemandRoot
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, SourceSetEntry
from corpus_structure.semantic.data_product_reference import DataProductReference
from semantic.data_operation_declaration_support import contract, declarations, resolved_binding


def model(scope, *, identifier="universe:arbitrary"):
    return compile_data_operations(declarations=declarations(contract(subject=identifier, subject_definition={"id": identifier, "identifier_kind": "string", "scope": scope})))


def test_nullable_project_subject_uses_actual_checked_scope_and_identity():
    acquired = model("project")
    context = SubjectContext("project:A", "knowledge:A", None, b"{}", subject_definition="universe:arbitrary")
    validate_subject_context(acquired, context)
    frozen = freeze_demand(acquired, roots=(RootSubject(context.subject, None, b"{}"),), targets=(acquired.operations[0].semantic_id,), inference="declared", execution_profile="controlled")
    assert frozen.record["roots"][0]["original_source"] is None
    body = body_identity("equal value").key
    source_free = contextual_product_identity(kind="kind:A", context=context, body=body).key
    assert source_free != contextual_product_identity(kind="kind:A", context=replace(context, original_source="source:A"), body=body).key
    assert source_free != contextual_product_identity(kind="kind:A", context=replace(context, original_source="None"), body=body).key


@pytest.mark.parametrize("scope", ["original-source", "original-document", "selected-source-set", "invocation"])
def test_source_required_subjects_cannot_be_made_source_free_by_their_name(scope):
    acquired = model(scope, identifier="project")
    with pytest.raises(ValueError, match="only a checked project-scoped"):
        freeze_demand(acquired, roots=(RootSubject("project-as-name", None, b"{}"),), targets=(acquired.operations[0].semantic_id,), inference="declared", execution_profile="controlled")


def test_project_context_shape_is_not_permission_for_request_binding():
    acquired = model("project")
    binding = resolved_binding(acquired)
    source_free = replace(binding,
        subject_context=replace(binding.subject_context, subject_definition=acquired.operations[0].subject, original_source=None),
        roles=tuple(replace(role, members=tuple(replace(member, subject_definition=acquired.operations[0].subject, original_source=None) for member in role.members)) for role in binding.roles),
    )
    request, _ = project_operation_binding(acquired, source_free)
    assert request.subject_context.original_source is None
    source_scoped = replace(acquired, subject_definitions=(replace(acquired.subject_definitions[0], scope="original-source"),))
    with pytest.raises(ValueError, match="only a checked project-scoped"):
        project_operation_binding(source_scoped, source_free)


def test_explicit_null_is_a_required_root_field_and_semantic_source_set_pin():
    root = DemandRoot(subject="knowledge", original_source=None, analyzed_scope={})
    assert root.model_dump()["original_source"] is None
    with pytest.raises(ValidationError, match="original_source"):
        DemandRoot.model_validate({"subject": "knowledge", "analyzed_scope": {}})
    acquired = model("project")
    context = SubjectContext("project:A", "knowledge", None, b"{}", subject_definition="universe:arbitrary")
    entry = SourceSetEntry.from_semantic_source(DataProductReference("product:knowledge"), context=context)
    assert entry.original_source is None
    validate_subject_context(acquired, context)
    assert FrozenSourceSet("retained", (entry,)).entries == (entry,)


def test_member_projection_allows_null_only_for_its_checked_project_subject():
    from corpus_structure.semantic.data_operation_ports import PortRefusal, project_product_members
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle

    schema = b"""id: urn:nullable-member
name: nullable_member
prefixes: {ex: 'urn:nullable-member:'}
default_prefix: ex
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
 Item:
  attributes:
   label: {range: string}
 Packet:
  attributes:
   body: {range: Item}
 Container:
  attributes:
   members: {range: Packet, multivalued: true}
"""
    acquired = compile_data_operations(SourceBundle("nullable_member", (SourceArtifact("nullable_member", schema),)), declarations=declarations(contract(subject="universe", subject_definition={"id": "universe", "identifier_kind": "string", "scope": "project"})))
    item = next(identity.key for identity in acquired.identities if identity.owner == "urn:nullable-member:Item" and identity.domain == "kind")
    value = {"members": [{"member_id": "knowledge", "kind_contract": item, "body": {"label": "equal data"}, "context": {"subject": "knowledge", "subject_definition": "universe", "original_source": None, "analyzed_scope": {}}}]}
    assert len(project_product_members(acquired, "urn:nullable-member:Container", value)) == 1
    scoped = replace(acquired, subject_definitions=(replace(acquired.subject_definitions[0], scope="original-source"),))
    with pytest.raises(PortRefusal, match="only a checked project-scoped"):
        project_product_members(scoped, "urn:nullable-member:Container", value)
