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

import yaml

from corpus_structure.ingest.annotations import AnnotationProfile, restore_annotations
from corpus_structure.methods.m1_source import M1CandidateProduct, M1Candidates, M1Config, M1GlinerReply, M1GlinerRequest

from .data_operation_model import BoundRoleMember, ResolvedRoleBinding
from .data_operation_json import json_bytes, json_loads
from .declared_contexts import DeclaredContextPopulation
from .declared_record_sources import DeclaredNativeFrameSource, declared_record_inputs
from .identity import canonical_bytes
from .types import PreparedRelease, SourceArtifact, SourceBundle

_MODEL = Path(__file__).parents[1] / "model/semantic/data-operation-candidate-inspection.yaml"


def m1_operation_inputs(bundle):
    from .sentence_products import sentence_product_inputs
    from .declared_candidate_products import candidate_inspection_inputs

    if "data_operation_sentences" not in {source.name for source in bundle.sources}:
        bundle = sentence_product_inputs(bundle)
    return candidate_inspection_inputs(bundle)


@lru_cache(maxsize=32)
def _algorithm_ast(content: bytes):
    return ast.dump(ast.parse(content), include_attributes=False)


def m1_profile_assets(configuration, record_schemas):
    configuration = M1Config.model_validate(configuration)
    values = configuration.model_dump(mode="json")
    for field in ("snapshot", "source_dependencies", "source_dependency_method"):
        values.pop(field)
    root = Path(__file__).parents[1]
    paths = ("methods/m1_source.py", "methods/record_assembly.py", "methods/record_packs.py", "methods/gliner.py", "methods/source_preparation.py", "methods/contribution_adapter.py", "methods/record_readings.py", "methods/assertion_qualification.py", "methods/math/pdf.py", "semantic/declared_record_sources.py", "semantic/declared_contexts.py", "semantic/source_contexts.py", "semantic/record_contracts.py", "semantic/records.py", "semantic/contributions.py", "semantic/record_interpretation.py", "semantic/m1_products.py", "semantic/declared_candidate_products.py")
    return SourceArtifact("m1/profile-assets", canonical_bytes({"version": "declared-m1-inspection-v1", "configuration": values, "schema_root": record_schemas.root, "schemas": [(source.name, source.content.hex()) for source in record_schemas.sources], "algorithms": [(name, _algorithm_ast((root / name).read_bytes())) for name in paths], "model": _MODEL.read_bytes().hex()}))


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
    return SourceArtifact("m1/acquisition", canonical_bytes({"snapshot": str(configuration.snapshot)}))


def m1_operation_sources(configuration, *, record_schemas, include_dependencies=True, sentence_selection=None):
    from .python_operation_sources import PythonSource, PythonSourceCollection

    root = Path(__file__).parents[1]
    paths = ("methods/m1_declared.py", "semantic/m1_products.py", "semantic/declared_candidate_products.py")
    own = PythonSourceCollection(tuple(PythonSource("corpus_structure." + name.removesuffix(".py").replace("/", "."), (root / name).read_bytes(), str(root / name)) for name in paths), boundary_contracts=(m1_profile_assets(configuration, record_schemas), m1_execution_custody(configuration)))
    if not include_dependencies:
        return own
    from .primary_operations import combine_primary_sources
    from .sentence_products import sentence_operation_sources
    from .source_discovery import source_discovery_operation_sources

    return combine_primary_sources(source_discovery_operation_sources(), sentence_operation_sources(configuration.sentences, selection=sentence_selection), own)


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
        return cls(source.text, tuple(value["pieces"]), tuple(value["items"]), tuple(value["ancestors"]), value["health"])


@dataclass(frozen=True)
class PreparedM1Inputs:
    prepared: PreparedRelease
    configuration: M1Config
    primary_member: BoundRoleMember
    annotation_member: BoundRoleMember
    sources_role: ResolvedRoleBinding
    project: str
    check_active: Callable[[], None]

    def run(self, primary, annotations, sources) -> Generator[M1GlinerRequest, M1GlinerReply, M1CandidateProduct]:
        from corpus_structure.methods.source_preparation import prepare_source
        from .sentence_products import source_annotation_rows

        frame = DeclaredNativeFrameSource.acquire(self.prepared, primary, self.primary_member, project=self.project)
        population = DeclaredContextPopulation.from_role(self.prepared, self.sources_role, sources, project=self.project)
        if frame.pin not in {source.pin for source in population.sources}:
            raise ValueError("primary source is outside its declared complete context population")
        checked = self.prepared.validate_json("DdoSourceAnnotations", json_bytes(annotations)).model_dump(mode="json", exclude_unset=True)
        if checked["source"] != primary["source"] or checked["selectors"] != primary["selectors"]:
            raise ValueError("M1 annotations belong to another exact source/scope")
        from corpus_structure.ingest.sentences import SentenceConfig

        if SentenceConfig.model_validate(checked["configuration"]) != self.configuration.sentences:
            raise ValueError("M1 annotation configuration differs from its admitted profile")
        profile = AnnotationProfile(self.configuration.sentences, execution_profile=checked["execution_profile"])
        products = restore_annotations(source_annotation_rows(checked), source=frame, profile=profile)
        if self.configuration.annotation_rules:
            raise ValueError("M1 named-rule profile requires its declared lower-rule input operation")
        data = NativeCandidateData.from_frame(frame)
        prepared_source = prepare_source(data, source_frame=frame, context_population=population, profile=profile, persisted_annotations=products, max_chars=self.configuration.max_context_chars, max_pieces=self.configuration.max_context_pieces, max_annotation_chars=self.configuration.max_annotation_chars, check_active=self.check_active, policy=self.configuration.policy, formula_prose=self.configuration.formula_prose, region_pointers=self.configuration.region_pointers)
        annotation_info = {"semantic_product": self.annotation_member.product, "member": self.annotation_member.member, "kind_contract": self.annotation_member.kind_contract, "dependency_digest": __import__("hashlib").sha256(canonical_bytes(checked)).hexdigest(), "execution_profile": checked["execution_profile"]}
        return (yield from M1Candidates().plan_candidate_replies(prepared=self.prepared, view=data, prepared_source=prepared_source, annotation_result=annotation_info, cfg=self.configuration, check_active=self.check_active, primary_layers={}))


def execute_declared_m1(receiver, primary, annotations, sources) -> Generator[M1GlinerRequest, M1GlinerReply, M1CandidateProduct]:
    return (yield from receiver.profile.run(primary, annotations, sources))


def execute_m1_kernel(
    primary: dict, annotations: dict, sources: tuple[dict, ...],
    primary_member: BoundRoleMember, annotation_member: BoundRoleMember,
    sources_role: ResolvedRoleBinding, project: str, configuration: str,
    *, prepared: PreparedRelease, check_active: Callable[[], None],
) -> Generator[M1GlinerRequest, M1GlinerReply, M1CandidateProduct]:
    """Original child entrypoint; one prepared capsule, one generator, no DB/provider."""
    from corpus_structure.methods.m1_declared import M1SourceCandidatesOperation

    profile = PreparedM1Inputs(prepared, M1Config.model_validate_json(configuration), primary_member, annotation_member, sources_role, project, check_active)
    return (yield from M1SourceCandidatesOperation(profile).run(primary, annotations, sources))


def candidate_report(prepared, model, product, primary, context):
    """Project this producer's explicit outcome through the shared candidate contract."""
    from .declared_candidate_products import candidate_inspection_report

    return candidate_inspection_report(prepared, model, primary, context,
        inspection_outcome=product.outcome.value, records=product.records or (),
        contributions=product.contributions or (), operations=product.contribution_operations or (),
        coordinate_texts=product.contribution_coordinate_texts,
        coverage=tuple({name: value for name, value in asdict(row).items() if value is not None} for row in product.coverage),
        diagnostics=product.parse_detail or {})


def complete_m1_inspection(prepared, model, product, primary, context, *, cpu_evidence=None, host_evidence=None):
    """Map the kernel's terminal domain outcome once, retaining valid partial output."""
    from corpus_structure.core.vocab import ObservationOutcome
    from .data_operation_prepared_call import PreparedCallResult

    if product.outcome == ObservationOutcome.FAILED:
        import structlog

        structlog.get_logger(__name__).error("m1.provider_inspection_failed", reason=product.error,
            coverage=[asdict(row) for row in product.coverage], diagnostics=product.parse_detail)
        return PreparedCallResult(None, cpu_evidence, host_evidence, "failed")
    return PreparedCallResult(candidate_report(prepared, model, product, primary, context), cpu_evidence, host_evidence)


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
        from corpus_structure.core.vocab import ObservationOutcome
        from corpus_structure.core.work import PreparedWork
        from corpus_structure.methods.gliner import GlinerRefused
        from corpus_structure.methods.gliner_worker import GlinerWorkerError
        from corpus_structure.methods.native_host import NativeExecutionReceipt
        from corpus_structure.methods.native_host_clients import HostedGliner
        from .data_operation_cpu import PythonCPUDescriptor
        from .data_operation_prepared_call import PreparedCallResult
        from .data_operation_stream import plan_cpu_coroutine

        if binding is None or binding.subject_context is None:
            raise ValueError("M1 requires its exact native binding and qualified subject context")
        selected = [(key, value) for key, value in execution_owner.consumer_inputs.items() if value.selection.binding is binding]
        if len(selected) != 1:
            raise ValueError("M1 requires its one already hydrated governing producer selection")
        obligation, _ = selected[0]
        primary, annotations, selected_sources = execution_owner.consumer_results[obligation]
        role = next(role for role in binding.roles if role.role == "sources")
        if tuple(value.member for value in selected_sources) != role.members:
            raise ValueError("M1 native selector changed the exact source population")
        signature = inspect.signature(execute_m1_kernel, eval_str=True)
        bound = signature.bind(**arguments.arguments,
            primary_member=primary.member, annotation_member=annotations.member,
            sources_role=role, project=binding.subject_context.project_id,
            configuration=self.configuration.model_dump_json(), prepared=self.prepared,
            check_active=check_active)
        captured = m1_operation_sources(self.configuration, record_schemas=self.record_schemas, include_dependencies=False)
        descriptor = PythonCPUDescriptor(tuple((source.module, source.filename, source.content) for source in captured.sources), "corpus_structure.semantic.m1_products.execute_m1_kernel", (), verification="prepared-kernel", control_parameter="check_active", prepared_parameter="prepared", prepared_release_id=self.prepared.release_id, invocation_form="coroutine")
        receipts = []
        hosted = HostedGliner(self.configuration.profile(), group=execution_owner.native_hosts, native_profile=self.configuration.native_execution_profile)

        def answer(question):
            if question.profile != self.configuration.profile() or question.native_profile != self.configuration.native_execution_profile:
                raise ValueError("M1 inference question differs from its admitted numerical profile")

            def serve():
                check_active()
                try:
                    reports = hosted.extract(question.pack, question.inputs, threshold=question.threshold, check_active=check_active, receipt_sink=receipts.append)
                    return M1GlinerReply(reports=reports)
                except GlinerRefused as error:
                    return M1GlinerReply(failure="refused", message=str(error))
                except GlinerWorkerError as error:
                    return M1GlinerReply(failure="worker", message=str(error))

            (reply,) = yield (PreparedWork(lambda: execution_owner.submit_python(serve)),)
            return reply

        product, cpu = yield from plan_cpu_coroutine(descriptor, bound, signature, verify=self.verify, execution_owner=execution_owner, check_active=check_active, answer_plan=answer)
        evidence = TypeAdapter(tuple[NativeExecutionReceipt, ...]).dump_json(tuple(receipts)) if receipts else None
        frame = None if product.outcome == ObservationOutcome.FAILED else DeclaredNativeFrameSource.acquire(self.prepared, arguments.arguments["primary"], primary.member, project=binding.subject_context.project_id)
        return complete_m1_inspection(self.prepared, self.model, product, frame, binding.subject_context, cpu_evidence=canonical_bytes(cpu.execution_receipt.record()), host_evidence=evidence)


def resolve_m1_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.m1_declared import M1SourceCandidatesOperation
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection, gliner_selection
    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    assets = {asset.name: asset for asset in custody}
    if "m1/profile-assets" not in assets or "m1/acquisition" not in assets:
        raise PortRefusal("M1 lacks its explicit semantic profile and physical acquisition custody")
    semantic = json.loads(assets["m1/profile-assets"].content)
    acquisition = json.loads(assets["m1/acquisition"].content)
    configuration = M1Config.model_validate({**semantic["configuration"], "snapshot": acquisition["snapshot"]})
    if configuration.native_execution_profile is None:
        raise PortRefusal("M1 requires its explicitly admitted numerical native execution profile")
    if configuration.formula_syntax:
        raise PortRefusal("M1 formula syntax profile requires an explicitly bound formal evidence operation")
    if configuration.annotation_rules:
        raise PortRefusal("M1 named-rule profile requires an explicitly bound lower-rule operation")
    native = NativeProfile(**configuration.native_execution_profile)
    selection = NativeSelection(native, configuration.snapshot)
    if gliner_selection(configuration.profile(), native.runtime_identity).native != native:
        raise PortRefusal("M1 numerical execution differs from its frozen configuration")
    selected = model.operation(operation)
    if selected.semantic_id != M1SourceCandidatesOperation.__data_operation__["id"]:
        raise PortRefusal("M1 prepared factory belongs to another governing producer")
    receiver = M1SourceCandidatesOperation(None)
    record_schemas = SourceBundle(semantic["schema_root"], tuple(SourceArtifact(name, bytes.fromhex(content)) for name, content in semantic["schemas"]))
    admitted_schemas = dict(json.loads(prepared.manifest)["sources"])
    if any(admitted_schemas.get(source.name) != source.digest for source in record_schemas.sources):
        raise PortRefusal("M1 record schemas differ from the actual admitted release")
    plan = M1InvocationPlan(prepared, model, configuration, sources, record_schemas)
    captured = m1_operation_sources(configuration, record_schemas=record_schemas, include_dependencies=False)
    port = PreparedOriginalCallPort(identity, model, selected, sources, custody,
        receiver.run, plan.plan, "corpus_structure.semantic.m1_products.M1InvocationPlan.plan",
        authorize, (m1_profile_assets(configuration, record_schemas), m1_execution_custody(configuration)), captured,
        functions=(("corpus_structure.semantic.m1_products.execute_m1_kernel", execute_m1_kernel),
            ("corpus_structure.semantic.m1_products.PreparedM1Inputs.run", PreparedM1Inputs.run),
            ("corpus_structure.semantic.m1_products.candidate_report", candidate_report),
            ("corpus_structure.semantic.m1_products.complete_m1_inspection", complete_m1_inspection),
            ("corpus_structure.methods.m1_source.M1Candidates.plan_candidates", M1Candidates.plan_candidates),
            ("corpus_structure.methods.m1_source.M1Candidates.plan_candidate_replies", M1Candidates.plan_candidate_replies)),
        native_selections=(selection,), requires_prepared_schema=True, completion_type=dict)
    plan.port = port
    return port
