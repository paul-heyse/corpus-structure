"""Controlled finite source inventory with genuine declared CPU/native custody.

The grammar recognizes only the complete literal ``Ada acts.``. Its annotations
are owned finite matcher traces, not external provider observations or accepted
science. The production comparison, issuer and dossier consume its real outputs.
"""

import inspect
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, ClassVar

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.identity import canonical_bytes

TEXT = "Ada acts."
MODULE = "semantic.structural_native_fixture"
ASSET = "structural-native-fixture/source-assets"
OPERATION = "fixture.structural_inventory"


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
        definition_component_packets,
        definition_component_report_values,
    )

    if source["text"] != TEXT:
        raise ValueError("controlled finite grammar requires its exact complete source text")
    (piece,) = [item for item in source["pieces"] if item["kind"] == "native_text"]
    if (piece["start"], piece["end"]) != (0, len(TEXT)):
        raise ValueError("controlled grammar requires the actual complete native piece")
    frame = DeclaredNativeFrameSource.from_retained_record(
        canonical_bytes(source).decode(), canonical_bytes(pin).decode()
    )
    source_ref = DeclaredStructuralSource.model_validate(pin)
    trace = "annotation:" + sha256(canonical_bytes([pin, TEXT, "finite-Ada-acts-1"])).hexdigest()
    operations = [
        dict(
            operation_key=operation_identity(question, "6", pin, "finite-Ada-acts-1"),
            question=question,
            operation_version="6",
            outcome="succeeded",
            inspected_count=1,
            emitted_count=count,
            computation_dependencies=(pin["source"],),
        )
        for question, count in (
            ("source_predicate_frames", 4),
            ("source_predicate_interpretation", 1),
        )
    ]
    rows = []

    def emit(kind, semantic_type, key, *, anchors=(), members=(), component=None, dependencies=()):
        row = dict(
            contract="RetainedContributionSemantics",
            kind=kind,
            semantic_type="structural." + semantic_type,
            item_key=key,
            operation_key=operations[1 if semantic_type == "predicate_reading" else 0][
                "operation_key"
            ],
            pin=pin,
            anchors=anchors,
            disposition="located_proposal" if anchors else "scoped_proposal",
            standing="retained_private",
            score_state="missing",
            computation_dependencies=dependencies,
        )
        if anchors:
            row["occurrence_id"] = occurrence_identity(anchors)
        if members:
            row["members"] = members
        if component is not None:
            row["component"] = component
        # Normalize through the actual schema before deriving immutable identity.
        row = prepared.validate_json(
            "SourceContribution",
            json_bytes({**row, "contribution_id": "source-contribution:" + "0" * 64}),
        ).model_dump(mode="python")
        row["contribution_id"] = contribution_identity(row)
        rows.append(row)
        return row["contribution_id"]

    members = []
    for index, (role, start, end) in enumerate(
        (("actor", 0, 3), ("predicate", 4, 8), ("focus", 0, 9))
    ):
        anchor = dict(
            pin=pin,
            space="native",
            pointer=piece["item_ref"],
            precision="exact",
            start=start,
            end=end,
            source_piece=TEXT[start:end],
        )
        anchor["anchor_id"] = anchor_identity(anchor)
        identity = emit(
            "occurrence", "predicate_member", role, anchors=(anchor,), dependencies=(trace,)
        )
        members.append(
            dict(
                role=role,
                contribution=identity,
                token_indices=[0, 1, 2] if role == "focus" else [index],
                head_token=1 if role == "focus" else index,
                extents=[dict(start=start, end=end)],
                outcome="complete",
            )
        )
    common = dict(
        protocol="witnessed-component-1",
        interpretation="unassessed",
        question_version="6",
        scope="finite-source-frame",
    )
    frame_id = emit(
        "composite",
        "predicate_frame",
        "frame",
        members=tuple(row["contribution"] for row in members),
        dependencies=(trace, *(row["contribution"] for row in members)),
        component=dict(
            **common,
            dependencies=(trace, *(row["contribution"] for row in members)),
            bases=(dict(kind="matched_cue", dependencies=(trace,)),),
            question="source_predicate_frames",
            kind="predicate_frame",
            annotation=trace,
            block=piece["item_ref"],
            predicate_token=1,
            variant="controlled-finite-1",
            grammatical_reading="described_process",
            focus_state="exact",
            frame_members=members,
        ),
    )
    emit(
        "composite",
        "predicate_reading",
        "reading",
        members=(frame_id,),
        dependencies=(frame_id,),
        component=dict(
            **common,
            dependencies=(frame_id,),
            bases=(dict(kind="matched_cue", dependencies=(frame_id,)),),
            question="source_predicate_interpretation",
            kind="predicate_reading",
            frame=frame_id,
            reading="described_process",
            voice="active",
            polarity="positive",
        ),
    )
    checked_operations, checked_rows = bind_contributions(
        prepared,
        source=pin["source"],
        operations=operations,
        contributions=rows,
        coordinate_texts=(dict(pin=pin, space="native", pointer=piece["item_ref"], text=TEXT),),
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
        contributions=checked_rows,
        operations=checked_operations,
        coordinate_texts=(dict(pin=pin, space="native", pointer=piece["item_ref"], text=TEXT),),
        coverage=(dict(family="controlled-predicate", scope=pin["source"], outcome="produced"),),
        diagnostics=dict(controlled_finite_grammar="finite-Ada-acts-1", annotation=trace),
        report_class="DdoPredicateInspectionReport",
    )
    component = declared_definition_component(
        term=dict(passage_id="root", start=0, end=3, text="Ada"),
        content=dict(passage_id="root", start=4, end=8, text="acts"),
        interpretation="unresolved",
        basis="unqualified",
        scope="selected",
        evidence=("root",),
        reason="Controlled lexical candidate; no definition interpretation is established.",
    )
    component_report = DeclaredDefinitionComponentsReport.model_validate(
        dict(
            inputs=dict(
                question="Select an unresolved lexical root",
                scope="selected",
                inventory_id="finite-source-root",
                policy_id="controlled-finite-1",
                sources=[source_ref],
                passages=[
                    dict(
                        passage_id="root",
                        source_ref=source_ref.identity,
                        start=0,
                        end=9,
                        text=TEXT,
                        scope="selected",
                    )
                ],
                dependencies=[pin["source_product"]],
            ),
            members=definition_component_packets(prepared, actual_context, (component,)),
            definition_components=dict(
                stages=[
                    dict(
                        passage_id="root",
                        operation="attachment",
                        outcome="succeeded",
                        reason="Controlled lexical root remains unresolved.",
                    )
                ],
            ),
            sources_input=[source_input],
        )
    )
    return dict(
        predicates=predicates, components=definition_component_report_values(component_report)
    )


def execute_profile(receiver, source):
    raise ValueError("controlled source inventory requires its actual acquired CPU plan")


def execute_kernel(
    source: dict, pin: dict, context: dict, source_input: dict, *, prepared, check_active
) -> dict[str, dict]:
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    check_active()
    return source_values(
        prepared, bound_data_operation_model(prepared), source, pin, context, source_input
    )


class ControlledStructuralInventory:
    __data_operation__: ClassVar[dict] = {
        "id": "fixture.structural_inventory",
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
                    "source_set": "fixture-structural-source",
                    "identity_requirements": ["episode"],
                    "coverage": {"role": "source", "description": "actual-selected-source"},
                },
            },
            {
                "name": "predicates",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoPredicateInspectionReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
            {
                "name": "components",
                "direction": "output",
                "kind": "urn:corpus:structural:DeclaredDefinitionComponentsReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "result_fields": {"predicates": "predicates", "components": "components"},
        "applicability": [{"kind": "documentation", "text": "exact-finite-Ada-acts-source-only"}],
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
        "behavior": "controlled-finite-source-inventory",
        "binding": {"operator": "scan", "roles": ["source"]},
        "opaque": [
            {
                "reference": "semantic.structural_native_fixture.execute_profile",
                "contract": "structural-native-fixture/source-assets",
                "role": "controlled-finite-source-computation",
            }
        ],
        "assets": [
            {
                "reference": "controlled-source-inventory",
                "contract": "structural-native-fixture/source-assets",
                "role": "actual-controlled-computation-bytes",
            }
        ],
    }

    def run(self, source: dict) -> dict[str, dict]:
        return execute_profile(self, source)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort

        if operation != OPERATION:
            raise ValueError("controlled source factory belongs to another operation")
        receiver, plan = ControlledStructuralInventory(), InventoryPlan(prepared)
        port = PreparedOriginalCallPort(
            identity,
            model,
            model.operation(operation),
            sources,
            custody,
            receiver.run,
            plan.plan,
            MODULE + ".InventoryPlan.plan",
            authorize,
            (assets(),),
            operation_sources(),
            functions=((MODULE + ".execute_kernel", execute_kernel),),
            requires_prepared_schema=True,
        )
        plan.port = port
        return port


@dataclass
class InventoryPlan:
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


def assets():
    from corpus_structure.semantic.python_module_projection import admitted_operation_module_meaning
    from corpus_structure.semantic.types import SourceArtifact

    return SourceArtifact(
        ASSET,
        canonical_bytes(
            dict(
                version="controlled-finite-structural-source-1",
                source=admitted_operation_module_meaning(Path(__file__).read_bytes()).hex(),
            )
        ),
    )


def operation_sources():
    from corpus_structure.semantic import data_operation_prepared_call
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    path = Path(__file__).resolve()
    adapter = Path(data_operation_prepared_call.__file__).resolve()
    return PythonSourceCollection(
        (
            PythonSource(MODULE, path.read_bytes(), str(path)),
            PythonSource(data_operation_prepared_call.__name__, adapter.read_bytes(), str(adapter)),
        ),
        boundary_contracts=(assets(),),
    )
