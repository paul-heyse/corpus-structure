"""Domain publication of declared author-markup synthesis, not arbitrary parser readings."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping

from corpus_structure.core.evidence import RenditionContent
from corpus_structure.core.locators import LocatorIndex

from .consolidation import SourceItem
from .identity import canonical_bytes
from .publication import EvidenceRow
from .types import PreparedRelease


def statement_identity(release_id: str, realization_id: str, rendition_key: str, locator: str) -> str:
    return 'entity:' + sha256(canonical_bytes([release_id,realization_id,'source-statement',rendition_key,locator])).hexdigest()


@dataclass(frozen=True)
class MarkupProjection:
    items: tuple[SourceItem, ...]
    unresolved: tuple[str, ...] = ()
    evidence_ranges: tuple[tuple[str, int, int], ...] = ()


def project_markup(
    prepared: PreparedRelease, realization_id: str, *, observation_key: str,
    payload: Mapping[str, Any], content: RenditionContent, page: str, rendition_key: str,
    segment_key: str, provider: str, operation_version: str,
) -> MarkupProjection:
    """Only an explicit admitted source-profile synthesis can emit a source relation.

    Math spans, scope readings and non-synthesizing markup remain source reports for downstream
    algorithms; they are not automatically scientific claims. Bad locators remain explicit.
    """
    synthesis = payload.get('synthesize')
    if synthesis is None:
        return MarkupProjection(())
    index = LocatorIndex(content,page)
    # The stored markup segment is the physical source coordinate, never entity identity.
    from corpus_structure.core.evidence import segment_key as physical_key
    segment = next((s for s in content.document.walk() if physical_key(rendition_key,s.kind,s.start,s.end)==segment_key),None)
    if segment is None:
        raise ValueError('markup segment differs from the bound rendition')
    subject_locator = index.unit_key(segment)
    target_locator = synthesis['object']['ref']
    try:
        target = index.resolve(target_locator)
    except (ValueError, KeyError, LookupError):
        return MarkupProjection((),(target_locator,))
    predicate = prepared.expand_name(synthesis['predicate'])
    definition = next(d for d in prepared.definitions if d.name=='SourceStatement')
    prop = next(p for p in definition.properties if p.iri==predicate)
    if prop.range!='SourceStatement' or prop.inlined:
        raise ValueError('source synthesis requires a declared statement relation')
    qualification={'modality':'asserted','polarity':True}
    raw_evidence = synthesis.get('evidence',())
    if not raw_evidence:
        raise ValueError('source synthesis requires actual located evidence')
    evidence=[]
    ranges=[]
    for ordinal, raw in enumerate(raw_evidence):
        start,end=raw['start'],raw['end']
        if not (segment.start<=start<end<=segment.end):
            raise ValueError('synthesized evidence lies outside its source segment')
        eid='evidence:'+sha256(canonical_bytes([observation_key,ordinal,start,end])).hexdigest()
        evidence.append(EvidenceRow(eid,page,subject_locator,provider,operation_version))
        ranges.append((eid,start,end))
    refs=tuple(evidence)
    subject=statement_identity(prepared.release_id,realization_id,rendition_key,subject_locator)
    target_id=statement_identity(prepared.release_id,realization_id,rendition_key,target_locator)
    out=[]
    for role,entity,locator,node in (('subject',subject,subject_locator,segment),('object',target_id,target_locator,target)):
        attributes={'id':entity,'locator':locator}
        kind=(payload.get('value') or {}).get('statement_kind') if role=='subject' else (node.attrs.get('hint') or {}).get('statement_kind')
        if kind is not None:
            attributes['statement_kind']=kind
        for name,value in attributes.items():
            out.append(SourceItem(entity,'SourceStatement',name,value,qualification,observation_key,role+'/'+name,'stated',refs))
    out.append(SourceItem(subject,'SourceStatement',prop.name,target_id,qualification,observation_key,'synthesize','stated',refs))
    return MarkupProjection(tuple(out),evidence_ranges=tuple(ranges))
