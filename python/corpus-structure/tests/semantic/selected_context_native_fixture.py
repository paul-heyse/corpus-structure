"""Finite independently authored primary rows; only the E5 encoder is provider evidence."""

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from corpus_structure.semantic.identity import canonical_bytes

MODULE = "semantic.selected_context_native_fixture"
ASSET = "selected-context-native-fixture/source-assets"
OPERATION = "fixture.selected_context_inventory"


def execute_profile(receiver, source, recipe):
    raise ValueError("finite primary fixture requires its actual acquired CPU plan")


def execute_kernel(source: dict, recipe: str, pin: dict, context: dict, source_input: dict, *, prepared, check_active) -> dict[str, dict]:
    from corpus_structure.semantic.contributions import contribution_identity, operation_identity
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from semantic.selected_context_support import case

    check_active()
    frame = DeclaredNativeFrameSource(canonical_bytes(source).decode(), canonical_bytes(pin).decode())
    _, occurrence, primary, _, _, _ = case(recipe, frame=frame)
    occurrence.update(
        contract="RetainedContributionSemantics", candidate_type="contribution",
        operation_key=operation_identity("finite_selected_context", "1", pin, recipe),
        item_key="finite-focal:" + recipe, disposition="located_proposal", standing="retained_private",
        score_state="missing", computation_dependencies=(pin["source"],),
    )
    occurrence = prepared.validate_json("DdoCandidateSourceContribution", json_bytes(occurrence)).model_dump(mode="python")
    occurrence["contribution_id"] = contribution_identity(occurrence)
    body = dict(primary[0], coverage=[])
    # Packet contexts are not addresses; the projection retains these exact authored rows.
    model = bound_data_operation_model(prepared)
    member_contract = next(item.key for item in model.identities if item.domain == "kind" and item.owner == "urn:corpus:test:selected-context/SelectedContextMember")
    for packet in body["members"]:
        packet["kind_contract"] = member_contract
        packet["context"] = {key: context[key] for key in ("subject", "subject_definition", "original_source", "analyzed_scope")}
    return dict(occurrence=occurrence, primary=body)


class SelectedContextInventory:
    __data_operation__: ClassVar[dict] = {
        "id": "fixture.selected_context_inventory",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {
            "id": "original-source-view",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "role-associated",
        "context": ["controlled-finite-native-source-grammar"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "parameter": "source",
                "direction": "input",
                "subject_target": "source-set",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "fixture-selected-context-source",
                    "identity_requirements": ["episode"],
                    "coverage": {"role": "source", "description": "actual-selected-source"},
                },
            },
            {
                "name": "occurrence",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
            {
                "name": "primary",
                "direction": "output",
                "kind": "urn:corpus:test:selected-context/SelectedContextPrimary",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "result_fields": {"occurrence": "occurrence", "primary": "primary"},
        "applicability": [{"kind": "documentation", "text": "exact-finite-selected-context-source-only"}],
        "invariants": [
            {
                "kind": "documentation",
                "text": "controlled-extraction-is-not-provider-or-scientific-evidence",
            }
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "whole-finite-source",
        },
        "outcomes": ["success"],
        "precision_description": "exact-original-native-pieces",
        "dependencies": [],
        "effects": [],
        "parameters": {"recipe": {}},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-cpu",
        },
        "behavior": "controlled-finite-selected-primary",
        "binding": {"operator": "scan", "roles": ["source"]},
        "opaque": [
            {
                "reference": "semantic.selected_context_native_fixture.execute_profile",
                "contract": "selected-context-native-fixture/source-assets",
                "role": "controlled-finite-source-computation",
            }
        ],
        "assets": [
            {
                "reference": "controlled-source-inventory",
                "contract": "selected-context-native-fixture/source-assets",
                "role": "actual-controlled-computation-bytes",
            }
        ],
    }

    def run(self, source: dict, recipe: str) -> dict[str, dict]:
        return execute_profile(self, source, recipe)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort

        if operation != OPERATION:
            raise ValueError("controlled source factory belongs to another operation")
        receiver, plan = SelectedContextInventory(), SelectedContextPlan(prepared)
        port = PreparedOriginalCallPort(
            identity,
            model,
            model.operation(operation),
            sources,
            custody,
            receiver.run,
            plan.plan,
            MODULE + ".SelectedContextPlan.plan",
            authorize,
            (assets(),),
            operation_sources(),
            functions=((MODULE + ".execute_kernel", execute_kernel),),
            requires_prepared_schema=True,
        )
        plan.port = port
        return port


@dataclass
class SelectedContextPlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.semantic.data_operation_json import json_loads
        from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
        from corpus_structure.semantic.structural_products import DeclaredStructuralInputPin

        if binding is None or binding.subject_context is None or not binding.sufficient:
            raise ValueError(
                "controlled inventory requires actual sufficient native source support"
            )
        (role,) = [role for role in binding.roles if role.role == "source"]
        (member,) = role.members
        context = binding.subject_context
        frame = DeclaredNativeFrameSource.acquire(
            self.prepared, arguments.arguments["source"], member, project=context.project_id
        )
        bound = inspect.signature(execute_kernel, eval_str=True).bind(
            source=arguments.arguments["source"],
            recipe=arguments.arguments["recipe"],
            pin=frame.pin.values(),
            context=dict(
                project_id=context.project_id,
                subject=context.subject,
                original_source=context.original_source,
                subject_definition=context.subject_definition,
                analyzed_scope=json_loads(context.analyzed_scope),
            ),
            source_input=DeclaredStructuralInputPin.from_bound(
                member, project=context.project_id
            ).model_dump(mode="python"),
            prepared=self.prepared,
            check_active=check_active,
        )
        return (
            yield from self.port.plan_cpu(
                execute_kernel,
                bound,
                operation_sources(),
                prepared_release_id=self.prepared.release_id,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def schema():
    from corpus_structure.semantic.types import SourceArtifact
    return SourceArtifact("selected-context-fixture", b"""
id: urn:corpus:test:selected-context
name: selected_context_fixture
imports: [data_operation_source, observations]
classes:
  SelectedContextPrimary:
    is_a: DdoCharacterizationEnvelope
    class_uri: urn:corpus:test:selected-context/SelectedContextPrimary
    attributes:
      members: {range: SelectedContextPacket, inlined: true, multivalued: true, required: true}
      dependencies: {range: DdoSemanticProductReference, inlined: true, multivalued: true}
  SelectedContextPacket:
    is_a: SourceRecordProduct
    attributes:
      member_id: {required: true}
      kind_contract: {required: true}
      context: {range: DdoSourceViewContext, inlined: true, required: true}
      body: {range: SelectedContextMember, inlined: true, required: true}
  SelectedContextMember:
    class_uri: urn:corpus:test:selected-context/SelectedContextMember
    is_a: SourceRecordProduct
    attributes:
      record_type: {required: true}
      local_id: {required: true}
      kind: {}
      family: {}
      vocabulary: {}
      status: {}
      native_label: {}
      occurrences: {multivalued: true}
      children: {range: SelectedContextChild, multivalued: true, inlined: true}
      extents: {range: SelectedContextExtent, multivalued: true, inlined: true}
      native_mention: {range: SelectedContextMention, inlined: true}
      native_edu: {range: SelectedContextEdu, inlined: true}
      native_rst: {range: SelectedContextRst, inlined: true}
      group: {}
      member: {}
      order: {range: integer}
  SelectedContextChild:
    attributes:
      role: {required: true}
      target: {required: true}
  SelectedContextExtent:
    attributes:
      projection: {required: true}
      native_pointer: {required: true}
      start: {range: integer, required: true}
      end: {range: integer, required: true}
  SelectedContextMention:
    attributes:
      first: {range: integer, required: true}
      last: {range: integer, required: true}
      mapping_status: {required: true}
  SelectedContextEdu:
    attributes:
      index: {range: integer, required: true}
  SelectedContextRst:
    attributes:
      left_start: {range: integer, required: true}
      left_end: {range: integer, required: true}
      right_start: {range: integer, required: true}
      right_end: {range: integer, required: true}
      nuclearity: {required: true}
""")


def assets():
    from corpus_structure.semantic.types import SourceArtifact
    return SourceArtifact(ASSET, canonical_bytes({"fixture": "finite-selected-primary-1"}))


def operation_sources():
    from methods import contextual_query_support

    from corpus_structure.semantic import data_operation_prepared_call
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )
    from semantic import selected_context_support
    modules = (__import__(__name__, fromlist=["*"]), selected_context_support, contextual_query_support, data_operation_prepared_call)
    return PythonSourceCollection(tuple(PythonSource(module.__name__, Path(module.__file__).read_bytes(), str(Path(module.__file__).resolve())) for module in modules), boundary_contracts=(assets(),))
