"""Declared rendering over actual demand-selected PDF and original-byte custody."""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml
from pydantic import TypeAdapter
from sqlalchemy import func, select

from corpus_structure.semantic.input_values import _untrusted_value

from .data_operation_ports import PortCompletion, PortRefusal, RoleValue
from .data_operation_values import decode_semantic_value, semantic_value
from .identity import canonical_bytes
from .runtime_slice import AuthenticatedSlice
from .types import SourceArtifact, SourceBundle

TARGET = "source.pdf_region/render"
VISUAL_INPUT_TARGET = "source.visual_input/render"
_MODEL = Path(__file__).parents[1] / "model/semantic/data-operation-pdf-region.yaml"


def pdf_region_inputs(bundle):
    name, root = "data_operation_pdf_region", "data_operation_pdf_region_root"
    if {name, root} & {item.name for item in bundle.sources}:
        raise ValueError("PDF region uses reserved schema names")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, _MODEL.read_bytes()),
            SourceArtifact(
                "data_operation_visual", _MODEL.with_name("data-operation-visual.yaml").read_bytes()
            ),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:pdf-region-root",
                        "name": root,
                        "imports": [bundle.root, name, "data_operation_visual"],
                    }
                ).encode(),
            ),
        ),
    )


def pdf_region_profile():
    from importlib.metadata import version

    root = Path(__file__).parents[1]
    return SourceArtifact(
        "pdf-region/profile",
        canonical_bytes(
            {
                "version": "selected-original-pdf-region-v1",
                "files": [
                    (name, (root / name).read_bytes().hex())
                    for name in (
                        "serve/native_regions.py",
                        "semantic/pdf_record_reader.py",
                        "model/semantic/data-operation-pdf-region.yaml",
                        "semantic/pdf_visual_mapping.py",
                        "model/semantic/data-operation-visual.yaml",
                    )
                ],
                "libraries": {name: version(name) for name in ("pypdfium2", "Pillow")},
            }
        ),
    )


def pdf_region_operation_sources(capture_sources):
    from .primary_operations import combine_primary_sources
    from .python_operation_sources import PythonSource, PythonSourceCollection

    if capture_sources is None:
        raise ValueError("PDF rendering requires its actual capture operation dependency")
    root = Path(__file__).parents[1]
    own = PythonSourceCollection(
        tuple(
            PythonSource(module, path.read_bytes(), str(path))
            for module, path in (
                (
                    "corpus_structure.semantic.input_values",
                    Path(__file__).with_name("input_values.py"),
                ),
                (
                    "corpus_structure.ingest.pdf_region_operation",
                    root / "ingest/pdf_region_operation.py",
                ),
                ("corpus_structure.semantic.native_requests", Path(__file__)),
                (
                    "corpus_structure.ingest.pdf_visual_input_operation",
                    root / "ingest/pdf_visual_input_operation.py",
                ),
            )
        ),
        boundary_contracts=(pdf_region_profile(),),
    )
    return combine_primary_sources(capture_sources, own)


def execute_pdf_region(receiver, capture, pointer, region_index, scale):
    return receiver.port.render(
        capture,
        pointer,
        region_index,
        scale,
        binding=receiver.binding,
        execution_owner=receiver.execution_owner,
        check_active=receiver.check_active,
    )


def execute_pdf_visual_input(receiver, capture, selection):
    selected = receiver.port.prepared.validate_python("DdoVisualSelection", selection).model_dump(
        mode="python", exclude_unset=True
    )
    result = receiver.port.render(
        capture,
        selected.get("pointer"),
        selected.get("region_index"),
        "2",
        binding=receiver.binding,
        execution_owner=receiver.execution_owner,
        check_active=receiver.check_active,
        page_no=selected["page_no"],
        rotation=selected.get("rotation", 0),
    )
    result["selection"] = selected
    return result


@dataclass(frozen=True)
class PreparedPdfRegionPort:
    identity: Any
    model: Any
    operation: Any
    prepared: Any
    authorize: Any
    custody: tuple
    sources: Any
    _verification: AuthenticatedSlice = field(init=False, compare=False, repr=False)
    logical_signature: inspect.Signature = field(init=False, compare=False, repr=False)
    native_selections = ()

    @property
    def implementation(self):
        from corpus_structure.ingest.pdf_region_operation import PdfRegionOperation
        from corpus_structure.ingest.pdf_visual_input_operation import PdfVisualInputOperation

        return (
            PdfRegionOperation if self.operation.semantic_id == TARGET else PdfVisualInputOperation
        )

    def __post_init__(self):
        from .data_operation_prepared_products import (
            authenticated_prepared_product,
            verify_prepared_product,
        )
        from .file_custody import verified_file

        if (
            self.operation.semantic_id not in {TARGET, VISUAL_INPUT_TARGET}
            or self.operation.effects
        ):
            raise PortRefusal("renderer requires its exact declared pure computation")
        bridge_name, bridge = (
            ("execute_pdf_region", execute_pdf_region)
            if self.operation.semantic_id == TARGET
            else ("execute_pdf_visual_input", execute_pdf_visual_input)
        )
        functions = (
            (self.operation.callable_surfaces[0].declaration, self.implementation.run),
            ("corpus_structure.semantic.native_requests." + bridge_name, bridge),
            ("corpus_structure.semantic.native_requests.PreparedPdfRegionPort.render", self.render),
        )
        asset = pdf_region_profile()
        verify_prepared_product(
            self.identity,
            self.model,
            self.operation,
            self.sources,
            self.custody,
            assets=(asset,),
            functions=functions,
            authorize=self.authorize,
            required_sources=self.sources,
        )
        verification = authenticated_prepared_product(
            self.sources, functions, required_sources=self.sources
        )
        root = Path(__file__).parents[1]
        files = tuple(
            verified_file(root / name, sha256(bytes.fromhex(content)).hexdigest())
            for name, content in json.loads(asset.content)["files"]
        )
        verification.files = tuple(
            {file.path: file for file in (*verification.files, *files)}.values()
        )
        object.__setattr__(self, "_verification", verification)
        signature = inspect.signature(self.implementation.run, eval_str=True)
        object.__setattr__(
            self,
            "logical_signature",
            signature.replace(parameters=tuple(signature.parameters.values())[1:]),
        )

    def verify(self):
        self._verification.check()
        self.authorize(self.identity)

    def render(
        self,
        capture,
        pointer,
        region_index,
        scale,
        *,
        binding,
        execution_owner,
        check_active,
        page_no=None,
        rotation=0,
    ):
        from corpus_structure.serve.native_regions import render_pdf_region

        from .metadata import table
        from .original_documents import original_document_subject
        from .pdf_publication import PdfExecutionReceipt
        from .pdf_record_reader import PublishedPdfReader, PublishedReadBudget
        from .product_reference import ProductReference

        claim, context = execution_owner.claim, binding.subject_context
        if (
            claim is None
            or context is None
            or (
                binding.subject != original_document_subject(capture["document"])
                or context.original_source != capture["document"]
            )
        ):
            raise PortRefusal("rendering requires its genuine native claim and original document")
        members = tuple(
            member for role in binding.roles if role.role == "capture" for member in role.members
        )
        if (
            len(members) != 1
            or members[0].member is not None
            or len(members[0].support_episodes) != 1
        ):
            raise PortRefusal("rendering requires one exact whole capture and producing episode")
        selected = members[0]
        check_active()
        with execution_owner.engine.connect() as conn:
            receipt_body = conn.scalar(
                select(
                    func.ops.ddo_pdf_capture_source(
                        claim.request_id,
                        context.project_id,
                        selected.product,
                        selected.support_episodes[0],
                    )
                )
            )
            receipt = TypeAdapter(PdfExecutionReceipt).validate_json(
                canonical_bytes(receipt_body), strict=True
            )
            publication = receipt.publication
            if any(
                getattr(publication, name) != capture[name]
                for name in (
                    "source_digest",
                    "logical_digest",
                    "recipe_digest",
                    "schema_digest",
                    "kind",
                )
            ):
                raise PortRefusal("selected PDF differs from its actual native publication receipt")
            reader = PublishedPdfReader(
                conn,
                ProductReference(
                    publication.task_id, publication.product_key, publication.logical_digest
                ),
                projection_context=self.prepared,
                read_budget=PublishedReadBudget(
                    100_000, execution_owner.invocation.executor.policy.max_reply_bytes
                ),
            )
            region = reader.region(pointer, region_index) if pointer else None
            if page_no is None and region is None:
                raise PortRefusal("region rendering requires its exact native occurrence")
            if page_no is not None and region is not None and region["page_no"] != page_no:
                raise PortRefusal("visual crop belongs to another physical page")
            documents, artifacts = table("kb.document"), table("kb.source_artifact")
            query = (
                select(artifacts.c.content)
                .join_from(
                    documents, artifacts, artifacts.c.artifact_digest == documents.c.content_hash
                )
                .where(
                    documents.c.project_id == context.project_id,
                    documents.c.key == capture["document"],
                    documents.c.content_hash == publication.source_digest,
                    documents.c.mime == "application/pdf",
                )
            )
            size = conn.scalar(select(func.octet_length(query.scalar_subquery())))
            if size is None or size > execution_owner.invocation.executor.policy.max_packet_bytes:
                raise PortRefusal(
                    "actual original PDF is absent or exceeds admitted input capacity"
                )
            original = bytes(conn.scalar(query))
            if sha256(original).hexdigest() != publication.source_digest:
                raise PortRefusal("retained original bytes differ from the exact publication")
        # No connection remains borrowed during rasterization.
        check_active()
        extra = {}
        if page_no is None:
            assert region is not None
            content = render_pdf_region(original, region, scale=float(scale))
        else:
            from io import BytesIO

            from PIL import Image

            from .pdf_visual_mapping import render_visual_input

            content, transform = render_visual_input(original, page_no, region, rotation)
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
            extra = dict(
                page_no=page_no,
                rotation=rotation,
                width=width,
                height=height,
                transform_json=json.dumps(transform, separators=(",", ":"), allow_nan=False),
            )
        check_active()
        if page_no is None:
            extra.update(pointer=pointer, region_index=region_index)
        return dict(
            document=capture["document"],
            source_digest=publication.source_digest,
            logical_digest=publication.logical_digest,
            scale=scale,
            encoding="png",
            content_digest=sha256(content).hexdigest(),
            content_hex=content.hex(),
            **extra,
        )

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from corpus_structure.core.method import PreparedWork

        if (
            binding is None
            or not binding.sufficient
            or binding.operation != self.operation.semantic_id
        ):
            raise PortRefusal("renderer requires its admitted sufficient binding")
        ids = {(item.owner, item.domain): item.key for item in self.model.identities}
        incoming = next(role for role in self.operation.roles if role.direction == "input")
        if (
            len(values) != 1
            or values[0].role != "capture"
            or values[0].kind_contract != ids[incoming.kind, "kind"]
        ):
            raise PortRefusal("renderer requires its exact nominal capture input")
        capture = self.prepared.validate_json(
            "DdoPdfPublication", canonical_bytes(_untrusted_value(values[0].value))
        ).model_dump(mode="json")
        parameters = decode_semantic_value(json.loads(binding.parameters))
        expected = (
            {"pointer", "region_index", "scale"}
            if self.operation.semantic_id == TARGET
            else {"selection"}
        )
        if set(parameters) != expected:
            raise PortRefusal("renderer requires its frozen native region selection")

        def compute():
            self.verify()
            body = self.implementation(
                self, binding=binding, execution_owner=execution_owner, check_active=check_active
            ).run(capture, **parameters)
            body = self.prepared.validate_python(
                "DdoPdfRegion" if self.operation.semantic_id == TARGET else "DdoVisualInput", body
            ).model_dump(mode="python", exclude_unset=True)
            output = next(role for role in self.operation.roles if role.direction == "output")
            completion = PortCompletion(
                self.operation.semantic_id,
                (
                    RoleValue(
                        output.name,
                        ids[output.kind, "kind"],
                        canonical_bytes(body),
                        canonical_bytes(semantic_value(body)),
                    ),
                ),
                outcome="success",
            )

            self.verify()
            return completion

        (completion,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        check_active()
        return completion


def request_source_view(engine, *, request, source_root, policy=None, admission_engine=None):
    """Create and execute one explicit rendering demand; return authentic native receipts."""
    from .data_operation_service import (
        NativeDemandRequest,
        create_native_demand,
        execute_data_demand,
    )

    if not isinstance(request, NativeDemandRequest) or request.targets != (TARGET,):
        raise ValueError("rendering requires an explicit NativeDemandRequest for " + TARGET)
    with engine.begin() as conn:
        demand = create_native_demand(conn, request)
    return execute_data_demand(
        engine,
        demand["demand_id"],
        source_root=source_root,
        policy=policy,
        project_id=request.project_id,
        admission_engine=admission_engine,
    )
