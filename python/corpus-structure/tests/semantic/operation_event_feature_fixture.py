"""Controlled real CPU numerical features from actual selected report/source values.

No authored value impersonates a computed report or receipt. This fixture grants
no interpretation authority: it only exercises existing source feature arithmetic
and the native ordered primitive-output transport used by the declared scorer.
"""

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from corpus_structure.semantic.identity import canonical_bytes

MODULE = "semantic.operation_event_feature_fixture"
ASSET = "operation-event-fixture/features"
OPERATION = "fixture.operation_event_features"


class OperationEventFeatures:
    __data_operation__: ClassVar[dict] = {
        "id": "fixture.operation_event_features",
        "profile": "derivation",
        "subject": "fitted-operation-event",
        "subject_definition": {
            "id": "fitted-operation-event",
            "identifier_kind": "string",
            "scope": "project",
        },
        "discovery_relation": "role-associated",
        "entrypoints": ["run"],
        "context": ["actual-selected-report-and-source", "controlled-numerical-feature-transport"],
        "roles": [
            {
                "name": "report",
                "parameter": "report",
                "kind": "urn:corpus:structural:DeclaredDefinitionComponentsReport",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "event-score-report",
                    "identity_requirements": ["episode"],
                    "coverage": {"role": "report", "description": "exact-whole-report"},
                },
            },
            {
                "name": "source",
                "parameter": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "event-score-source",
                    "identity_requirements": ["episode"],
                    "coverage": {"role": "source", "description": "exact-source-piece"},
                },
            },
            {
                "name": "features",
                "kind": "float",
                "direction": "output",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
            },
        ],
        "applicability": [
            {"kind": "documentation", "text": "exact-component-source-feature-arithmetic"}
        ],
        "invariants": [{"kind": "documentation", "text": "real-ordered-primitive-feature-output"}],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "complete-selected-feature-vector",
        },
        "outcomes": ["success"],
        "precision_description": "existing-float64-feature-arithmetic",
        "dependencies": [],
        "effects": [],
        "parameters": {
            "component_id": {"value_type": "string", "required": True},
            "event": {"value_type": "string", "required": True},
        },
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-cpu",
        },
        "behavior": "controlled-current-source-feature-vector-1",
        "binding": {"operator": "scan", "roles": ["report", "source"]},
        "opaque": [
            {
                "reference": "semantic.operation_event_feature_fixture.kernel",
                "contract": "operation-event-fixture/features",
                "role": "actual-source-feature-arithmetic",
            }
        ],
        "assets": [
            {
                "reference": "features",
                "contract": "operation-event-fixture/features",
                "role": "actual-current-feature-kernel",
            }
        ],
    }

    def run(
        self, report: dict, source: dict, *, component_id: str, event: str
    ) -> tuple[float, ...]:
        raise ValueError("controlled feature transport requires its acquired source plan")

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort

        selected = model.operation(operation)
        if selected.semantic_id != OPERATION or selected.effects:
            raise ValueError(
                "controlled feature fixture requires its actual pure declared operation"
            )
        receiver = OperationEventFeatures()
        plan = FeaturePlan(prepared)
        port = PreparedOriginalCallPort(
            identity,
            model,
            selected,
            sources,
            custody,
            receiver.run,
            plan.plan,
            MODULE + ".FeaturePlan.plan",
            authorize,
            (assets(),),
            operation_sources(),
            functions=((MODULE + ".kernel", kernel),),
            requires_prepared_schema=True,
            retain_cpu_reply=True,
        )
        plan.port = port
        return port


def assets():
    from corpus_structure.evaluate.declared_operation_events import (
        operation_event_computation_assets,
    )
    from corpus_structure.semantic.python_module_projection import admitted_operation_module_meaning
    from corpus_structure.semantic.types import SourceArtifact

    return SourceArtifact(
        ASSET,
        canonical_bytes(
            dict(
                fixture=admitted_operation_module_meaning(Path(__file__).read_bytes()).hex(),
                computation=operation_event_computation_assets().content.hex(),
            )
        ),
    )


def operation_sources():
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    return PythonSourceCollection(
        (PythonSource(MODULE, Path(__file__).read_bytes(), str(Path(__file__).resolve())),),
        boundary_contracts=(assets(),),
    )


def kernel(input_basis: list, *, prepared, check_active) -> dict:
    from corpus_structure.evaluate.selected_operation_events import component_event_features
    from corpus_structure.semantic.data_operation_cpu_basis import (
        cpu_authority_reply,
        cpu_basis_values,
    )
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.source_products import FrozenNativeSource
    from corpus_structure.semantic.structural_products import DeclaredDefinitionComponentsReport

    grouped, _ = cpu_basis_values(input_basis, scalar_roles=("report", "source"), set_roles=())
    report = DeclaredDefinitionComponentsReport.model_validate_json(
        json_bytes(grouped["report"][0].body)
    )
    source_row = grouped["source"][0]
    source = FrozenNativeSource.acquire(prepared, source_row.body)
    coordinate = source.value["source"]
    pin = DeclaredStructuralSource.model_validate(
        DeclaredRecordSource(
            coordinate["document"],
            coordinate["projection"],
            coordinate["section_pointer"],
            coordinate["membership"],
            source_row.context,
            source_row.product_id,
            source_row.member_id,
            source_row.kind_contract,
        ).pin()
    )
    parameters = decode_semantic_value(input_basis)["parameters"]
    check_active()
    features = component_event_features(
        report, parameters["component_id"], source, pin, parameters["event"]
    )
    if features.features is None:
        raise ValueError("selected current numerical features are unavailable")
    check_active()
    return cpu_authority_reply(input_basis, features.features)


@dataclass
class FeaturePlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.evaluate.declared_operation_events import _input_basis
        from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_value
        from corpus_structure.semantic.data_operation_prepared_call import PreparedCallResult

        basis = _input_basis(self.port, binding, arguments.arguments)
        bound = inspect.signature(kernel).bind(
            basis, prepared=self.prepared, check_active=check_active
        )
        reply = yield from self.port.plan_cpu_reply(
            kernel,
            bound,
            operation_sources(),
            prepared_release_id=self.prepared.release_id,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        value = cpu_authority_value(reply.content, expected_basis=basis)
        return PreparedCallResult(
            tuple(value),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )
