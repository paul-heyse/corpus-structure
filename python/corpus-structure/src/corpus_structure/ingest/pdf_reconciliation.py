"""Retained NVIDIA observations mapped and adjudicated into one native content graph.

Library kernels supply structure and comparisons. The archived policy owns selection; raw
observations remain immutable inputs, including failed passes and rejected readings.
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from corpus_structure.semantic.identity import canonical_bytes

_CLASS = re.compile(r'<class_([^>]+)>')
_COORD = re.compile(r'<x_(\d+(?:\.\d+)?)><y_(\d+(?:\.\d+)?)>')
_LABELS = frozenset({'Text','Title','Section-header','List-item','TOC','Caption','Footnote','Bibliography','Page-header','Page-footer','Formula','Table','Chart','Picture','Code'})


@dataclass(frozen=True, slots=True)
class MappedObservation:
    document: Any
    # Native mapped pointer -> original raw occurrence. Children inherit block identity.
    origins: Mapping[str, str]
    dispositions: tuple[Mapping[str, Any], ...]
    observation: Mapping[str, Any]


def _context(context, operation):
    if context is None:
        from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
        context = trusted_pdf_context()
    context.execution.require_operation(operation)
    return context


def _validate_native(document: Any) -> None:
    # Upstream's decorator is annotated as a Pydantic descriptor. Resolve its actual
    # callable here, as at the native publication boundary.
    validate = document.validate_document
    if not callable(validate):
        raise TypeError("native Docling document validator is not callable")
    validate()
    if not document.validate_tree(document.body):
        raise ValueError("native Docling tree is invalid")


def _walk(node, document):
    yield node
    for ref in node.children:
        yield from _walk(ref.resolve(document), document)


def _repair_copied_references(original, copied, source, target):
    """Docling copies containment but rich cell/floating refs need the same relocation."""
    pairs=list(zip(_walk(original,source),_walk(copied,target),strict=True))
    relocated={old.self_ref:new.self_ref for old,new in pairs}
    for old,new in pairs:
        if hasattr(new,'data') and hasattr(new.data,'table_cells'):
            for cell in new.data.table_cells:
                ref=getattr(cell,'ref',None)
                if ref is not None:
                    if ref.cref not in relocated:
                        raise ValueError('rich cell references outside copied native subtree')
                    cell.ref=type(ref)(cref=relocated[ref.cref])
        for name in ('captions','references','footnotes'):
            if hasattr(new,name):
                setattr(new,name,[type(ref)(cref=relocated.get(ref.cref,ref.cref)) for ref in getattr(old,name)])
    return pairs


def _box(node, document):
    current = node
    while not getattr(current, 'prov', ()) and current.parent is not None:
        current = current.parent.resolve(document)
    prov = getattr(current, 'prov', ())
    if not prov:
        children=[p for child in _walk(node,document) for p in getattr(child,'prov',())]
        if not children or len({p.page_no for p in children})!=1:return None
        page=children[0].page_no
        boxes=[p.bbox.to_top_left_origin(document.pages[page].size.height) for p in children]
        return page,min(b.l for b in boxes),min(b.t for b in boxes),max(b.r for b in boxes),max(b.b for b in boxes)
    p = prov[0]
    box = p.bbox.to_top_left_origin(document.pages[p.page_no].size.height)
    return p.page_no, box.l, box.t, box.r, box.b


def _text(node, document):
    if hasattr(node, 'data') and hasattr(node.data, 'table_cells'):
        return '\n'.join(c.text for c in node.data.table_cells)
    return ' '.join(n.text for n in _walk(node, document) if getattr(n, 'text', ''))


def _family(node):
    label = str(node.label)
    return 'table' if label == 'table' else 'chart' if label == 'picture' else 'formula' if label == 'formula' else 'text'


def map_pdf_observation(observation: Mapping[str, Any], raw_response: bytes, *, context=None) -> MappedObservation:
    """Map actual native coordinate/class serialization; retain every block disposition.

    No image bytes or inference are needed for replay. B is layout evidence only. Each
    raw block is mapped separately so repeated equal blocks retain occurrence identity.
    """
    _context(context, 'map_pdf_observation')
    from docling.utils.nemotron_parse_v3_5_utils import parse_nemotron_parse_v3_5
    from docling_core.types.doc import DoclingDocument, Size
    from .pdf_hierarchy import native_nodes

    body = observation['observation']
    if body.get('raw_response_digest') != sha256(raw_response).hexdigest():
        raise ValueError('mapping raw response differs from retained observation')
    image = body['image']; transform = image['transform']
    result = DoclingDocument(name='Retained NVIDIA observations')
    origins: dict[str, str] = {}; dispositions: list[dict[str, Any]] = []
    if body['pass_role'] == 'B' or body['outcome'] != 'succeeded':
        return MappedObservation(result, origins, ({'outcome':'evidence_only','reason':body['outcome'] if body['pass_role'] != 'B' else 'layout_pass'},), observation)
    if transform['status'] != 'coarse':
        return MappedObservation(result, origins, ({'outcome':'unresolved','reason':'unqualified_transform'},), observation)
    page_no = image['page_no']
    result.add_page(page_no=page_no, size=Size(width=transform['page_width'],height=transform['page_height']))
    # The declared affine maps PDF TOPLEFT -> submitted pixels. Invert all four corners;
    # this handles rotated/cropped submissions without inventing word/cell geometry.
    a,b,c,d,e,f = transform['affine']; determinant = a*d-b*c
    if not math.isfinite(determinant) or abs(determinant) < 1e-12:
        raise ValueError('submitted image affine is not invertible')
    def inverse(x,y):
        return ((d*(x-e)-c*(y-f))/determinant,(-b*(x-e)+a*(y-f))/determinant)
    raw = raw_response.decode('utf-8'); start = 0
    declared = {o['occurrence_id'] for o in observation.get('occurrences', ())}
    for ordinal, match in enumerate(_CLASS.finditer(raw)):
        segment = raw[start:match.end()]; start=match.end(); identity=f'block-{ordinal}'
        disposition: dict[str, Any] = {'occurrence_id':identity,'label':match.group(1),'outcome':'mapped'}
        if identity not in declared:
            raise ValueError('raw block has no retained qualified occurrence: '+identity)
        coords=list(_COORD.finditer(segment))
        if len(coords)<2 or match.group(1) not in _LABELS:
            disposition.update(outcome='unsupported',reason='malformed_coordinates' if len(coords)<2 else 'unknown_label')
            dispositions.append(disposition); continue
        values=[float(v) for m in (coords[0],coords[-1]) for v in m.groups()]
        # Pinned public geometry.model_bbox_to_image_norm: normalized overshoot through
        # 1.5 is clipped; 1.5..1000 is quantized; larger coordinates are submitted pixels.
        maximum=max(abs(v) for v in values)
        if maximum>1000:
            normalized=[v/(image['width'] if i%2==0 else image['height']) for i,v in enumerate(values)]
            disposition['coordinate_frame']='submitted_pixels'
        else:
            scale=1000.0 if maximum>1.5 else 1.0
            normalized=[v/scale for v in values]
            disposition['coordinate_scale']=scale
            disposition['coordinate_frame']='quantized_1000' if scale==1000 else 'content_normalized'
        disposition['normalization']='clipped' if any(v<0 or v>1 for v in normalized) else 'normalized' if maximum>1.5 else 'none'
        normalized=[min(1,max(0,v)) for v in normalized]
        if normalized[0]>normalized[2] or normalized[1]>normalized[3]:
            disposition['reason']='corner_order_normalized'
            disposition['normalization']='normalized'
        normalized=[min(normalized[0],normalized[2]),min(normalized[1],normalized[3]),max(normalized[0],normalized[2]),max(normalized[1],normalized[3])]
        count=0
        def replace_coord(m):
            nonlocal count
            count+=1
            if count==1: return f'<x_{normalized[0]}><y_{normalized[1]}>'
            if count==len(coords): return f'<x_{normalized[2]}><y_{normalized[3]}>'
            return ''
        canonical=_COORD.sub(replace_coord,segment)
        try:
            mapped=parse_nemotron_parse_v3_5(canonical,Size(width=image['width'],height=image['height']),page_no,normalize_heading_levels=False)
            for node in native_nodes(mapped).values():
                for prov in getattr(node,'prov',()):
                    box=prov.bbox
                    corners=[inverse(x,y) for x in (box.l,box.r) for y in (box.t,box.b)]
                    xs,ys=zip(*corners,strict=True)
                    prov.bbox=type(box)(l=max(0,min(xs)),t=max(0,min(ys)),r=min(transform['page_width'],max(xs)),b=min(transform['page_height'],max(ys)),coord_origin='TOPLEFT')
                    prov.charspan=(0,0)
            before=len(result.body.children)
            result.add_document(mapped)
            for oldref,newref in zip(mapped.body.children,result.body.children[before:],strict=True):
                for old,new in _repair_copied_references(oldref.resolve(mapped),newref.resolve(result),mapped,result):
                    origins[new.self_ref]=identity
            if not mapped.body.children:
                disposition.update(outcome='dropped',reason='provider_mapper_empty')
        except (ValueError,IndexError,TypeError) as error:
            disposition.update(outcome='unsupported',reason=type(error).__name__+': '+str(error))
        dispositions.append(disposition)
    if raw[start:].strip(): dispositions.append({'outcome':'dropped','reason':'unterminated_raw_tail','raw_start':start})
    _validate_native(result)
    return MappedObservation(result, origins, tuple(dispositions), observation)


def compare_pdf_occurrences(left: str, right: str, *, mathematical=False, symbolic=False, assumptions=None, context=None) -> dict[str, Any]:
    """Separate text edit alignment, positioned syntax and optional symbolic equivalence."""
    _context(context,'compare_pdf_occurrences')
    from rapidfuzz.distance import Levenshtein
    result: dict[str,Any]={'text_equal':left==right,'text_agreement':Levenshtein.normalized_similarity(left,right),
        'opcodes':[list(op) for op in Levenshtein.opcodes(left,right)]}
    if mathematical and left!=right:
        from corpus_structure.methods.math import grammar
        l,r=grammar.syntax(left),grammar.syntax(right)
        result['syntax']={'left':str(l.status),'right':str(r.status),'left_positions':[(s.start,s.end) for s in l.occurrences],'right_positions':[(s.start,s.end) for s in r.occurrences]}
        result['structural_equal']=l.tree is not None and r.tree is not None and l.tree==r.tree
        if symbolic:
            # No ambient assumptions: the caller's explicit context is part of evidence.
            ctx=grammar.MathContext() if assumptions is None else assumptions
            lv,rv=grammar.interpret(l,ctx,symbolic=True),grammar.interpret(r,ctx,symbolic=True)
            try:
                import sympy
                with grammar.deadline(grammar.PARSE_SECONDS):
                    result['equivalent']=sympy.simplify(grammar.to_sympy(lv)-grammar.to_sympy(rv))==0
            except (ValueError,TypeError,NotImplementedError,grammar.NotParsed,grammar.Ambiguous,grammar.Expired):
                result['equivalent']=None
            result['assumptions']=repr(ctx)
    return result


@dataclass(slots=True)
class _Origin:
    input_index: int
    occurrence_id: str
    disposition: str = 'selected'
    alternatives: list[tuple[int,str]] = field(default_factory=list)
    evidence: dict[str,Any] = field(default_factory=dict)


def _selected_occurrences(document, origins):
    from .pdf_hierarchy import native_nodes
    nodes=native_nodes(document); rows: list[dict[str, Any]]=[]
    for pointer,node in nodes.items():
        label=str(node.label)
        row: dict[str, Any]={'occurrence_id':pointer,'kind':'formula' if label=='formula' else 'chart' if label=='picture' and getattr(node,'meta',None) and getattr(node.meta,'tabular_chart',None) else 'item','address_space':'selected_item','precision':'item','pointer':pointer}
        if hasattr(node,'text'): row['text']=node.text
        anchor=node
        while not getattr(anchor,'prov',()) and anchor.parent is not None:
            anchor=anchor.parent.resolve(document)
        if getattr(anchor,'prov',()):
            p=anchor.prov[0]; box=p.bbox
            generated=origins[id(node)].input_index!=0
            precision='coarse' if generated else 'item'
            if anchor is not node: row['grounding_pointer']=anchor.self_ref;precision='inherited'
            row.update(precision=precision,page_no=p.page_no,region={'address_space':'pdf_points','precision':precision,'normalization':'inherited' if anchor is not node else 'none','left':box.l,'top':box.t,'right':box.r,'bottom':box.b,'origin':'top_left' if box.coord_origin.value=='TOPLEFT' else 'bottom_left'})
        rows.append(row)
        from corpus_structure.semantic.pdf_integrated import native_cells
        cell_path,cells=native_cells(node.model_dump(mode='json',by_alias=True))
        if cells:
            for i,cell in enumerate(cells):
                entry: dict[str, Any]={'occurrence_id':f'{pointer}{cell_path}/{i}','pointer':pointer,'cell_index':i,'kind':'cell','address_space':'native_cell','precision':'coarse' if origins[id(node)].input_index else 'cell','text':cell['text']}
                if row.get('region'):
                    entry.update(page_no=row['page_no'],grounding_pointer=pointer,region={**row['region'],'precision':'inherited','normalization':'inherited'},precision='inherited')
                rows.append(entry)
    return rows


def select_pdf_integration(native_product: Mapping[str,Any], structural_pin: Mapping[str,Any], observations: Sequence[tuple[Mapping[str,Any],Mapping[str,Any],bytes]], original: bytes, recipe_bytes: bytes, native_schema: bytes, *, policy: Mapping[str,Any]|None=None, context=None, product_key='integrated'):
    """Select one graph with preserved alternatives and policy-governed keep/add/replace.

    Selection is local to qualified page/geometry candidates. Multiple overlapping readings
    remain unresolved. C has explicit table/chart precedence, never confidence authority.
    """
    context=_context(context,'select_pdf_integration')
    from docling_core.types.doc import DoclingDocument
    from docling.utils.vlm_utils import normalize_section_header_levels
    from corpus_structure.semantic.pdf_integrated import prepare_integrated_pdf_product
    from .pdf import PdfConversion, publication_payload
    from .pdf_hierarchy import native_nodes,snapshot
    policy=dict(policy or {'policy_id':'pdf-integration-v1','conflict_action':'replace','unmatched_action':'add','specialized_crop_precedence':True})
    policy=context.boundary.validate_json('PdfIntegrationPolicy',json.dumps(policy)).model_dump(mode='json')
    if policy['conflict_action'] not in {'keep','replace','unresolved'} or policy['unmatched_action'] not in {'add','unresolved'}:
        raise ValueError('policy action is inapplicable to its governed situation')
    doc=DoclingDocument.model_validate(native_product['document']); nodes=native_nodes(doc)
    origins={id(n):_Origin(0,p) for p,n in nodes.items()}
    inputs=[{**structural_pin,'role':'structural'}]; coverage=[]; rejected=[]; removed=[]; mapping_partial=False; mapping_reports=[]; correspondences=[]
    # Grid buckets bound correspondence to intersecting page regions, not an all-item matrix.
    # Rebuild a page index only for each affected page, preserving native document lifetime.
    mapped_inputs=[]
    for pin,observation,raw in observations:
        if observation['artifact_digest']!=native_product['artifact_digest']:
            raise ValueError('recognition and structural original differ')
        index=len(inputs);inputs.append({**pin,'role':'recognition'})
        mapped_inputs.append((index,observation,raw))
        for c in observation['coverage']:
            coverage.append({**c,'coverage_id':f'input-{index}-{c["coverage_id"]}','supports':[{'input_index':index,'coverage_id':c['coverage_id']}], 'outcome':'partial' if c['outcome']=='complete' else c['outcome']})
    # A content first, then specialized C. B remains independently retained layout evidence.
    mapped_inputs.sort(key=lambda row: row[1]['observation']['pass_role']=='C')
    by_page=defaultdict(list)
    for n in nodes.values():
        box=_box(n,doc)
        if box is None or str(n.label) in {'section','list','unspecified'}:continue
        if n.parent and str(n.parent.resolve(doc).label) in {'inline','table','list_item'}:continue
        by_page[box[0]].append(n)
    for index,observation,raw in mapped_inputs:
        frame=observation['observation']['image']['transform']
        page_no=observation['observation']['image']['page_no']
        native_page=doc.pages.get(page_no)
        if native_page is None or (frame['status']=='coarse' and (frame['page_rotation']!=0 or (native_page.size.width,native_page.size.height)!=(frame['page_width'],frame['page_height']))):
            mapping_reports.append({'input_index':index,'outcome':'unresolved','reason':'native_provider_page_frames_are_not_qualified'})
            mapping_partial=True
            continue
        mapped=map_pdf_observation(observation,raw,context=context)
        mapping_reports.extend(dict(d,input_index=index) for d in mapped.dispositions)
        mapping_partial |= any(d.get('outcome') in {'unsupported','dropped','unresolved'} for d in mapped.dispositions)
        image=mapped.observation['observation']['image'];page=image['page_no']
        buckets=defaultdict(list)
        def keys(box):
            _,l,t,r,b=box
            return ((x,y) for x in range(int(l//64),int(r//64)+1) for y in range(int(t//64),int(b//64)+1))
        # Candidate roots exclude organizational containers and descendants already represented
        # by rich inline/list/table roots.
        candidates=by_page[page]
        for n in candidates:
            for key in keys(_box(n,doc)):buckets[key].append(n)
        for ref in list(mapped.document.body.children):
            incoming_root=ref.resolve(mapped.document)
            incoming=incoming_root
            if str(incoming.label)=='list' and len(incoming.children)==1: incoming=incoming.children[0].resolve(mapped.document)
            box=_box(incoming,mapped.document)
            if box is None: continue
            seen={id(n):n for key in keys(box) for n in buckets[key]}
            overlaps=[]
            _,l,t,r,b=box; area=max(0,r-l)*max(0,b-t)
            for n in seen.values():
                nb=_box(n,doc)
                if nb is None:continue
                _,nl,nt,nr,nbottom=nb
                intersection=max(0,min(r,nr)-max(l,nl))*max(0,min(b,nbottom)-max(t,nt))
                fraction=intersection/max(1e-9,min(area,max(0,nr-nl)*max(0,nbottom-nt)))
                if fraction>=.45: overlaps.append((n,fraction))
            same=[(n,f) for n,f in overlaps if _family(n)==_family(incoming)]
            source=mapped.origins[incoming.self_ref]
            evidence={'mapping':[d for d in mapped.dispositions if d.get('occurrence_id')==source],'policy':policy,'candidates':[(origins[id(n)].input_index,origins[id(n)].occurrence_id,f) for n,f in overlaps]}
            correspondences.append((index,source,[(origins[id(n)].input_index,origins[id(n)].occurrence_id) for n,_ in overlaps], 'matched' if len(overlaps)==1 else 'ambiguous' if overlaps else 'unmatched', evidence))
            chosen=None; disposition='added'; alternative=[]
            if len(same)==1 and len(overlaps)==1:
                chosen=same[0][0]; previous=origins[id(chosen)]
                comparison=compare_pdf_occurrences(_text(chosen,doc),_text(incoming,mapped.document),mathematical=_family(incoming)=='formula',context=context)
                evidence['comparison']=comparison
                if comparison['text_equal'] and _family(incoming) not in {'table','chart'}:
                    previous.alternatives.append((index,source));previous.evidence.update(evidence);continue
                if str(chosen.label)=='section_header':
                    rejected.append((index,source,'retained_alternative',evidence));continue
                if previous.input_index and not (mapped.observation['observation']['pass_role']=='C' and _family(incoming) in {'table','chart'} and policy['specialized_crop_precedence']):
                    rejected.append((index,source,'unresolved',evidence));continue
                if policy['conflict_action']!='replace':
                    rejected.append((index,source,'retained_alternative' if policy['conflict_action']=='keep' else 'unresolved',evidence));continue
                disposition='replaced';alternative=[(previous.input_index,previous.occurrence_id),*previous.alternatives]
            elif overlaps or policy['unmatched_action']!='add':
                rejected.append((index,source,'unresolved',evidence));continue
            if chosen is None and str(incoming.label)=='list_item':incoming=incoming_root
            # Add rich subtree through Docling; track object identity while deletion renumbers pointers.
            if chosen is not None:
                parent=chosen.parent.resolve(doc)
                position=parent.children.index(chosen.get_ref())
                doc.insert_node_items(node_items=[incoming],doc=mapped.document,sibling=chosen,after=False)
            else:
                positions=[(n,nbox) for n in candidates if (nbox:=_box(n,doc)) is not None]
                # Choose neighboring content in the same column. Its existing containment
                # supplies section meaning; geometric proximity never creates a new section.
                same_column=[(n,nbox) for n,nbox in positions if min(r,nbox[3])>max(l,nbox[1])]
                positions=same_column or positions
                preceding=[(n,nbox) for n,nbox in positions if nbox[2]<=t]
                following=[(n,nbox) for n,nbox in positions if nbox[2]>t]
                if preceding:
                    nearest=max(preceding,key=lambda pair:(pair[1][2],pair[1][1]))[0]
                elif following:
                    nearest=min(following,key=lambda pair:(pair[1][2],pair[1][1]))[0]
                else:
                    rejected.append((index,source,'unresolved',{**evidence,'reason':'no_qualified_native_page_placement'}))
                    continue
                anchor=nearest
                parent=anchor.parent.resolve(doc) if anchor.parent is not None else doc.body
                while str(parent.label) not in {'section','chapter'} and parent is not doc.body:
                    anchor=parent
                    parent=anchor.parent.resolve(doc) if anchor.parent is not None else doc.body
                anchor_box=_box(anchor,doc)
                if anchor_box is not None and str(anchor.label)=='list' and anchor_box[2]<t<anchor_box[4]:
                    rejected.append((index,source,'unresolved',{**evidence,'reason':'list_internal_containment_unqualified'}))
                    continue
                after=anchor_box is None or (anchor_box[2],anchor_box[1]) <= (t,l)
                position=parent.children.index(anchor.get_ref())+(1 if after else 0)
                doc.insert_node_items(node_items=[incoming],doc=mapped.document,sibling=anchor,after=after)
                evidence['placement']={'parent':parent.self_ref,'neighbor':anchor.self_ref,'after':after,'basis':'native_section_and_same_page_reading_geometry'}
            copied_root=parent.children[position].resolve(doc)
            copied=[new for old,new in _repair_copied_references(incoming,copied_root,mapped.document,doc)]
            for n in copied:origins[id(n)]=_Origin(index,source,disposition,list(alternative),evidence)
            if chosen is not None: removed.append(chosen)
            # Maintain sparse local index after replacing; old references are removed.
            if chosen is not None:
                candidates[:]=[n for n in candidates if id(n)!=id(chosen)]
                for key in list(buckets):buckets[key]=[n for n in buckets[key] if id(n)!=id(chosen)]
            for n in copied:
                if n.parent and n.parent.cref not in {c.self_ref for c in copied}:
                    nbox=_box(n,doc)
                    if nbox:
                        candidates.append(n)
                        for key in keys(nbox):buckets[key].append(n)
    if removed: doc.delete_items(node_items=removed)
    normalize_section_header_levels(doc)
    _validate_native(doc)
    selected=snapshot(doc)
    conversion=PdfConversion(native_product['artifact_digest'],recipe_bytes,selected,'success',(),(),(),None)
    section_refs=frozenset(p for p,n in native_nodes(doc).items() if str(n.label)=='section')
    content=publication_payload(conversion,product_key=product_key,schema_digest=sha256(native_schema).hexdigest(),section_refs=section_refs,include_application_metadata=False)
    occurrences=_selected_occurrences(doc,origins); relations=[]
    final_nodes=native_nodes(doc)
    for occurrence in occurrences:
        node=final_nodes[occurrence['pointer']];origin=origins[id(node)]
        source_id=origin.occurrence_id
        if occurrence['kind']=='cell' and origin.input_index==0:
            from corpus_structure.semantic.pdf_integrated import native_cells
            path,_=native_cells(node.model_dump(mode='json',by_alias=True))
            source_id+=f'{path}/{occurrence["cell_index"]}'
        endpoints=[{'role':'input','input_index':origin.input_index,'occurrence_id':source_id},{'role':'output','occurrence_id':occurrence['occurrence_id']}]
        endpoints.extend({'role':'alternative','input_index':i,'occurrence_id':s} for i,s in origin.alternatives)
        relations.append({'relation_id':'decision:'+occurrence['occurrence_id'],'kind':'decision','outcome':origin.disposition,'comparison':'geometry','policy':policy['policy_id'],'evidence':canonical_bytes(origin.evidence or {'reason':'retained_structural_content','policy':policy}).decode(),'endpoints':endpoints})
    outputs_by_source=defaultdict(list)
    for o in occurrences:
        origin=origins[id(final_nodes[o['pointer']])]
        outputs_by_source[(origin.input_index,origin.occurrence_id)].append(o['occurrence_id'])
    for index,source,candidates,outcome,evidence in correspondences:
        endpoints=[{'role':'input','input_index':index,'occurrence_id':source}]
        endpoints.extend({'role':'input','input_index':i,'occurrence_id':s} for i,s in candidates)
        local_ids=set(outputs_by_source.get((index,source),()))
        for candidate in candidates: local_ids.update(outputs_by_source.get(candidate,()))
        endpoints.extend({'role':'output','occurrence_id':o} for o in sorted(local_ids))
        relations.append({'relation_id':f'correspondence:{index}:{source}:{len(relations)}','kind':'correspondence','outcome':outcome,'comparison':'geometry','policy':policy['policy_id'],'evidence':canonical_bytes(evidence).decode(),'endpoints':endpoints})
    for index,source,outcome,evidence in rejected:
        relations.append({'relation_id':f'alternative:{index}:{source}:{len(relations)}','kind':'decision','outcome':outcome,'comparison':'geometry','policy':policy['policy_id'],'evidence':canonical_bytes(evidence).decode(),'endpoints':[{'role':'alternative','input_index':index,'occurrence_id':source}]})
    if not coverage:coverage=[{'coverage_id':'selection','scope':'whole_document','family':'selected_content','discovery_policy':policy['policy_id'],'outcome':'unknown','detail':'No qualified recognition coverage'}]
    payload={'version':1,'kind':'integrated','product_key':product_key,'artifact_digest':native_product['artifact_digest'],'recipe_digest':sha256(recipe_bytes).hexdigest(),'inputs':inputs,'content':content,'occurrences':occurrences,'relations':relations,'mapping_reports':mapping_reports,'coverage':coverage,'health':{'execution_outcome':'partial' if rejected else 'succeeded','mapping_outcome':'partial' if rejected or mapping_partial else 'coarse','source_fidelity':'conflict' if rejected else 'unassessed','validation_report':'Docling validate_document/validate_tree and application invariants; coarse block mapping, no source completeness claim'}}
    return prepare_integrated_pdf_product(payload,original,recipe_bytes,native_schema=native_schema,context=context)
