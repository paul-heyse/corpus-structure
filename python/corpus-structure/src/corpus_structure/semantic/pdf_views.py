"""Pinned sealed-publication reads share the existing native section projector."""

import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import func, select

from .data_operation_identity import decode_semantic_value, semantic_value
from .data_operation_outcomes import successful_return_outcome
from .identity import canonical_bytes
from .source_discovery import PreparedSourceDiscovery
from .source_products import FrozenNativeSource
from .types import SourceArtifact


def pdf_views_assets():
    root = Path(__file__).parents[1]
    files = (
        "ingest/pdf_section_views.py",
        "ingest/pdf_hierarchy.py",
        "semantic/source_products.py",
        "semantic/characterization_manifests.py",
    )
    return SourceArtifact(
        "pdf-views/profile-assets",
        canonical_bytes(
            {
                "version": "published-source-views-v1",
                "files": [(name, (root / name).read_bytes().hex()) for name in files],
            }
        ),
    )


def pdf_views_custody():
    root = Path(__file__).parents[1]
    files = (
        "semantic/pdf_views.py",
        "semantic/pdf_record_reader.py",
        "semantic/pdf_domain.py",
        "semantic/source_discovery.py",
    )
    return SourceArtifact(
        "pdf-views/execution-custody",
        canonical_bytes({"files": [(name, (root / name).read_bytes().hex()) for name in files]}),
    )


def pdf_views_operation_sources(capture_sources=None):
    from .primary_operations import combine_primary_sources
    from .python_operation_sources import PythonSource, PythonSourceCollection

    root = Path(__file__).parents[1]
    own = PythonSourceCollection(
        tuple(
            PythonSource(module, path.read_bytes(), str(path))
            for module, path in (
                ("corpus_structure.ingest.pdf_views", root / "ingest/pdf_views.py"),
                ("corpus_structure.semantic.pdf_views", Path(__file__)),
            )
        ),
        boundary_contracts=(pdf_views_assets(), pdf_views_custody()),
    )
    if capture_sources is None:
        raise ValueError(
            "PDF source-view discovery requires its actual captured capture dependency"
        )
    return combine_primary_sources(capture_sources, own)


@dataclass(frozen=True)
class PreparedPdfViews:
    prepared: Any
    model: Any

    def project(self, capture, sections, membership, *, binding, execution_owner, check_active):
        from corpus_structure.ingest.pdf_section_views import published_section_projections

        from .original_documents import original_document_subject
        from .pdf_publication import PdfExecutionReceipt
        from .pdf_record_reader import PublishedPdfReader, PublishedReadBudget
        from .product_reference import ProductReference

        if membership not in {"direct", "descendants"}:
            raise ValueError("source discovery requires an admitted section membership")
        claim = execution_owner.claim
        if claim is None or binding.subject_context is None:
            raise ValueError(
                "PDF source discovery requires actual request and source context custody"
            )
        if (
            binding.subject != original_document_subject(capture["document"])
            or binding.subject_context.original_source != capture["document"]
        ):
            raise ValueError("PDF source discovery changes its exact original document")
        members = tuple(
            member for role in binding.roles if role.role == "capture" for member in role.members
        )
        if (
            len(members) != 1
            or members[0].member is not None
            or len(members[0].support_episodes) != 1
        ):
            raise ValueError("PDF views require one whole capture with exact computational support")
        selected = members[0]
        check_active()
        with execution_owner.engine.connect() as connection:
            receipt_body = connection.scalar(
                select(
                    func.ops.ddo_pdf_capture_source(
                        claim.request_id,
                        binding.subject_context.project_id,
                        selected.product,
                        selected.support_episodes[0],
                    )
                )
            )
            receipt = TypeAdapter(PdfExecutionReceipt).validate_json(
                canonical_bytes(receipt_body), strict=True
            )
            publication = receipt.publication
            if (
                publication.source_digest != capture["source_digest"]
                or publication.logical_digest != capture["logical_digest"]
            ):
                raise ValueError(
                    "selected PDF source differs from its authenticated capture projection"
                )
            reader = PublishedPdfReader(
                connection,
                ProductReference(
                    publication.task_id, publication.product_key, publication.logical_digest
                ),
                projection_context=self.prepared,
                read_budget=PublishedReadBudget(
                    100_000, execution_owner.invocation.executor.policy.max_reply_bytes
                ),
            )
            projections = published_section_projections(
                reader,
                selections=tuple(sections),
                membership=membership,
                scope=None,
                check_active=check_active,
            )
            views = tuple(
                FrozenNativeSource.from_projection(
                    self.prepared,
                    document=capture["document"],
                    section_pointer=row.section_pointer,
                    membership=row.membership,
                    text=row.text,
                    pieces=row.pieces,
                    items=row.items,
                    ancestors=row.ancestors,
                    recognition=row.health.get("formula_outcomes", ()),
                ).value
                for row in projections
            )
        check_active()
        original = {
            "document": capture["document"],
            "content_hash": capture["source_digest"],
            "mime": "application/pdf",
        }
        return PreparedSourceDiscovery(self.prepared, self.model).project(original, views, True)


def execute_pdf_views(receiver, capture, sections, membership):
    return receiver.profile.project(
        capture,
        sections,
        membership,
        binding=receiver.binding,
        execution_owner=receiver.execution_owner,
        check_active=receiver.check_active,
    )


@dataclass(frozen=True)
class PreparedPdfViewsPort:
    identity: Any
    operation: Any
    profile: PreparedPdfViews
    authorize: Any
    custody: tuple
    sources: Any
    native_selections = ()

    @property
    def logical_signature(self):
        from corpus_structure.ingest.pdf_views import PdfSourceViewsOperation

        signature = inspect.signature(PdfSourceViewsOperation.run, eval_str=True)
        return signature.replace(parameters=tuple(signature.parameters.values())[1:])

    def _verify(self):
        from corpus_structure.ingest.pdf_views import PdfSourceViewsOperation

        from .data_operation_prepared_products import verify_prepared_product

        verify_prepared_product(
            self.identity,
            self.profile.model,
            self.operation,
            self.sources,
            self.custody,
            assets=(pdf_views_assets(), pdf_views_custody()),
            functions=(
                (self.operation.callable_surfaces[0].declaration, PdfSourceViewsOperation.run),
                ("corpus_structure.semantic.pdf_views.execute_pdf_views", execute_pdf_views),
                (
                    "corpus_structure.semantic.pdf_views.PreparedPdfViews.project",
                    PreparedPdfViews.project,
                ),
            ),
            authorize=self.authorize,
            required_sources=self.sources,
        )

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from corpus_structure.core.work import PreparedWork
        from corpus_structure.ingest.pdf_views import PdfSourceViewsOperation

        from .data_operation_ports import (
            PortCompletion,
            PortRefusal,
            RoleValue,
            _untrusted_value,
            project_product_members,
        )

        self._verify()
        if (
            binding is None
            or not binding.sufficient
            or binding.operation != self.operation.semantic_id
        ):
            raise PortRefusal("PDF source discovery requires its admitted sufficient binding")
        incoming = next(role for role in self.operation.roles if role.direction == "input")
        ids = {
            (identity.owner, identity.domain): identity.key
            for identity in self.profile.model.identities
        }
        if (
            len(values) != 1
            or values[0].role != "capture"
            or values[0].kind_contract != ids[incoming.kind, "kind"]
        ):
            raise PortRefusal("PDF source discovery requires exactly its nominal capture input")
        capture = self.profile.prepared.validate_json(
            "DdoPdfCapture", canonical_bytes(_untrusted_value(values[0].value))
        ).model_dump(mode="json")
        parameters = decode_semantic_value(json.loads(binding.parameters))
        if set(parameters) != {"sections", "membership"}:
            raise PortRefusal("PDF views lack their frozen relative selection")

        def compute():
            self._verify()
            population = PdfSourceViewsOperation(
                self.profile,
                binding=binding,
                execution_owner=execution_owner,
                check_active=check_active,
            ).run(capture, tuple(parameters["sections"]), parameters["membership"])
            output = next(role for role in self.operation.roles if role.direction == "output")
            body = self.profile.prepared.validate_json(
                "DdoSourceViewPopulation", population.content
            ).model_dump(mode="python", exclude_unset=True)
            self._verify()
            return PortCompletion(
                self.operation.semantic_id,
                (
                    RoleValue(
                        output.name,
                        ids[output.kind, "kind"],
                        population.content,
                        canonical_bytes(semantic_value(body)),
                        project_product_members(self.profile.model, output.kind, body),
                    ),
                ),
                outcome=successful_return_outcome(self.operation),
            )

        (completion,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        check_active()
        return completion


def resolve_pdf_views_port(prepared, model, operation, *, identity, authorize, custody, sources):
    selected = model.operation(operation)
    if selected.semantic_id != "source.pdf_views/discovery" or selected.effects:
        raise ValueError("PDF views require their exact declared read-only discovery profile")
    port = PreparedPdfViewsPort(
        identity, selected, PreparedPdfViews(prepared, model), authorize, custody, sources
    )
    port._verify()
    return port
