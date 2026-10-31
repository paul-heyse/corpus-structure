"""Prepared native containment and section scope, shared by mathematical consumers.

The retained native graph supplies identity and parentage; projection pieces supply text
coordinates. No parsing, source rewriting or inferred sibling relationship is performed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NativeTopology:
    root: str
    order: dict[str,int]
    chains: dict[str,tuple[str,...]]
    section_parents: dict[str,str|None]
    ends: dict[str,int]
    bounds: dict[str,tuple[int,int]]

    def section(self,pointer:str)->str:
        return self.chains[pointer][0]

    def scope_chain(self,pointer:str,source:str)->tuple[str,...]:
        return tuple(f'{source}:section:{section}' for section in self.chains[pointer])


def prepare_native_topology(view:Any)->NativeTopology:
    nodes={item['self_ref']:item for item in (*view.ancestors,*view.items)}
    root=view.ref.section_pointer
    sections={ref for ref,item in nodes.items() if item.get('label') in {'section','chapter'}}|{root}
    order={item['self_ref']:index for index,item in enumerate(view.items)}
    chains={}
    for pointer in order:
        cursor=pointer;seen=set();chain=[]
        while True:
            if cursor in seen:
                raise ValueError('native section topology contains a parent cycle')
            seen.add(cursor)
            if cursor in sections:chain.append(cursor)
            if cursor==root:break
            parent=(nodes.get(cursor,{}).get('parent') or {}).get('$ref')
            if parent is None:
                # A direct projection may omit external container nodes. Its admitted view
                # membership still supplies the root section; do not invent inner sections.
                cursor=root
            elif parent not in nodes and parent!=root:
                raise ValueError('native section topology has an unavailable parent: '+parent)
            else:cursor=parent
        chains[pointer]=tuple(chain)
    chains.setdefault(root,(root,))
    selected_sections={section for chain in chains.values() for section in chain}
    parents={section:(chains[section][1] if len(chains.get(section,()))>1 else None)
             for section in selected_sections}
    ends={section:max((index+1 for pointer,index in order.items() if section in chains[pointer]),default=len(order))
          for section in selected_sections}
    bounds={root:(0,len(view.text))}
    for piece in view.pieces:
        pointer=piece.get('item_ref')
        if pointer not in chains or piece['start']>=piece['end']:continue
        for section in chains[pointer]:
            previous=bounds.get(section)
            bounds[section]=(piece['start'],piece['end']) if previous is None else (
                min(previous[0],piece['start']),max(previous[1],piece['end']))
    return NativeTopology(root,order,chains,parents,ends,bounds)


def native_topology(view:Any)->NativeTopology:
    prepared=getattr(view,'topology',None)
    return prepared if prepared is not None else prepare_native_topology(view)
