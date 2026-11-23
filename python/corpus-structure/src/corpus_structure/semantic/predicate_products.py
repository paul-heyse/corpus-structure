"""Acquired predicate projection over genuine retained native/primary products."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .data_operation_model import ResolvedRoleBinding, SubjectContext
from .data_operation_partitions import PartitionedInput
from .data_operation_population import AcquiredPopulation
from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .sentence_population_inputs import SentencePopulationInputs, prepare_sentence_populations
from .types import PreparedRelease, SourceArtifact

_ROOT = Path(__file__).parents[1]
_PATHS = (
    "semantic/established_validity.py",
    "semantic/formal_products.py",
    "methods/predicate_declared.py",
    "semantic/predicate_products.py",
    "methods/predicate_contributions.py",
    "methods/predicate_frames.py",
    "methods/predicate_cross_block.py",
    "methods/structural_roles.py",
    "semantic/constructions/retained_rules.py",
    "semantic/constructions/retained_rules.json",
    "semantic/declared_record_sources.py",
    "semantic/declared_candidate_products.py",
    "semantic/source_contexts.py",
    "semantic/contributions.py",
    "semantic/contribution_input_references.py",
    "semantic/record_contracts.py",
    "semantic/sentence_partitions.py",
    "semantic/sentence_population_inputs.py",
    "semantic/sentence_products.py",
    "semantic/construction_products.py",
    "semantic/data_product_reference.py",
)


def predicate_inputs(bundle):
    from .construction_products import construction_product_inputs
    from .declared_candidate_products import candidate_inspection_inputs

    if "data_operation_constructions" not in {source.name for source in bundle.sources}:
        bundle = construction_product_inputs(bundle)
    return candidate_inspection_inputs(bundle)


def predicate_profile_assets():
    return SourceArtifact(
        "predicates/profile-assets",
        canonical_bytes(
            {
                "version": "declared-retained-predicate-v1",
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex()
                            if name in ("methods/predicate_declared.py",)
                            else (_ROOT / name).read_bytes().hex()
                        ),
                    )
                    for name in _PATHS
                ],
            }
        ),
    )


def predicate_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in (
                "methods/predicate_declared.py",
                "semantic/predicate_products.py",
                "semantic/data_operation_prepared_call.py",
            )
        ),
        boundary_contracts=(predicate_profile_assets(),),
    )


@dataclass(frozen=True)
class PreparedPredicateInputs:
    prepared: PreparedRelease
    roles: tuple[ResolvedRoleBinding, ...]
    context: SubjectContext
    check_active: Callable[[], None]

    def members(self, role, *, whole=True):
        selected = next(value for value in self.roles if value.role == role)
        if any(
            (whole and member.member is not None) or member.multiplicity != 1
            for member in selected.members
        ):
            raise ValueError("predicate input requires actual whole product inventories")
        return selected.members

    def subject_context(self, member):
        from .data_operation_model import SubjectContext

        return SubjectContext(
            self.context.project_id,
            member.subject,
            member.original_source,
            member.analyzed_scope,
            subject_definition=member.subject_definition,
        )

    def run(self, source, annotations: PartitionedInput, constructions, formal):
        from corpus_structure.methods.predicate_contributions import (
            declared_predicate_evidence,
            predicate_qualifier_refusal,
        )

        from .construction_products import CharacterizationSnapshot
        from .data_operation_admission import bound_data_operation_model
        from .declared_candidate_products import candidate_inspection_report
        from .declared_record_sources import DeclaredNativeFrameSource
        from .enriched_document_products import RetainedCharacterizationProduct
        from .formal_products import acquired_formal_product
        from .sentence_products import (
            acquired_source_annotations,
            retained_source_annotation_products,
        )
        from .source_contexts import NativeSourceContext, PreparedNativeSources, source_slice
        from .source_products import FrozenNativeSource

        model = bound_data_operation_model(self.prepared)
        selected = FrozenNativeSource.acquire(self.prepared, source)
        (source_member,) = self.members("source", whole=False)
        frame = DeclaredNativeFrameSource.acquire(
            self.prepared, source, source_member, project=self.context.project_id
        )
        (annotation_member,) = self.members("annotations")
        native = acquired_source_annotations(
            self.prepared,
            model,
            annotations.header,
            annotations.packets,
            selected,
            member=annotation_member,
            project=self.context.project_id,
            populations=annotations.populations,
        )
        retained_formal = []
        for member, body in zip(self.members("formal"), formal, strict=True):
            original = FrozenNativeSource.acquire(
                self.prepared, {**selected.value, "selectors": body["selectors"]}
            )
            product = acquired_formal_product(
                self.prepared,
                body,
                original,
                model=model,
                subject_context=self.subject_context(member),
                member=member,
            )
            if product.semantic_id != member.product:
                raise ValueError("predicate formal body differs from its bound product")
            retained_formal.append(product)
        retained = []
        for member, body in zip(self.members("constructions"), constructions, strict=True):
            product = RetainedCharacterizationProduct.acquire(
                self.prepared,
                model,
                self.prepared.index.definitions["DdoPrimaryConstructionProduct"].iri,
                canonical_bytes(body),
                subject_context=self.subject_context(member),
            )
            if product.semantic_id != member.product:
                raise ValueError("predicate construction body differs from its bound product")
            retained.append(CharacterizationSnapshot(product.semantic_id, product.content))
        products = retained_source_annotation_products(selected, native)
        self.check_active()
        if not frame.text:
            return candidate_inspection_report(
                self.prepared,
                model,
                frame,
                self.context,
                report_class="DdoPredicateInspectionReport",
                inspection_outcome="empty",
                diagnostics={"inspection": "closed-empty-original-source"},
            )
        context = NativeSourceContext(
            frame,
            (),
            (source_slice(frame, 0, len(frame.text)),),
            "declared retained predicate projection",
            "retained-primary-source-readings-v1",
            "exact bound original source",
            max_chars=len(frame.text),
            max_pieces=max(1, len(frame.pieces)),
            max_sources=1,
            version=2,
            preparation=PreparedNativeSources((frame,), max_sources=1),
        )
        evidence = declared_predicate_evidence(
            frame,
            context,
            products,
            dependency="native-product:" + native.semantic_id,
            primary_products=tuple(retained),
            formal_products=tuple(retained_formal),
            qualifier_preflight=lambda value: predicate_qualifier_refusal(self.prepared, value),
            check_active=self.check_active,
        )
        from .contribution_input_references import pack_contribution_input_support

        contributions, support = pack_contribution_input_support(
            evidence.contributions, self.roles, primary_evidence=evidence.primary_evidence
        )
        return candidate_inspection_report(
            self.prepared,
            model,
            frame,
            self.context,
            report_class="DdoPredicateInspectionReport",
            input_support=support,
            inspection_outcome="produced" if evidence.contributions else "empty",
            contributions=contributions,
            operations=evidence.operations,
            coordinate_texts=evidence.coordinate_texts,
            coverage=[
                {
                    "family": row["question"],
                    "scope": canonical_bytes(selected.value["selectors"]).decode(),
                    "outcome": row["outcome"],
                    **({"reason": row["reason"]} if "reason" in row else {}),
                }
                for row in evidence.operations
            ],
            diagnostics={
                "inspection_complete": evidence.inspection_complete,
            },
        )


def execute_predicate_profile(receiver, source, annotations, constructions, formal):
    return receiver.inputs.run(source, annotations, constructions, formal)


def predicate_kernel(
    arguments: dict,
    annotation_header: bytes,
    annotation_placements: SentencePopulationInputs,
    annotation_items: tuple[AcquiredPopulation, ...],
    roles: tuple[ResolvedRoleBinding, ...],
    context: SubjectContext,
    *,
    prepared: PreparedRelease,
    check_active: Callable[[], None],
) -> dict:
    from corpus_structure.methods.predicate_declared import PredicateEvidenceOperation

    annotations = annotation_placements.attach(annotation_header, annotation_items)
    return PredicateEvidenceOperation(
        PreparedPredicateInputs(prepared, roles, context, check_active)
    ).run(annotations=annotations, **arguments)


@dataclass
class PredicateCallPlan:
    prepared: PreparedRelease
    port: Any = None

    def verify(self):
        if predicate_profile_assets() != self.port.assets[0]:
            raise ValueError("predicate original source or semantic assets changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):
        if binding is None or binding.subject_context is None:
            raise ValueError("predicate call requires its exact qualified binding")
        operands = dict(arguments.arguments)
        annotations = operands.pop("annotations")
        placements, transfers = prepare_sentence_populations(
            annotations, self.port.identity.recipe
        )
        signature = inspect.signature(predicate_kernel, eval_str=True)
        bound = signature.bind(
            arguments=operands,
            annotation_header=annotations.header,
            annotation_placements=placements,
            annotation_items=tuple(item.population for item in transfers),
            roles=binding.roles,
            context=binding.subject_context,
            prepared=self.prepared,
            check_active=check_active,
        )
        captured = predicate_operation_sources()
        return (
            yield from self.port.plan_cpu(
                predicate_kernel,
                bound,
                captured,
                prepared_release_id=self.prepared.release_id,
                population_inputs={"annotation_items": transfers},
                verify=self.verify,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def resolve_predicate_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.predicate_declared import PredicateEvidenceOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != PredicateEvidenceOperation.__data_operation__["id"]:
        raise PortRefusal("predicate factory differs from its governing operation")
    receiver = PredicateEvidenceOperation(None)
    plan = PredicateCallPlan(prepared)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.predicate_products.PredicateCallPlan.plan",
        authorize,
        (predicate_profile_assets(),),
        predicate_operation_sources(),
        functions=(
            ("corpus_structure.semantic.predicate_products.predicate_kernel", predicate_kernel),
            (
                "corpus_structure.semantic.predicate_products.execute_predicate_profile",
                execute_predicate_profile,
            ),
            (
                "corpus_structure.semantic.predicate_products.PreparedPredicateInputs.run",
                PreparedPredicateInputs.run,
            ),
        ),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
