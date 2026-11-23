"""Declared M1 inspection over admitted source values and original CPU coroutine."""

from __future__ import annotations

import ast
import inspect
import json
from collections.abc import Callable, Generator
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from corpus_structure.ingest.annotations import AnnotationProfile, restore_annotations
from corpus_structure.methods.m1_source import (
    M1CandidateProduct,
    M1Config,
    M1GlinerReply,
    M1GlinerRequest,
    plan_candidates,
)

from .data_operation_model import (
    BoundRoleMember,
    EffectiveDataOperationModel,
    ResolvedRoleBinding,
    SubjectContext,
)
from .data_operation_population import AcquiredPopulation
from .declared_contexts import DeclaredContextPopulation
from .declared_record_sources import DeclaredNativeFrameSource
from .identity import canonical_bytes
from .sentence_population_inputs import SentencePopulationInputs, prepare_sentence_populations
from .types import PreparedRelease, SourceArtifact, SourceBundle

_MODEL = Path(__file__).parents[1] / "model/semantic/data-operation-candidate-inspection.yaml"


def m1_operation_inputs(bundle):
    from .construction_products import construction_product_inputs
    from .declared_candidate_products import candidate_inspection_inputs

    if "data_operation_constructions" not in {source.name for source in bundle.sources}:
        bundle = construction_product_inputs(bundle)
    return candidate_inspection_inputs(bundle)


@lru_cache(maxsize=32)
def _algorithm_ast(content: bytes):
    return ast.dump(ast.parse(content), include_attributes=False)


def m1_profile_assets(configuration, record_schemas):
    configuration = M1Config.model_validate(configuration)
    values = configuration.model_dump(mode="json")
    values.pop("snapshot")
    from .predicate_products import predicate_profile_assets

    root = Path(__file__).parents[1]
    paths = (
        "methods/m1_source.py",
        "methods/gliner_batching.py",
        "methods/record_assembly.py",
        "methods/record_packs.py",
        "methods/gliner.py",
        "methods/source_preparation.py",
        "methods/contribution_adapter.py",
        "methods/record_readings.py",
        "methods/assertion_qualification.py",
        "methods/math/pdf.py",
        "semantic/declared_record_sources.py",
        "semantic/declared_contexts.py",
        "semantic/source_contexts.py",
        "semantic/record_contracts.py",
        "semantic/contributions.py",
        "semantic/record_interpretation.py",
        "semantic/m1_products.py",
        "semantic/declared_candidate_products.py",
        "semantic/sentence_products.py",
        "semantic/sentence_partitions.py",
        "semantic/data_operation_partitions.py",
        "semantic/sentence_population_inputs.py",
    )
    return SourceArtifact(
        "m1/profile-assets",
        canonical_bytes(
            {
                "version": "declared-m1-inspection-v1",
                "configuration": values,
                "schema_root": record_schemas.root,
                "schemas": [
                    (source.name, source.content.hex()) for source in record_schemas.sources
                ],
                "algorithms": [
                    (name, _algorithm_ast((root / name).read_bytes())) for name in paths
                ],
                "model": _MODEL.read_bytes().hex(),
                "predicate_assets": json.loads(predicate_profile_assets().content),
            }
        ),
    )


def freeze_m1_configuration(configuration):
    """Acquire the actual numerical profile before authoring/admission, without inference."""
    from corpus_structure.methods.native_profiles import gliner_selection, preflight_native_runtime

    configuration = M1Config.model_validate(configuration)
    if configuration.native_execution_profile is not None:
        return configuration
    runtime = preflight_native_runtime("gliner", configuration.snapshot)["runtime_identity"]
    selection = gliner_selection(configuration.profile(), runtime)
    return configuration.model_copy(update={"native_execution_profile": selection.native.wire})


def m1_execution_custody(configuration):
    configuration = M1Config.model_validate(configuration)
    return SourceArtifact(
        "m1/acquisition", canonical_bytes({"snapshot": str(configuration.snapshot)})
    )


def m1_acquisition_specification():
    from corpus_structure.methods.m1_declared import M1SourceCandidatesOperation

    from .data_operation_prepared_products import PreparedProductSpecification

    prefix = "corpus_structure.semantic.m1_products."
    return PreparedProductSpecification(
        (
            (
                "corpus_structure.methods.m1_declared.M1SourceCandidatesOperation.run",
                M1SourceCandidatesOperation.run,
            ),
            (prefix + "M1InvocationPlan.plan", M1InvocationPlan.plan),
            (prefix + "execute_m1_kernel", execute_m1_kernel),
            (prefix + "PreparedM1Inputs.run", PreparedM1Inputs.run),
            (prefix + "candidate_report", candidate_report),
            (prefix + "complete_m1_inspection", complete_m1_inspection),
            (prefix + "plan_m1_gliner", plan_m1_gliner),
            ("corpus_structure.methods.m1_source.plan_candidates", plan_candidates),
        ),
        support_modules=(
            "corpus_structure.semantic.declared_candidate_products",
            "corpus_structure.semantic.data_operation_partitions",
            "corpus_structure.semantic.data_operation_prepared_call",
        ),
    )


def m1_operation_sources(
    configuration, *, record_schemas, include_dependencies=True, sentence_selection=None
):
    configuration = M1Config.model_validate(configuration)
    own = m1_acquisition_specification().capture(
        Path(__file__).parents[1],
        boundary_contracts=(
            m1_profile_assets(configuration, record_schemas),
            m1_execution_custody(configuration),
        ),
    )
    if not include_dependencies:
        return own
    from .characterization_ports import construction_operation_sources
    from .primary_operations import combine_primary_sources
    from .source_discovery import source_discovery_operation_sources

    return combine_primary_sources(
        source_discovery_operation_sources(),
        construction_operation_sources(
            sentence_configuration=configuration.sentences,
            sentence_selection=sentence_selection,
        ),
        own,
    )


@dataclass(frozen=True)
class NativeCandidateData:
    """Exact native language columns; no physical view or task facade."""

    text: str
    pieces: tuple[dict, ...]
    items: tuple[dict, ...]
    ancestors: tuple[dict, ...]
    health: dict

    @classmethod
    def from_frame(cls, source):
        value = json.loads(source.native_context)
        return cls(
            source.text,
            source.inspectable_pieces,
            tuple(value["items"]),
            tuple(value["ancestors"]),
            value["health"],
        )


@dataclass(frozen=True)
class PreparedM1Inputs:
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    configuration: M1Config
    primary_member: BoundRoleMember
    annotation_member: BoundRoleMember
    construction_member: BoundRoleMember
    sources_role: ResolvedRoleBinding
    project: str
    check_active: Callable[[], None]

    def run(
        self, primary, annotations, construction, sources
    ) -> Generator[M1GlinerRequest, M1GlinerReply, M1CandidateProduct]:
        from corpus_structure.methods.source_preparation import prepare_source

        from .data_operation_json import json_loads
        from .sentence_products import SourceAnnotations, source_annotation_rows

        frame = DeclaredNativeFrameSource.acquire(
            self.prepared, primary, self.primary_member, project=self.project
        )
        population = DeclaredContextPopulation.from_role(
            self.prepared, self.sources_role, sources, project=self.project
        )
        if frame.pin not in {source.pin for source in population.sources}:
            raise ValueError("primary source is outside its declared complete context population")
        checked = json_loads(annotations.header)
        inventory = SourceAnnotations(
            annotations.header,
            self.prepared,
            self.model,
            partitions=annotations.packets,
            populations=annotations.populations,
        )
        if checked["source"] != primary["source"] or tuple(checked["selectors"]) != tuple(
            primary["selectors"]
        ):
            raise ValueError("M1 annotations belong to another exact source/scope")
        from corpus_structure.ingest.sentences import SentenceConfig

        if SentenceConfig.model_validate(checked["configuration"]) != self.configuration.sentences:
            raise ValueError("M1 annotation configuration differs from its admitted profile")
        profile = AnnotationProfile(
            self.configuration.sentences, execution_profile=checked["execution_profile"]
        )
        products = restore_annotations(
            source_annotation_rows(inventory), source=frame, profile=profile
        )
        from corpus_structure.methods.predicate_frames import prepare_predicate_readings

        from .construction_products import CharacterizationSnapshot
        from .enriched_document_products import RetainedCharacterizationProduct

        member = self.construction_member
        if member.member is not None or member.multiplicity != 1:
            raise ValueError("M1 predicate input requires one actual whole construction product")
        retained = RetainedCharacterizationProduct.acquire(
            self.prepared,
            self.model,
            self.prepared.index.definitions["DdoPrimaryConstructionProduct"].iri,
            canonical_bytes(construction),
            subject_context=SubjectContext(
                self.project,
                member.subject,
                member.original_source,
                member.analyzed_scope,
                subject_definition=member.subject_definition,
            ),
        )
        if retained.semantic_id != member.product:
            raise ValueError("M1 construction body differs from its selected native product")
        readings = prepare_predicate_readings(
            (CharacterizationSnapshot(retained.semantic_id, retained.content),)
        )
        readings.for_source(frame.pin)
        data = NativeCandidateData.from_frame(frame)
        prepared_source = prepare_source(
            data,
            source_frame=frame,
            context_population=population,
            profile=profile,
            persisted_annotations=products,
            max_chars=self.configuration.max_context_chars,
            max_pieces=self.configuration.max_context_pieces,
            max_annotation_chars=self.configuration.max_annotation_chars,
            check_active=self.check_active,
            policy=self.configuration.policy,
            formula_prose=self.configuration.formula_prose,
            region_pointers=self.configuration.region_pointers,
        )
        annotation_info = {
            "semantic_product": self.annotation_member.product,
            "member": self.annotation_member.member,
            "kind_contract": self.annotation_member.kind_contract,
            "dependency_digest": __import__("hashlib").sha256(canonical_bytes(checked)).hexdigest(),
            "execution_profile": checked["execution_profile"],
        }
        return (
            yield from plan_candidates(
                prepared=self.prepared,
                model=self.model,
                view=data,
                prepared_source=prepared_source,
                annotation_result=annotation_info,
                primary_products=readings,
                cfg=self.configuration,
                check_active=self.check_active,
            )
        )


def execute_declared_m1(
    receiver, primary, annotations, construction, sources
) -> Generator[M1GlinerRequest, M1GlinerReply, M1CandidateProduct]:
    return (yield from receiver.profile.run(primary, annotations, construction, sources))


def execute_m1_kernel(
    primary: dict,
    annotation_header: bytes,
    annotation_placements: SentencePopulationInputs,
    annotation_items: tuple[AcquiredPopulation, ...],
    construction: dict,
    sources: tuple[dict, ...],
    primary_member: BoundRoleMember,
    annotation_member: BoundRoleMember,
    construction_member: BoundRoleMember,
    sources_role: ResolvedRoleBinding,
    project: str,
    configuration: str,
    *,
    prepared: PreparedRelease,
    check_active: Callable[[], None],
) -> Generator[M1GlinerRequest, M1GlinerReply, M1CandidateProduct]:
    """Original child entrypoint; one prepared capsule, one generator, no DB/provider."""
    from corpus_structure.methods.m1_declared import M1SourceCandidatesOperation

    from .data_operation_admission import bound_data_operation_model

    profile = PreparedM1Inputs(
        prepared,
        bound_data_operation_model(prepared),
        M1Config.model_validate_json(configuration),
        primary_member,
        annotation_member,
        construction_member,
        sources_role,
        project,
        check_active,
    )
    return (
        yield from M1SourceCandidatesOperation(profile).run(
            primary,
            annotation_placements.attach(annotation_header, annotation_items),
            construction,
            sources,
        )
    )


def candidate_report(prepared, model, product, primary, context):
    """Project this producer's explicit outcome through the shared candidate contract."""
    from .declared_candidate_products import candidate_inspection_report

    return candidate_inspection_report(
        prepared,
        model,
        primary,
        context,
        inspection_outcome=product.outcome.value,
        records=product.records or (),
        contributions=product.contributions or (),
        operations=product.contribution_operations or (),
        coordinate_texts=product.contribution_coordinate_texts,
        coverage=tuple(
            {name: value for name, value in asdict(row).items() if value is not None}
            for row in product.coverage
        ),
        diagnostics=product.parse_detail or {},
    )


def complete_m1_inspection(
    prepared,
    model,
    product,
    primary,
    context,
    *,
    cpu_evidence=None,
    host_evidence=None,
    provider_evidence=None,
):
    """Map the kernel's terminal domain outcome once, retaining valid partial output."""
    from corpus_structure.semantic.source_types import ObservationOutcome

    from .data_operation_prepared_call import PreparedCallResult

    if product.outcome == ObservationOutcome.FAILED:
        import structlog

        structlog.get_logger(__name__).error(
            "m1.provider_inspection_failed",
            reason=product.error,
            coverage=[asdict(row) for row in product.coverage],
            diagnostics=product.parse_detail,
        )
        return PreparedCallResult(None, cpu_evidence, host_evidence, "failed", provider_evidence)
    return PreparedCallResult(
        candidate_report(prepared, model, product, primary, context),
        cpu_evidence,
        host_evidence,
        provider_execution_evidence=provider_evidence,
    )


def plan_m1_gliner(question, configuration, *, execution_owner, check_active, ordinal, receipts):
    """Serve the exact original question through the existing shared provider lane."""
    from corpus_structure.methods.characterization_resources import (
        GLiNERWork,
        LogicalProviderMember,
    )
    from corpus_structure.methods.native_host import NativeRetirementUncertain, payload_digest

    if (
        question.profile != configuration.profile()
        or question.native_profile != configuration.native_execution_profile
    ):
        raise ValueError("M1 inference question differs from its admitted numerical profile")
    check_active()
    claim = execution_owner.claim
    correlation = payload_digest(
        {
            "request": claim.request_id,
            "generation": claim.generation,
            "task": claim.task_id,
            "attempt": claim.attempt,
            "question": ordinal,
        }
    )
    logical = LogicalProviderMember(
        claim.request_id,
        claim.generation,
        claim.task_id,
        claim.attempt,
        "m1-question:" + str(ordinal),
        0,
        len(question.inputs),
        payload_digest([asdict(value) for value in question.inputs]),
    )
    request = GLiNERWork(
        question.profile,
        question.pack,
        question.inputs,
        question.threshold,
        "flat",
        correlation,
        (check_active,),
        logical_members=(logical,),
    )
    (reply,) = yield (
        execution_owner.providers.work(request, reservation=execution_owner.reservation),
    )
    check_active()
    if reply.correlation != correlation:
        raise ValueError("M1 provider response belongs to another physical question")
    if reply.execution_receipt is not None:
        receipts.append(reply.execution_receipt)
    if reply.retirement_uncertain:
        raise NativeRetirementUncertain(reply.error_message)
    if reply.error_type in {"GlinerRefused", "Pm2WorkerRefused"}:
        from corpus_structure.methods.gliner_worker import GlinerAdmission

        return M1GlinerReply(
            admissions=tuple(
                GlinerAdmission(
                    index,
                    item.context_id,
                    item.context_digest,
                    False,
                    reply.error_message or reply.error_type,
                )
                for index, item in enumerate(question.inputs)
            )
        )
    if reply.error_type in {"GlinerWorkerError", "Pm2WorkerError"}:
        return M1GlinerReply(failure="worker", message=reply.error_message or reply.error_type)
    if reply.error_type is not None:
        _ = reply.payload
        raise ValueError("unknown M1 provider failure disposition")
    if len(reply.admissions) != len(question.inputs) or any(
        (admission.context_id, admission.context_digest) != (value.context_id, value.context_digest)
        for admission, value in zip(reply.admissions, question.inputs, strict=True)
    ):
        raise ValueError("M1 provider changed the original admission population")
    return M1GlinerReply(admissions=reply.admissions, reports=reply.reports)


@dataclass
class M1InvocationPlan:
    prepared: PreparedRelease
    model: Any
    configuration: M1Config
    sources: Any
    record_schemas: SourceBundle
    port: Any = None

    def verify(self):
        from .data_operation_ports import PortRefusal

        self.port._verify()
        if m1_profile_assets(self.configuration, self.record_schemas) != self.port.assets[0]:
            raise PortRefusal("M1 original semantic algorithm/schema/configuration assets changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from pydantic import TypeAdapter

        from corpus_structure.methods.characterization_resources import ProviderExecutionReceipt
        from corpus_structure.semantic.source_types import ObservationOutcome

        from .data_operation_cpu import PythonCPUDescriptor
        from .data_operation_stream import plan_cpu_coroutine

        if binding is None or binding.subject_context is None:
            raise ValueError("M1 requires its exact native binding and qualified subject context")
        selected = [
            (key, value)
            for key, value in execution_owner.consumer_inputs.items()
            if value.selection.binding is binding
        ]
        if len(selected) != 1:
            raise ValueError("M1 requires its one already hydrated governing producer selection")
        obligation, _ = selected[0]
        primary, annotations, construction, selected_sources = execution_owner.consumer_results[
            obligation
        ]
        role = next(role for role in binding.roles if role.role == "sources")
        if tuple(value.member for value in selected_sources) != role.members:
            raise ValueError("M1 native selector changed the exact source population")
        physical_arguments = dict(arguments.arguments)
        nominal_annotations = physical_arguments.pop("annotations")
        if nominal_annotations is not annotations.partitioned:
            raise ValueError("M1 annotations differ from their exact admitted partitioned input")
        placements, transfers = prepare_sentence_populations(
            nominal_annotations, self.port.identity.recipe
        )
        signature = inspect.signature(execute_m1_kernel, eval_str=True)
        bound = signature.bind(
            **physical_arguments,
            annotation_header=nominal_annotations.header,
            annotation_placements=placements,
            annotation_items=tuple(item.population for item in transfers),
            primary_member=primary.member,
            annotation_member=annotations.member,
            construction_member=construction.member,
            sources_role=role,
            project=binding.subject_context.project_id,
            configuration=self.configuration.model_dump_json(),
            prepared=self.prepared,
            check_active=check_active,
        )
        captured = m1_operation_sources(
            self.configuration, record_schemas=self.record_schemas, include_dependencies=False
        )
        descriptor = PythonCPUDescriptor(
            tuple((source.module, source.filename, source.content) for source in captured.sources),
            "corpus_structure.semantic.m1_products.execute_m1_kernel",
            (),
            verification="prepared-kernel",
            control_parameter="check_active",
            prepared_parameter="prepared",
            prepared_release_id=self.prepared.release_id,
            invocation_form="coroutine",
        )
        receipts = []
        ordinal = 0

        def answer(question):
            nonlocal ordinal
            ordinal += 1
            return (
                yield from plan_m1_gliner(
                    question,
                    self.configuration,
                    execution_owner=execution_owner,
                    check_active=check_active,
                    ordinal=ordinal,
                    receipts=receipts,
                )
            )

        product, cpu = yield from plan_cpu_coroutine(
            descriptor,
            bound,
            signature,
            verify=self.verify,
            execution_owner=execution_owner,
            check_active=check_active,
            answer_plan=answer,
            population_inputs={"annotation_items": transfers},
        )
        evidence = (
            TypeAdapter(tuple[ProviderExecutionReceipt, ...]).dump_json(tuple(receipts))
            if receipts
            else None
        )
        frame = (
            None
            if product.outcome == ObservationOutcome.FAILED
            else DeclaredNativeFrameSource.acquire(
                self.prepared,
                arguments.arguments["primary"],
                primary.member,
                project=binding.subject_context.project_id,
            )
        )
        return complete_m1_inspection(
            self.prepared,
            self.model,
            product,
            frame,
            binding.subject_context,
            cpu_evidence=canonical_bytes(cpu.execution_receipt.record()),
            provider_evidence=evidence,
        )


def resolve_m1_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.m1_declared import M1SourceCandidatesOperation
    from corpus_structure.methods.native_profiles import (
        NativeProfile,
        NativeSelection,
        gliner_selection,
    )

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    assets = {asset.name: asset for asset in custody}
    if "m1/profile-assets" not in assets or "m1/acquisition" not in assets:
        raise PortRefusal("M1 lacks its explicit semantic profile and physical acquisition custody")
    semantic = json.loads(assets["m1/profile-assets"].content)
    acquisition = json.loads(assets["m1/acquisition"].content)
    configuration = M1Config.model_validate(
        {**semantic["configuration"], "snapshot": acquisition["snapshot"]}
    )
    if configuration.native_execution_profile is None:
        raise PortRefusal("M1 requires its explicitly admitted numerical native execution profile")
    native = NativeProfile(**configuration.native_execution_profile)
    selection = NativeSelection(native, configuration.snapshot)
    if gliner_selection(configuration.profile(), native.runtime_identity).native != native:
        raise PortRefusal("M1 numerical execution differs from its frozen configuration")
    selected = model.operation(operation)
    if selected.semantic_id != M1SourceCandidatesOperation.__data_operation__["id"]:
        raise PortRefusal("M1 prepared factory belongs to another governing producer")
    receiver = M1SourceCandidatesOperation(None)
    record_schemas = SourceBundle(
        semantic["schema_root"],
        tuple(
            SourceArtifact(name, bytes.fromhex(content)) for name, content in semantic["schemas"]
        ),
    )
    admitted_schemas = dict(json.loads(prepared.manifest)["sources"])
    if any(admitted_schemas.get(source.name) != source.digest for source in record_schemas.sources):
        raise PortRefusal("M1 record schemas differ from the actual admitted release")
    plan = M1InvocationPlan(prepared, model, configuration, sources, record_schemas)
    captured = m1_operation_sources(
        configuration, record_schemas=record_schemas, include_dependencies=False
    )
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.m1_products.M1InvocationPlan.plan",
        authorize,
        (m1_profile_assets(configuration, record_schemas), m1_execution_custody(configuration)),
        captured,
        # The common port supplies the first two bindings from its original and physical plan.
        functions=m1_acquisition_specification().functions[2:],
        native_selections=(selection,),
        requires_prepared_schema=True,
        completion_type=dict,
    )
    plan.port = port
    return port
