"""Operational native PDF ingestion under the existing method/attempt lifecycle."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable, Mapping, Sequence
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text

from corpus_structure.core.method import (
    Digest,
    MethodContext,
    Resources,
    SourceRunContext,
    SourceViewDraft,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import (
    ConfidenceSource,
    MethodFamily,
    MethodTier,
    ObservationOutcome,
    TaskUnitType,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.parsing_products import ProductReference

from .pdf import PdfConversion, PdfRecipe, publication_payload
from .pdf_assets import PreparedPdfAssets, prepare_pdf_assets
from .pdf_candidates import CandidatePage, InlineCandidate
from .pdf_enrichment import PdfEnrichmentRequest
from .pdf_health import FormulaOutcome
from .pdf_health import error_summary as _error_summary
from .pdf_hierarchy import (
    NativeSnapshot,
    SectionPolicy,
    load_snapshot,
    native_nodes,
    organize,
    project_section,
)
from .pdf_worker import PdfWorker


class PdfRuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    layout_revision: str = "8f39ad3c0b4c58e9c2d2c84a38465abf757272d8"
    formula_revision: str = "ecedbe111d15c2dc60bfd4a823cbe80127b58af4"
    model_cache: Path = Field(default_factory=lambda: Path.home() / ".cache/docling/models")
    device: Literal["cpu", "cuda"] = "cuda"
    ocr_device: Literal["cpu", "cuda"] = "cpu"
    timeout_seconds: float | None = None
    parser_threads: int = Field(default=8, ge=1)
    stage_batch_size: int = Field(default=4, ge=1)

    def recipe(self) -> PdfRecipe:
        return PdfRecipe(
            self.layout_revision,
            self.formula_revision,
            self.device,
            self.ocr_device,
            self.parser_threads,
            self.stage_batch_size,
            self.timeout_seconds,
        )


class PdfIngestConfig(PdfRuntimeConfig):
    originals: tuple[str, ...] = ("siegrist_random/Full_PDF/Full.pdf",)
    section_rule: str = "native-organizational-headings-v2"
    section_pattern: str = r"^\d+(?:\.\d+)*\s*[:.)-]?\s+\S"
    organizational_heading_pattern: str = r"\S"
    local_heading_pattern: str = SectionPolicy("default").local_heading_pattern
    sections: tuple[str, ...] = ()
    membership: Literal["direct", "descendants"] = "direct"
    native_product: ProductReference | None = None

    def section_policy(self) -> SectionPolicy:
        return SectionPolicy(
            self.section_rule,
            self.section_pattern,
            organizational_pattern=self.organizational_heading_pattern,
            local_heading_pattern=self.local_heading_pattern,
        )


class IngestPdf:
    name = "ingest.pdf"
    version = "2"
    family = MethodFamily.INGEST
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.ENCODER
    confidence_source: ConfidenceSource | None = None
    Config = PdfIngestConfig
    resources = Resources(worker="encoder", batch_size=1, max_concurrency=1)

    def __init__(self) -> None:
        self._prepared: dict[tuple[str, str], tuple[PdfRecipe, PreparedPdfAssets]] = {}
        self._workers: dict[str, PdfWorker] = {}

    def _runtime(self, cfg: PdfRuntimeConfig) -> tuple[PdfRecipe, PreparedPdfAssets]:
        base = cfg.recipe()
        key = (base.digest, str(cfg.model_cache.resolve()))
        if key not in self._prepared:
            assets = prepare_pdf_assets(base, cache=cfg.model_cache, offline=True)
            self._prepared[key] = (
                dataclasses.replace(
                    base, model_artifacts=assets.files, model_revisions=assets.repositories
                ),
                assets,
            )
        return self._prepared[key]

    def _worker(self, recipe: PdfRecipe, assets: PreparedPdfAssets) -> PdfWorker:
        worker = self._workers.get(recipe.digest)
        if worker is not None and worker.closed and worker.pid is not None:
            worker.close()
            if worker.pid is not None:
                raise RuntimeError("a native PDF child has not completed shutdown")
        if worker is None or worker.closed:
            worker = PdfWorker(recipe, assets=assets)
            self._workers[recipe.digest] = worker
        return worker

    def close(self) -> None:
        errors = []
        for worker in self._workers.values():
            try:
                worker.close()
            except BaseException as error:
                errors.append(error)
        self._workers = {
            key: worker for key, worker in self._workers.items() if worker.pid is not None
        }
        if errors:
            primary = next(
                (error for error in errors if not isinstance(error, Exception)), errors[0]
            )
            for error in errors:
                if error is primary:
                    continue
                primary.add_note("additional PDF child teardown failure: " + str(error)[:1800])
            raise primary

    def original_recipe(self, cfg: PdfIngestConfig) -> bytes:
        """Preparation only; orchestration commits original custody before calling run."""
        if cfg.native_product is not None:
            return canonical_bytes(
                {
                    "recipe_id": "native-pdf-adoption-v1",
                    "native_product": cfg.native_product.values(),
                    "section_policy": {
                        "rule_id": cfg.section_rule,
                        "organizational_pattern": cfg.organizational_heading_pattern,
                        "local_heading_pattern": cfg.local_heading_pattern,
                        "numbered_pattern": cfg.section_pattern,
                    },
                }
            )
        recipe, _ = self._runtime(cfg)
        return recipe.to_bytes()

    def select(self, run: SourceRunContext, cfg: PdfIngestConfig) -> Iterable[UnitRef]:
        corpus = run.options.get("corpus")
        listed = corpus.get("documents") if isinstance(corpus, dict) else None
        keys = [str(k) for k in listed] if isinstance(listed, list) else []
        with run.reader.connection() as conn:
            rows = conn.execute(
                text(
                    "SELECT d.id,d.key FROM kb.document d JOIN ops.run r "
                    "ON r.project_id=d.project_id WHERE r.id=:run AND d.key=ANY(:keys) "
                    "AND d.source_uri=ANY(:sources) ORDER BY d.key"
                ),
                dict(run=run.run_id, keys=keys, sources=list(cfg.originals)),
            )
            return [UnitRef(TaskUnitType.DOCUMENT, int(r.id), str(r.key)) for r in rows]

    def input_digest(self, unit: UnitView, cfg: PdfIngestConfig) -> Digest:
        if unit.ref.unit_key is None:
            raise ValueError("native PDF unit requires its retained document key")
        value: dict[str, Any] = {
            "document": unit.ref.unit_key,
            "recipe": sha256(self.original_recipe(cfg)).hexdigest(),
        }
        if cfg.membership == "descendants" and not cfg.sections:
            value["projection_scope"] = unit.run.options.get("scope")
        return Digest(canonical_bytes(value))

    def run(
        self, units: Sequence[UnitView], cfg: PdfIngestConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        consumer_release = _consumer_release(ctx)
        outputs = []
        for unit in units:
            retained_native = ()
            if unit.ref.unit_id is None:
                raise ValueError("native PDF unit requires original document id")
            try:
                if cfg.native_product is not None:
                    # Explicit sanctioned adoption is not conversion or a new native producer.
                    archived = ctx.reader.native_document(cfg.native_product)
                    values = archived.values()
                    if (
                        values.get("source_scope") != "whole_document"
                        or values["health"]["conversion"] != "success"
                    ):
                        raise ValueError(
                            "PDF adoption requires a complete whole-document native product"
                        )
                    native = _snapshot_from_values(values)
                    doc = load_snapshot(native)
                    nodes = native_nodes(doc)
                    selected_product = cfg.native_product
                    products = ()
                    if not any(str(n.label) in {"section", "chapter"} for n in nodes.values()):
                        # Reuse successful conversion after a previous organization failure.
                        organization = organize(native, cfg.section_policy())
                        adopted_recipe = self.original_recipe(cfg)
                        conversion = _conversion_from_product(archived, adopted_recipe)
                        payload = publication_payload(
                            conversion,
                            product_key="organized",
                            schema_digest=sha256(archived.schema_bytes).hexdigest(),
                            native=organization.document,
                            section_refs=frozenset(s.group_ref for s in organization.sections),
                            parent=(
                                cfg.native_product.task_id,
                                cfg.native_product.product_key,
                                cfg.native_product.content_digest,
                            ),
                        )
                        current = ctx.reader.prepare_pdf_product(
                            payload, archived.original, archived.schema_bytes, adopted_recipe
                        )
                        products = (current,)
                        retained_native = products
                        selected_product = ctx.reader.native_product_reference(
                            unit.ref.unit_id, "organized", current.digest
                        )
                        native = organization.document
                        values = payload
                        nodes = native_nodes(load_snapshot(native))
                    sections = _select_sections(nodes, cfg, scope=ctx.run.options.get("scope"))
                    drafts = _drafts(
                        unit.ref.unit_id,
                        selected_product,
                        native,
                        values["health"],
                        sections,
                        cfg.membership,
                        consumer_release,
                        recognition_coverage=values.get("recognition_coverage", ()),
                    )
                    outputs.append(
                        UnitResult(
                            ref=unit.ref,
                            outcome=ObservationOutcome.EMPTY,
                            native_products=products,
                            source_views=drafts,
                        )
                    )
                    continue
                recipe, assets = self._runtime(cfg)
                converter = self._worker(recipe, assets)
                schema_bytes = (
                    files("corpus_structure")
                    .joinpath("model", "semantic", "docling-validation.schema.json")
                    .read_bytes()
                )
                schema_digest = sha256(schema_bytes).hexdigest()
                original = ctx.reader.original(unit.ref.unit_id)
                conversion = converter.convert_bytes(original, check_active=ctx.check_active)
                raw_payload = publication_payload(
                    conversion,
                    product_key="native",
                    schema_digest=schema_digest,
                    include_application_metadata=False,
                )
                raw = ctx.reader.prepare_pdf_product(
                    raw_payload, original, schema_bytes, conversion.recipe
                )
                retained_native = (raw,)
                raw_ref = ctx.reader.native_product_reference(
                    unit.ref.unit_id, "native", raw.digest
                )
                organization = organize(conversion.native, cfg.section_policy())
                section_refs = frozenset(s.group_ref for s in organization.sections)
                organized_payload = publication_payload(
                    conversion,
                    product_key="organized",
                    schema_digest=schema_digest,
                    native=organization.document,
                    section_refs=section_refs,
                    parent=(raw_ref.task_id, raw_ref.product_key, raw_ref.content_digest),
                )
                organized = ctx.reader.prepare_pdf_product(
                    organized_payload, original, schema_bytes, conversion.recipe
                )
                retained_native = (raw, organized)
                organized_ref = ctx.reader.native_product_reference(
                    unit.ref.unit_id, "organized", organized.digest
                )
                doc = load_snapshot(organization.document)
                drafts = _drafts(
                    unit.ref.unit_id,
                    organized_ref,
                    organization.document,
                    organized_payload["health"],
                    _select_sections(native_nodes(doc), cfg, scope=ctx.run.options.get("scope")),
                    cfg.membership,
                    consumer_release,
                )
                outputs.append(
                    UnitResult(
                        ref=unit.ref,
                        outcome=ObservationOutcome.EMPTY,
                        native_products=(raw, organized),
                        source_views=drafts,
                    )
                )
            except Exception as error:
                summary = _error_summary(error)
                ctx.logger.warning("ingest.pdf %s: %s", unit.ref.unit_key, summary)
                outputs.append(
                    UnitResult(
                        ref=unit.ref,
                        outcome=ObservationOutcome.FAILED,
                        error=summary,
                        native_products=retained_native,
                    )
                )
        return outputs


def _consumer_release(ctx: MethodContext) -> str:
    runs = table("ops.run")
    with ctx.reader.connection() as conn:
        return conn.execute(
            select(runs.c.release_id).where(runs.c.id == ctx.run.run_id)
        ).scalar_one()


def _snapshot_from_values(values: Mapping[str, Any]) -> NativeSnapshot:
    from .pdf_hierarchy import NativeSnapshot

    payload = json.dumps(
        values["document"],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return NativeSnapshot(payload, sha256(payload).hexdigest(), values["native_schema_version"])


def _select_sections(
    nodes: Mapping[str, Any], cfg: PdfIngestConfig, *, scope: Any = None
) -> tuple[str, ...]:
    sections = [p for p, n in nodes.items() if str(n.label) in {"section", "chapter"}]
    if not sections:
        raise ValueError(
            "native product has no qualified organizational sections; organize it before adoption"
        )
    matched = [
        p
        for p in sections
        if not cfg.sections or p in cfg.sections or nodes[p].name in cfg.sections
    ]
    if cfg.sections and len(matched) != len(set(cfg.sections)):
        raise ValueError("requested intact section selection is missing or ambiguous")
    if (
        cfg.membership == "descendants"
        and not cfg.sections
        and isinstance(scope, dict)
        and scope.get("kind") == "native_sections"
    ):
        from corpus_structure.semantic.source_views import resolve_native_sections

        matched = list(
            resolve_native_sections(
                {pointer: nodes[pointer].name for pointer in sections}, scope["sections"]
            )
        )
    matched_set = set(matched)

    def ancestry(pointer):
        node = nodes[pointer]
        while node.parent is not None:
            yield node.parent.cref
            node = nodes[node.parent.cref]

    if cfg.membership == "direct":
        return tuple(
            p for p in sections if p in matched_set or any(a in matched_set for a in ancestry(p))
        )
    return tuple(p for p in matched if not any(a in matched_set for a in ancestry(p)))


def _member_order(nodes, section_refs, section, membership):
    """Native body preorder for the explicit section membership, reused after mutation."""
    pointers = []

    def collect(pointer):
        item = nodes[pointer]
        if item.content_layer.value != "body" or (
            pointer != section and pointer in section_refs and membership == "direct"
        ):
            return
        pointers.append(pointer)
        for child in item.children:
            collect(child.cref)

    collect(section)
    return tuple(pointers)


def _drafts(
    document_id: int,
    native_product: ProductReference,
    native: NativeSnapshot,
    health: Mapping[str, Any],
    sections: tuple[str, ...],
    membership: Literal["direct", "descendants"],
    consumer_release: str,
    *,
    replacements: Mapping[tuple[str, str], int] | None = None,
    recognition_coverage: Sequence[Mapping[str, Any]] = (),
    document: Any = None,
    node_index: dict[str, Any] | None = None,
) -> tuple[SourceViewDraft, ...]:
    doc = load_snapshot(native) if document is None else document
    nodes = native_nodes(doc) if node_index is None else node_index
    section_refs = frozenset(p for p, n in nodes.items() if str(n.label) in {"section", "chapter"})
    recipe = canonical_bytes(
        {
            "recipe": "native-section-text-v3",
            "content_layers": ["body"],
            "organization_owner": native_product.values(),
        }
    )
    drafts = []
    for section in sections:
        projection = project_section(
            doc,
            native.digest,
            section,
            "direct" if membership == "direct" else "descendant",
            section_refs=section_refs,
            node_index=nodes,
        )
        item_refs = _member_order(nodes, section_refs, section, membership)
        ancestors = []
        item = nodes[section]
        while item.parent is not None:
            if item.parent.cref not in {"#/body", "#/furniture"}:
                ancestors.append(item.parent.cref)
            item = nodes[item.parent.cref]
        from corpus_structure.semantic.source_views import source_view_health

        view_health = source_view_health(
            health,
            section,
            membership,
            [nodes[p].model_dump(mode="json", by_alias=True) for p in item_refs],
            tuple(reversed(ancestors)),
            recognition_coverage=recognition_coverage,
        )
        key = (
            "source-view:"
            + sha256(
                canonical_bytes(
                    {
                        "consumer_release": consumer_release,
                        "native": native_product.values(),
                        "section": section,
                        "membership": membership,
                        "recipe": sha256(recipe).hexdigest(),
                    }
                )
            ).hexdigest()
        )
        drafts.append(
            SourceViewDraft(
                key,
                document_id,
                native_product,
                section,
                membership,
                projection.text,
                tuple(p.to_wire() for p in projection.pieces),
                tuple(item_refs),
                tuple(reversed(ancestors)),
                view_health,
                recipe,
                replaces_source_view_id=(replacements or {}).get((section, membership)),
            )
        )
    return tuple(drafts)


def _conversion_from_product(product, recipe_bytes: bytes) -> PdfConversion:
    values = product.values()
    candidates = tuple(
        CandidatePage(
            page["page_no"],
            page["has_words"],
            page["has_chars"],
            tuple(InlineCandidate.from_wire(candidate) for candidate in page["candidates"]),
            page.get("has_vectors", False),
            page.get("native_text_quality", "unassessed"),
            tuple(page.get("ocr_regions", ())),
        )
        for page in values.get("inline_candidate_pages", [])
    )
    return PdfConversion(
        values["artifact_digest"],
        recipe_bytes,
        _snapshot_from_values(values),
        values["health"]["conversion"],
        tuple(values["health"].get("issues", [])),
        tuple(
            FormulaOutcome(row["pointer"], row["outcome"], row.get("error"))
            for row in values["health"].get("formula_outcomes", [])
        ),
        tuple(
            (r["name"], r["version"]) for r in values.get("runtime_report", {}).get("packages", [])
        ),
        (values["page_start"], values["page_end"])
        if values.get("source_scope") == "page_range"
        else None,
        runtime=tuple(
            (r["name"], r["value"]) for r in values.get("runtime_report", {}).get("bindings", [])
        ),
        effective_options=values.get("runtime_report", {}).get("effective_options", "{}").encode(),
        inline_candidates=candidates,
        confidence=values.get("runtime_report", {}).get("confidence", "{}").encode(),
    )


class PdfEnrichConfig(PdfRuntimeConfig):
    # Released classification rules: a cell's nonempty recognition never establishes math.
    cell_math_pattern: str = (
        "(?:[=+\xd7\xf7\u2211\u220f\u222b\u221a\u221e\u2264\u2265\u2208\u2282\u222a\u2229^_\\\\]|"
        "(?<!\\w)[A-Za-z](?!\\w)|\\d)"
    )
    cell_prose_pattern: str = "[A-Za-z]{2,}(?:[\\s,;:'\u2019().-]+[A-Za-z]{2,})*[.!?]?"
    crop_padding_points: float = Field(default=0.75, ge=0)


class EnrichPdfMath:
    """One book-scoped native derivation, sharing its ingestion resource owner."""

    name = "enrich.pdf_math"
    version = "1"
    family = MethodFamily.INGEST
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.ENCODER
    confidence_source: ConfidenceSource | None = None
    Config = PdfEnrichConfig
    resources = Resources(worker="encoder", batch_size=1, max_concurrency=1)

    def __init__(self, producer: IngestPdf) -> None:
        self.producer = producer

    def original_recipe(self, cfg: PdfEnrichConfig) -> bytes:
        recipe, _ = self.producer._runtime(cfg)
        return canonical_bytes(
            {
                "recipe_id": "native-scoped-math-v1",
                "native_recipe": json.loads(recipe.to_bytes()),
                "candidate_policy": "native-font-token-vector-ocr-word-v3",
                "cells_policy": "all-nonempty-selected-cells-v1",
                "cell_math_pattern": cfg.cell_math_pattern,
                "cell_prose_pattern": cfg.cell_prose_pattern,
                "crop_padding_points": cfg.crop_padding_points,
                "crop_scale": 2.0,
            }
        )

    def select(self, run: SourceRunContext, cfg: PdfEnrichConfig) -> Iterable[UnitRef]:
        ids = list(dict.fromkeys(v.document_id for v in run.reader.source_views()))
        documents = table("kb.document")
        with run.reader.connection() as conn:
            rows = conn.execute(
                select(documents.c.id, documents.c.key)
                .where(documents.c.id.in_(ids))
                .order_by(documents.c.id)
            )
            return tuple(UnitRef(TaskUnitType.DOCUMENT, row.id, row.key) for row in rows)

    def input_digest(self, unit: UnitView, cfg: PdfEnrichConfig) -> Digest:
        views = [v for v in unit.run.reader.source_views() if v.document_id == unit.ref.unit_id]
        return Digest(
            canonical_bytes(
                {
                    "document": unit.ref.unit_id,
                    "views": [
                        {
                            "key": v.key,
                            "native": v.native_product.values(),
                            "projection": v.projection_digest,
                        }
                        for v in views
                    ],
                    "recipe": sha256(self.original_recipe(cfg)).hexdigest(),
                }
            )
        )

    def run(
        self, units: Sequence[UnitView], cfg: PdfEnrichConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        from .pdf import CellEnrichment
        from .pdf_enrichment import RecognitionUnavailable

        outputs = []
        release = _consumer_release(ctx)
        _require_enrichment_operation(ctx, release)
        for unit in units:
            try:
                views = [v for v in ctx.reader.source_views() if v.document_id == unit.ref.unit_id]
                if not views or unit.ref.unit_id is None:
                    raise RecognitionUnavailable(
                        "native enrichment requires selected intact source views"
                    )
                if (
                    len(
                        {
                            (
                                v.native_product.task_id,
                                v.native_product.product_key,
                                v.native_product.content_digest,
                            )
                            for v in views
                        }
                    )
                    != 1
                ):
                    raise RecognitionUnavailable(
                        "document enrichment requires a single pinned native source product"
                    )
                parent = views[0].native_product
                product = ctx.reader.native_document(parent)
                recipe_bytes = self.original_recipe(cfg)
                conversion = _conversion_from_product(product, recipe_bytes)
                document = load_snapshot(conversion.native)
                nodes = native_nodes(document)
                # Analysis units and ancestor context are separate rows over one shared product.
                specs = list(dict.fromkeys((v.section_pointer, v.membership) for v in views))
                for view in views:
                    current = nodes[view.section_pointer]
                    while current.parent is not None:
                        pointer = current.parent.cref
                        current = nodes[pointer]
                        if (
                            str(current.label) in {"section", "chapter"}
                            and (pointer, "direct") not in specs
                        ):
                            specs.append((pointer, "direct"))
                section_refs = frozenset(
                    p for p, n in nodes.items() if str(n.label) in {"section", "chapter"}
                )

                required_pages_by_scope = {
                    (section, membership): {
                        prov.page_no
                        for pointer in _member_order(nodes, section_refs, section, membership)
                        if str(nodes[pointer].label) in {"text", "list_item", "caption", "footnote"}
                        and not nodes[pointer].children
                        and nodes[pointer].text.strip()
                        for prov in getattr(nodes[pointer], "prov", ())
                    }
                    for section, membership in specs
                }
                selected = set().union(
                    *(
                        _member_order(nodes, section_refs, section, membership)
                        for section, membership in specs
                    )
                )
                recipe, assets = self.producer._runtime(cfg)
                worker = self.producer._worker(recipe, assets)
                computed = worker.enrich(
                    PdfEnrichmentRequest(
                        conversion,
                        product.original,
                        frozenset(selected),
                        cfg.cell_math_pattern,
                        cfg.cell_prose_pattern,
                        cfg.crop_padding_points,
                    ),
                    check_active=ctx.check_active,
                )
                conversion = dataclasses.replace(
                    conversion,
                    packages=computed.packages,
                    runtime=computed.runtime,
                    effective_options=computed.effective_options,
                    inline_candidates=computed.candidate_pages,
                )
                derived = computed.native
                document = load_snapshot(derived)
                nodes = native_nodes(document)
                reports = list(computed.cell_reports)
                enriched = CellEnrichment(
                    conversion.native.digest, derived, computed.outcomes, computed.mappings
                )
                payload = publication_payload(
                    conversion,
                    product_key="math-enriched",
                    schema_digest=sha256(product.schema_bytes).hexdigest(),
                    native=derived,
                    section_refs=section_refs,
                    parent=(parent.task_id, parent.product_key, parent.content_digest),
                    enrichment=enriched,
                )
                payload["cell_reports"] = reports
                # Whole-book native content is retained; only the declared rows close recognition.
                payload["health"].update(
                    inline_coverage="unknown",
                    cell_coverage="unknown",
                    candidate_policy="native-font-token-vector-ocr-word-v3",
                    cells_policy="all-nonempty-selected-cells-v1",
                )
                nodes = native_nodes(document)
                outcomes = {
                    row["pointer"]: row["outcome"] for row in payload["health"]["formula_outcomes"]
                }
                coverage = []
                for section, membership in specs:
                    pointers = _member_order(nodes, section_refs, section, membership)
                    formula_refs = [
                        pointer for pointer in pointers if str(nodes[pointer].label) == "formula"
                    ]
                    inline_refs = [
                        pointer
                        for pointer in formula_refs
                        if nodes[pointer].parent is not None
                        and str(nodes[nodes[pointer].parent.cref].label) == "inline"
                    ]
                    display_refs = [
                        pointer
                        for pointer in formula_refs
                        if nodes[pointer].parent is None
                        or str(nodes[nodes[pointer].parent.cref].label) not in {"inline", "table"}
                    ]
                    cell_rows = [row for row in reports if row["table_pointer"] in pointers]
                    candidate_pages = {page.page_no: page for page in conversion.inline_candidates}
                    required_pages = required_pages_by_scope[(section, membership)]
                    discovery_complete = all(
                        number in candidate_pages
                        and candidate_pages[number].usable_words
                        and candidate_pages[number].has_vectors
                        for number in required_pages
                    )
                    states = {
                        "display": all(
                            outcomes.get(pointer) == "succeeded" for pointer in display_refs
                        ),
                        "inline": discovery_complete
                        and all(outcomes.get(pointer) == "succeeded" for pointer in inline_refs),
                        "cell": all(
                            row["classification"] == "prose" or row["outcome"] == "succeeded"
                            for row in cell_rows
                        ),
                    }
                    policies = {
                        "display": "detected-native-display-v1",
                        "inline": "native-font-token-vector-ocr-word-v3",
                        "cell": "all-nonempty-selected-cells-v1",
                    }
                    coverage.extend(
                        dict(
                            section_pointer=section,
                            membership=membership,
                            universe=universe,
                            outcome="complete"
                            if complete and conversion.conversion_status == "success"
                            else "partial",
                            policy=policies[universe],
                        )
                        for universe, complete in states.items()
                    )
                payload["recognition_coverage"] = coverage
                prepared = ctx.reader.prepare_pdf_product(
                    payload, product.original, product.schema_bytes, recipe_bytes
                )
                reference = ctx.reader.native_product_reference(
                    unit.ref.unit_id, "math-enriched", prepared.digest
                )
                replacements: dict[tuple[str, str], int] = {
                    (v.section_pointer, v.membership): v.id for v in views
                }
                drafts = tuple(
                    draft
                    for section, membership in specs
                    for draft in _drafts(
                        unit.ref.unit_id,
                        reference,
                        derived,
                        payload["health"],
                        (section,),
                        membership,
                        release,
                        replacements=replacements,
                        recognition_coverage=coverage,
                        document=document,
                        node_index=nodes,
                    )
                )
                analysis_specs = {(v.section_pointer, v.membership) for v in views}
                drafts = tuple(
                    dataclasses.replace(
                        d, analysis_eligible=(d.section_pointer, d.membership) in analysis_specs
                    )
                    for d in drafts
                )
                outputs.append(
                    UnitResult(
                        ref=unit.ref,
                        outcome=ObservationOutcome.EMPTY,
                        native_products=(prepared,),
                        source_views=drafts,
                    )
                )
            except Exception as error:
                summary = _error_summary(error)
                ctx.logger.warning("enrich.pdf_math %s: %s", unit.ref.unit_id, summary)
                outputs.append(
                    UnitResult(ref=unit.ref, outcome=ObservationOutcome.FAILED, error=summary)
                )
        return outputs


def _require_enrichment_operation(ctx: MethodContext, release: str) -> None:
    from corpus_structure.semantic.contracts import require_database_operation

    with ctx.reader.connection() as conn:
        require_database_operation(conn, release, "enrich_pdf_math")
