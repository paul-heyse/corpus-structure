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
from typing import TYPE_CHECKING, Any

from jsonschema.validators import validator_for
from sqlalchemy import Connection, select, text

from .identity import canonical_bytes
from .prepare import prepare_release
from .types import PreparedRelease, SourceArtifact, SourceBundle

PDF_CONTRACT_DIGEST = sha256(
    files("corpus_structure").joinpath("model", "semantic", "pdf-products.yaml").read_bytes()
).hexdigest()

if TYPE_CHECKING:
    from .contracts import ExecutionModelProducts


@dataclass(frozen=True, slots=True)
class PreparedPdfContext:
    release_id: str | None
    boundary: PreparedRelease
    execution: ExecutionModelProducts
    contract_digest: str
    native_schema_digest: str


@lru_cache(maxsize=16)
def _boundary(bundle: SourceBundle) -> PreparedRelease:
    return prepare_release(bundle)


def prepare_pdf_context(
    prepared: PreparedRelease, execution_schema: SourceBundle
) -> PreparedPdfContext:
    from .contracts import bound_execution_model, execution_payload

    execution = bound_execution_model(prepared)
    execution.require_operation("publish_native_document")
    payload = execution_payload(prepared)
    if payload is None:
        raise ValueError("native PDF contract requires archived execution inputs")
    actual = {
        "root": execution_schema.root,
        "sources": [{"name": s.name, "sha256": s.digest} for s in execution_schema.sources],
    }
    if actual != json.loads(payload)["inputs"]["schema"]:
        raise ValueError("PDF schema inputs differ from archived execution binding")
    source = next((s for s in execution_schema.sources if s.name == "pdf_products"), None)
    if source is None:
        raise ValueError("archived release has no native PDF contract")
    return PreparedPdfContext(
        prepared.release_id,
        _boundary(execution_schema),
        execution,
        source.digest,
        dict(execution.implementation_digests)["pdf/docling-validation.schema.json"],
    )


@lru_cache(maxsize=1)
def trusted_pdf_context() -> PreparedPdfContext:
    from .contracts import compile_execution_model, trusted_execution_inputs

    inputs = trusted_execution_inputs()
    source = next(s for s in inputs.schema.sources if s.name == "pdf_products")
    return PreparedPdfContext(
        None,
        _boundary(inputs.schema),
        compile_execution_model(inputs),
        source.digest,
        next(
            s.digest
            for s in inputs.implementations
            if s.name == "pdf/docling-validation.schema.json"
        ),
    )


def pdf_context_for_task(conn: Connection, task_id: int) -> PreparedPdfContext:
    from .releases import open_release

    tasks, runs, inputs = table("ops.task"), table("ops.run"), table("sem.input")
    release_id = conn.execute(
        select(runs.c.release_id)
        .join_from(tasks, runs, tasks.c.run_id == runs.c.id)
        .where(tasks.c.id == task_id)
    ).scalar_one()
    prepared = open_release(conn, release_id)
    return pdf_context_for_release(conn, prepared)


def pdf_context_for_release(conn: Connection, prepared: PreparedRelease) -> PreparedPdfContext:
    from .contracts import execution_payload

    inputs = table("sem.input")
    release_id = prepared.release_id
    payload = execution_payload(prepared)
    if payload is None:
        raise ValueError("producing task has no archived execution binding")
    manifest = json.loads(payload)["inputs"]["schema"]
    names = ["execution/schema/" + s["name"] for s in manifest["sources"]]
    rows = conn.execute(
        select(inputs.c.input_name, inputs.c.content).where(
            inputs.c.release_id == release_id,
            inputs.c.input_kind == "dependency",
            inputs.c.input_name.in_(names),
        )
    ).mappings()
    retained = {r["input_name"]: bytes(r["content"]) for r in rows}
    if set(retained) != set(names):
        raise ValueError("PDF archived schema custody is incomplete")
    bundle = SourceBundle(
        manifest["root"],
        tuple(
            SourceArtifact(s["name"], retained["execution/schema/" + s["name"]])
            for s in manifest["sources"]
        ),
    )
    return prepare_pdf_context(prepared, bundle)


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


def resolve_native_pointer(document: Mapping[str, Any], pointer: str) -> Any:
    """Resolve a qualified local native pointer; build custody belongs to its envelope."""
    if not pointer.startswith("#/"):
        raise ValueError("native pointer must be a local document reference")
    value: Any = document
    try:
        for raw in pointer[2:].split("/"):
            part = raw.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                if not part.isdecimal() or str(int(part)) != part:
                    raise ValueError("noncanonical native array pointer")
                value = value[int(part)]
            else:
                value = value[part]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("native pointer is dangling: " + pointer) from error
    return value


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
) -> PreparedPdfProduct:
    context = trusted_pdf_context() if context is None else context
    context.execution.require_operation("prepare_native_document")
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
    for field, content in (
        ("artifact_digest", original),
        ("schema_digest", schema_bytes),
        ("recipe_digest", recipe_bytes),
    ):
        if value[field] != sha256(content).hexdigest():
            raise ValueError(field + " differs from retained bytes")
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
    if value["source_scope"] == "page_range":
        if (
            value.get("page_start") is None
            or value.get("page_end") is None
            or value["page_start"] > value["page_end"]
        ):
            raise ValueError("page-range source requires ordered physical page bounds")
        if any(
            not value["page_start"] <= int(page) <= value["page_end"]
            for page in document.get("pages", {})
        ):
            raise ValueError("native page lies outside declared source scope")
    elif value.get("page_start") is not None or value.get("page_end") is not None:
        raise ValueError("whole-document scope cannot carry page-range bounds")
    parent = [value.get(k) for k in ("parent_task_id", "parent_product_key", "parent_digest")]
    if any(v is not None for v in parent) and not all(v is not None for v in parent):
        raise ValueError("derived document requires complete parent product identity")
    pointers, ordinals = set(), set()
    for item in value["items"]:
        pointer = item["pointer"]
        if pointer in pointers or item["ordinal"] in ordinals:
            raise ValueError("duplicate native occurrence pointer or reading ordinal")
        pointers.add(pointer)
        ordinals.add(item["ordinal"])
        native = resolve_native_pointer(document, pointer)
        if native.get("self_ref") != pointer or native.get("label") != item["label"]:
            raise ValueError("item projection differs from native occurrence")
        if native.get("content_layer") != item["content_layer"]:
            raise ValueError("item layer differs from native occurrence")
        if "text" in item and native.get("text") != item["text"]:
            raise ValueError("item text differs from native occurrence")
        native_parent = (native.get("parent") or {}).get("$ref")
        if native_parent != item.get("parent_pointer"):
            raise ValueError("item parent differs from native occurrence")
        for field in ("parent_pointer", "section_pointer"):
            if field in item:
                resolve_native_pointer(document, item[field])
    for item in value["items"]:
        if item.get("parent_pointer") is not None and item["parent_pointer"] not in pointers:
            raise ValueError("native parent is missing from item projection")
        if item.get("section_pointer") is not None and item["section_pointer"] not in pointers:
            raise ValueError("section is missing from item projection")
    outcomes = value["health"].get("formula_outcomes", [])
    if len({o["pointer"] for o in outcomes}) != len(outcomes):
        raise ValueError("duplicate formula recognition outcome")
    for outcome in outcomes:
        if outcome["pointer"] not in pointers:
            raise ValueError("formula recognition outcome has no native occurrence")
    if value["health"]["display_coverage"] == "complete":
        successful = {o["pointer"] for o in outcomes if o["outcome"] == "succeeded"}

        def display_item(item):
            if item["label"] != "formula":
                return False
            parent = item.get("parent_pointer")
            label = resolve_native_pointer(document, parent).get("label") if parent else None
            return label not in {"table", "inline"}

        if any(display_item(i) and i["pointer"] not in successful for i in value["items"]):
            raise ValueError("complete formula coverage lacks attributable recognition")
    seen_regions = set()
    for region in value["regions"]:
        key = (region["pointer"], region["region_index"])
        if key in seen_regions or region["pointer"] not in pointers:
            raise ValueError("region occurrence is duplicate or has no indexed item")
        seen_regions.add(key)
        native = resolve_native_pointer(document, region["pointer"])
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
    health = value["health"]
    for universe, policy in (("inline", "candidate_policy"), ("cell", "cells_policy")):
        if health.get(universe + "_coverage") == "complete" and (
            not health.get(universe + "_scope")
            or health.get(universe + "_membership") not in {"direct", "descendants"}
            or not health.get(policy)
        ):
            raise ValueError(
                "complete recognition coverage requires its named scope, membership and candidate policy"
            )
        for pointer in health.get(universe + "_scope", ()):
            if resolve_native_pointer(document, pointer).get("label") not in {"section", "chapter"}:
                raise ValueError("recognition coverage scope is not a native section")
    coverage = set()
    for row in value.get("recognition_coverage", ()):
        key = row["section_pointer"], row["membership"], row["universe"]
        if key in coverage:
            raise ValueError("duplicate scoped recognition coverage")
        coverage.add(key)
        if resolve_native_pointer(document, row["section_pointer"]).get("label") not in {
            "section",
            "chapter",
        }:
            raise ValueError("recognition coverage row requires a native section")
    if coverage and any(
        health.get(universe + "_coverage") != "unknown" for universe in ("inline", "cell")
    ):
        raise ValueError("scoped row coverage cannot masquerade as a global native summary")
    reports = set()
    outcomes = {row["pointer"]: row["outcome"] for row in health.get("formula_outcomes", ())}
    for report in value.get("cell_reports", ()):
        key = report["table_pointer"], report["cell_index"]
        if key in reports:
            raise ValueError("duplicate native cell report")
        reports.add(key)
        table = resolve_native_pointer(document, report["table_pointer"])
        cells = table.get("data", {}).get("table_cells", ())
        if (
            table.get("label") != "table"
            or not 0 <= report["cell_index"] < len(cells)
            or str(report["page_no"]) not in document.get("pages", {})
        ):
            raise ValueError("cell report is outside its native table/cell/page")
        if not any(p["page_no"] == report["page_no"] for p in table.get("prov", ())):
            raise ValueError("cell report page differs from its native table")
        if report["classification"] == "prose" and (
            report["outcome"] != "not_requested" or report.get("formula_pointer") is not None
        ):
            raise ValueError("prose cell report cannot claim native formula recognition")
        if report["classification"] == "math" and report["outcome"] == "succeeded":
            pointer = report.get("formula_pointer")
            if (
                pointer is None
                or (cells[report["cell_index"]].get("ref") or {}).get("$ref") != pointer
                or resolve_native_pointer(document, pointer).get("label") != "formula"
                or outcomes.get(pointer) != "succeeded"
            ):
                raise ValueError("successful math cell lacks qualified rich formula recognition")
    runtime = value.get("runtime_report")
    if runtime is not None:
        if not isinstance(json.loads(runtime["effective_options"]), dict):
            raise ValueError("native effective options must be an upstream option object")
        if "confidence" in runtime and not isinstance(json.loads(runtime["confidence"]), dict):
            raise ValueError("native confidence must be its upstream report object")
        for field in ("packages", "bindings"):
            names = [row["name"] for row in runtime.get(field, ())]
            if len(names) != len(set(names)):
                raise ValueError("native runtime report repeats a named binding")
    candidate_pages = set()
    for page in value.get("inline_candidate_pages", []):
        page_no = page["page_no"]
        if page_no in candidate_pages or str(page_no) not in document.get("pages", {}):
            raise ValueError("inline candidate page is duplicate or outside native scope")
        candidate_pages.add(page_no)
        dimensions = document["pages"][str(page_no)]["size"]
        for candidate in page.get("candidates", []):
            if (
                candidate["page_no"] != page_no
                or candidate["origin"] not in {"TOPLEFT", "BOTTOMLEFT"}
                or candidate["basis"]
                not in {"native-math-font-v1", "native-math-token-v1", "native-vector-gap-v1"}
            ):
                raise ValueError("inline candidate has an unqualified page/origin/basis")
            if not (
                0 <= candidate["left"] <= candidate["right"] <= dimensions["width"]
                and 0
                <= min(candidate["top"], candidate["bottom"])
                <= max(candidate["top"], candidate["bottom"])
                <= dimensions["height"]
            ):
                raise ValueError("inline candidate is outside physical page")
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


def store_pdf_product(
    conn: Connection,
    *,
    task_id: int,
    attempt: int,
    holder: str,
    product: PreparedPdfProduct,
    context: PreparedPdfContext | None = None,
) -> str:
    from .contracts import require_database_operation

    archived = pdf_context_for_task(conn, task_id)
    if context is not None and context != archived:
        raise ValueError("PDF context differs from producing task release")
    archived.execution.require_operation("publish_native_document")
    if archived.release_id is None:
        raise ValueError("native publication requires an archived release")
    require_database_operation(conn, archived.release_id, "publish_native_document")
    if (
        not product._validated
        or product.contract_digest != archived.contract_digest
        or sha256(product.schema_bytes).hexdigest() != archived.native_schema_digest
    ):
        raise ValueError(
            "native publication requires a prepared immutable product under this archive"
        )
    return conn.execute(
        text(
            "SELECT ops.publish_native_document(:task,:attempt,:holder,:contract,:payload,"
            ":original,:schema_bytes,:recipe_bytes)"
        ),
        dict(
            task=task_id,
            attempt=attempt,
            holder=holder,
            contract=product.contract_digest,
            payload=product.payload,
            original=None,
            schema_bytes=product.schema_bytes,
            recipe_bytes=product.recipe_bytes,
        ),
    ).scalar_one()


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
    from .contracts import require_database_operation

    context = pdf_context_for_task(conn, task_id)
    context.execution.require_operation("retain_pdf_original")
    if context.release_id is None:
        raise ValueError("source custody requires an archived release")
    require_database_operation(conn, context.release_id, "retain_pdf_original")
    if not original.startswith(b"%PDF-"):
        raise ValueError("PDF original has no PDF header")
    return conn.execute(
        text("SELECT ops.retain_pdf_original(:task,:attempt,:holder,:original,:recipe)"),
        dict(task=task_id, attempt=attempt, holder=holder, original=original, recipe=recipe_bytes),
    ).scalar_one()


def pdf_shape_guard_sql() -> str:
    """Native envelope/projection guards share the effective LinkML shape generator."""
    from .native_shapes import record_shape_guards

    return (
        "IF product ? 'document_json' THEN "
        "RAISE EXCEPTION 'internal PDF field supplied' USING ERRCODE='23514'; END IF;\n"
        "parsing_item := (product - 'document') || "
        "jsonb_build_object('document_json', (product->'document')::text);\n"
        + record_shape_guards(trusted_pdf_context().boundary, "PdfNativeEnvelope", "parsing_item")
    )
