"""Native PDF ingestion, demanded enrichment, and intact SourceView profiling."""
from __future__ import annotations

from collections.abc import Iterable,Sequence
from typing import Literal

from pydantic import BaseModel,ConfigDict

from corpus_structure.core.method import Digest,MeasurementDraft,MethodContext,Resources,SourceRunContext,UnitRef,UnitResult,UnitView
from corpus_structure.core.vocab import ConfidenceSource,MeasurementScope,MethodFamily,MethodTier,ObservationOutcome,TaskUnitType
from corpus_structure.semantic.identity import canonical_bytes
from .pdf_methods import EnrichPdfMath,IngestPdf
from .sentences import SentenceConfig


class MethodRefused(RuntimeError):
    """An archived method descriptor has no current executable writer."""


class SegmentSentences:
    """Named sentence preparation recipe, used by in-memory native text adapters."""
    name='segment.sentences'
    version='1'
    family=MethodFamily.INGEST
    unit_type=TaskUnitType.RENDITION
    tier=MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource|None=None
    Config=SentenceConfig
    resources=Resources()

    def select(self,run:SourceRunContext,cfg:SentenceConfig)->Iterable[UnitRef]:
        return ()

    def input_digest(self,unit:UnitView,cfg:SentenceConfig)->Digest:
        raise MethodRefused('sentence preparation runs within a native SourceView adapter')

    def run(self,units:Sequence[UnitView],cfg:SentenceConfig,ctx:MethodContext)->Sequence[UnitResult]:
        raise MethodRefused('sentence preparation runs within a native SourceView adapter')


class ProfileSegmentsConfig(BaseModel):
    model_config=ConfigDict(frozen=True,extra='forbid')
    features:Literal['chars_math']='chars_math'


class ProfileSegments:
    """M02 measures selected intact SourceViews; historical segment metrics retain their meaning."""
    name='profile.segments'
    version='2'
    family=MethodFamily.PROFILE
    unit_type=TaskUnitType.SOURCE_VIEW
    tier=MethodTier.DETERMINISTIC
    confidence_source:ConfidenceSource|None=None
    Config=ProfileSegmentsConfig
    resources=Resources(worker='cpu',batch_size=8)

    def select(self,run:SourceRunContext,cfg:ProfileSegmentsConfig)->Iterable[UnitRef]:
        return tuple(UnitRef(TaskUnitType.SOURCE_VIEW,v.id,v.key) for v in run.reader.source_views())

    def input_digest(self,unit:UnitView,cfg:ProfileSegmentsConfig)->Digest:
        if unit.ref.unit_id is None:
            raise MethodRefused('profiling requires an immutable SourceView')
        view=unit.run.reader.source_view(unit.ref.unit_id)
        return Digest(canonical_bytes({'native':view.ref.native_product.values(),'projection':view.ref.projection_digest}))

    def run(self,units:Sequence[UnitView],cfg:ProfileSegmentsConfig,ctx:MethodContext)->Sequence[UnitResult]:
        out=[]
        for unit in units:
            if unit.ref.unit_id is None:
                raise MethodRefused('profiling requires an immutable SourceView')
            view=ctx.reader.source_view(unit.ref.unit_id)
            items={item['self_ref']:item for item in view.items}
            math=[p for p in view.pieces if p.get('item_ref') in items and items[p['item_ref']]['label']=='formula']
            length=len(view.text)
            parent_labels=[items.get(items[p['item_ref']].get('parent',{}).get('$ref'),{}).get('label') for p in math]
            inline=sum(label=='inline' for label in parent_labels)
            display=sum(label not in {'inline','table'} for label in parent_labels)
            values={'chars':float(length),'math_share':round(sum(p['end']-p['start'] for p in math)/length,6) if length else 0.0,
                    'inline_math':float(inline),'display_math':float(display)}
            measurements=tuple(MeasurementDraft(metric='source_view.'+name,scope_type=MeasurementScope.SOURCE_VIEW,
                scope_id=view.ref.id,scope_key=view.ref.key,value=value) for name,value in values.items())
            out.append(UnitResult(ref=unit.ref,outcome=ObservationOutcome.EMPTY,measurements=measurements))
        return out


def native_methods():
    """Fresh operation ownership per registry; enrichment shares its run's PDF child owner."""
    producer=IngestPdf()
    return (producer,EnrichPdfMath(producer),SegmentSentences(),ProfileSegments())


METHODS=native_methods()
