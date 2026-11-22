"""Dossier assembly from actual admitted components, candidate closures and decisions."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import Field, TypeAdapter

from .data_operation_model import ResolvedRoleBinding, SubjectContext
from .declared_structural_references import (
    DeclaredContributionRef,
    DeclaredRelationshipRef,
    DeclaredStructuralRef,
)
from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .structural_base import StructuralValue
from .types import PreparedRelease, SourceArtifact

_ROOT = Path(__file__).parents[1]
_PATHS = (
    "methods/dossier_declared.py",
    "semantic/dossier_products.py",
    "methods/structural_products.py",
    "methods/dossier_contributions.py",
    "semantic/structural_products.py",
    "semantic/declared_structural_references.py",
    "semantic/declared_structural_calls.py",
    "semantic/declared_candidate_products.py",
    "semantic/contextual_operations.py",
    "semantic/structural_admission.py",
    "semantic/declared_structural_admission.py",
    "semantic/structural_admission_native.py",
    "semantic/source_contexts.py",
    "semantic/declared_record_sources.py",
)


class DossierCandidateSelection(StructuralValue):
    report_reference: str = Field(min_length=1)
    contribution_id: str = Field(min_length=1)


class DossierComparisonSelection(StructuralValue):
    comparison_reference: str = Field(min_length=1)
    side: Literal["left", "right"]
    relationship_reference: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    edge_id: str = Field(min_length=1)
    applicability_reference: str | None = None
    conflict_passage_id: str | None = None


class DossierPassageSelection(StructuralValue):
    source_reference: str = Field(min_length=1)
    passage_id: str = Field(min_length=1)
    start: int = Field(ge=0, strict=True)
    end: int = Field(gt=0, strict=True)
    scope: str = Field(min_length=1)
    effective_version: str = ""
    parent: str = ""


def dossier_inputs(bundle):
    from .contextual_operations import contextual_inputs
    from .declared_candidate_products import candidate_inspection_inputs

    return contextual_inputs(candidate_inspection_inputs(bundle))


def dossier_profile_assets():
    return SourceArtifact(
        "dossiers/profile-assets",
        canonical_bytes(
            {
                "version": "declared-dossier-assembly-v1",
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex()
                            if name in ("methods/dossier_declared.py",)
                            else (_ROOT / name).read_bytes().hex()
                        ),
                    )
                    for name in _PATHS
                ],
            }
        ),
    )


def dossier_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in (
                "methods/dossier_declared.py",
                "semantic/dossier_products.py",
                "semantic/data_operation_prepared_call.py",
            )
        ),
        boundary_contracts=(dossier_profile_assets(),),
    )


@dataclass(frozen=True)
class DossierRelationship:
    binding: Any
    frame: Any
    root_meaning: Any


def declared_comparison_occurrence(relationship, reference, source, passage, root_ref, root):
    """Resolve selected native anchors and the genuine target carrier, with no relabelling."""
    from .structural_products import LocatedDefinitionSpan

    binding, frame = relationship.binding, relationship.frame
    edge, decision = binding.edge, binding.decision
    if (
        edge.relation not in {"denotes", "defined-by", "specializes"}
        or reference.edge_id != edge.edge_id
        or reference.project_id != source.project_id
        or decision.scope != passage.scope
        or root.scope != passage.scope
        or not passage.effective_version
        or decision.effective_version != passage.effective_version
        or root.effective_version != passage.effective_version
        or not source.matches_pin(binding.source_pin)
        or frame.pin.values() != binding.source_pin
    ):
        raise ValueError("comparison side lacks the exact scoped root relationship")
    exact = canonical_bytes(root_ref.model_dump(mode="json", exclude_none=True)).decode()
    carriers = tuple(
        value
        for value in binding.representations
        if value.target_id == root.component_id
        and value.source_binding == exact
        and value.type_name == "definition"
    )
    if len(carriers) != 1:
        raise ValueError("comparison relationship does not carry the exact native root component")
    if canonical_bytes(binding.target.meaning) != canonical_bytes(relationship.root_meaning):
        raise ValueError("comparison relationship changes the root source-resolved meaning")
    spans = []
    for anchor in binding.anchors:
        if (
            anchor["pin"] != frame.pin.values()
            or anchor.get("space") != "native"
            or anchor.get("precision") != "exact"
        ):
            raise ValueError("comparison relationship lacks exact native source evidence")
        pieces = tuple(
            piece
            for piece in frame.value["pieces"]
            if piece["kind"] == "native_text"
            and piece["item_ref"]
            + (
                "/data/table_cells/" + str(piece["cell_index"])
                if piece.get("cell_index") is not None
                else ""
            )
            == anchor["pointer"]
        )
        if len(pieces) != 1:
            raise ValueError("comparison relationship has an ambiguous native field bridge")
        (piece,) = pieces
        start, end = piece["start"] + anchor["start"], piece["start"] + anchor["end"]
        if (
            not piece["start"] <= start < end <= piece["end"]
            or frame.text[start:end] != anchor["source_piece"]
        ):
            raise ValueError("comparison relationship differs from actual native source text")
        spans.append(
            LocatedDefinitionSpan(
                passage_id=passage.passage_id, start=start, end=end, text=anchor["source_piece"]
            )
        )
    return edge.relation, tuple(sorted(set(spans), key=lambda span: (span.start, span.end)))


@dataclass(frozen=True)
class PreparedDossierInputs:
    prepared: PreparedRelease
    roles: tuple[ResolvedRoleBinding, ...]
    context: SubjectContext
    check_active: Callable[[], None]

    def members(self, name):
        selected = next(role for role in self.roles if role.role == name)
        if any(
            member.multiplicity != 1 or (name != "sources" and member.member is not None)
            for member in selected.members
        ):
            raise ValueError("dossier inputs require their exact whole native inventories")
        return selected.members

    def run(
        self,
        sources,
        components,
        definitions,
        comparisons,
        candidates,
        relationships,
        admissions,
        *,
        component_id,
        candidate_selections,
        comparison_selections,
        extra_passages,
        question,
        scope,
        inventory_id,
        policy_id,
        member_budget,
        representation_policy,
    ):
        from corpus_structure.methods.structural_products import (
            dossier_root,
            produce_structural_dossier,
        )

        from .contextual_operations import contextual_relationship_binding
        from .contributions import contribution_identity
        from .data_product_reference import SemanticReference
        from .declared_candidate_products import candidate_member_values
        from .declared_record_sources import DeclaredNativeFrameSource
        from .declared_structural_calls import _passage
        from .declared_structural_references import DeclaredComponentRef, DeclaredStructuralSource
        from .structural_products import (
            DeclaredComparisonReport,
            DeclaredDefinitionApplicabilityReport,
            DeclaredDefinitionComponentsReport,
            DeclaredDossierComparisonSelection,
            DeclaredDossierReport,
            DeclaredStructuralInput,
        )

        def pairs(role, values):
            return tuple(zip(self.members(role), values, strict=True))

        def key(member):
            return canonical_bytes([member.product, member.member]).decode()

        source_pairs = pairs("sources", sources)
        frames = {
            key(member): DeclaredNativeFrameSource.acquire(
                self.prepared, value, member, project=self.context.project_id
            )
            for member, value in source_pairs
        }
        source_refs = {
            frame.pin.source_key: DeclaredStructuralSource.model_validate(frame.pin.values())
            for frame in frames.values()
        }
        passages = {}
        dependencies = []
        retained = []
        declared_reports = {}

        def retain(member, raw, report_type):
            self.check_active()
            if report_type is DeclaredDefinitionComponentsReport:
                from .structural_products import read_definition_components_report

                report = read_definition_components_report(raw)
            else:
                report = report_type.model_validate(raw)
            reference = DeclaredStructuralRef.from_bound(
                member, project=self.context.project_id, structural_id=report.product_id
            )
            # A derived report and its original inputs have distinct declared
            # subjects. Authenticate each complete source pin against the bound
            # dossier sources; keep the output reference in its own native context.
            for source in report.inputs.sources:
                original = source_refs.get(source.source)
                if original != source:
                    raise ValueError(
                        "dossier predecessor source is outside its exact bound original closure"
                    )
            for passage in report.inputs.passages:
                previous = passages.get(passage.passage_id)
                if previous is not None and previous != passage:
                    raise ValueError(
                        "dossier passage identity collides with a different retained passage"
                    )
                source = next(
                    value for value in report.inputs.sources if value.identity == passage.source_ref
                )
                frame = frames[source.source]
                if frame.text[passage.start : passage.end] != passage.text or not any(
                    start <= passage.start < passage.end <= end
                    for start, end in frame.selected_ranges
                ):
                    raise ValueError(
                        "dossier predecessor passage differs from its actual analyzed native source"
                    )
                passages[passage.passage_id] = passage
            dependencies.extend((member.product, report.product_id, *report.inputs.dependencies))
            payload: dict[str, Any] = {"report": report}
            retained.append((reference, payload))
            declared_reports[key(member)] = reference
            return report, reference, payload

        (component_member,) = self.members("components")
        component_report, _, _ = retain(
            component_member, components, DeclaredDefinitionComponentsReport
        )
        root_reference = DeclaredComponentRef.from_bound(
            component_member,
            project=self.context.project_id,
            structural_id=component_report.product_id,
            component_id=component_id,
        )
        root = dossier_root(root_reference, retained)
        if root.scope != scope:
            raise ValueError("dossier scope differs from its actual selected root")
        definition_members = {}
        for member, raw in pairs("definitions", definitions):
            report, reference, payload = retain(member, raw, DeclaredDefinitionApplicabilityReport)
            definition_members[reference] = (
                member,
                cast(DeclaredDefinitionApplicabilityReport, report),
                payload,
            )
        for member, raw in pairs("comparisons", comparisons):
            retain(member, raw, DeclaredComparisonReport)
        apply_structural_admissions(
            retained,
            pairs("admissions", admissions),
            project_id=self.context.project_id,
        )
        dependencies.extend(member.product for member in self.members("admissions"))
        for selected in TypeAdapter(tuple[DossierPassageSelection, ...]).validate_json(
            extra_passages
        ):
            frame = frames[selected.source_reference]
            _, passage = _passage(
                frame,
                passage_id=selected.passage_id,
                start=selected.start,
                end=selected.end,
                scope=selected.scope,
                version=selected.effective_version,
                parent=selected.parent,
            )
            if not any(
                start <= passage.start < passage.end <= end for start, end in frame.selected_ranges
            ):
                raise ValueError("dossier additional passage exceeds actual analyzed source")
            if passage.passage_id in passages and passages[passage.passage_id] != passage:
                raise ValueError("dossier additional passage changes an actual retained passage")
            passages[passage.passage_id] = passage
        contribution_retained = []
        candidate_values = {
            key(member): (member, raw) for member, raw in pairs("candidates", candidates)
        }
        checked_candidates = {}
        for selected in TypeAdapter(tuple[DossierCandidateSelection, ...]).validate_json(
            candidate_selections
        ):
            if selected.report_reference not in checked_candidates:
                member, raw = candidate_values[selected.report_reference]
                rows = candidate_member_values(raw, candidate_type="contribution")
                if not rows or any(
                    contribution_identity(row) != row["contribution_id"] for row in rows
                ):
                    raise ValueError(
                        "dossier candidate identity differs from its retained inventory"
                    )
                if any(
                    packet["member_id"] != "contribution:" + packet["body"]["contribution_id"]
                    for packet in raw["members"]
                    if packet["body"]["candidate_type"] == "contribution"
                ):
                    raise ValueError(
                        "dossier candidate address differs from its actual contribution identity"
                    )
                if len({row["contribution_id"] for row in rows}) != len(rows):
                    raise ValueError("dossier candidate inventory repeats a contribution identity")
                checked_candidates[selected.report_reference] = (
                    member,
                    raw,
                    {row["contribution_id"]: row for row in rows},
                )
            member, raw, rows = checked_candidates[selected.report_reference]
            frame = frames[raw["source_pin"]["source"]]
            source_context = {
                key: raw["source_pin"][key]
                for key in (
                    "project_id",
                    "subject",
                    "subject_definition",
                    "original_source",
                    "analyzed_scope_meaning",
                )
            }
            reference_context = DeclaredContributionRef.from_bound(
                member, project=self.context.project_id, contribution_id=selected.contribution_id
            ).context
            if raw["source_pin"] != frame.pin.values() or source_context != reference_context:
                raise ValueError("dossier candidate report differs from its actual native source")
            closure, pending = {}, [selected.contribution_id]
            while pending:
                identifier = pending.pop()
                if identifier in closure:
                    continue
                row = rows[identifier]
                closure[identifier] = row
                pending.extend(value["contribution_id"] for value in row.get("endpoints", ()))
                pending.extend(row.get("members", ()))
            reference = DeclaredContributionRef.from_bound(
                member, project=self.context.project_id, contribution_id=selected.contribution_id
            )
            dependencies.extend((member.product, reference.contribution_id))
            contribution_retained.append(
                (
                    reference,
                    {
                        "contributions": tuple(closure.values()),
                        "sources": [
                            {"pin": item.pin.values(), "projection": item.value}
                            for item in frames.values()
                        ],
                    },
                )
            )
        if set(candidate_values) != set(checked_candidates):
            raise ValueError("dossier candidate input includes an unselected inventory")
        relationship_values = {
            key(member): (member, raw) for member, raw in pairs("relationships", relationships)
        }
        relationship_bindings, selections = {}, []
        used_relationships = set()
        for selected in TypeAdapter(tuple[DossierComparisonSelection, ...]).validate_json(
            comparison_selections
        ):
            member, raw = relationship_values[selected.relationship_reference]
            binding = contextual_relationship_binding(
                raw, decision_id=selected.decision_id, edge_id=selected.edge_id
            )
            frame = frames[binding.source_pin["source"]]
            reference = DeclaredRelationshipRef.from_bound(
                member, project=self.context.project_id, edge_id=selected.edge_id
            )
            from .structural_admission import structural_statement

            root_meaning = structural_statement(component_report, root.component_id)[
                "definition_component"
            ]
            relationship_bindings[reference] = DossierRelationship(binding, frame, root_meaning)
            used_relationships.add(selected.relationship_reference)
            dependencies.append(member.product)
            comparison_reference = declared_reports[selected.comparison_reference]
            applicability_reference = (
                declared_reports[selected.applicability_reference]
                if selected.applicability_reference is not None
                else None
            )
            if applicability_reference is not None and binding.edge.relation != "specializes":
                from .data_product_reference import read_semantic_reference
                from .reference_resolution import selected_producing_reference_bindings

                producer, report, payload = definition_members[applicability_reference]
                origin = selected_producing_reference_bindings(producer).resolve(
                    read_semantic_reference(report.relationship_input)
                )
                payload["relationship_origin"] = origin
            selections.append(
                DeclaredDossierComparisonSelection(
                    comparison_product_id=comparison_reference.product_id,
                    side=selected.side,
                    relationship_ref=reference,
                    applicability_ref=applicability_reference,
                    conflict_passage_id=selected.conflict_passage_id,
                )
            )
        if used_relationships != set(relationship_values):
            raise ValueError("dossier relationship input includes an unselected decision")
        inputs = DeclaredStructuralInput(
            question=question,
            scope=scope,
            inventory_id=inventory_id,
            policy_id=policy_id,
            sources=tuple(source_refs.values()),
            passages=tuple(passages.values()),
            dependencies=tuple(dict.fromkeys(dependencies)),
            coverage_limits=(
                "Only explicitly selected retained predecessors are assembled; membership is not exhaustive.",
                "Only explicitly selected native structural admissions support comparison-statement facets; assembly establishes no member truth.",
            ),
        )
        value = produce_structural_dossier(
            inputs,
            root_component=root_reference,
            root=root,
            retained=tuple(retained),
            relationships=relationship_bindings,
            contribution_retained=tuple(contribution_retained),
            comparison_selections=tuple(selections),
            member_budget=member_budget,
            policy=representation_policy,
            check_active=self.check_active,
        )

        result = DeclaredDossierReport.model_validate(
            {
                **value.model_dump(mode="python"),
                "components_input": SemanticReference.whole("components").whole_value(),
            }
        )
        self.check_active()
        return result.model_dump(mode="json", exclude_none=True)


def execute_dossier(
    receiver,
    sources,
    components,
    definitions,
    comparisons,
    candidates,
    relationships,
    admissions,
    **selection,
):
    return receiver.inputs.run(
        sources,
        components,
        definitions,
        comparisons,
        candidates,
        relationships,
        admissions,
        **selection,
    )


def apply_structural_admissions(retained, admissions, *, project_id):
    """Supply the existing kernel only exact scoped whole-statement conclusions.

    Native completion authenticates each issuer's ordinary receipt and exact input
    support. These CPU checks prevent borrowing another retained report's statement;
    product possession alone confers no admission authority.
    """
    from .data_operation_values import semantic_value
    from .declared_structural_admission import DdoStructuralAdmission
    from .declared_structural_references import DeclaredProductRef
    from .structural_admission import structural_statement

    by_reference = {
        canonical_bytes(
            DeclaredProductRef.model_validate(
                reference.model_dump(exclude={"structural_id"})
            ).model_dump()
        ): payload
        for reference, payload in retained
    }
    used = set()
    for member, raw in admissions:
        value = DdoStructuralAdmission.model_validate(raw)
        key = canonical_bytes(value.report.model_dump())
        if value.report.project_id != project_id or key not in by_reference:
            raise ValueError(
                "dossier admission is outside its exact retained native report population"
            )
        if key in used:
            raise ValueError("dossier repeats admission for the same exact native report")
        used.add(key)
        payload = by_reference[key]
        if (
            value.statement_meaning_json
            != canonical_bytes(semantic_value(structural_statement(payload["report"]))).decode()
        ):
            raise ValueError("dossier admission substitutes its actual source-qualified statement")
        payload["public_assertions"] = (
            {
                "statement": value.statement,
                "assessment_id": member.product,
                "assessment_scope": "comparison_statement",
            },
        )


def dossier_kernel(
    arguments: dict,
    roles: tuple[ResolvedRoleBinding, ...],
    context: SubjectContext,
    *,
    prepared: PreparedRelease,
    check_active: Callable[[], None],
) -> dict:
    from corpus_structure.methods.dossier_declared import DossierOperation

    return DossierOperation(PreparedDossierInputs(prepared, roles, context, check_active)).run(
        **arguments
    )


@dataclass
class DossierCallPlan:
    prepared: PreparedRelease
    port: Any = None

    def verify(self):
        if dossier_profile_assets() != self.port.assets[0]:
            raise ValueError("dossier source or semantic assets changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):

        if binding is None or binding.subject_context is None:
            raise ValueError("dossier call requires its actual qualified binding")
        signature = inspect.signature(dossier_kernel, eval_str=True)
        bound = signature.bind(
            arguments=arguments.arguments,
            roles=binding.roles,
            context=binding.subject_context,
            prepared=self.prepared,
            check_active=check_active,
        )
        captured = dossier_operation_sources()
        return (
            yield from self.port.plan_cpu(
                dossier_kernel,
                bound,
                captured,
                prepared_release_id=self.prepared.release_id,
                verify=self.verify,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def resolve_dossier_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.dossier_declared import DossierOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != DossierOperation.__data_operation__["id"]:
        raise PortRefusal("dossier factory differs from its governing operation")
    plan = DossierCallPlan(prepared)
    receiver = DossierOperation(None)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.dossier_products.DossierCallPlan.plan",
        authorize,
        (dossier_profile_assets(),),
        dossier_operation_sources(),
        functions=(
            ("corpus_structure.semantic.dossier_products.dossier_kernel", dossier_kernel),
            ("corpus_structure.semantic.dossier_products.execute_dossier", execute_dossier),
            (
                "corpus_structure.semantic.dossier_products.PreparedDossierInputs.run",
                PreparedDossierInputs.run,
            ),
        ),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
