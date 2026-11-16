"""Finite count-definition matcher with authentic current source/CPU custody.

Three distinct role carriers include two on the same physical span. The captured
literal matcher supplies private controlled interpretation, not provider evidence.
"""

import inspect
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, ClassVar

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.identity import canonical_bytes

TEXT = "A count means a number."
MODULE = "semantic.contextual_native_fixture"
ASSET = "contextual-native-fixture/source-assets"
CUES = "fixture.contextual_cues"
COMPONENTS = "fixture.contextual_components"


def source_values(prepared, model, source, pin, context, source_input):
    from corpus_structure.semantic.contributions import (
        bind_contributions,
        contribution_identity,
        occurrence_identity,
        operation_identity,
    )
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.declared_candidate_products import candidate_inspection_report
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.record_contracts import anchor_identity
    from corpus_structure.semantic.structural_products import (
        DeclaredDefinitionComponentsReport,
        declared_definition_component,
    )

    if source["text"] != TEXT:
        raise ValueError("controlled count matcher requires its exact complete literal")
    (piece,) = [row for row in source["pieces"] if row["kind"] == "native_text"]
    if (piece["start"], piece["end"]) != (0, len(TEXT)):
        raise ValueError("controlled count matcher requires the actual complete source piece")
    frame = DeclaredNativeFrameSource(
        canonical_bytes(source).decode(), canonical_bytes(pin).decode()
    )
    source_ref = DeclaredStructuralSource.model_validate(pin)
    trace = (
        "annotation:"
        + sha256(canonical_bytes([pin, TEXT, "finite-count-definition-1"])).hexdigest()
    )
    question = "controlled_literal_definition_roles"
    operation = dict(
        operation_key=operation_identity(question, "1", pin, "finite-count-definition-1"),
        question=question,
        operation_version="1",
        outcome="succeeded",
        inspected_count=1,
        emitted_count=3,
        computation_dependencies=(pin["source"],),
    )
    rows = []
    for role, literal in (("subject", "count"), ("unrelated", "count"), ("object", "number")):
        start = TEXT.index(literal)
        anchor = dict(
            pin=pin,
            space="native",
            pointer=piece["item_ref"],
            precision="exact",
            start=start,
            end=start + len(literal),
            source_piece=literal,
        )
        anchor["anchor_id"] = anchor_identity(anchor)
        row = dict(
            contract="RetainedContributionSemantics",
            kind="occurrence",
            semantic_type="source_rule." + role,
            item_key=role,
            operation_key=operation["operation_key"],
            pin=pin,
            anchors=(anchor,),
            occurrence_id=occurrence_identity((anchor,)),
            disposition="located_proposal",
            standing="retained_private",
            score_state="missing",
            computation_dependencies=(trace,),
        )
        checked = prepared.validate_json(
            "SourceContribution",
            json_bytes(dict(row, contribution_id="source-contribution:" + "0" * 64)),
        ).model_dump(mode="python")
        checked["contribution_id"] = contribution_identity(checked)
        rows.append(checked)
    coordinate = dict(pin=pin, space="native", pointer=piece["item_ref"], text=TEXT)
    operations, contributions = bind_contributions(
        prepared,
        source=pin["source"],
        operations=[operation],
        contributions=rows,
        coordinate_texts=(coordinate,),
    )
    actual_context = SubjectContext(
        context["project_id"],
        context["subject"],
        context["original_source"],
        canonical_bytes(context["analyzed_scope"]),
        subject_definition=context["subject_definition"],
    )
    predicates = candidate_inspection_report(
        prepared,
        model,
        frame,
        actual_context,
        inspection_outcome="produced",
        contributions=contributions,
        operations=operations,
        coordinate_texts=(coordinate,),
        coverage=(
            dict(
                family="controlled-literal-definition-roles",
                scope=pin["source"],
                outcome="produced",
            ),
        ),
        diagnostics=dict(controlled_finite_grammar="finite-count-definition-1", annotation=trace),
        report_class="DdoPredicateInspectionReport",
    )

    def span(literal):
        start = TEXT.index(literal)
        return dict(passage_id="clause", start=start, end=start + len(literal), text=literal)

    component = declared_definition_component(
        term=span("count"),
        content=span("number"),
        interpretation="definition",
        basis="matched_cue",
        scope="selected",
        evidence=("clause",),
        reason="Captured finite literal matcher recognizes only the complete count-means-number clause; independent support remains unassessed.",
    )
    components = DeclaredDefinitionComponentsReport.model_validate(
        dict(
            inputs=dict(
                question="Locate the controlled explicit count definition",
                scope="selected",
                inventory_id="finite-count-definition",
                policy_id="finite-count-definition-1",
                sources=[source_ref],
                passages=[
                    dict(
                        passage_id="clause",
                        source_ref=source_ref.identity,
                        start=0,
                        end=len(TEXT),
                        text=TEXT,
                        scope="selected",
                    )
                ],
                dependencies=[pin["source_product"]],
            ),
            definition_components=dict(
                components=[component],
                stages=[
                    dict(
                        passage_id="clause",
                        operation="attachment",
                        outcome="succeeded",
                        reason="Complete literal matched the finite definition rule.",
                    )
                ],
            ),
            sources_input=[source_input],
        )
    ).model_dump(mode="python")
    introductions = DeclaredDefinitionComponentsReport.model_validate(
        {
            **components,
            "inputs": {
                **components["inputs"],
                "question": "Which passage introduces count as a number?",
            },
        }
    ).model_dump(mode="python")
    return dict(predicates=predicates, components=components, introductions=introductions)


def _matched_source_values(input_basis: list, *, prepared, check_active) -> dict:
    from corpus_structure.semantic.contextual_witnesses import contextual_input_reference
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_basis_values
    from corpus_structure.semantic.declared_record_sources import (
        DeclaredNativeFrameSource,
        DeclaredRecordSource,
    )
    from corpus_structure.semantic.structural_products import DeclaredStructuralInputPin

    check_active()
    roles, context = cpu_basis_values(input_basis, scalar_roles=("source",), set_roles=())
    if set(roles) != {"source"} or len(roles["source"]) != 1:
        raise ValueError("finite matcher requires its actual exact source basis")
    row = roles["source"][0]
    actual = row
    if actual.context != context:
        raise ValueError("finite matcher source differs from its actual output context")
    source = actual.body
    coordinate = source["source"]
    address = DeclaredRecordSource(
        coordinate["document"],
        coordinate["projection"],
        coordinate["section_pointer"],
        coordinate["membership"],
        actual.context,
        actual.product_id,
        actual.member_id,
        actual.kind_contract,
    )
    frame = DeclaredNativeFrameSource(
        canonical_bytes(source).decode(), canonical_bytes(address.pin()).decode()
    )
    source_input = DeclaredStructuralInputPin(
        **contextual_input_reference(row).model_dump(),
        reference=canonical_bytes([actual.product_id, actual.member_id]).decode(),
    )
    result = source_values(
        prepared,
        bound_data_operation_model(prepared),
        source,
        frame.pin.values(),
        context.record,
        source_input.model_dump(mode="python"),
    )
    return result


def execute_cue_kernel(input_basis: list, *, prepared, check_active) -> dict:
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_reply

    result = _matched_source_values(input_basis, prepared=prepared, check_active=check_active)
    return cpu_authority_reply(input_basis, result["predicates"])


def execute_component_kernel(input_basis: list, *, prepared, check_active) -> dict:
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_reply
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value

    parameters = decode_semantic_value(input_basis)["parameters"]
    if set(parameters) != {"purpose"} or parameters["purpose"] not in {"meaning", "introduction"}:
        raise ValueError(
            "finite component matcher requires an explicit definition or introduction purpose"
        )
    result = _matched_source_values(input_basis, prepared=prepared, check_active=check_active)
    return cpu_authority_reply(
        input_basis, result["components" if parameters["purpose"] == "meaning" else "introductions"]
    )


def execute_cue_profile(receiver, source):
    return receiver.execute(source)


def execute_component_profile(receiver, source, purpose):
    return receiver.execute(source, purpose=purpose)


class ControlledContextualCues:
    __data_operation__: ClassVar[dict] = {
        "id": "fixture.contextual_cues",
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
                    "source_set": "fixture-contextual-source",
                    "identity_requirements": ["episode"],
                    "coverage": {"role": "source", "description": "actual-selected-source"},
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoPredicateInspectionReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [
            {"kind": "documentation", "text": "exact-finite-count-definition-source-only"}
        ],
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
        "parameters": {},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-cpu",
        },
        "behavior": "controlled-finite-source-role-carriers",
        "binding": {"operator": "scan", "roles": ["source"]},
        "opaque": [
            {
                "reference": "semantic.contextual_native_fixture.execute_cue_profile",
                "contract": "contextual-native-fixture/source-assets",
                "role": "controlled-finite-source-computation",
            }
        ],
        "assets": [
            {
                "reference": "controlled-source-inventory",
                "contract": "contextual-native-fixture/source-assets",
                "role": "actual-controlled-computation-bytes",
            }
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, source: dict) -> dict:
        return execute_cue_profile(self, source)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        return resolve_fixture_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )


class ControlledContextualComponents:
    __data_operation__: ClassVar[dict] = {
        "id": "fixture.contextual_components",
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
                    "source_set": "fixture-contextual-source",
                    "identity_requirements": ["episode"],
                    "coverage": {"role": "source", "description": "actual-selected-source"},
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "urn:corpus:structural:DeclaredDefinitionComponentsReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [
            {"kind": "documentation", "text": "exact-finite-count-definition-source-only"}
        ],
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
        "parameters": {"purpose": {}},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-cpu",
        },
        "behavior": "controlled-finite-count-definition",
        "binding": {"operator": "scan", "roles": ["source"]},
        "opaque": [
            {
                "reference": "semantic.contextual_native_fixture.execute_component_profile",
                "contract": "contextual-native-fixture/source-assets",
                "role": "controlled-finite-source-computation",
            }
        ],
        "assets": [
            {
                "reference": "controlled-source-inventory",
                "contract": "contextual-native-fixture/source-assets",
                "role": "actual-controlled-computation-bytes",
            }
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, source: dict, purpose: str) -> dict:
        return execute_component_profile(self, source, purpose)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        return resolve_fixture_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )


@dataclass
class FixtureCallPlan:
    prepared: Any
    kernel: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.semantic.data_operation_cpu_basis import cpu_input_basis_from_binding

        if binding is None or binding.subject_context is None or not binding.sufficient:
            raise ValueError("controlled matcher requires actual sufficient native source support")
        basis = cpu_input_basis_from_binding(
            self.port.operation.recipe, binding, {"source": (arguments.arguments["source"],)}
        )
        bound = inspect.signature(self.kernel, eval_str=True).bind(
            input_basis=basis, prepared=self.prepared, check_active=check_active
        )
        return (
            yield from self.port.plan_cpu(
                self.kernel,
                bound,
                operation_sources(),
                prepared_release_id=self.prepared.release_id,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def resolve_fixture_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort

    if operation == CUES:
        receiver, kernel = ControlledContextualCues(None), execute_cue_kernel
    elif operation == COMPONENTS:
        receiver, kernel = ControlledContextualComponents(None), execute_component_kernel
    else:
        raise ValueError("finite source factory belongs to another declared operation")
    plan = FixtureCallPlan(prepared, kernel)
    port = PreparedOriginalCallPort(
        identity,
        model,
        model.operation(operation),
        sources,
        custody,
        receiver.run,
        plan.plan,
        MODULE + ".FixtureCallPlan.plan",
        authorize,
        (assets(),),
        operation_sources(),
        functions=((MODULE + "." + kernel.__name__, kernel),),
        requires_prepared_schema=True,
        retain_cpu_reply=True,
    )
    plan.port = port
    return port


def assets():
    from corpus_structure.semantic.python_module_projection import admitted_operation_module_meaning
    from corpus_structure.semantic.types import SourceArtifact

    return SourceArtifact(
        ASSET,
        canonical_bytes(
            dict(
                version="controlled-finite-contextual-source-1",
                source=admitted_operation_module_meaning(Path(__file__).read_bytes()).hex(),
            )
        ),
    )


def operation_sources():
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    path = Path(__file__).resolve()
    return PythonSourceCollection(
        (PythonSource(MODULE, path.read_bytes(), str(path)),), boundary_contracts=(assets(),)
    )
