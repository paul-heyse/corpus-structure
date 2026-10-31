"""Operational native PDF ingestion under the existing method/attempt lifecycle."""
from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable, Sequence
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from corpus_structure.core.method import (
    Digest, MethodContext, Resources, SourceRunContext, SourceViewDraft, UnitRef, UnitResult, UnitView,
)
from corpus_structure.core.vocab import ConfidenceSource, MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.identity import canonical_bytes

from .pdf import PdfConverter, PdfRecipe, publication_payload
from .pdf_assets import PreparedPdfAssets, prepare_pdf_assets
from .pdf_hierarchy import SectionPolicy, load_snapshot, native_nodes, organize, project_section


class PdfIngestConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    originals: tuple[str, ...] = ("siegrist_random/Full_PDF/Full.pdf",)
    layout_revision: str = "8f39ad3c0b4c58e9c2d2c84a38465abf757272d8"
    formula_revision: str = "ecedbe111d15c2dc60bfd4a823cbe80127b58af4"
    model_cache: Path = Field(default_factory=lambda: Path.home()/".cache/docling/models")
    device: Literal["cpu", "cuda"] = "cuda"
    ocr_device: Literal["cpu", "cuda"] = "cpu"
    timeout_seconds: float | None = None
    parser_threads: int = Field(default=8, ge=1)
    stage_batch_size: int = Field(default=4, ge=1)
    section_rule: str = "numbered-book-sections-v1"
    section_pattern: str = r"^\d+(?:\.\d+)*\s*[:.)-]?\s+\S"
    sections: tuple[str, ...] = ()
    membership: Literal["direct", "descendants"] = "direct"

    def recipe(self) -> PdfRecipe:
        return PdfRecipe(self.layout_revision, self.formula_revision, self.device, self.ocr_device,
                         self.parser_threads, self.stage_batch_size, self.timeout_seconds)


class IngestPdf:
    name = "ingest.pdf"
    version = "1"
    family = MethodFamily.INGEST
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = None
    Config = PdfIngestConfig
    resources = Resources(worker="encoder", batch_size=1, max_concurrency=1)

    def __init__(self) -> None:
        self._prepared: dict[PdfIngestConfig, tuple[PdfRecipe, PreparedPdfAssets]] = {}
        self._workers: dict[str, PdfConverter] = {}

    def _runtime(self, cfg: PdfIngestConfig) -> tuple[PdfRecipe, PreparedPdfAssets]:
        if cfg not in self._prepared:
            base = cfg.recipe()
            assets = prepare_pdf_assets(base, cache=cfg.model_cache, offline=True)
            self._prepared[cfg] = (dataclasses.replace(base, model_artifacts=assets.files, model_revisions=assets.repositories), assets)
        return self._prepared[cfg]

    def original_recipe(self, cfg: PdfIngestConfig) -> bytes:
        """Preparation only; orchestration commits original custody before calling run."""
        recipe, _ = self._runtime(cfg)
        return recipe.to_bytes()

    def select(self, run: SourceRunContext, cfg: PdfIngestConfig) -> Iterable[UnitRef]:
        corpus = run.options.get("corpus")
        listed = corpus.get("documents") if isinstance(corpus, dict) else None
        keys = [str(k) for k in listed] if isinstance(listed, list) else []
        with run.reader.connection() as conn:
            rows = conn.execute(text("SELECT d.id,d.key FROM kb.document d JOIN ops.run r "
                "ON r.project_id=d.project_id WHERE r.id=:run AND d.key=ANY(:keys) "
                "AND d.source_uri=ANY(:sources) ORDER BY d.key"),
                dict(run=run.run_id, keys=keys, sources=list(cfg.originals)))
            return [UnitRef(TaskUnitType.DOCUMENT, int(r.id), str(r.key)) for r in rows]

    def input_digest(self, unit: UnitView, cfg: PdfIngestConfig) -> Digest:
        if unit.ref.unit_key is None:
            raise ValueError("native PDF unit requires its retained document key")
        return Digest(canonical_bytes({"document": unit.ref.unit_key,
                                      "recipe": sha256(self.original_recipe(cfg)).hexdigest()}))

    def run(self, units: Sequence[UnitView], cfg: PdfIngestConfig,
            ctx: MethodContext) -> Sequence[UnitResult]:
        recipe, assets = self._runtime(cfg)
        converter = self._workers.setdefault(recipe.digest, PdfConverter(recipe, assets=assets))
        schema_bytes = files("corpus_structure").joinpath("model", "semantic", "docling-validation.schema.json").read_bytes()
        schema_digest = sha256(schema_bytes).hexdigest()
        outputs = []
        for unit in units:
            if unit.ref.unit_id is None:
                raise ValueError("native PDF unit requires original document id")
            try:
                original = ctx.reader.original(unit.ref.unit_id)
                conversion = converter.convert_bytes(original)
                raw_payload = publication_payload(conversion, product_key="native", schema_digest=schema_digest)
                raw = ctx.reader.prepare_pdf_product(raw_payload, original, schema_bytes, conversion.recipe)
                raw_ref = ctx.reader.native_product_reference(unit.ref.unit_id, "native", raw.digest)
                organization = organize(conversion.native, SectionPolicy(cfg.section_rule, cfg.section_pattern))
                section_refs = frozenset(s.group_ref for s in organization.sections)
                organized_payload = publication_payload(conversion, product_key="organized",
                    schema_digest=schema_digest, native=organization.document, section_refs=section_refs,
                    parent=(raw_ref.task_id, raw_ref.product_key, raw_ref.content_digest))
                organized = ctx.reader.prepare_pdf_product(organized_payload, original, schema_bytes, conversion.recipe)
                organized_ref = ctx.reader.native_product_reference(unit.ref.unit_id, "organized", organized.digest)
                document = load_snapshot(organization.document)
                nodes = native_nodes(document)
                selected = [s for s in organization.sections if not cfg.sections or
                            s.group_ref in cfg.sections or nodes[s.heading_ref].text in cfg.sections]
                if cfg.sections and len(selected) != len(set(cfg.sections)):
                    raise ValueError("requested intact section selection is missing or ambiguous")
                drafts = []
                projection_recipe = canonical_bytes({"recipe": "native-section-text-v1",
                    "content_layers":["body"],"section_policy": {"rule_id":cfg.section_rule,"numbered_pattern":cfg.section_pattern,"organizational_refs":[]}})
                for section in selected:
                    projection = project_section(document, organization.document.digest,
                        section.group_ref, "direct" if cfg.membership=="direct" else "descendant",
                        section_refs=section_refs, node_index=nodes)
                    item_refs = []
                    def collect(pointer: str) -> None:
                        node = nodes[pointer]
                        if node.content_layer.value != "body":
                            return
                        if pointer != section.group_ref and pointer in section_refs and cfg.membership=="direct":
                            return
                        item_refs.append(pointer)
                        for child in node.children:
                            collect(child.cref)
                    collect(section.group_ref)
                    ancestors = []
                    owner = nodes[section.group_ref]
                    while owner.parent is not None:
                        if owner.parent.cref not in {"#/body", "#/furniture"}:
                            ancestors.append(owner.parent.cref)
                        owner = nodes[owner.parent.cref]
                    key = "source-view:"+sha256(canonical_bytes({"native":organized.digest,
                        "section":section.group_ref,"membership":cfg.membership,
                        "recipe":sha256(projection_recipe).hexdigest()})).hexdigest()
                    drafts.append(SourceViewDraft(key, unit.ref.unit_id, organized_ref,
                        section.group_ref,cfg.membership,projection.text,
                        tuple(dataclasses.asdict(p) for p in projection.pieces),tuple(item_refs),
                        tuple(reversed(ancestors)),organized_payload['health'],projection_recipe))
                outputs.append(UnitResult(ref=unit.ref,outcome=ObservationOutcome.EMPTY,
                    native_products=(raw,organized),source_views=tuple(drafts)))
            except Exception as error:
                ctx.logger.warning("ingest.pdf %s: %s", unit.ref.unit_key,error)
                outputs.append(UnitResult(ref=unit.ref,outcome=ObservationOutcome.FAILED,
                    error=f"{type(error).__name__}: {error}"))
        return outputs
