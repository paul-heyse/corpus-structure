"""PDF family adapter using existing private-build, receipt and publication owners."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import func, select

from .data_operation_outcomes import successful_return_outcome
from .identity import canonical_bytes
from .source_products import source_product_inputs
from .types import SourceArtifact, SourceBundle

_MODEL = Path(__file__).parents[1] / "model/semantic/data-operation-pdf-capture.yaml"


def pdf_capture_inputs(bundle):
    bundle = source_product_inputs(bundle)
    name, root = "data_operation_pdf_capture", "data_operation_pdf_capture_root"
    if {name, root} & {item.name for item in bundle.sources}:
        raise ValueError("PDF capture uses reserved schema names")
    return SourceBundle(root, (
        *bundle.sources, SourceArtifact(name, _MODEL.read_bytes()),
        SourceArtifact(root, yaml.safe_dump({"id": "urn:corpus:pdf-capture-root", "name": root, "imports": [bundle.root, name]}).encode()),
    ))


def pdf_capture_assets(recipe):
    from corpus_structure.ingest.pdf import pdf_package_versions

    return SourceArtifact("pdf-capture/profile-assets", canonical_bytes({
        "version": "native-pdf-capture-v1", "recipe": recipe.to_bytes().hex(),
        "libraries": pdf_package_versions(), "model": _MODEL.read_bytes().hex(),
    }))


def pdf_capture_custody(recipe, assets, *, directory, nemotron_endpoint=None, require_nemotron_handoff=False):
    if tuple(recipe.model_artifacts) != tuple(assets.files) or tuple(recipe.model_revisions) != tuple(assets.repositories):
        raise ValueError("PDF capture recipe does not retain its actual prepared assets")
    root = Path(__file__).parents[1]
    files = ("semantic/pdf_capture.py", "orchestrate/pdf_streaming.py", "ingest/pdf_worker.py", "ingest/pdf_assets.py", "ingest/pdf.py")
    return SourceArtifact("pdf-capture/execution-custody", canonical_bytes({
        "version": "native-pdf-capture-custody-v1", "recipe": recipe.to_bytes().hex(),
        "assets": {"root": str(assets.root.resolve()), "manifest": assets.manifest.hex(), "files": assets.files, "repositories": assets.repositories},
        "directory": str(Path(directory).resolve()), "nemotron_endpoint": nemotron_endpoint,
        "require_nemotron_handoff": require_nemotron_handoff,
        "files": [(name, (root / name).read_bytes().hex()) for name in files],
    }))


def pdf_capture_operation_sources(recipe, assets, *, directory, nemotron_endpoint=None, require_nemotron_handoff=False):
    from .python_operation_sources import PythonSource, PythonSourceCollection

    if recipe.recipe_id != "docling-standard-pdf-stream-v1":
        raise ValueError("declared PDF capture requires the admitted owned stream recipe")
    path = Path(__file__).parents[1] / "ingest/pdf_capture.py"
    return PythonSourceCollection((PythonSource("corpus_structure.semantic.pdf_capture", Path(__file__).read_bytes(), str(Path(__file__))), PythonSource("corpus_structure.ingest.pdf_capture", path.read_bytes(), str(path)),), boundary_contracts=(
        pdf_capture_assets(recipe), pdf_capture_custody(recipe, assets, directory=directory,
            nemotron_endpoint=nemotron_endpoint, require_nemotron_handoff=require_nemotron_handoff),
    ))


def pdf_publication_value(document, publication, health):
    """The existing native PDF proof independently checks this exact projection."""
    return {"document": document, **{name: getattr(publication, name) for name in (
        "source_digest", "logical_digest", "schema_digest", "recipe_digest", "kind")},
        "health": {name: health[name] for name in ("conversion", "display_coverage", "inline_coverage", "cell_coverage")}}


@dataclass(frozen=True)
class PdfCaptureProduct:
    content: bytes
    receipt: bytes


@dataclass(frozen=True)
class PreparedPdfCapture:
    prepared: Any
    model: Any
    recipe: Any
    assets: Any
    directory: Path
    nemotron_endpoint: str | None
    require_nemotron_handoff: bool

    def capture(self, original, *, subject_context, execution_owner, check_active):
        from corpus_structure.core.method import PdfRecordProducerRequest
        from corpus_structure.orchestrate.pdf_streaming import produce_published_pdf_records
        from .metadata import table
        from .pdf_contracts import pdf_context_for_release, store_pdf_original
        from .pdf_publication import inspect_pdf_execution_receipt
        from .pdf_record_reader import PublishedPdfReader, PublishedReadBudget
        from .product_reference import ProductReference

        claim = execution_owner.claim
        if claim is None:
            raise ValueError("PDF capture requires an actual native producer claim")
        from .original_documents import original_document_subject

        context = subject_context
        if original["document"] != context.original_source or context.subject != original_document_subject(original["document"]):
            raise ValueError("PDF capture original differs from the qualified native request")
        engine = execution_owner.engine
        check_active()
        with engine.begin() as connection:
            documents, artifacts = table("kb.document"), table("kb.source_artifact")
            selected = (select(artifacts.c.content).join_from(documents, artifacts, artifacts.c.artifact_digest == documents.c.content_hash)
                        .where(documents.c.project_id == context.project_id, documents.c.key == original["document"],
                               documents.c.content_hash == original["content_hash"], documents.c.mime == original["mime"]))
            size = connection.scalar(select(func.octet_length(selected.scalar_subquery())))
            if size is None or size > execution_owner.invocation.executor.policy.max_packet_bytes:
                raise ValueError("PDF capture original is absent or exceeds reserved input capacity")
            content = bytes(connection.execute(selected).scalar_one())
            if sha256(content).hexdigest() != original["content_hash"] or not content.startswith(b"%PDF-"):
                raise ValueError("PDF capture original bytes differ from admitted custody")
            pdf = pdf_context_for_release(connection, self.prepared)
            if pdf.domain is None:
                raise ValueError("declared PDF capture requires its archived PDF domain facet")
            schema_bytes = pdf.domain.source("implementation/pdf/docling-validation.schema.json").content
        check_active()
        with engine.begin() as connection:
            store_pdf_original(connection, task_id=claim.task_id, attempt=claim.attempt, holder=claim.holder,
                               original=content, recipe_bytes=self.recipe.to_bytes())
        directory = self.directory / sha256(claim.request_id.encode()).hexdigest() / str(claim.generation)
        directory.mkdir(parents=True, exist_ok=True)
        publication = produce_published_pdf_records(engine, claim, claim.holder,
            PdfRecordProducerRequest(self.recipe, self.assets, content, schema_bytes,
                                     self.nemotron_endpoint, self.require_nemotron_handoff),
            directory=directory, check_active=check_active)
        check_active()
        with engine.begin() as connection:
            receipt = inspect_pdf_execution_receipt(connection, publication, attempt=claim.attempt, holder=claim.holder)
            reader = PublishedPdfReader(connection,
                ProductReference(publication.task_id, publication.product_key, publication.logical_digest),
                projection_context=self.prepared,
                read_budget=PublishedReadBudget(100, execution_owner.invocation.executor.policy.max_reply_bytes))
            health = [row for row in reader.iter_companions("health") if "conversion" in row]
            if len(health) != 1:
                raise ValueError("PDF capture lacks one authenticated whole-document health projection")
            value = pdf_publication_value(original["document"], publication, health[0])
        checked = self.prepared.validate_json("DdoPdfCapture", canonical_bytes(value))
        return PdfCaptureProduct(canonical_bytes(checked.model_dump(mode="json", exclude_unset=True)), canonical_bytes(asdict(receipt)))


def execute_pdf_capture(receiver, original):
    # Direct callers must use the acquired effect port, which supplies native custody.
    return receiver.profile.capture(original, subject_context=receiver.subject_context, execution_owner=receiver.execution_owner, check_active=receiver.check_active)


@dataclass(frozen=True)
class PreparedPdfCapturePort:
    identity: Any
    operation: Any
    profile: PreparedPdfCapture
    authorize: Any
    custody: tuple
    sources: Any
    native_selections = ()

    def _verify(self):
        from corpus_structure.ingest.pdf_capture import PdfCaptureOperation
        from .data_operation_prepared_products import verify_prepared_product

        contracts = {artifact.name: artifact for artifact in self.custody}
        acquired = contracts.get("pdf-capture/execution-custody")
        if acquired is None:
            raise ValueError("PDF capture has no exact acquired runtime custody")
        record = json.loads(acquired.content)
        root = Path(__file__).parents[1]
        if any((root / name).read_bytes() != bytes.fromhex(content) for name, content in record["files"]):
            raise ValueError("PDF capture implementation changed after acquisition")
        verify_prepared_product(self.identity, self.profile.model, self.operation, self.sources, self.custody,
            assets=(pdf_capture_assets(self.profile.recipe), acquired),
            functions=((self.operation.callable_surfaces[0].declaration, PdfCaptureOperation.run),
                       ("corpus_structure.semantic.pdf_capture.execute_pdf_capture", execute_pdf_capture),
                       ("corpus_structure.semantic.pdf_capture.PreparedPdfCapture.capture", PreparedPdfCapture.capture),
                       ("corpus_structure.semantic.pdf_capture.pdf_publication_value", pdf_publication_value)),
            authorize=self.authorize, required_sources=self.sources)

    @property
    def logical_signature(self):
        import inspect
        from corpus_structure.ingest.pdf_capture import PdfCaptureOperation
        signature = inspect.signature(PdfCaptureOperation.run, eval_str=True)
        return signature.replace(parameters=tuple(signature.parameters.values())[1:])

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from corpus_structure.core.work import PreparedWork
        from .data_operation_identity import semantic_value
        from .data_operation_ports import PortCompletion, PortRefusal, RoleValue, _untrusted_value

        self._verify()
        if binding is None or not binding.sufficient or binding.subject_context is None:
            raise PortRefusal("PDF capture requires its authenticated complete subject context")
        inputs = [role for role in self.operation.roles if role.direction == "input"]
        ids = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        if len(values) != 1 or values[0].role != "original" or values[0].kind_contract != ids[inputs[0].kind, "kind"]:
            raise PortRefusal("PDF capture requires one nominal original-document role")
        original = _untrusted_value(values[0].value)
        original = self.profile.prepared.validate_python("DdoOriginalDocument", original).model_dump(mode="json")
        if original["mime"] != "application/pdf":
            raise PortRefusal("native PDF capture cannot reinterpret another MIME type")

        def compute():
            self._verify()
            from corpus_structure.ingest.pdf_capture import PdfCaptureOperation
            result = PdfCaptureOperation(self.profile, execution_owner=execution_owner,
                subject_context=binding.subject_context, check_active=check_active).run(original)
            self._verify()
            output = next(role for role in self.operation.roles if role.direction == "output")
            body = self.profile.prepared.validate_json("DdoPdfCapture", result.content).model_dump(mode="python", exclude_unset=True)
            return PortCompletion(self.operation.semantic_id,
                (RoleValue(output.name, ids[output.kind, "kind"], result.content, canonical_bytes(semantic_value(body))),),
                outcome=successful_return_outcome(self.operation), pdf_execution_evidence=result.receipt)

        (result,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        check_active()
        return result


def resolve_pdf_capture_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets

    captured = [artifact for artifact in custody if artifact.name == "pdf-capture/execution-custody"]
    if len(captured) != 1:
        raise ValueError("PDF capture requires one frozen acquisition context")
    record = json.loads(captured[0].content)
    recipe = PdfRecipe.from_bytes(bytes.fromhex(record["recipe"]))
    actual = record["assets"]
    assets = PreparedPdfAssets(Path(actual["root"]), bytes.fromhex(actual["manifest"]),
        tuple(tuple(item) for item in actual["files"]), tuple(tuple(item) for item in actual["repositories"]))
    profile = PreparedPdfCapture(prepared, model, recipe, assets, Path(record["directory"]),
                                 record["nemotron_endpoint"], record["require_nemotron_handoff"])
    port = PreparedPdfCapturePort(identity, model.operation(operation), profile, authorize, custody, sources)
    port._verify()
    return port
