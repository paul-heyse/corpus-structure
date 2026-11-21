"""Prepared application contracts around an externally owned native Docling document.

The bundled LinkML companion owns the envelope and projections. Docling owns document
shape; the exact local validation schema is retained with the product, never fetched on read.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
from typing import TYPE_CHECKING, Any, Literal

from jsonschema.validators import validator_for
from sqlalchemy import Connection, select

from corpus_structure.model.compiled import model_projection

from . import pdf_report_validation
from .identity import canonical_bytes
from .prepare import prepare_release
from .types import PreparedRelease, SourceArtifact

PDF_CONTRACT_DIGEST = sha256(
    files("corpus_structure").joinpath("model", "semantic", "pdf-products.yaml").read_bytes()
).hexdigest()

if TYPE_CHECKING:
    from .pdf_domain import PdfDomainContract


@dataclass(frozen=True, slots=True)
class PreparedPdfContext:
    release_id: str | None
    boundary: PreparedRelease
    domain: PdfDomainContract
    contract_digest: str
    staging: SourceArtifact

    def require_operation(self, name: str):
        return self.domain.require_operation(name)

    @property
    def terminal_task_states(self) -> frozenset[str]:
        from .data_operation_protocol import data_task_lifecycle

        protocol = self.domain.source("native/data-operation-protocol.yaml")
        return frozenset(data_task_lifecycle(protocol.content)["terminal"])

    @property
    def native_schema_digest(self) -> str:
        return self.domain.source("implementation/pdf/docling-validation.schema.json").digest


def _context_from_domain(release_id: str | None, domain: PdfDomainContract) -> PreparedPdfContext:
    """Lower one already captured domain; native authoring has no application release."""
    return PreparedPdfContext(
        release_id,
        prepare_release(domain.schema),
        domain,
        domain.source("schema/pdf_products").digest,
        SourceArtifact(
            "pdf/staging-model.yaml", domain.source("implementation/pdf/staging-model.yaml").content
        ),
    )


def prepare_pdf_context(prepared: PreparedRelease, domain: PdfDomainContract) -> PreparedPdfContext:
    """Prepare the captured current PDF facet using its own schema and policies."""
    qualified = trusted_pdf_context().require_operation("read_pdf_product")["implementation"]
    if domain.require_operation("read_pdf_product")["implementation"] != qualified:
        raise ValueError("PDF read ABI is unsupported by the qualified reader")
    return _context_from_domain(prepared.release_id, domain)


@model_projection
def trusted_pdf_context() -> PreparedPdfContext:
    from .pdf_domain import PdfDomainContract, pdf_domain_sources

    contract, *sources = pdf_domain_sources()
    domain = PdfDomainContract(contract.content, tuple(sources))
    return _context_from_domain(None, domain)


def integrated_metadata_policy(
    context: PreparedPdfContext | None = None,
) -> dict[str, Any]:
    """Read the single released policy for metadata crossing an integration boundary."""
    import yaml

    context = trusted_pdf_context() if context is None else context
    source = yaml.safe_load(context.staging.content)["annotations"][
        "pds:integrated_metadata_policy"
    ]
    return context.boundary.validate_json("PdfIntegratedMetadataPolicy", source).model_dump(
        mode="json"
    )


def projection_write_levels(context: PreparedPdfContext, staging: bytes) -> list[str]:
    """Validate and normalize the captured PDF projection write policy."""
    import yaml

    annotations = yaml.safe_load(staging)["annotations"]
    policy = context.boundary.validate_json(
        "PdfProjectionWriteProfile", annotations["pds:projection_write_profile"]
    )
    return sorted(set(policy.model_dump(mode="json")["allowed_isolation"]))


def pdf_context_for_task(conn: Connection, task_id: int) -> PreparedPdfContext:
    from .releases import open_release

    tasks = table("ops.task")
    release_id = conn.execute(select(tasks.c.release_id).where(tasks.c.id == task_id)).scalar_one()
    if release_id is None:
        raise ValueError("PDF producer task has no current declared release")
    prepared = open_release(conn, release_id)
    return pdf_context_for_release(conn, prepared)


def pdf_context_for_release(conn: Connection, prepared: PreparedRelease) -> PreparedPdfContext:
    from .data_operation_admission import bound_data_operation_model
    from .pdf_domain import read_pdf_domain, require_pdf_model_asset

    model = bound_data_operation_model(prepared)
    if not any(op.capabilities.preparation == "pdf-native" for op in model.operations):
        raise ValueError("producer release has no declared native PDF capability")
    domain = read_pdf_domain(conn, prepared.release_id)
    require_pdf_model_asset(model, domain)
    return prepare_pdf_context(prepared, domain)


def pdf_context_for_run(conn: Connection, run_id: int) -> PreparedPdfContext:
    from .releases import open_release

    runs = table("ops.run")
    release = conn.execute(select(runs.c.release_id).where(runs.c.id == run_id)).scalar_one()
    return pdf_context_for_release(conn, open_release(conn, release))


def table(name: str):
    # Native metadata is unnecessary for pure preparation or lightweight service registration.
    from .metadata import table as shared_table

    return shared_table(name)


@lru_cache(maxsize=16)
def _native_validator(schema_bytes: bytes):
    schema = json.loads(schema_bytes)
    validator = validator_for(schema)
    validator.check_schema(schema)

    # Network reference resolution is deliberately unavailable to the local native contract.
    def local_refs(value: Any) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and not ref.startswith("#"):
                raise ValueError("native schema must use retained local references")
            for child in value.values():
                local_refs(child)
        elif isinstance(value, list):
            for child in value:
                local_refs(child)

    local_refs(schema)
    return validator(schema)


@dataclass(frozen=True, slots=True)
class PreparedPdfProduct:
    payload: bytes
    original: bytes
    schema_bytes: bytes
    recipe_bytes: bytes
    contract_digest: str
    _validated: bool = field(default=False, init=False, repr=False, compare=False)

    @property
    def digest(self) -> str:
        return sha256(self.payload).hexdigest()

    def values(self) -> dict[str, Any]:
        return json.loads(self.payload)


def prepare_pdf_product(
    payload: Mapping[str, Any],
    original: bytes,
    schema_bytes: bytes,
    recipe_bytes: bytes,
    *,
    context: PreparedPdfContext | None = None,
    publication_kind: Literal["native", "integrated"] = "native",
) -> PreparedPdfProduct:
    context = trusted_pdf_context() if context is None else context
    context.require_operation("prepare_native_document")
    supplied = dict(payload)
    document = supplied.pop("document")
    # This transformation is an internal boundary only. The persisted wire document stays JSON.
    if "document_json" in supplied:
        raise ValueError("document_json is internal and cannot be supplied on the wire")
    supplied["document_json"] = canonical_bytes(document).decode()
    value = context.boundary.validate_json("PdfNativeEnvelope", json.dumps(supplied)).model_dump(
        mode="json", exclude_none=True
    )
    value.pop("document_json")
    value["document"] = document
    value.setdefault("regions", [])
    value["health"].setdefault("issues", [])
    for digest_field, content in (
        ("artifact_digest", original),
        ("schema_digest", schema_bytes),
        ("recipe_digest", recipe_bytes),
    ):
        if value[digest_field] != sha256(content).hexdigest():
            raise ValueError(digest_field + " differs from retained bytes")
    if value["schema_digest"] != context.native_schema_digest:
        raise ValueError("native schema is not admitted by the archived producer contract")
    _native_validator(schema_bytes).validate(document)
    # Schema alone admits dangling pointers. Native validation owns tree semantics;
    # it may clamp geometry, which is forbidden after a payload acquired identity.
    from docling_core.types.doc import DoclingDocument

    native = DoclingDocument.model_validate(document)
    before = native.model_dump(mode="json", by_alias=True)
    try:
        # Upstream annotates this decorated method as a descriptor, not a callable.
        validate_tree = native.validate_document
        if not callable(validate_tree):
            raise TypeError("native Docling tree validator is not callable")
        validate_tree()
    except (ValueError, IndexError) as error:
        raise ValueError("malformed native document tree/reference") from error
    if native.model_dump(mode="json", by_alias=True) != before:
        raise ValueError("native document must be normalized before preparation")
    if not original.startswith(b"%PDF-"):
        raise ValueError("PDF original has no PDF header")

    if document.get("version") != value["native_schema_version"]:
        raise ValueError("native schema version differs from document")
    pointers, ordinals = set(), set()
    for item in value["items"]:
        pointer = item["pointer"]
        if pointer in pointers or item["ordinal"] in ordinals:
            raise ValueError("duplicate native occurrence pointer or reading ordinal")
        pointers.add(pointer)
        ordinals.add(item["ordinal"])
        native = pdf_report_validation.resolve_native_pointer(document, pointer)
        if native.get("self_ref") != pointer or native.get("label") != item["label"]:
            raise ValueError("item projection differs from native occurrence")
        if native.get("content_layer") != item["content_layer"]:
            raise ValueError("item layer differs from native occurrence")
        if "text" in item and native.get("text") != item["text"]:
            raise ValueError("item text differs from native occurrence")
        native_parent = (native.get("parent") or {}).get("$ref")
        if native_parent != item.get("parent_pointer"):
            raise ValueError("item parent differs from native occurrence")
        for pointer_field in ("parent_pointer", "section_pointer"):
            if pointer_field in item:
                pdf_report_validation.resolve_native_pointer(document, item[pointer_field])
    for item in value["items"]:
        if item.get("parent_pointer") is not None and item["parent_pointer"] not in pointers:
            raise ValueError("native parent is missing from item projection")
        if item.get("section_pointer") is not None and item["section_pointer"] not in pointers:
            raise ValueError("section is missing from item projection")
    seen_regions = set()
    for region in value["regions"]:
        key = (region["pointer"], region["region_index"])
        if key in seen_regions or region["pointer"] not in pointers:
            raise ValueError("region occurrence is duplicate or has no indexed item")
        seen_regions.add(key)
        native = pdf_report_validation.resolve_native_pointer(document, region["pointer"])
        prov = native.get("prov", [])
        if region["region_index"] >= len(prov):
            raise ValueError("region is not native item provenance")
        provenance = prov[region["region_index"]]
        bbox = provenance["bbox"]
        if (
            provenance["page_no"] != region["page_no"]
            or any(
                bbox[k] != region[field]
                for k, field in (("l", "left"), ("t", "top"), ("r", "right"), ("b", "bottom"))
            )
            or {"TOPLEFT": "top_left", "BOTTOMLEFT": "bottom_left"}.get(bbox["coord_origin"])
            != region["origin"]
        ):
            raise ValueError("region differs from native provenance")
        if not (
            0 <= region["left"] <= region["right"] <= region["page_width"]
            and 0
            <= min(region["top"], region["bottom"])
            <= max(region["top"], region["bottom"])
            <= region["page_height"]
        ):
            raise ValueError("region lies outside physical page")
        page = document.get("pages", {}).get(str(region["page_no"]))
        if (
            page is None
            or page["size"]["width"] != region["page_width"]
            or page["size"]["height"] != region["page_height"]
        ):
            raise ValueError("region dimensions differ from native physical page")
        if (region["origin"] == "top_left" and region["top"] > region["bottom"]) or (
            region["origin"] == "bottom_left" and region["top"] < region["bottom"]
        ):
            raise ValueError("region coordinate origin contradicts vertical bounds")
    pdf_report_validation.validate_pdf_report_metadata(
        {**value, "kind": publication_kind},
        integrated_policy=integrated_metadata_policy(context)
        if publication_kind == "integrated"
        else None,
    )
    from .pdf_ocr_contracts import validate_pdf_inline_reports, validate_pdf_ocr_pages

    validate_pdf_ocr_pages(value)
    validate_pdf_inline_reports(value)
    result = PreparedPdfProduct(
        canonical_bytes(value), original, schema_bytes, recipe_bytes, context.contract_digest
    )
    object.__setattr__(result, "_validated", True)
    return result


def require_pdf_coverage(
    product: PreparedPdfProduct,
    *universes: str,
    whole_document: bool = False,
    section_pointer: str | None = None,
    membership: str | None = None,
) -> None:
    """A complete consumer cannot reinterpret missing/unknown recognition as absence."""
    values = product.values()
    if whole_document and values["source_scope"] != "whole_document":
        raise ValueError("whole-document source coverage is unavailable")
    health = values["health"]
    for universe in universes:
        scope = health.get(universe + "_scope", [])
        if scope and (
            whole_document
            or section_pointer not in scope
            or membership != health.get(universe + "_membership")
        ):
            raise ValueError(
                "required PDF recognition coverage is outside the qualified section scope"
            )
    if health["conversion"] != "success" or any(
        health.get(universe + "_coverage") != "complete" for universe in universes
    ):
        raise ValueError("required PDF recognition coverage is unavailable")


def store_pdf_original(
    conn: Connection,
    *,
    task_id: int,
    attempt: int,
    holder: str,
    original: bytes,
    recipe_bytes: bytes,
) -> str:
    """Retain source before inference behind the producing attempt and release."""
    from .pdf_domain import require_pdf_database_action

    context = pdf_context_for_task(conn, task_id)
    context.require_operation("retain_pdf_original")
    if context.release_id is None:
        raise ValueError("source custody requires an archived release")
    require_pdf_database_action(conn, context.release_id, "retain_pdf_original")
    if not original.startswith(b"%PDF-"):
        raise ValueError("PDF original has no PDF header")
    from ._pdf_native_calls import retain_pdf_original
    from .identifiers import TaskAttempt, TaskId
    from .releases import open_release

    return retain_pdf_original(
        conn,
        task_id=TaskId(task_id),
        attempt=TaskAttempt(attempt),
        holder=holder,
        original=original,
        recipe_bytes=recipe_bytes,
        projection_context=open_release(conn, context.release_id),
    )
