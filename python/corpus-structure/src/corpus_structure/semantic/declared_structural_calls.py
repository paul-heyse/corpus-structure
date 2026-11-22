"""Prepared structural calls over exact admitted native source/report values.

The existing structural kernels remain semantic authority. These calls acquire no
Reader, discover no inputs and own no physical pool; the invocation's CPU owner
executes the original declared callable with its explicitly bound input context.
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from .data_operation_json import json_bytes
from .data_operation_model import ResolvedRoleBinding
from .data_operation_version import MODEL_VERSION
from .declared_structural_references import (
    DeclaredContributionRef,
    DeclaredStructuralSource,
)
from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .types import PreparedRelease, SourceArtifact

NAMESPACE = "urn:corpus:structural:"
_ASSET = "structural/call-assets"
_PATHS = (
    "analytics.py",
    "semantic/established_validity.py",
    "methods/structural_declared.py",
    "methods/structural_products.py",
    "methods/dossier_contributions.py",
    "semantic/declared_structural_calls.py",
    "semantic/declared_structural_references.py",
    "semantic/structural_products.py",
    "semantic/artifact_identity.py",
    "semantic/declared_candidate_products.py",
    "semantic/declared_record_sources.py",
    "semantic/contributions.py",
    "semantic/formal_readings.py",
    "semantic/formal_products.py",
)


def structural_operation_declarations():
    """Capture DTO-generated shape bytes; the compiler never imports candidate DTOs."""
    from .nominal_schema_kinds import nominal_schema_kinds
    from .structural_products import (
        DeclaredArtifactReport,
        DeclaredClauseReport,
        DeclaredComparisonReport,
        DeclaredConditionReport,
        DeclaredDefinitionApplicabilityReport,
        DeclaredDefinitionComponentsReport,
        DeclaredDossierReport,
        DeclaredNamedDefinitionComponentsReport,
    )

    schema = TypeAdapter(
        DeclaredComparisonReport
        | DeclaredConditionReport
        | DeclaredDossierReport
        | DeclaredDefinitionComponentsReport
        | DeclaredNamedDefinitionComponentsReport
        | DeclaredDefinitionApplicabilityReport
        | DeclaredArtifactReport
        | DeclaredClauseReport
    ).json_schema()
    kinds = nominal_schema_kinds(schema, namespace=NAMESPACE, root_name="Products")
    for kind in kinds:
        if kind["id"] == NAMESPACE + "DeclaredNamedDefinitionComponentsReport":
            kind["is_a"] = NAMESPACE + "DeclaredDefinitionComponentsReport"
    return SourceArtifact(
        "structural/nominal-kinds.json",
        canonical_bytes(
            {
                "version": MODEL_VERSION,
                "kinds": kinds,
            }
        ),
    )


def structural_call_assets():
    root = Path(__file__).parents[1]
    return SourceArtifact(
        _ASSET,
        canonical_bytes(
            {
                "version": "declared-structural-calls-v1",
                "schemas": structural_operation_declarations().content.decode(),
                "algorithms": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((root / name).read_bytes()).decode()
                            if name in ("methods/structural_declared.py",)
                            else ast.dump(
                                ast.parse((root / name).read_bytes()), include_attributes=False
                            )
                        ),
                    )
                    for name in _PATHS
                ],
            }
        ),
    )


def structural_operation_sources(*, include_formal=True):
    """Capture structural execution and the rule owner for optional formal inputs."""
    from .python_operation_sources import PythonSource, PythonSourceCollection

    root = Path(__file__).parents[1]
    own = PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (root / name).read_bytes(),
                str(root / name),
            )
            for name in (
                "methods/structural_declared.py",
                "semantic/declared_structural_calls.py",
                "semantic/data_operation_prepared_call.py",
            )
        ),
        boundary_contracts=(structural_call_assets(),),
    )

    if not include_formal:
        return own
    from .formal_products import formal_operation_sources
    from .primary_operations import combine_primary_sources

    return combine_primary_sources(formal_operation_sources(), own)


def structural_inputs(bundle):
    from .declared_candidate_products import candidate_inspection_inputs
    from .formal_products import formal_product_inputs

    bundle = candidate_inspection_inputs(bundle)
    if "data_operation_characterization" not in {source.name for source in bundle.sources}:
        bundle = formal_product_inputs(bundle)
    return bundle


@dataclass(frozen=True)
class PreparedStructuralInputs:
    prepared: PreparedRelease
    roles: tuple[ResolvedRoleBinding, ...]
    project: str
    check_active: Callable[[], None]

    def member(self, name):
        (role,) = (role for role in self.roles if role.role == name)
        if len(role.members) != 1:
            raise ValueError("structural scalar input requires its one exact selected member")
        return role.members[0]

    def reference(self, name):
        from .structural_products import DeclaredStructuralInputPin

        return DeclaredStructuralInputPin.from_bound(self.member(name), project=self.project)

    def references(self, name):
        from .structural_products import DeclaredStructuralInputPin

        (role,) = (role for role in self.roles if role.role == name)
        return tuple(
            DeclaredStructuralInputPin.from_bound(member, project=self.project)
            for member in role.members
        )

    def selected(self, name, values, reference):
        (role,) = (role for role in self.roles if role.role == name)
        if len(values) != len(role.members):
            raise ValueError("structural values differ from exact selected input population")
        (selected,) = (
            (member, value)
            for member, value in zip(role.members, values, strict=True)
            if canonical_bytes([member.product, member.member]).decode() == reference
        )
        return selected

    def frame(self, name, value):
        from .declared_record_sources import DeclaredNativeFrameSource

        return DeclaredNativeFrameSource.acquire(
            self.prepared, value, self.member(name), project=self.project
        )

    def contribution(self, name, report, frame, identifier, *, member=None):
        from .contributions import contribution_identity
        from .data_operation_admission import bound_data_operation_model
        from .data_operation_kind_refinements import input_kind_contracts
        from .declared_candidate_products import candidate_member_values

        selected = member or self.member(name)
        model = bound_data_operation_model(self.prepared)
        root = self.prepared.index.definitions["DdoPredicateInspectionReport"].iri
        accepted = input_kind_contracts(model, (root,))[root]
        if selected.kind_contract not in accepted:
            raise ValueError("structural reading requires its actual predicate producer capability")
        owners = [
            identity.owner
            for identity in model.identities
            if identity.domain == "kind" and identity.key == selected.kind_contract
        ]
        if len(owners) != 1:
            raise ValueError("structural reading lacks its exact concrete input kind")
        definition = next(
            definition for definition in self.prepared.definitions if definition.iri == owners[0]
        )
        checked = self.prepared.validate_json(definition.name, json_bytes(report)).model_dump(
            mode="python", exclude_unset=True
        )
        reference = DeclaredContributionRef.from_bound(
            member or self.member(name), project=self.project, contribution_id=identifier
        )
        source = frame.pin.values()
        if checked["source_pin"] != source:
            raise ValueError("structural report differs from its exact admitted original source")
        context = {
            "project_id": source["project_id"],
            "subject": source["subject"],
            "subject_definition": source["subject_definition"],
            "original_source": source["original_source"],
            "analyzed_scope_meaning": source["analyzed_scope_meaning"],
        }
        if reference.context != context or reference.member_id is not None:
            raise ValueError("structural inventory requires its exact whole report context")
        questions = {row["question"]: row for row in checked["operations"]}
        if any(
            question not in questions
            or questions[question]["operation_version"] != "6"
            or questions[question]["outcome"] not in {"succeeded", "empty"}
            for question in ("source_predicate_frames", "source_predicate_interpretation")
        ):
            raise ValueError("structural reading requires complete retained predicate inspection")
        rows = candidate_member_values(checked, candidate_type="contribution")
        if any(
            contribution_identity(row) != row["contribution_id"] or row["pin"] != source
            for row in rows
        ):
            raise ValueError(
                "structural candidate identity/source differs from retained report inventory"
            )
        ids = [row["contribution_id"] for row in rows]
        if len(set(ids)) != len(ids) or identifier not in ids:
            raise ValueError(
                "structural selection is outside the exact report contribution inventory"
            )
        for packet in checked["members"]:
            if (
                packet["body"]["candidate_type"] == "contribution"
                and packet["member_id"] != "contribution:" + packet["body"]["contribution_id"]
            ):
                raise ValueError("candidate member address differs from its domain content ID")
        return reference, {
            "contributions": rows,
            "sources": [{"pin": source, "projection": frame.value}],
        }


def _passage(frame, *, passage_id, start, end, scope, version="", parent=""):
    from .structural_products import StructuralPassage

    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(frame.text):
        raise ValueError("authored structural bounds exceed their actual native source")
    source = DeclaredStructuralSource.model_validate(frame.pin.values())
    return source, StructuralPassage(
        passage_id=passage_id,
        source_ref=source.identity,
        start=start,
        end=end,
        text=frame.text[start:end],
        scope=scope,
        effective_version=version or None,
        parent=parent or None,
    )


def execute_comparison(receiver, sources, reports, formal, **selection):
    from corpus_structure.methods.structural_products import produce_structural_comparison

    from .data_operation_admission import bound_data_operation_model
    from .data_operation_model import SubjectContext
    from .data_product_reference import DataProductReference
    from .declared_record_sources import DeclaredNativeFrameSource
    from .formal_products import retained_formal_product
    from .formal_readings import FormalSourceReadings
    from .source_products import FrozenNativeSource
    from .structural_products import DeclaredComparisonReport, DeclaredStructuralInput

    profile = receiver.profile
    profile.check_active()
    left_member, left_body = profile.selected(
        "sources", sources, selection["left_source_reference"]
    )
    right_member, right_body = profile.selected(
        "sources", sources, selection["right_source_reference"]
    )
    left_report_member, left_report = profile.selected(
        "reports", reports, selection["left_report_reference"]
    )
    right_report_member, right_report = profile.selected(
        "reports", reports, selection["right_report_reference"]
    )
    left = DeclaredNativeFrameSource.acquire(
        profile.prepared, left_body, left_member, project=profile.project
    )
    right = DeclaredNativeFrameSource.acquire(
        profile.prepared, right_body, right_member, project=profile.project
    )
    left_ref, left_retained = profile.contribution(
        "reports", left_report, left, selection["left_reading"], member=left_report_member
    )
    right_ref, right_retained = profile.contribution(
        "reports", right_report, right, selection["right_reading"], member=right_report_member
    )
    a, left_passage = _passage(
        left,
        passage_id=selection["left_passage_id"],
        start=selection["left_start"],
        end=selection["left_end"],
        scope=selection["scope"],
        version=selection["left_version"],
        parent=selection["left_parent"],
    )
    b, right_passage = _passage(
        right,
        passage_id=selection["right_passage_id"],
        start=selection["right_start"],
        end=selection["right_end"],
        scope=selection["scope"],
        version=selection["right_version"],
        parent=selection["right_parent"],
    )
    model = bound_data_operation_model(profile.prepared)
    retained_formal = {a.identity: [], b.identity: []}
    lexical = {a.identity: [], b.identity: []}
    (formal_role,) = (role for role in profile.roles if role.role == "formal")
    for member, raw in zip(formal_role.members, formal, strict=True):
        matches = [
            (reference, frame)
            for reference, frame in dict(((a, left), (b, right))).items()
            if raw["source"] == frame.value["source"]
            and raw["selectors"] == frame.value["selectors"]
        ]
        if len(matches) != 1 or member.member is not None:
            raise ValueError(
                "comparison formal product lacks its exact whole selected original scope"
            )
        address, frame = matches[0]
        source = FrozenNativeSource.acquire(profile.prepared, frame.value)
        context = SubjectContext(
            profile.project,
            member.subject,
            member.original_source,
            member.analyzed_scope,
            subject_definition=member.subject_definition,
        )
        product = retained_formal_product(
            profile.prepared, raw, source, model=model, subject_context=context, member=member
        )
        if product.semantic_id != member.product:
            raise ValueError("comparison formal body differs from its exact native product")
        retained_formal[address.identity].append(
            (DataProductReference(product.semantic_id), product.inventory())
        )
        lexical[address.identity].extend(raw["lexicon"])
    primary_readings = {
        address.identity: FormalSourceReadings._from_retained(
            frame.value, retained_formal[address.identity], lexical[address.identity]
        )
        for address, frame in dict(((a, left), (b, right))).items()
        if retained_formal[address.identity]
    }
    inputs = DeclaredStructuralInput(
        question=selection["question"],
        scope=selection["scope"],
        inventory_id=selection["inventory_id"],
        policy_id=selection["policy_id"],
        sources=tuple(dict.fromkeys((a, b))),
        passages=(left_passage, right_passage),
        dependencies=tuple(
            dict.fromkeys(
                (
                    left_ref.product_id,
                    right_ref.product_id,
                    left_ref.contribution_id,
                    right_ref.contribution_id,
                    *(member.product for member in formal_role.members),
                )
            )
        ),
        coverage_limits=(
            "Only retained predicate coverage is used; unavailable formal characterization remains unresolved.",
        ),
    )
    report = produce_structural_comparison(
        inputs,
        left_id=left_passage.passage_id,
        right_id=right_passage.passage_id,
        left_reading=left_ref,
        right_reading=right_ref,
        left_retained=left_retained,
        right_retained=right_retained,
        primary_layers=None,
        primary_readings=primary_readings,
        check_active=profile.check_active,
    )
    return DeclaredComparisonReport.model_validate(
        {
            **report.model_dump(mode="python"),
            "sources_input": profile.references("sources"),
            "reports_input": profile.references("reports"),
            "formal_input": profile.references("formal"),
        }
    ).model_dump(mode="json")


def execute_condition(receiver, source, report, **selection):
    from corpus_structure.methods.structural_products import condition_qualification

    from .structural_products import DeclaredConditionReport, DeclaredStructuralInput

    profile = receiver.profile
    profile.check_active()
    frame = profile.frame("source", source)
    reference, retained = profile.contribution("report", report, frame, selection["attachment"])
    address, passage = _passage(
        frame,
        passage_id=selection["passage_id"],
        start=selection["start"],
        end=selection["end"],
        scope=selection["scope"],
        version=selection["effective_version"],
    )
    inputs = DeclaredStructuralInput(
        question=selection["question"],
        scope=selection["scope"],
        inventory_id=selection["inventory_id"],
        policy_id=selection["policy_id"],
        sources=(address,),
        passages=(passage,),
        dependencies=(address.source_product,),
    )
    return DeclaredConditionReport(
        inputs=inputs,
        source_input=profile.reference("source"),
        condition_qualification=condition_qualification(
            inputs, reference.contribution_id, retained, project_id=profile.project
        ),
    ).model_dump(mode="json")


def comparison_kernel(
    arguments: dict,
    roles: tuple[ResolvedRoleBinding, ...],
    project: str,
    *,
    prepared: PreparedRelease,
    check_active: Callable[[], None],
) -> dict:
    from corpus_structure.methods.structural_declared import DeclaredStructuralComparison

    return DeclaredStructuralComparison(
        PreparedStructuralInputs(prepared, roles, project, check_active)
    ).run(**arguments)


def condition_kernel(
    arguments: dict,
    roles: tuple[ResolvedRoleBinding, ...],
    project: str,
    *,
    prepared: PreparedRelease,
    check_active: Callable[[], None],
) -> dict:
    from corpus_structure.methods.structural_declared import DeclaredConditionQualification

    return DeclaredConditionQualification(
        PreparedStructuralInputs(prepared, roles, project, check_active)
    ).run(**arguments)


@dataclass
class StructuralCallPlan:
    prepared: PreparedRelease
    kernel: Callable
    sources: object
    port: Any = None

    def verify(self):
        from .data_operation_ports import PortRefusal

        if structural_call_assets() != self.port.assets[0]:
            raise PortRefusal("structural original algorithm/DTO schema assets changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):

        if binding is None or binding.subject_context is None:
            raise ValueError("structural call lacks its actual bound qualified context")
        selections = [
            value
            for value in execution_owner.consumer_inputs.values()
            if value.selection.binding is binding
        ]
        if len(selections) != 1:
            raise ValueError("structural call lacks its one governing hydrated selection")
        signature = inspect.signature(self.kernel, eval_str=True)
        bound = signature.bind(
            arguments=arguments.arguments,
            roles=binding.roles,
            project=binding.subject_context.project_id,
            prepared=self.prepared,
            check_active=check_active,
        )
        captured = structural_operation_sources(include_formal=False)
        return (
            yield from self.port.plan_cpu(
                self.kernel,
                bound,
                captured,
                prepared_release_id=self.prepared.release_id,
                verify=self.verify,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def resolve_structural_call(
    prepared, model, operation, *, receiver, kernel, identity, authorize, custody, sources
):
    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != receiver.__data_operation__["id"]:
        raise PortRefusal("structural factory differs from its governing producer")
    captured = structural_operation_sources(include_formal=False)
    plan = StructuralCallPlan(prepared, kernel, sources)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.declared_structural_calls.StructuralCallPlan.plan",
        authorize,
        (structural_call_assets(),),
        captured,
        functions=((kernel.__module__ + "." + kernel.__qualname__, kernel),),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
