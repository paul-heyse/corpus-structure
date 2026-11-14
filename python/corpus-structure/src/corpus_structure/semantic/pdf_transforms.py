"""Acquired PDF transformations over exact native publication support.

The existing PDF workers, finite kernels, private staging and sealed publication
remain their owners. This adapter supplies actual native-request custody only.
"""

from __future__ import annotations

import inspect
import json
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass
from hashlib import file_digest, sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select

from .identity import canonical_bytes
from .types import SourceArtifact


class PdfEnrichmentOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cell_math_pattern: str = (
        "(?:[=+×÷∑∏∫√∞≤≥∈⊂∪∩^_\\\\]|(?<!\\w)[A-Za-z](?!\\w)|\\d)"
    )
    cell_prose_pattern: str = "[A-Za-z]{2,}(?:[\\s,;:'’().-]+[A-Za-z]{2,})*[.!?]?"
    crop_padding_points: float = Field(default=0.75, ge=0)


class PdfIntegrationOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    # The exact existing released recovery contract; no generic retry is added.
    recovery_policy: dict[str, Any] | None
    integration_policy: dict[str, Any]
    source_recovery: Literal["grinstead-snell-witnessed-v1"] | None = None

    @field_validator("recovery_policy")
    @classmethod
    def recovery(cls, value):
        from corpus_structure.ingest.pdf_recognition_methods import PdfRecognitionRecoveryPolicy

        return None if value is None else PdfRecognitionRecoveryPolicy.model_validate(value).model_dump(mode="json")

    @field_validator("integration_policy")
    @classmethod
    def policy(cls, value):
        from .pdf_integrated import normalize_pdf_integration_policy

        return normalize_pdf_integration_policy(value)


class PdfRecognitionResources(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    python: str = Field(min_length=1)
    script: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    receipts: str = Field(min_length=1)
    timeout_seconds: float = Field(gt=0)


def _root():
    return Path(__file__).parents[1]


def _implementation_files(mode):
    common = (
        "semantic/pdf_transforms.py", "semantic/pdf_capture.py",
        "semantic/data_operation_pdf_effect.py", "semantic/pdf_effect_contract.py",
        "semantic/pdf_record_reader.py", "semantic/pdf_publication.py",
        "semantic/pdf_integrated.py", "orchestrate/pdf_streaming.py",
        "ingest/pdf_methods.py", "ingest/pdf_record_product.py",
        "ingest/pdf_hierarchy.py", "ingest/pdf_section_views.py",
        "ingest/pdf_candidate_source.py", "ingest/pdf_worker.py", "ingest/pdf_capacity.py",
    )
    extra = (
        "ingest/pdf_selected_enrichment.py", "ingest/pdf_enrichment.py",
        "ingest/pdf_candidate_geometry.py",
    ) if mode == "enriched" else (
        "ingest/pdf_recognition.py", "ingest/pdf_recognition_methods.py",
        "ingest/pdf_stream_reconciliation.py", "ingest/pdf_reconciliation.py",
        "ingest/pdf_incumbent_recovery.py",
    )
    return common + extra


def _file_hash(path):
    with Path(path).open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def pdf_transform_custody(mode, *, directory, recipe=None, assets=None, options, recognition_recipe=None, resources=None, nemotron_endpoint=None):
    if mode not in {"enriched", "integrated"}:
        raise ValueError("unknown PDF transformation capability")
    options = (PdfEnrichmentOptions if mode == "enriched" else PdfIntegrationOptions).model_validate(options)
    record = dict(
        mode=mode, directory=str(Path(directory).resolve()), options=options.model_dump(mode="json"),
        files=[(name, (_root() / name).read_bytes().hex()) for name in _implementation_files(mode)],
    )
    if mode == "enriched":
        from .pdf_capture import pdf_capture_custody

        record["native"] = json.loads(pdf_capture_custody(recipe, assets, directory=directory, nemotron_endpoint=nemotron_endpoint, require_nemotron_handoff=nemotron_endpoint is not None).content)
    else:
        from corpus_structure.ingest.pdf_recognition import NemotronRecipe

        if not isinstance(recognition_recipe, NemotronRecipe):
            raise ValueError("recognition requires an explicit immutable NemotronRecipe")
        resources = PdfRecognitionResources.model_validate(resources)
        worker = Path(resources.script).resolve()
        interpreter = Path(resources.python).resolve()
        record.update(
            recognition_recipe=asdict(recognition_recipe),
            recognition_bytes=recognition_recipe.to_bytes().hex(),
            resources=resources.model_copy(update={"script": str(worker), "python": str(interpreter), "receipts": str(Path(resources.receipts).resolve())}).model_dump(mode="json"),
            worker_digest=_file_hash(worker), worker_source=worker.read_bytes().hex(), interpreter_digest=_file_hash(interpreter),
        )
    return SourceArtifact("pdf-" + mode + "/execution-custody", canonical_bytes(record))


def pdf_transform_operation_sources(mode, **profile):
    from .python_operation_sources import PythonSource, PythonSourceCollection

    module = "pdf_enrichment_operation" if mode == "enriched" else "pdf_integration_operation"
    path = _root() / "ingest" / (module + ".py")
    custody = pdf_transform_custody(mode, **profile)
    return PythonSourceCollection(
        tuple(PythonSource(name, source.read_bytes(), str(source)) for name, source in (
            ("corpus_structure.ingest." + module, path),
            ("corpus_structure.semantic.pdf_transforms", Path(__file__)),
            ("corpus_structure.semantic.data_operation_pdf_effect", Path(__file__).with_name("data_operation_pdf_effect.py")),
            ("corpus_structure.semantic.pdf_effect_contract", Path(__file__).with_name("pdf_effect_contract.py")),
            ("corpus_structure.semantic.data_operation_effects", Path(__file__).with_name("data_operation_effects.py")),
        )),
        boundary_contracts=(custody,),
    )


def _endpoint(mode):
    if mode == "enriched":
        from corpus_structure.ingest.pdf_enrichment_operation import PdfEnrichmentOperation

        return PdfEnrichmentOperation
    from corpus_structure.ingest.pdf_integration_operation import PdfIntegrationOperation

    return PdfIntegrationOperation


@dataclass(frozen=True)
class SelectedPdfInput:
    product: Any
    parent: Any
    candidates: Any
    sections: tuple[tuple[str, str], ...]
    context: Any


def _read_selected_pdf(prepared, capture, binding, execution_owner, directory, *, sections=(), membership="direct", check_active):
    """Authenticate the exact semantic support before detaching any native body."""
    from dataclasses import replace
    from corpus_structure.ingest.pdf_candidate_source import ReplayCandidatePageSource
    from corpus_structure.ingest.pdf_section_views import published_section_projections
    from corpus_structure.ingest.pdf_streaming import _atomic_bytes
    from pydantic import TypeAdapter
    from .pdf_contracts import PreparedPdfProduct, pdf_context_for_release
    from .pdf_payloads import prepare_payload_family
    from .pdf_publication import PdfExecutionReceipt
    from .pdf_record_reader import PublishedPdfReader, PublishedReadBudget
    from .product_reference import ProductReference
    from .metadata import table

    claim = execution_owner.claim
    if claim is None or binding.subject_context is None:
        raise ValueError("PDF transformation requires an actual native request claim")
    if capture["document"] != binding.subject_context.original_source:
        raise ValueError("selected PDF publication changes the qualified original")
    members = [member for role in binding.roles if role.role == "capture" for member in role.members]
    if len(members) != 1 or members[0].member is not None or len(members[0].support_episodes) != 1:
        raise ValueError("PDF transformation requires one whole exact computational publication")
    check_active()
    with execution_owner.engine.connect() as connection:
        receipt = TypeAdapter(PdfExecutionReceipt).validate_json(canonical_bytes(connection.scalar(select(func.ops.ddo_pdf_capture_source(claim.request_id, binding.subject_context.project_id, members[0].product, members[0].support_episodes[0])))), strict=True)
        publication = receipt.publication
        if any(getattr(publication, key) != capture[key] for key in ("source_digest", "logical_digest", "recipe_digest", "schema_digest", "kind")):
            raise ValueError("selected PDF value differs from its authentic publication")
        parent = ProductReference(publication.task_id, publication.product_key, publication.logical_digest)
        reader = PublishedPdfReader(connection, parent, projection_context=prepared, read_budget=PublishedReadBudget(100_000, execution_owner.invocation.executor.policy.max_packet_bytes))
        context = pdf_context_for_release(connection, prepared)
        artifacts = table("kb.source_artifact")
        digests = (publication.source_digest, publication.schema_digest, publication.recipe_digest)
        size = connection.scalar(select(func.sum(func.octet_length(artifacts.c.content))).where(artifacts.c.artifact_digest.in_(digests)))
        if size is None or size > execution_owner.invocation.executor.policy.max_packet_bytes:
            raise ValueError("selected PDF custody exceeds reserved input capacity")
        bodies = {digest: bytes(content) for digest, content in connection.execute(select(artifacts.c.artifact_digest, artifacts.c.content).where(artifacts.c.artifact_digest.in_(digests)))}
        if set(bodies) != set(digests) or any(sha256(bodies[digest]).hexdigest() != digest for digest in digests):
            raise ValueError("selected publication original/schema/recipe custody differs")
        values = reader.native_product_values(include_candidate_pages=False)
        product = PreparedPdfProduct(canonical_bytes(values), bodies[publication.source_digest], bodies[publication.schema_digest], bodies[publication.recipe_digest], context.contract_digest)
        projections = published_section_projections(reader, selections=tuple(sections), membership=membership, scope=None, check_active=check_active)
        specs = tuple((row.section_pointer, row.membership) for row in projections)
        directory.mkdir(parents=True, exist_ok=False)
        replays = {}
        for payload in reader.iter_candidate_payloads(context=context):
            check_active()
            if payload.page_no in replays:
                raise ValueError("duplicate selected PDF candidate page")
            replay = _atomic_bytes(directory / f"candidate-{payload.page_no:06}.arrow", payload.content, "candidate_payload")
            replays[payload.page_no] = replace(replay, rows=1, page_no=payload.page_no, schema_digest=payload.schema_digest, logical_digest=payload.logical_digest)
        candidates = ReplayCandidatePageSource(replays, prepare_payload_family(context))
    check_active()
    return SelectedPdfInput(product, parent, candidates, specs, context)


@dataclass(frozen=True)
class PreparedPdfTransform:
    prepared: Any
    model: Any
    record: dict[str, Any]

    @property
    def mode(self):
        return self.record["mode"]

    def recipe_bytes(self, pages=()):
        record = self.record
        if self.mode == "enriched":
            return canonical_bytes(dict(recipe_id="native-scoped-math-v2", inline_alignment_policy="native-prose-context-order-v1", native_recipe=json.loads(bytes.fromhex(record["native"]["recipe"])), candidate_policy="native-font-token-vector-ocr-word-v3", cells_policy="all-nonempty-selected-cells-v1", **record["options"], crop_scale=2.0))
        return canonical_bytes(dict(recipe_id="pdf-integrated-source-v1", recognition=sha256(bytes.fromhex(record["recognition_bytes"])).hexdigest(), recognition_pages=pages, **record["options"]))

    def transform(self, capture, *, binding, execution_owner, check_active, sections=(), membership="direct", pages=()):
        import shutil
        from .pdf_capture import PdfCaptureProduct, pdf_publication_value
        from .pdf_contracts import store_pdf_original
        from .pdf_publication import inspect_pdf_execution_receipt
        from .pdf_record_reader import PublishedPdfReader, PublishedReadBudget
        from .product_reference import ProductReference
        from corpus_structure.orchestrate.pdf_streaming import publish_pdf_record_draft

        claim = execution_owner.claim
        if claim is None:
            raise ValueError("PDF transformation requires an actual request claim")
        owner = Path(self.record["directory"]) / sha256(claim.request_id.encode()).hexdigest() / str(claim.generation)
        owner.mkdir(parents=True, exist_ok=True)
        # Each attempt has its own detached files. Immutable page receipts have a separate captured owner.
        from tempfile import mkdtemp
        directory = Path(mkdtemp(prefix="selected-", dir=owner))
        try:
            selected = _read_selected_pdf(self.prepared, capture, binding, execution_owner, directory / "candidates", sections=sections, membership=membership, check_active=check_active)
            recipe_bytes = self.recipe_bytes(pages)
            with execution_owner.engine.begin() as connection:
                store_pdf_original(connection, task_id=claim.task_id, attempt=claim.attempt, holder=claim.holder, original=selected.product.original, recipe_bytes=recipe_bytes)
            if self.mode == "enriched":
                publication_scope = nullcontext(self._enrich(selected, recipe_bytes, check_active))
            else:
                publication_scope = contextmanager(self._integrate)(selected, recipe_bytes, pages, execution_owner, directory, check_active)
            with publication_scope as draft:
                publication = publish_pdf_record_draft(execution_owner.engine, claim, claim.holder, draft, directory=owner, check_active=check_active)
            with execution_owner.engine.connect() as connection:
                receipt = inspect_pdf_execution_receipt(connection, publication, attempt=claim.attempt, holder=claim.holder)
                reader = PublishedPdfReader(connection, ProductReference(publication.task_id, publication.product_key, publication.logical_digest), projection_context=self.prepared, read_budget=PublishedReadBudget(100, execution_owner.invocation.executor.policy.max_reply_bytes))
                health = [row for row in reader.iter_companions("health") if "conversion" in row]
                if len(health) != 1:
                    raise ValueError("transformed publication requires one exact whole-document health projection")
                value = pdf_publication_value(capture["document"], publication, health[0])
            schema = "DdoPdfEnrichedPublication" if self.mode == "enriched" else "DdoPdfIntegratedPublication"
            checked = self.prepared.validate_python(schema, value)
            return PdfCaptureProduct(canonical_bytes(checked.model_dump(mode="json", exclude_unset=True)), canonical_bytes(asdict(receipt)))
        finally:
            shutil.rmtree(directory)

    def _enrich(self, selected, recipe_bytes, check_active):
        from contextlib import nullcontext
        from corpus_structure.ingest.pdf import PdfRecipe
        from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
        from corpus_structure.ingest.pdf_capacity import native_before_nemotron
        from corpus_structure.ingest.pdf_selected_enrichment import enrich_selected_pdf
        from corpus_structure.ingest.pdf_worker import PdfWorker

        native = self.record["native"]
        recipe = PdfRecipe.from_bytes(bytes.fromhex(native["recipe"]))
        actual = native["assets"]
        assets = PreparedPdfAssets(Path(actual["root"]), bytes.fromhex(actual["manifest"]), tuple(tuple(item) for item in actual["files"]), tuple(tuple(item) for item in actual["repositories"]))
        assets.verify()
        endpoint = native["nemotron_endpoint"]
        handoff = native_before_nemotron(endpoint, check_active=check_active) if endpoint is not None else nullcontext()
        with handoff:
            worker = PdfWorker(recipe, assets=assets)
            try:
                return enrich_selected_pdf(selected.product, selected.parent, selected.sections, PdfEnrichmentOptions.model_validate(self.record["options"]), recipe_bytes, selected.candidates, worker, check_active=check_active)
            finally:
                worker.close()

    def _integrate(self, selected, recipe_bytes, pages, execution_owner, directory, check_active):
        from corpus_structure.core.method import PdfRecordPublicationDraft
        from corpus_structure.ingest.pdf import native_conversion_health
        from corpus_structure.ingest.pdf_hierarchy import load_snapshot, native_nodes
        from corpus_structure.ingest.pdf_methods import _snapshot_from_values
        from corpus_structure.ingest.pdf_recognition import NemotronRecipe, PreparedRecognitionSource, RecognitionWorker, recognition_observation_values, repetition_recovery_recipe, repetitive_capped_page
        from corpus_structure.ingest.pdf_stream_reconciliation import reconcile_pdf_stream
        from .pdf_integrated import PreparedPdfOriginal, prepare_integrated_pdf_product, store_pdf_observation
        from .product_reference import ProductReference

        options = PdfIntegrationOptions.model_validate(self.record["options"])
        values = selected.product.values()
        if values["source_scope"] != "whole_document" or values["health"]["conversion"] != "success":
            raise ValueError("integration requires a complete successful retained Standard source")
        available = tuple(sorted(int(page) for page in values["document"]["pages"]))
        requested = tuple(pages) or available
        if len(set(requested)) != len(requested) or not set(requested) <= set(available):
            raise ValueError("recognition pages differ from exact physical page inventory")
        if options.source_recovery is not None and pages:
            raise ValueError("witnessed source recovery requires the whole original")
        source_witness = None
        if options.source_recovery is not None:
            from corpus_structure.ingest.pdf_incumbent_recovery import read_source_witness
            source_witness = read_source_witness(selected.product.original)
        recipe = NemotronRecipe(**self.record["recognition_recipe"])
        original = PreparedPdfOriginal(selected.product.original)
        source = PreparedRecognitionSource(original.content, original.digest)
        resources = PdfRecognitionResources.model_validate(self.record["resources"])
        worker = RecognitionWorker(python=Path(resources.python), script=Path(resources.script), endpoint=resources.endpoint, receipts=Path(resources.receipts), timeout_seconds=resources.timeout_seconds)
        selected.context.require_operation("recognize_pdf_observation")
        claim = execution_owner.claim
        assert claim is not None

        def retain(page, actual_recipe, *, verify_retained=False):
            for row, raw, artifacts in page.requests(verify_retained=verify_retained):
                check_active()
                observation = recognition_observation_values(page, row, raw, source=source, recipe=actual_recipe)
                product = prepare_integrated_pdf_product(observation, original, actual_recipe.to_bytes(), artifacts=artifacts, context=selected.context)
                with execution_owner.engine.begin() as connection:
                    digest = store_pdf_observation(connection, task_id=claim.task_id, attempt=claim.attempt, holder=claim.holder, product=product, context=selected.context)
                pin = ProductReference(claim.task_id, product.values()["product_key"], digest)
                yield pin.values(), product.values(), raw

        def observations():
            failures = []
            stream = worker.replay_completed_pages(source, recipe, requested, check_active=check_active) if source_witness is not None else worker.recognize_pages(source, recipe, requested, check_active=check_active, concurrency=4, reuse_failures=True)
            for page in stream:
                yield from retain(page, recipe, verify_retained=source_witness is not None)
                recovery = options.recovery_policy
                if not page.succeeded and recovery is not None and repetitive_capped_page(page, minimum_run=recovery["min_identical_character_run"]):
                    alternate = repetition_recovery_recipe(recipe)
                    if alternate.recipe_id != recovery["permitted_recipe_id"]:
                        raise ValueError("recovery recipe differs from admitted policy")
                    page = next(worker.recognize_pages(source, alternate, [page.page_no], check_active=check_active, reuse_failures=True))
                    yield from retain(page, alternate)
                if not page.succeeded:
                    failures.append(page.page_no)
            if failures:
                raise RuntimeError(f"unresolved triple-pass physical pages: {failures}")

        document = load_snapshot(_snapshot_from_values(values))
        with reconcile_pdf_stream(document, selected.parent.values(), observations(), source.digest, directory=directory, policy=options.integration_policy, context=selected.context, source_witness=source_witness) as reconciled:
            health = native_conversion_health(native_nodes(reconciled.document), "success", ())
            # Publication consumes owned Arrow companions before reconciliation closes.
            yield PdfRecordPublicationDraft(document=reconciled.document, product_key="integrated", kind="integrated", original=original.content, schema_bytes=selected.product.schema_bytes, recipe_bytes=recipe_bytes, health=health, companions={**{family: reconciled.journal.collection(family) for family in ("input", "occurrence", "relation", "mapping_report", "coverage")}, "health": ({"health": health, "source_scope": "whole_document"}, reconciled.health)}, metadata={"inline_candidate_pages": (selected.candidates.encoded(number) for number in selected.candidates.page_nos)})


def execute_pdf_enrichment(receiver, capture, sections, membership):
    return receiver.profile.transform(capture, sections=sections, membership=membership, binding=receiver.binding, execution_owner=receiver.execution_owner, check_active=receiver.check_active)


def execute_pdf_integration(receiver, capture, pages):
    return receiver.profile.transform(capture, pages=pages, binding=receiver.binding, execution_owner=receiver.execution_owner, check_active=receiver.check_active)


@dataclass(frozen=True)
class PreparedPdfTransformPort:
    identity: Any
    operation: Any
    profile: PreparedPdfTransform
    authorize: Any
    custody: tuple
    sources: Any
    native_selections = ()

    @property
    def logical_signature(self):
        signature = inspect.signature(_endpoint(self.profile.mode).run, eval_str=True)
        return signature.replace(parameters=tuple(signature.parameters.values())[1:])

    def _verify(self):
        from .data_operation_prepared_products import verify_prepared_product

        record = self.profile.record
        if any((_root() / name).read_bytes() != bytes.fromhex(content) for name, content in record["files"]):
            raise ValueError("PDF transformation implementation changed after acquisition")
        if self.profile.mode == "integrated" and (_file_hash(record["resources"]["script"]) != record["worker_digest"] or _file_hash(record["resources"]["python"]) != record["interpreter_digest"]):
            raise ValueError("recognition worker/interpreter changed after acquisition")
        endpoint = _endpoint(self.profile.mode)
        implementation = execute_pdf_enrichment if self.profile.mode == "enriched" else execute_pdf_integration
        asset = next(item for item in self.custody if item.name == "pdf-" + self.profile.mode + "/execution-custody")
        if canonical_bytes(record) != asset.content:
            raise ValueError("PDF transformation resource profile differs from immutable acquired custody")
        verify_prepared_product(self.identity, self.profile.model, self.operation, self.sources, self.custody, assets=(asset,), functions=((self.operation.callable_surfaces[0].declaration, endpoint.run), ("corpus_structure.semantic.pdf_transforms." + implementation.__name__, implementation), *( ("corpus_structure.semantic.pdf_transforms.PreparedPdfTransform." + name, getattr(PreparedPdfTransform, name)) for name in ("transform", "_enrich", "_integrate", "recipe_bytes")), ("corpus_structure.semantic.pdf_transforms._read_selected_pdf", _read_selected_pdf)), authorize=self.authorize, required_sources=self.sources)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from corpus_structure.core.work import PreparedWork
        from .data_operation_identity import semantic_value
        from .data_operation_outcomes import successful_return_outcome
        from .data_operation_ports import PortCompletion, PortRefusal, RoleValue, _untrusted_value

        self._verify()
        if binding is None or not binding.sufficient or binding.subject_context is None:
            raise PortRefusal("PDF transformation requires an authenticated sufficient subject context")
        inputs = [role for role in self.operation.roles if role.direction == "input"]
        ids = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        if len(values) != 1 or values[0].role != "capture" or values[0].kind_contract != ids[inputs[0].kind, "kind"]:
            raise PortRefusal("PDF transformation requires one exact nominal Standard publication")
        capture = self.profile.prepared.validate_python("DdoPdfCapture", _untrusted_value(values[0].value)).model_dump(mode="json")
        from .data_operation_identity import decode_semantic_value

        parameters = decode_semantic_value(json.loads(binding.parameters))

        def compute():
            self._verify()
            receiver = _endpoint(self.profile.mode)(self.profile, binding=binding, execution_owner=execution_owner, check_active=check_active)
            result = receiver.run(capture, **parameters)
            self._verify()
            output = next(role for role in self.operation.roles if role.direction == "output")
            schema = "DdoPdfEnrichedPublication" if self.profile.mode == "enriched" else "DdoPdfIntegratedPublication"
            body = self.profile.prepared.validate_json(schema, result.content).model_dump(mode="python", exclude_unset=True)
            return PortCompletion(self.operation.semantic_id, (RoleValue(output.name, ids[output.kind, "kind"], result.content, canonical_bytes(semantic_value(body))),), outcome=successful_return_outcome(self.operation), pdf_execution_evidence=result.receipt)
        (result,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        check_active()
        return result


def resolve_pdf_transform_port(prepared, model, operation, *, identity, authorize, custody, sources, mode):
    records = [item for item in custody if item.name == "pdf-" + mode + "/execution-custody"]
    if len(records) != 1:
        raise ValueError("PDF transformation lacks its exact captured resource profile")
    profile = PreparedPdfTransform(prepared, model, json.loads(records[0].content))
    if profile.mode != mode:
        raise ValueError("PDF transformation profile changes its acquired capability")
    port = PreparedPdfTransformPort(identity, model.operation(operation), profile, authorize, custody, sources)
    port._verify()
    return port
