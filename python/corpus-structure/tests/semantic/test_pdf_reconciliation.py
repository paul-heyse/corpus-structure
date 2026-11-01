"""Independent retained coordinate/token examples; no model inference or fixtures as oracle."""
from copy import deepcopy
from hashlib import sha256

import pytest

from corpus_structure.ingest.pdf_reconciliation import (
    map_pdf_observation, compare_pdf_occurrences, select_pdf_integration,
)
from .test_pdf_integrated import native_source, observation, pin


def recognized(source, raw, *, role='A', page=1):
    value=observation(source,pass_role=role)
    value['observation']['raw_response_digest']=sha256(raw).hexdigest()
    value['observation']['image'].update(page_no=page,width=200,height=300)
    value['observation']['image']['transform']={
        'status':'coarse','page_width':200.,'page_height':300.,'page_rotation':0,
        'crop_left':0.,'crop_top':0.,'crop_right':200.,'crop_bottom':300.,
        'affine':[1.,0.,0.,1.,0.,0.],
    }
    value['occurrences']=[{'occurrence_id':f'block-{i}','kind':'text','address_space':'recognized_text','precision':'block','page_no':page} for i in range(raw.count(b'<class_'))]
    value['coverage'][0].update(scope=f'page:{page}',family='nemotron-pass-'+role)
    return value


def integrate(source,raw,*,policy=None):
    obs=recognized(source,raw)
    return select_pdf_integration(source.payload,pin(1,'native','0'*64,'structural'),[(pin(2,'a','1'*64,'recognition'),obs,raw)],source.original,source.recipe,source.schema,policy=policy).values()


def test_mapper_repeated_equal_occurrences_and_raw_geometry(native_source):
    raw=b'<x_0.05><y_0.033333>equal<x_0.3><y_0.066666><class_Text><x_0.05><y_0.133333>equal<x_0.3><y_0.166666><class_Text>'
    mapped=map_pdf_observation(recognized(native_source,raw),raw)
    assert len(mapped.document.texts)==2
    assert mapped.origins=={'#/texts/0':'block-0','#/texts/1':'block-1'}
    assert mapped.document.texts[0].prov[0].bbox.l==10
    assert mapped.document.texts[0].prov[0].bbox.t==pytest.approx(9.9999)
    assert mapped.document.texts[0].prov[0].charspan==(0,0)


def test_crop_transform_is_inverted_with_independent_expected_points(native_source):
    raw=b'<x_0.2><y_0.1>crop<x_0.8><y_0.9><class_Text>'
    obs=recognized(native_source,raw)
    obs['observation']['image'].update(width=100,height=200)
    # x_pixels=2*x_pdf-40; y_pixels=2*y_pdf-60.
    obs['observation']['image']['transform'].update(crop_left=20.,crop_top=30.,crop_right=70.,crop_bottom=130.,affine=[2.,0.,0.,2.,-40.,-60.])
    box=map_pdf_observation(obs,raw).document.texts[0].prov[0].bbox
    assert (box.l,box.t,box.r,box.b)==(30.,40.,60.,120.)


def test_mapper_keeps_table_spans_chart_metadata_and_inline_math(native_source):
    raw=(rb'<x_0.1><y_0.2>\begin{tabular}{cc}\multicolumn{2}{c}{Header} \\ 1 & 2\end{tabular}<x_0.9><y_0.5><class_Table>'
        rb'<x_0.1><y_0.6><chart type="line"><title>Speed</title>\n| t | m/s |\n|---|---|\n|1|2|<x_0.9><y_0.9><class_Chart>'
        rb'<x_0.1><y_0.05>Value $x+1$ follows<x_0.9><y_0.1><class_Text>').replace(rb'\n',b'\n')
    doc=map_pdf_observation(recognized(native_source,raw),raw).document
    assert doc.tables[0].data.table_cells[0].col_span==2
    assert doc.pictures[0].meta.tabular_chart.chart_data.num_rows>=1
    assert any(t.label=='formula' and t.text=='x+1' for t in doc.texts)
    assert all(not getattr(c,'bbox',None) for c in doc.tables[0].data.table_cells)


def test_selection_replace_preserves_original_alternative_and_replay(native_source):
    raw=b'<x_0.05><y_0.033333>corrected<x_0.3><y_0.066666><class_Text>'
    first=integrate(native_source,raw)
    assert first==integrate(native_source,raw)
    assert any(t['text']=='corrected' for t in first['content']['document']['texts'])
    decisions=[r for r in first['relations'] if r['outcome']=='replaced']
    assert decisions and any(e.get('input_index')==0 and e['role']=='alternative' for e in decisions[0]['endpoints'])
    assert all(o['precision']!='glyph' for o in first['occurrences'])


def test_policy_remapping_reuses_raw_and_retains_conflict(native_source):
    raw=b'<x_0.05><y_0.033333>corrected<x_0.3><y_0.066666><class_Text>'
    policy={'policy_id':'pdf-integration-v1','conflict_action':'unresolved','unmatched_action':'add','specialized_crop_precedence':True}
    result=integrate(native_source,raw,policy=policy)
    assert [t['text'] for t in result['content']['document']['texts']]==['equal','equal']
    assert any(r['outcome']=='unresolved' for r in result['relations'])


def test_generated_inline_formula_has_parent_grounding_not_fake_glyph_box(native_source):
    raw=rb'<x_0.5><y_0.5>Value $x+1$ follows<x_0.95><y_0.6><class_Text>'
    result=integrate(native_source,raw)
    formula=next(o for o in result['occurrences'] if o['kind']=='formula')
    assert formula['precision']=='inherited'
    assert formula['grounding_pointer']!=formula['pointer']
    assert 'start' not in formula and 'end' not in formula
    node=result['content']['document']['texts'][int(formula['pointer'].split('/')[-1])]
    assert node['prov']==[]


def test_failure_layout_unknown_and_truncation_dispositions(native_source):
    raw=b'<x_0.2><y_0.1>unknown<x_0.8><y_0.2><class_Alien><x_0.2>broken<class_Text>tail'
    mapped=map_pdf_observation(recognized(native_source,raw),raw)
    assert [d['outcome'] for d in mapped.dispositions]==['unsupported','unsupported','dropped']
    assert not mapped.document.body.children
    layout=map_pdf_observation(recognized(native_source,raw,role='B'),raw)
    assert layout.dispositions[0]['reason']=='layout_pass'
    obs=recognized(native_source,raw);obs['observation']['outcome']='failed'
    assert not map_pdf_observation(obs,raw).document.body.children
    with pytest.raises(ValueError,match='differs'):
        map_pdf_observation(obs,raw+b'changed')


def test_text_syntax_and_symbolic_comparison_are_distinct():
    plain=compare_pdf_occurrences('x+1','1+x')
    assert not plain['text_equal'] and 'equivalent' not in plain
    syntax=compare_pdf_occurrences('x+1','1+x',mathematical=True)
    assert 'syntax' in syntax and 'equivalent' not in syntax
    symbolic=compare_pdf_occurrences('x+1','1+x',mathematical=True,symbolic=True)
    assert symbolic['equivalent'] is True
