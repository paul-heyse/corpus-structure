"""Traverse reference positions from the admitted LinkML class/property descriptors."""
from __future__ import annotations
from collections.abc import Mapping,Sequence
from typing import Any
from corpus_structure.semantic.types import ClassDefinition,PropertyDefinition

def record_definition(definitions:Sequence[ClassDefinition],range_name:str|None,value:Mapping[str,Any])->ClassDefinition|None:
    if range_name is None:return None
    candidates=[]
    for definition in definitions:
        if definition.abstract or not (definition.name==range_name or range_name in definition.ancestors):continue
        props={p.name:p for p in definition.properties}
        if not set(value)<=props.keys():continue
        if any(p.equals_string is not None and value.get(p.name)!=p.equals_string for p in props.values()):continue
        candidates.append(definition)
    if not candidates:
        if any(d.name==range_name for d in definitions):raise ValueError(f'no admitted {range_name} record matches the validated value')
        return None
    depth=max(len(d.ancestors) for d in candidates)
    best=[d for d in candidates if len(d.ancestors)==depth]
    if len(best)!=1:raise ValueError(f'ambiguous admitted record type for {range_name}')
    return best[0]

def entity_reference(definitions:Sequence[ClassDefinition],prop:PropertyDefinition)->bool:
    return not prop.inlined and any(d.name==prop.range and (d.name=='Entity' or 'Entity' in d.ancestors) for d in definitions)

def rewrite_references(definitions:Sequence[ClassDefinition],range_name:str,value:Any,entities:Mapping[str,str],claims:Mapping[str,str]|None=None)->Any:
    """Rewrite only declared entity/fact positions; plain string fields retain their text."""
    claims={} if claims is None else claims
    if not isinstance(value,Mapping):return value
    definition=record_definition(definitions,range_name,value)
    if definition is None:return dict(value)
    def member(prop,item):
        if prop.reference_role=='fact':return claims.get(item,item)
        if entity_reference(definitions,prop):return entities.get(item,item)
        if prop.inlined:return rewrite_references(definitions,prop.range,item,entities,claims)
        return item
    result:dict[str,Any]={}
    for prop in definition.properties:
        if prop.name not in value:continue
        item=value[prop.name]
        if prop.collection_key:
            rewritten=[member(prop,child) for child in item.values()]
            entries={}
            for child in rewritten:
                if not isinstance(child,Mapping):raise TypeError('declared keyed collection item must be a record')
                entries[child[prop.collection_key]]=child
            result[prop.name]=entries
            if len(result[prop.name])!=len(rewritten):raise ValueError('reference mapping collides a declared collection key')
        elif prop.multivalued:result[prop.name]=[member(prop,child) for child in item]
        else:result[prop.name]=member(prop,item)
    return result

def entity_references(definitions:Sequence[ClassDefinition],range_name:str,value:Any)->frozenset[str]:
    if not isinstance(value,Mapping):return frozenset()
    definition=record_definition(definitions,range_name,value)
    if definition is None:return frozenset()
    result=set()
    for prop in definition.properties:
        if prop.name not in value:continue
        raw=value[prop.name]
        members=raw.values() if prop.collection_key else raw if prop.multivalued else (raw,)
        for item in members:
            if entity_reference(definitions,prop):result.add(item)
            elif prop.inlined:result.update(entity_references(definitions,prop.range,item))
    return frozenset(result)
