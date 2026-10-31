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

from .pdf import PdfConversion, PdfConverter, PdfRecipe, publication_payload, pdf_package_versions
from .pdf_health import FormulaOutcome
from .pdf_candidates import CandidatePage, InlineCandidate
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
                                    "native_product":cfg.native_product.values(),
                                    "section_policy":{"rule_id":cfg.section_rule,
                                        "organizational_pattern":cfg.organizational_heading_pattern,
                                        "local_heading_pattern":cfg.local_heading_pattern,
                                        "numbered_pattern":cfg.section_pattern}})
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
            retained_native = ()
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
                    selected_product=cfg.native_product
                    products=()
                    if not any(str(n.label) in {'section','chapter'} for n in nodes.values()):
                        # A successful conversion remains reusable if a previous organization failed.
                        organization=organize(native,cfg.section_policy())
                        adopted_recipe=self.original_recipe(cfg)
                        conversion=_conversion_from_product(archived,adopted_recipe)
                        payload=publication_payload(conversion,product_key='organized',
                            schema_digest=sha256(archived.schema_bytes).hexdigest(),native=organization.document,
                            section_refs=frozenset(s.group_ref for s in organization.sections),
                            parent=(cfg.native_product.task_id,cfg.native_product.product_key,cfg.native_product.content_digest))
                        current=ctx.reader.prepare_pdf_product(payload,archived.original,archived.schema_bytes,adopted_recipe)
                        products=(current,)
                        selected_product=ctx.reader.native_product_reference(unit.ref.unit_id,'organized',current.digest)
                        native=organization.document
                        values=payload
                        nodes=native_nodes(load_snapshot(native))
                    sections=_select_sections(nodes,cfg)
                    drafts=_drafts(unit.ref.unit_id,selected_product,native,values['health'],
                                   sections,cfg.membership,consumer_release)
                    outputs.append(UnitResult(ref=unit.ref,outcome=ObservationOutcome.EMPTY,
                                              native_products=products,source_views=drafts))
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
                retained_native = (raw,)
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
                    error=f"{type(error).__name__}: {error}",native_products=retained_native))
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
    if not sections:
        raise ValueError('native product has no qualified organizational sections; organize it before adoption')
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
        from corpus_structure.semantic.source_views import source_view_health
        view_health=source_view_health(health,section,membership,
            [nodes[p].model_dump(mode='json',by_alias=True) for p in item_refs],tuple(reversed(ancestors)))
        key='source-view:'+sha256(canonical_bytes({'consumer_release':consumer_release,
            'native':native_product.values(),'section':section,'membership':membership,
            'recipe':sha256(recipe).hexdigest()})).hexdigest()
        drafts.append(SourceViewDraft(key,document_id,native_product,section,membership,projection.text,
            tuple(dataclasses.asdict(p) for p in projection.pieces),tuple(item_refs),tuple(reversed(ancestors)),
            view_health,recipe,replaces_source_view_id=(replacements or {}).get((section,membership))))
    return tuple(drafts)


def _conversion_from_product(product,recipe_bytes:bytes) -> PdfConversion:
    values=product.values()
    candidates=tuple(CandidatePage(page['page_no'],page['has_words'],page['has_chars'],
        tuple(InlineCandidate(**candidate) for candidate in page['candidates']),page.get('has_vectors',False))
        for page in values.get('inline_candidate_pages',[]))
    return PdfConversion(values['artifact_digest'],recipe_bytes,_snapshot_from_values(values),
        values['health']['conversion'],tuple(values['health'].get('issues',[])),
        tuple(FormulaOutcome(row['pointer'],row['outcome'],row.get('error'))
              for row in values['health'].get('formula_outcomes',[])),
        tuple((r['name'],r['version']) for r in values.get('runtime_report',{}).get('packages',[])),
        (values['page_start'],values['page_end']) if values.get('source_scope')=='page_range' else None,
        runtime=tuple((r['name'],r['value']) for r in values.get('runtime_report',{}).get('bindings',[])),
        effective_options=values.get('runtime_report',{}).get('effective_options','{}').encode(),
        inline_candidates=candidates,
        confidence=values.get('runtime_report',{}).get('confidence','{}').encode())

class PdfEnrichConfig(PdfIngestConfig):
    # Released classification rules: a cell's nonempty recognition never establishes math.
    cell_math_pattern: str = r"(?:[=+×÷∑∏∫√∞≤≥∈⊂∪∩^_\\]|(?<!\w)[A-Za-z](?!\w)|\d)"
    cell_prose_pattern: str = r"[A-Za-z]{2,}(?:[\s,;:'’().-]+[A-Za-z]{2,})*[.!?]?"
    crop_padding_points: float = Field(default=0.75,ge=0)


class EnrichPdfMath:
    """One book-scoped native derivation, sharing its ingestion resource owner."""
    name='enrich.pdf_math'
    version='1'
    family=MethodFamily.INGEST
    unit_type=TaskUnitType.DOCUMENT
    tier=MethodTier.ENCODER
    confidence_source: ConfidenceSource|None=None
    Config=PdfEnrichConfig
    resources=Resources(worker='encoder',batch_size=1,max_concurrency=1)

    def __init__(self, producer: IngestPdf) -> None:
        self.producer=producer

    def original_recipe(self,cfg:PdfEnrichConfig)->bytes:
        recipe,_=self.producer._runtime(cfg)
        return canonical_bytes({'recipe_id':'native-scoped-math-v1','native_recipe':json.loads(recipe.to_bytes()),
            'candidate_policy':'native-font-token-vector-v2','cells_policy':'all-nonempty-selected-cells-v1',
            'cell_math_pattern':cfg.cell_math_pattern,'cell_prose_pattern':cfg.cell_prose_pattern,
            'crop_padding_points':cfg.crop_padding_points,'crop_scale':2.0})

    def select(self,run:SourceRunContext,cfg:PdfEnrichConfig)->Iterable[UnitRef]:
        ids=list(dict.fromkeys(v.document_id for v in run.reader.source_views()))
        documents=table('kb.document')
        with run.reader.connection() as conn:
            rows=conn.execute(select(documents.c.id,documents.c.key).where(documents.c.id.in_(ids)).order_by(documents.c.id))
            return tuple(UnitRef(TaskUnitType.DOCUMENT,row.id,row.key) for row in rows)

    def input_digest(self,unit:UnitView,cfg:PdfEnrichConfig)->Digest:
        views=[v for v in unit.run.reader.source_views() if v.document_id==unit.ref.unit_id]
        return Digest(canonical_bytes({'document':unit.ref.unit_id,
            'views':[{'key':v.key,'native':v.native_product.values(),'projection':v.projection_digest} for v in views],
            'recipe':sha256(self.original_recipe(cfg)).hexdigest()}))

    def run(self,units:Sequence[UnitView],cfg:PdfEnrichConfig,ctx:MethodContext)->Sequence[UnitResult]:
        from .pdf import CellEnrichment,apply_cells
        from .pdf_enrichment import (PdfRegionRenderer,RecognitionUnavailable,apply_inline,classify_cells,
                                     positioned_inline_candidates,table_candidates)
        from .pdf_hierarchy import snapshot
        outputs=[]
        release=_consumer_release(ctx)
        for unit in units:
            try:
                views=[v for v in ctx.reader.source_views() if v.document_id==unit.ref.unit_id]
                if not views or unit.ref.unit_id is None:
                    raise RecognitionUnavailable('native enrichment requires selected intact source views')
                if len({(v.native_product.task_id,v.native_product.product_key,v.native_product.content_digest) for v in views})!=1:
                    raise RecognitionUnavailable('document enrichment requires a single pinned native source product')
                if len({v.membership for v in views})!=1:
                    raise RecognitionUnavailable('document enrichment requires one declared membership policy')
                parent=views[0].native_product
                product=ctx.reader.native_document(parent)
                recipe_bytes=self.original_recipe(cfg)
                conversion=_conversion_from_product(product,recipe_bytes)
                document=load_snapshot(conversion.native)
                nodes=native_nodes(document)
                sections=list(dict.fromkeys(v.section_pointer for v in views))
                # Context sections use the same new product, preserving pointer qualification.
                for view in views:
                    current=nodes[view.section_pointer]
                    while current.parent is not None:
                        pointer=current.parent.cref
                        current=nodes[pointer]
                        if str(current.label) in {'section','chapter'} and pointer not in sections:
                            sections.append(pointer)
                membership=views[0].membership
                selected=set()
                section_refs=frozenset(p for p,n in nodes.items() if str(n.label) in {'section','chapter'})
                def collect(pointer,root):
                    item=nodes[pointer]
                    if item.content_layer.value!='body' or (pointer!=root and pointer in section_refs and membership=='direct'):
                        return
                    selected.add(pointer)
                    for child in item.children:
                        collect(child.cref,root)
                for section in sections:
                    collect(section,section)
                pages={p.page_no:p for p in conversion.inline_candidates}
                required_pages={prov.page_no for pointer in selected for prov in getattr(nodes[pointer],'prov',())}
                if any(p not in pages or not pages[p].has_words for p in required_pages):
                    raise RecognitionUnavailable('selected native pages lack attributable candidate discovery')
                cells=table_candidates(document,frozenset(selected))
                demanded,reports=classify_cells(document,cells,conversion.inline_candidates,
                    math_pattern=cfg.cell_math_pattern,prose_pattern=cfg.cell_prose_pattern)
                inline=positioned_inline_candidates(document,conversion.inline_candidates,frozenset(selected))
                recipe,assets=self.producer._runtime(cfg)
                converter=self.producer._workers.setdefault(recipe.digest,PdfConverter(recipe,assets=assets))
                stage=converter.formula_stage()
                with PdfRegionRenderer(product.original,padding_points=cfg.crop_padding_points) as renderer:
                    cell_outcomes,cell_mappings=apply_cells(document,demanded,stage=stage,render_region=renderer)
                    inline_outcomes,inline_mappings=apply_inline(document,inline,stage=stage,render_region=renderer)
                outcome_by_ref={o.item_ref:o for o in conversion.formula_outcomes+cell_outcomes}
                mapping_by_cell={(m['origin_pointer'],m['cell_index']):m for m in cell_mappings}
                for report in reports:
                    if report.get('formula_pointer') in outcome_by_ref:
                        report['outcome']=outcome_by_ref[report['formula_pointer']].outcome
                    mapped=mapping_by_cell.get((report['table_pointer'],report['cell_index']))
                    if mapped is not None:
                        outcome=outcome_by_ref[mapped['pointer']]
                        report.update(formula_pointer=mapped['pointer'],outcome=outcome.outcome)
                        if outcome.error:
                            report['error']=outcome.error
                conversion=dataclasses.replace(conversion,
                    packages=pdf_package_versions(),
                    runtime=converter.runtime_bindings(),effective_options=recipe.options().model_dump_json(serialize_as_any=True).encode())
                derived=snapshot(document)
                enriched=CellEnrichment(conversion.native.digest,derived,cell_outcomes+inline_outcomes,
                    cell_mappings+inline_mappings)
                payload=publication_payload(conversion,product_key='math-enriched',
                    schema_digest=sha256(product.schema_bytes).hexdigest(),native=derived,
                    section_refs=section_refs,parent=(parent.task_id,parent.product_key,parent.content_digest),enrichment=enriched)
                payload['cell_reports']=reports
                inline_complete=all(o.outcome=='succeeded' for o in inline_outcomes)
                cells_complete=all(r['classification']=='prose' or r['outcome']=='succeeded' for r in reports)
                payload['health'].update(inline_coverage='complete' if inline_complete else 'partial',
                    cell_coverage='complete' if cells_complete else 'partial',candidate_policy='native-font-token-vector-v2',
                    cells_policy='all-nonempty-selected-cells-v1',inline_scope=sections,cell_scope=sections,
                    inline_membership=membership,cell_membership=membership)
                prepared=ctx.reader.prepare_pdf_product(payload,product.original,product.schema_bytes,recipe_bytes)
                reference=ctx.reader.native_product_reference(unit.ref.unit_id,'math-enriched',prepared.digest)
                replacements: dict[tuple[str,str],int]={(v.section_pointer,v.membership):v.id for v in views}
                drafts=_drafts(unit.ref.unit_id,reference,derived,payload['health'],tuple(sections),membership,
                    release,replacements=replacements)
                # Only the original scope units are analysis-eligible. Context remains available to M13.
                analysis_sections={v.section_pointer for v in views}
                drafts=tuple(dataclasses.replace(d,analysis_eligible=d.section_pointer in analysis_sections) for d in drafts)
                outputs.append(UnitResult(ref=unit.ref,outcome=ObservationOutcome.EMPTY,
                    native_products=(prepared,),source_views=drafts))
            except Exception as error:
                ctx.logger.warning('enrich.pdf_math %s: %s',unit.ref.unit_id,error)
                outputs.append(UnitResult(ref=unit.ref,outcome=ObservationOutcome.FAILED,error=f'{type(error).__name__}: {error}'))
        return outputs
