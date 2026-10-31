"""Demanded native math enrichment; retained PDF and native products remain the source owners."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .pdf import CellCandidate, CellEnrichment
from .pdf_candidates import CandidatePage, InlineCandidate
from .pdf_health import ObservedFormulaStage
from .pdf_hierarchy import NativeSnapshot, load_snapshot, native_nodes, snapshot


class RecognitionUnavailable(ValueError):
    """A required native candidate cannot yet be qualified; never successful empty coverage."""


class PdfRegionRenderer:
    """One owned PDF renderer, at most one detached page image live between crops."""
    def __init__(self, original: bytes, *, scale: float = 2.0, padding_points: float = 0.75) -> None:
        import pypdfium2
        self.document = pypdfium2.PdfDocument(original)
        self.scale = scale
        self.padding_points = padding_points
        self._page_no: int | None = None
        self._image: Any = None

    def __enter__(self) -> PdfRegionRenderer:
        return self

    def __exit__(self, *args: Any) -> None:
        if self._image is not None:
            self._image.close()
        self.document.close()

    def __call__(self, page_no: int, bbox: Any) -> Any:
        if self._page_no != page_no:
            if self._image is not None:
                self._image.close()
            page = self.document[page_no-1]
            try:
                bitmap = page.render(scale=self.scale)
                try:
                    self._image = bitmap.to_pil().copy()
                finally:
                    bitmap.close()
            finally:
                page.close()
            self._page_no = page_no
        height = self._image.height/self.scale
        box = bbox.to_top_left_origin(height)
        box = box.model_copy(update=dict(l=box.l-self.padding_points,t=box.t-self.padding_points,
                                        r=box.r+self.padding_points,b=box.b+self.padding_points))
        left=max(0,int(box.l*self.scale)); top=max(0,int(box.t*self.scale))
        right=min(self._image.width,int(box.r*self.scale)+1)
        bottom=min(self._image.height,int(box.b*self.scale)+1)
        if left >= right or top >= bottom:
            raise RecognitionUnavailable('native math candidate has an empty PDF crop')
        return self._image.crop((left,top,right,bottom))


def table_candidates(document: Any, selected: frozenset[str]) -> tuple[CellCandidate,...]:
    """Every nonempty cell in selected native tables, without a mathematical-looking filter."""
    nodes=native_nodes(document)
    candidates=[]
    for pointer in selected:
        item=nodes[pointer]
        if not hasattr(item,'data') or not hasattr(item.data,'table_cells'):
            continue
        for index,cell in enumerate(item.data.table_cells):
            if not cell.text.strip() or getattr(cell,'ref',None) is not None:
                continue
            if cell.bbox is None:
                raise RecognitionUnavailable('nonempty table cell has no native crop geometry')
            pages={p.page_no for p in item.prov}
            if len(pages)!=1:
                raise RecognitionUnavailable('cell page correspondence is ambiguous in a multi-page native table')
            candidates.append(CellCandidate(pointer,index,next(iter(pages))))
    return tuple(sorted(candidates,key=lambda c:(c.page_no,c.table_ref,c.cell_index)))


@dataclass(frozen=True, slots=True)
class PositionedCandidate:
    item_ref: str
    start: int
    end: int
    candidate: InlineCandidate
    regions: tuple[InlineCandidate,...] = ()


def positioned_inline_candidates(document: Any, pages: tuple[CandidatePage,...],
                                selected: frozenset[str]) -> tuple[PositionedCandidate,...]:
    """Bind retained native candidates to exact native-text occurrences, refusing ambiguity."""
    nodes=native_nodes(document)
    grouped: dict[tuple[str,str],list[InlineCandidate]]=defaultdict(list)
    by_page: dict[int,list[Any]]=defaultdict(list)
    for pointer in selected:
        item=nodes[pointer]
        if str(item.label) not in {'text','list_item','caption','footnote'} or item.children:
            continue
        for prov in item.prov:
            by_page[prov.page_no].append((item,prov))
    for page in pages:
        if page.page_no in by_page and not page.has_words:
            raise RecognitionUnavailable('inline discovery lacks computed native word cells')
        for candidate in page.candidates:
            matches=[]
            for item,prov in by_page.get(page.page_no,()):
                box=prov.bbox.to_top_left_origin(document.pages[page.page_no].size.height)
                top,bottom=(candidate.top,candidate.bottom)
                if candidate.origin=='BOTTOMLEFT':
                    height=document.pages[page.page_no].size.height
                    top,bottom=height-candidate.top,height-candidate.bottom
                center_x=(candidate.left+candidate.right)/2
                center_y=(top+bottom)/2
                if box.l<=center_x<=box.r and min(box.t,box.b)<=center_y<=max(box.t,box.b):
                    matches.append(item)
            unique={item.self_ref:item for item in matches}
            if len(unique)>1:
                raise RecognitionUnavailable('inline candidate belongs to overlapping native text items')
            if unique:
                item=next(iter(unique.values()))
                grouped[(item.self_ref,candidate.text)].append(candidate)
    positioned=[]
    for (pointer,spelling),candidates in grouped.items():
        # Whole-word boundaries avoid matching a variable inside a prose identifier.
        pattern=(r'(?<!\w)'+re.escape(spelling)+r'(?!\w)' if spelling.isalnum() else re.escape(spelling)) if spelling else r'\s*'
        offsets=list(re.finditer(pattern,nodes[pointer].text))
        if spelling and len(offsets)==len(candidates):
            positioned.extend(PositionedCandidate(pointer,m.start(),m.end(),candidate)
                              for m,candidate in zip(offsets,candidates,strict=True))
            continue
        for candidate in candidates:
            def context_pattern(value: str) -> str:
                return r"\s+".join(re.escape(word) for word in value.split())
            before=context_pattern(candidate.before)
            after=context_pattern(candidate.after)
            qualified=(before+r"\s*" if before else '')+r"(?P<math>"+pattern+r")"+(r"\s*"+after if after else '')
            matches=list(re.finditer(qualified,nodes[pointer].text))
            if len(matches)!=1:
                raise RecognitionUnavailable(f'native inline text/geometry correspondence requires further alignment: {pointer} {spelling!r}')
            positioned.append(PositionedCandidate(pointer,matches[0].start('math'),matches[0].end('math'),candidate))
    by_anchor: dict[tuple[str,int,int],list[PositionedCandidate]]=defaultdict(list)
    for part in positioned:
        by_anchor[(part.item_ref,part.start,part.end)].append(part)
    merged=[]
    for (pointer,start,end),parts in by_anchor.items():
        regions=tuple(sorted((part.candidate for part in parts),key=lambda c:(c.page_no,c.top,c.left)))
        merged.append(PositionedCandidate(pointer,start,end,regions[0],regions if len(regions)>1 else ()))
    return tuple(sorted(merged,key=lambda c:(c.item_ref,c.start,c.end)))


def enrich_inline(source: NativeSnapshot, candidates: tuple[PositionedCandidate,...], *,
                  stage: ObservedFormulaStage, render_region: Any) -> CellEnrichment:
    from docling.datamodel.base_models import ItemAndImageEnrichmentElement
    from docling_core.types.doc import BoundingBox,CoordOrigin,DocItemLabel,ProvenanceItem
    document=load_snapshot(source)
    outcomes,mappings=apply_inline(document,candidates,stage=stage,render_region=render_region)
    return CellEnrichment(source.digest,snapshot(document),outcomes,mappings)


def apply_inline(document: Any,candidates: tuple[PositionedCandidate,...],*,
                 stage: ObservedFormulaStage,render_region: Any):
    """Apply selected inline decomposition within one owned document-enrichment operation."""
    from docling.datamodel.base_models import ItemAndImageEnrichmentElement
    from docling_core.types.doc import BoundingBox,CoordOrigin,DocItemLabel,ProvenanceItem
    nodes=native_nodes(document)
    grouped: dict[str,list[PositionedCandidate]]=defaultdict(list)
    for candidate in candidates:
        grouped[candidate.item_ref].append(candidate)
    start=len(stage.outcomes)
    pending=[]
    mappings=[]
    for pointer,parts in grouped.items():
        item=nodes[pointer]
        original=item.text
        previous=0
        for part in parts:
            source_span=original[part.start:part.end]
            vector_anchor=part.candidate.basis=='native-vector-gap-v1' and not source_span.strip()
            if part.start<previous or (not vector_anchor and source_span!=part.candidate.text):
                raise RecognitionUnavailable('inline candidate offsets overlap or differ from native text')
            previous=part.end
        group=document.add_inline_group(parent=item)
        item.text=''  # Raw original stays in the parent product and this item's orig field.
        position=0
        following_gap=False
        for part in parts:
            if position<part.start:
                raw=original[position:part.start]
                projected=(" " if following_gap and raw and raw[0].isalnum() else "")+raw
                child=document.add_text(label=DocItemLabel.TEXT,text=projected,orig=raw,parent=group)
                mappings.append(dict(pointer=child.self_ref,origin_pointer=pointer,source_field="text",
                    start=position,end=part.start,kind="native_text_range"))
            c=part.candidate
            regions=part.regions or (c,)
            boxes=[BoundingBox(l=r.left,t=r.top,r=r.right,b=r.bottom,coord_origin=CoordOrigin(r.origin)) for r in regions]
            formula=document.add_text(label=DocItemLabel.FORMULA,text=c.text,orig=c.text,parent=group)
            formula.prov=[ProvenanceItem(page_no=r.page_no,bbox=box,charspan=(0,len(c.text))) for r,box in zip(regions,boxes,strict=True)]
            crops=[render_region(r.page_no,box) for r,box in zip(regions,boxes,strict=True)]
            if len(crops)==1:
                image=crops[0]
            else:
                from PIL import Image
                image=Image.new("RGB",(sum(crop.width for crop in crops)+4*(len(crops)-1),max(crop.height for crop in crops)),"white")
                x=0
                for crop in crops:
                    image.paste(crop,(x,image.height-crop.height));x+=crop.width+4;crop.close()
            pending.append(ItemAndImageEnrichmentElement(item=formula,image=image))
            mappings.append(dict(pointer=formula.self_ref,origin_pointer=pointer,source_field="text",
                start=part.start,end=part.end,kind="vector_region_anchor" if not c.text else "native_text_range"))
            position=part.end
            following_gap=not c.text
        if position<len(original):
            raw=original[position:]
            projected=(" " if following_gap and raw and raw[0].isalnum() else "")+raw
            child=document.add_text(label=DocItemLabel.TEXT,text=projected,orig=raw,parent=group)
            mappings.append(dict(pointer=child.self_ref,origin_pointer=pointer,source_field="text",
                start=position,end=len(original),kind="native_text_range"))
    size=max(1,stage.elements_batch_size)
    for offset in range(0,len(pending),size):
        batch=pending[offset:offset+size]
        try:
            if len(list(stage(document,batch)))!=len(batch):
                raise RecognitionUnavailable('native inline inference did not return its complete batch')
        finally:
            for element in batch:
                element.image.close()
    return tuple(stage.outcomes[start:]),tuple(mappings)


def classify_cells(document: Any, candidates: tuple[CellCandidate,...], pages: tuple[CandidatePage,...],
                   *, math_pattern: str, prose_pattern: str) -> tuple[tuple[CellCandidate,...],list[dict[str,Any]]]:
    """Account for every cell before recognition; nonempty model output is not a classifier."""
    nodes=native_nodes(document)
    by_page={p.page_no:p for p in pages}
    demanded=[]
    reports=[]
    for candidate in candidates:
        cell=nodes[candidate.table_ref].data.table_cells[candidate.cell_index]
        page=by_page.get(candidate.page_no)
        box=cell.bbox.to_top_left_origin(document.pages[candidate.page_no].size.height)
        intersects=False
        for region in page.candidates if page else ():
            region_top,region_bottom=region.top,region.bottom
            if region.origin=='BOTTOMLEFT':
                height=document.pages[candidate.page_no].size.height
                region_top,region_bottom=height-region.top,height-region.bottom
            if box.l<region.right and region.left<box.r and min(box.t,box.b)<max(region_top,region_bottom) and min(region_top,region_bottom)<max(box.t,box.b):
                intersects=True
                break
        if intersects:
            classification,basis='math','native-candidate-intersection'
        elif re.search(math_pattern,cell.text):
            classification,basis='math','native-math-token'
        elif page and page.has_words and re.fullmatch(prose_pattern,cell.text.strip()):
            classification,basis='prose','native-word-text'
        else:
            classification,basis='unknown','unresolved-native-evidence'
        reports.append(dict(table_pointer=candidate.table_ref,cell_index=candidate.cell_index,page_no=candidate.page_no,
            classification=classification,basis=basis,outcome='not_requested' if classification=='prose' else 'unknown'))
        if classification=='math':
            demanded.append(candidate)
    return tuple(demanded),reports
