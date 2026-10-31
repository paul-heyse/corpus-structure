"""Operational native PDF ingestion under the existing method/attempt lifecycle."""
from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable, Sequence, Mapping
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from typing import Literal, Any

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from sqlalchemy import select, text

from corpus_structure.core.method import (
    Digest, MethodContext, Resources, SourceRunContext, SourceViewDraft, UnitRef, UnitResult, UnitView,
)
from corpus_structure.core.vocab import ConfidenceSource, MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.parsing_products import ProductReference
from corpus_structure.semantic.metadata import table

from .pdf import PdfConverter, PdfRecipe, publication_payload
from .pdf_assets import PreparedPdfAssets, prepare_pdf_assets
from .pdf_hierarchy import NativeSnapshot, SectionPolicy, load_snapshot, native_nodes, organize, project_section


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
    section_rule: str = "native-organizational-headings-v2"
    section_pattern: str = r"^\d+(?:\.\d+)*\s*[:.)-]?\s+\S"
    organizational_heading_pattern: str = r"\S"
    local_heading_pattern: str = SectionPolicy("default").local_heading_pattern
    sections: tuple[str, ...] = ()
    membership: Literal["direct", "descendants"] = "direct"
    native_product: ProductReference | None = None

    def section_policy(self) -> SectionPolicy:
        return SectionPolicy(self.section_rule,self.section_pattern,
            organizational_pattern=self.organizational_heading_pattern,
            local_heading_pattern=self.local_heading_pattern)

    def recipe(self) -> PdfRecipe:
        return PdfRecipe(self.layout_revision, self.formula_revision, self.device, self.ocr_device,
                         self.parser_threads, self.stage_batch_size, self.timeout_seconds)


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
        self._prepared: dict[tuple[str,str], tuple[PdfRecipe, PreparedPdfAssets]] = {}
        self._workers: dict[str, PdfConverter] = {}

    def _runtime(self, cfg: PdfIngestConfig) -> tuple[PdfRecipe, PreparedPdfAssets]:
        base = cfg.recipe()
        key = (base.digest, str(cfg.model_cache.resolve()))
        if key not in self._prepared:
            assets = prepare_pdf_assets(base, cache=cfg.model_cache, offline=True)
            self._prepared[key] = (dataclasses.replace(base, model_artifacts=assets.files, model_revisions=assets.repositories), assets)
        return self._prepared[key]

    def original_recipe(self, cfg: PdfIngestConfig) -> bytes:
        """Preparation only; orchestration commits original custody before calling run."""
        if cfg.native_product is not None:
            return canonical_bytes({"recipe_id":"native-pdf-adoption-v1",
                                    "native_product":cfg.native_product.values()})
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
        consumer_release = _consumer_release(ctx)
        outputs = []
        for unit in units:
            if unit.ref.unit_id is None:
                raise ValueError("native PDF unit requires original document id")
            try:
                if cfg.native_product is not None:
                    # Explicit sanctioned adoption is not conversion or a new native producer.
                    archived = ctx.reader.native_document(cfg.native_product)
                    values = archived.values()
                    if values.get("source_scope") != "whole_document" or values['health']['conversion']!='success':
                        raise ValueError("PDF adoption requires a complete whole-document native product")
                    native = _snapshot_from_values(values)
                    doc=load_snapshot(native)
                    nodes=native_nodes(doc)
                    sections=_select_sections(nodes,cfg)
                    drafts=_drafts(unit.ref.unit_id,cfg.native_product,native,values['health'],
                                   sections,cfg.membership,consumer_release)
                    outputs.append(UnitResult(ref=unit.ref,outcome=ObservationOutcome.EMPTY,
                                              source_views=drafts))
                    continue
                recipe,assets=self._runtime(cfg)
                converter=self._workers.setdefault(recipe.digest,PdfConverter(recipe,assets=assets))
                schema_bytes=files("corpus_structure").joinpath("model","semantic","docling-validation.schema.json").read_bytes()
                schema_digest=sha256(schema_bytes).hexdigest()
                original=ctx.reader.original(unit.ref.unit_id)
                conversion=converter.convert_bytes(original)
                raw_payload=publication_payload(conversion,product_key="native",schema_digest=schema_digest)
                raw=ctx.reader.prepare_pdf_product(raw_payload,original,schema_bytes,conversion.recipe)
                raw_ref=ctx.reader.native_product_reference(unit.ref.unit_id,"native",raw.digest)
                organization=organize(conversion.native,cfg.section_policy())
                section_refs=frozenset(s.group_ref for s in organization.sections)
                organized_payload=publication_payload(conversion,product_key="organized",
                    schema_digest=schema_digest,native=organization.document,section_refs=section_refs,
                    parent=(raw_ref.task_id,raw_ref.product_key,raw_ref.content_digest))
                organized=ctx.reader.prepare_pdf_product(organized_payload,original,schema_bytes,conversion.recipe)
                organized_ref=ctx.reader.native_product_reference(unit.ref.unit_id,"organized",organized.digest)
                doc=load_snapshot(organization.document)
                drafts=_drafts(unit.ref.unit_id,organized_ref,organization.document,
                    organized_payload['health'],_select_sections(native_nodes(doc),cfg),
                    cfg.membership,consumer_release)
                outputs.append(UnitResult(ref=unit.ref,outcome=ObservationOutcome.EMPTY,
                    native_products=(raw,organized),source_views=drafts))
            except Exception as error:
                ctx.logger.warning("ingest.pdf %s: %s",unit.ref.unit_key,error)
                outputs.append(UnitResult(ref=unit.ref,outcome=ObservationOutcome.FAILED,
                    error=f"{type(error).__name__}: {error}"))
        return outputs


def _consumer_release(ctx: MethodContext) -> str:
    runs=table('ops.run')
    with ctx.reader.connection() as conn:
        return conn.execute(select(runs.c.release_id).where(runs.c.id==ctx.run.run_id)).scalar_one()


def _snapshot_from_values(values: Mapping[str,Any]) -> NativeSnapshot:
    from .pdf_hierarchy import NativeSnapshot
    payload=json.dumps(values['document'],ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return NativeSnapshot(payload,sha256(payload).hexdigest(),values['native_schema_version'])


def _select_sections(nodes: Mapping[str,Any],cfg:PdfIngestConfig) -> tuple[str,...]:
    sections=[p for p,n in nodes.items() if str(n.label) in {'section','chapter'}]
    matched=[p for p in sections if not cfg.sections or p in cfg.sections or nodes[p].name in cfg.sections]
    if cfg.sections and len(matched)!=len(set(cfg.sections)):
        raise ValueError('requested intact section selection is missing or ambiguous')
    matched_set=set(matched)
    def ancestry(pointer):
        node=nodes[pointer]
        while node.parent is not None:
            yield node.parent.cref
            node=nodes[node.parent.cref]
    if cfg.membership=='direct':
        return tuple(p for p in sections if p in matched_set or any(a in matched_set for a in ancestry(p)))
    return tuple(p for p in matched if not any(a in matched_set for a in ancestry(p)))


def _drafts(document_id: int,native_product: ProductReference,native: NativeSnapshot,
            health: Mapping[str,Any],sections: tuple[str,...],membership: Literal["direct","descendants"],
            consumer_release: str,*,replacements: Mapping[tuple[str,str],int]|None=None) -> tuple[SourceViewDraft,...]:
    doc=load_snapshot(native)
    nodes=native_nodes(doc)
    section_refs=frozenset(p for p,n in nodes.items() if str(n.label) in {'section','chapter'})
    recipe=canonical_bytes({'recipe':'native-section-text-v3','content_layers':['body'],
                            'organization_owner':native_product.values()})
    drafts=[]
    for section in sections:
        projection=project_section(doc,native.digest,section,
            'direct' if membership=='direct' else 'descendant',section_refs=section_refs,node_index=nodes)
        item_refs=[]
        def collect(pointer):
            item=nodes[pointer]
            if item.content_layer.value!='body' or (pointer!=section and pointer in section_refs and membership=='direct'):
                return
            item_refs.append(pointer)
            for child in item.children:
                collect(child.cref)
        collect(section)
        ancestors=[]
        item=nodes[section]
        while item.parent is not None:
            if item.parent.cref not in {'#/body','#/furniture'}:
                ancestors.append(item.parent.cref)
            item=nodes[item.parent.cref]
        selected=set(item_refs)
        view_health={**health,'formula_outcomes':[o for o in health.get('formula_outcomes',[]) if o['pointer'] in selected]}
        key='source-view:'+sha256(canonical_bytes({'consumer_release':consumer_release,
            'native':native_product.values(),'section':section,'membership':membership,
            'recipe':sha256(recipe).hexdigest()})).hexdigest()
        drafts.append(SourceViewDraft(key,document_id,native_product,section,membership,projection.text,
            tuple(dataclasses.asdict(p) for p in projection.pieces),tuple(item_refs),tuple(reversed(ancestors)),
            view_health,recipe,replaces_source_view_id=(replacements or {}).get((section,membership))))
    return tuple(drafts)
