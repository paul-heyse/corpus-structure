"""Controlled current candidate computation over actual published native table cells.

This fixture has a genuine declared factory and CPU completion receipt. It is not
provider evidence: each native cell yields one exact and one unresolved reading so
independent source-only full-reading judgments have both classes to assess.
"""

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from corpus_structure.semantic.identity import canonical_bytes

ASSET = "record-policy-native-fixture/candidate-assets"
MODULE = "evaluate.declared_record_candidate_fixture"


def candidate_values(prepared, source, pin, *, model, check_active, family="table"):
    from copy import deepcopy

    from corpus_structure.semantic.record_contracts import (
        anchor_identity,
        evidence_set_identity,
        interpretation_identity,
        record_family_contract,
        record_identity,
    )

    if family not in {"table", "measurement"}:
        raise ValueError("controlled candidate family is not declared")
    value_role = "value" if family == "table" else "original_value"
    tables = [item for item in source["items"] if item.get("label") == "table"]
    if len(tables) != 1 or len(tables[0].get("data", {}).get("table_cells", ())) != 2:
        raise ValueError("controlled source requires its actual independent two-cell native table")
    table = tables[0]
    records, coordinates = [], []
    for position, cell in enumerate(table["data"]["table_cells"]):
        check_active()
        pointer, lexical = f"{table['self_ref']}/data/table_cells/{position}", cell["text"]
        anchors, evidence, fields = [], [], []
        for role, usage, anchor in (
            (
                value_role,
                "literal",
                dict(
                    pin=pin,
                    space="native",
                    pointer=pointer,
                    precision="exact",
                    start=0,
                    end=len(lexical),
                    source_piece=lexical,
                ),
            ),
            (
                "location",
                "native",
                dict(pin=pin, space="native", pointer=pointer, precision="item"),
            ),
        ):
            anchor["anchor_id"] = anchor_identity(anchor)
            anchors.append(anchor)
            if family == "measurement" and role == "location":
                continue
            support = dict(
                role=role, ordering="ordered", usage=usage, anchors=(anchor["anchor_id"],)
            )
            support["set_id"] = evidence_set_identity(support)
            field = dict(
                role=role,
                kind="literal" if role == value_role else "native",
                state="present",
                meaning_changing=True,
                evidence_status="available",
                evidence_sets=(support["set_id"],),
                value=dict(kind="decimal", lexical=lexical)
                if role == value_role
                else dict(kind="native_location", pointer=pointer),
            )
            if role == value_role:
                field.update(original=lexical, reason="source-read")
                coordinates.append(dict(pin=pin, space="native", pointer=pointer, text=lexical))
            evidence.append(support)
            fields.append(field)
        if family == "measurement":
            for role, kind, meaning_changing in (
                ("referent", "literal", True),
                ("property", "literal", True),
                ("value_role", "classified", True),
                ("unit", "literal", True),
                ("comparator", "literal", True),
                ("uncertainty", "literal", True),
                ("reference_quantity", "literal", True),
                ("condition", "literal", True),
                ("normalized_value", "normalized", False),
            ):
                fields.append(dict(
                    role=role, kind=kind, state="unstated", meaning_changing=meaning_changing,
                    evidence_status="unavailable", evidence_sets=(),
                    reason="not stated in this exact native numeric cell",
                ))
        record = dict(
            contract="FixtureRecordFields" if family == "table" else "MeasurementRecordFields",
            family=family,
            occurrence_recipe="source-anchor-membership-1",
            pin=pin,
            occurrence_anchors=(anchors[1]["anchor_id"],),
            standing="candidate",
            policy_version="m1-grouped-reading-logistic-1",
            anchors=tuple(anchors),
            evidence_sets=tuple(evidence),
            fields=tuple(fields),
            computation_dependencies=(f"native-group:cell-{position}",),
        )
        record["record_id"] = record_identity(
            record_family_contract(model, record["contract"]), record
        )
        record["interpretation_id"] = interpretation_identity(record)
        records.append(record)
        unresolved = deepcopy(record)
        value = next(field for field in unresolved["fields"] if field["role"] == value_role)
        value.update(
            state="unresolved", reason="controlled extraction did not resolve this interpretation"
        )
        value.pop("value")
        value.pop("original")
        unresolved["interpretation_id"] = interpretation_identity(unresolved)
        records.append(unresolved)
    return tuple(records), tuple(coordinates)


def execute_profile(receiver, source, question):
    raise ValueError("controlled candidate producer requires its actual acquired CPU plan")


def execute_kernel(
    source: dict, question: dict, pin: dict, context: dict, *, prepared, check_active
) -> dict:
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.declared_candidate_products import candidate_inspection_report
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    if question["source_pin_json"] != canonical_bytes(pin).decode():
        raise ValueError("controlled extraction question differs from exact selected source pin")
    frame = DeclaredNativeFrameSource(
        canonical_bytes(source).decode(), canonical_bytes(pin).decode()
    )
    rows, coordinates = candidate_values(
        prepared, source, pin, model=bound_data_operation_model(prepared), check_active=check_active,
        family=question.get("family", "table"),
    )
    actual_context = SubjectContext(
        context["project_id"],
        context["subject"],
        context["original_source"],
        canonical_bytes(context["analyzed_scope"]),
        subject_definition=context["subject_definition"],
    )
    if question["empty"]:
        rows = ()
    outcome = "produced" if rows else "empty"
    return candidate_inspection_report(
        prepared,
        bound_data_operation_model(prepared),
        frame,
        actual_context,
        inspection_outcome=outcome,
        records=rows,
        coordinate_texts=coordinates,
        coverage=(dict(family=question.get("family", "table"), scope=pin["source"], outcome=outcome),),
        diagnostics={"reports": [], "fixture": "controlled-native-two-cell-computation"},
    )


class Candidates:
    __data_operation__: ClassVar[dict] = {
        "id": "fixture.record_candidates",
        "profile": "derivation",
        "subject": "selected-native-source",
        "subject_definition": {
            "id": "selected-native-source",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "role-associated",
        "context": ["actual-selected-native-table", "controlled-reading-alternatives"],
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
                    "source_set": "fixture-record-sources",
                    "identity_requirements": ["episode"],
                    "coverage": {"role": "source", "description": "actual-selected-table-source"},
                },
            },
            {
                "name": "question",
                "parameter": "question",
                "direction": "input",
                "kind": "https://example.test/current-record-policy/FixtureCandidateQuestion",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "predeclared-extraction-question",
                    "origins": ["authored"],
                    "identity_requirements": ["original-source"],
                    "coverage": {
                        "role": "question",
                        "description": "exact-full-source-pin-and-context",
                    },
                },
            },
            {
                "name": "candidates",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [
            {"kind": "documentation", "text": "controlled-exact-two-cell-native-source-only"}
        ],
        "invariants": [
            {
                "kind": "documentation",
                "text": "both-complete-and-unresolved-readings-retained-without-labels",
            }
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "all-two-cell-alternative-readings",
        },
        "outcomes": ["success"],
        "precision_description": "exact-native-cell-and-unresolved-controlled-alternatives",
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
        "behavior": "controlled-native-cell-computation-without-independent-correctness-labels",
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source", "question"]},
                {
                    "operator": "equal",
                    "operands": [
                        {
                            "kind": "field",
                            "value_type": "subject-context",
                            "field": {
                                "role": "source",
                                "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                                "field": "@context",
                            },
                        },
                        {
                            "kind": "field",
                            "value_type": "subject-context",
                            "field": {
                                "role": "question",
                                "projection": "https://example.test/current-record-policy/FixtureCandidateQuestion",
                                "field": "@context",
                            },
                        },
                    ],
                },
            ],
        },
        "opaque": [
            {
                "reference": "evaluate.declared_record_candidate_fixture.execute_profile",
                "contract": "record-policy-native-fixture/candidate-assets",
                "role": "controlled-native-source-reading",
            }
        ],
        "assets": [
            {
                "reference": "controlled-native-candidate-source",
                "contract": "record-policy-native-fixture/candidate-assets",
                "role": "actual-controlled-computation-bytes",
            }
        ],
    }

    def run(self, source: dict, question: dict) -> dict:
        return execute_profile(self, source, question)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort

        selected = model.operation(operation)
        if selected.semantic_id != "fixture.record_candidates":
            raise ValueError("controlled candidate factory belongs to another operation")
        receiver, plan = Candidates(), CandidatePlan(prepared)
        port = PreparedOriginalCallPort(
            identity,
            model,
            selected,
            sources,
            custody,
            receiver.run,
            plan.plan,
            "evaluate.declared_record_candidate_fixture.CandidatePlan.plan",
            authorize,
            (assets(),),
            operation_sources(),
            functions=(
                ("evaluate.declared_record_candidate_fixture.execute_kernel", execute_kernel),
            ),
            requires_prepared_schema=True,
        )
        plan.port = port
        return port


@dataclass
class CandidatePlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        import json

        from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

        if binding is None or binding.subject_context is None or not binding.sufficient:
            raise ValueError(
                "controlled candidate computation requires exact native source support"
            )
        (role,) = [role for role in binding.roles if role.role == "source"]
        (member,) = role.members
        context = binding.subject_context
        frame = DeclaredNativeFrameSource.acquire(
            self.prepared, arguments.arguments["source"], member, project=context.project_id
        )
        signature = inspect.signature(execute_kernel, eval_str=True)
        bound = signature.bind(
            source=arguments.arguments["source"],
            question=arguments.arguments["question"],
            pin=frame.pin.values(),
            context={
                "project_id": context.project_id,
                "subject": context.subject,
                "subject_definition": context.subject_definition,
                "original_source": context.original_source,
                "analyzed_scope": json.loads(context.analyzed_scope),
            },
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
            {
                "version": "controlled-native-record-candidates-1",
                "source": admitted_operation_module_meaning(Path(__file__).read_bytes()).hex(),
            }
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


def copy_profile(receiver, original):
    raise ValueError("protected-copy fixture requires its real acquired CPU plan")


def copy_kernel(original: dict, *, check_active) -> dict:
    check_active()
    return original


class ProtectedCopy:
    """A real captured CPU copy that must never become a recognized grade issuer."""

    __data_operation__: ClassVar[dict] = {
        "id": "fixture.protected_grade_copy",
        "profile": "derivation",
        "subject": "knowledge-universe",
        "subject_definition": {
            "id": "knowledge-universe",
            "identifier_kind": "string",
            "scope": "project",
        },
        "discovery_relation": "role-associated",
        "context": ["explicit-protected-copy-control"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "original",
                "parameter": "original",
                "direction": "input",
                "subject_target": "source-set",
                "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoRecordGrade",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "fixture-copy-grade",
                    "identity_requirements": ["episode"],
                    "coverage": {"role": "original", "description": "exact-actual-protected-grade"},
                },
            },
            {
                "name": "copy",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoRecordGrade",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [
            {"kind": "documentation", "text": "controlled-copy-confers-no-grading-authority"}
        ],
        "invariants": [
            {"kind": "documentation", "text": "preserve-complete-original-protected-body"}
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "whole-selected-protected-copy",
        },
        "outcomes": ["success"],
        "precision_description": "exact-whole-protected-copy",
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
        "behavior": "controlled-copy-is-not-an-authenticated-native-record-grade-producer",
        "binding": {"operator": "scan", "roles": ["original"]},
        "opaque": [
            {
                "reference": "evaluate.declared_record_candidate_fixture.copy_profile",
                "contract": "record-policy-native-fixture/candidate-assets",
                "role": "controlled-protected-copy",
            }
        ],
        "assets": [
            {
                "reference": "controlled-copy-source",
                "contract": "record-policy-native-fixture/candidate-assets",
                "role": "actual-controlled-copy-computation-bytes",
            }
        ],
    }

    def run(self, original: dict) -> dict:
        return copy_profile(self, original)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort

        receiver, plan = ProtectedCopy(), CopyPlan()
        port = PreparedOriginalCallPort(
            identity,
            model,
            model.operation(operation),
            sources,
            custody,
            receiver.run,
            plan.plan,
            "evaluate.declared_record_candidate_fixture.CopyPlan.plan",
            authorize,
            (assets(),),
            operation_sources(),
            functions=(("evaluate.declared_record_candidate_fixture.copy_kernel", copy_kernel),),
        )
        plan.port = port
        return port


@dataclass
class CopyPlan:
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        bound = inspect.signature(copy_kernel, eval_str=True).bind(
            original=arguments.arguments["original"], check_active=check_active
        )
        return (
            yield from self.port.plan_cpu(
                copy_kernel,
                bound,
                operation_sources(),
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )
