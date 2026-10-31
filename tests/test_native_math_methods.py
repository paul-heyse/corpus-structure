"""Actual M09/M11/M13 branches consume immutable SourceViews and native addresses."""
from types import SimpleNamespace

from corpus_structure.core.method import SourceViewRef,UnitRef,UnitView,CoverageDraft
from corpus_structure.core.vocab import TaskUnitType,ObservationKind
from corpus_structure.methods.math.methods import ExtractMath,NormalizeFormula,ExtractMathConfig,NormalizeFormulaConfig,SymbolScope,SymbolScopeConfig
from corpus_structure.methods.math.native import NativeDomainRule,domain_blocks
from corpus_structure.methods.math.scope import Binders
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.semantic.parsing_products import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView


def view():
    text='Let x. Then x+x.'
    items=({'self_ref':'#/texts/0','label':'text','text':'Let '},
        {'self_ref':'#/texts/1','label':'formula','text':'x','orig':'x'},
        {'self_ref':'#/texts/2','label':'text','text':'. Then '},
        {'self_ref':'#/texts/3','label':'formula','text':'x+x','orig':'x+x'},
        {'self_ref':'#/texts/4','label':'text','text':'.'})
    extents=[(0,4),(4,5),(5,12),(12,15),(15,16)]
    pieces=tuple(dict(item_ref=i['self_ref'],start=a,end=b,kind='native_text')
                 for i,(a,b) in zip(items,extents,strict=True))
    ref=SourceViewRef(7,'native-section:7',1,ProductReference(2,'organized','a'*64),
                      '#/groups/0','direct','b'*64,'c'*64)
    health={'formula_outcomes':[{'pointer':'#/texts/1','outcome':'succeeded'},
        {'pointer':'#/texts/3','outcome':'succeeded'}],
        'inline_coverage':'complete','cell_coverage':'complete'}
    return PreparedSourceView(ref,text,pieces,items,(),health)


class Reader:
    prepared=None
    math_readings_batch=None
    def __init__(self):
        self.view=view();self.outputs={}
    def source_views(self): return [self.view.ref]
    def source_view(self,id): assert id==7;return self.view
    def source_observations(self,id,method,kind): return self.outputs.get((method,kind),[])
    def source_view_coverage(self,id,method):
        return [SimpleNamespace(task_id=4,release_id=5,coverage=CoverageDraft(family=method,scope='native-section:7',outcome='complete'))]
    def store(self,method,result):
        for ordinal,draft in enumerate(result.observations):
            row=SimpleNamespace(payload=draft.payload.model_dump(mode='json'),native_pointer=draft.native_pointer,
                observation_key=f'{method}:{ordinal}',payload_hash=str(ordinal),task_id=42)
            self.outputs.setdefault((method,draft.kind),[]).append(row)


def test_actual_methods_select_source_views_and_keep_native_offsets():
    reader=Reader();run=SimpleNamespace(reader=reader)
    unit=UnitView(UnitRef(TaskUnitType.SOURCE_VIEW,7,'native-section:7'),run,document_id=1,source_view_id=7)
    ctx=SimpleNamespace(reader=reader)
    assert list(ExtractMath().select(run,ExtractMathConfig()))==[unit.ref]
    m09=ExtractMath().run([unit],ExtractMathConfig(),ctx)[0]
    mentions=[o for o in m09.observations if o.kind is ObservationKind.MENTION]
    assert len(mentions)==3
    assert [o.recognized_span for o in mentions]==[(0,1),(0,1),(2,3)]
    assert [o.projected_span for o in mentions]==[(4,5),(12,13),(14,15)]
    assert all(o.rendition_id is None and o.span is None for o in mentions)
    reader.store('extract.math',m09)
    m11=NormalizeFormula().run([unit],NormalizeFormulaConfig(),ctx)[0]
    assert len([o for o in m11.observations if o.kind is ObservationKind.VALUE])==2
    records=[o for o in m11.observations if o.kind is ObservationKind.RECORD]
    assert len(records)==1
    assert records[0].payload.items[0]['interpretation_ref']['observation_key']
    assert records[0].payload.items[0]['symbolic']['expression']=="Symbol('x')"
    reader.store('normalize.formula',m11)
    cfg=SymbolScopeConfig(binders=Binders(sentence_initial=('let',)),sentences=SentenceConfig())
    # Scope consumes recorded M09/M11 values and may not re-enter mathematical inference.
    import unittest.mock
    with unittest.mock.patch('corpus_structure.methods.math.native.readings',side_effect=AssertionError('reparsed')):
        result=SymbolScope().run([unit],cfg,ctx)[0]
    assert all(o.source_view_id==7 and o.rendition_id is None for o in result.observations)
    scopes=[o.payload for o in result.observations if o.kind is ObservationKind.SCOPE]
    assert len(scopes)==3
    assert all(scope.outcome=="resolved" for scope in scopes)
    assert scopes[1].binding_observation==scopes[0].binding_observation


def test_domain_roles_are_release_rules_and_do_not_imply_proof_truth():
    source=SimpleNamespace(text='Proof. Details.',items=({'self_ref':'#/texts/0','label':'section_header','text':'Proof.'},),
        pieces=({'item_ref':'#/texts/0','start':0,'end':6},))
    assert domain_blocks(source,())==()
    rule=NativeDomainRule(rule_id='proof-heading-1',pattern=r'^Proof\.',statement_kind='proof',scope_role='proof')
    recognized=domain_blocks(source,(rule,))
    assert recognized[0][2]=='#/texts/0'
    assert recognized[0][3].rule_id=='proof-heading-1'


def test_ancestor_function_roles_require_forward_native_tree_order():
    from dataclasses import replace
    from corpus_structure.methods.math.methods import MathSection
    from corpus_structure.methods.math.native import native_ancestor_declarations,readings
    from corpus_structure.core.vocab import ParseOutcome
    rule=NativeDomainRule(rule_id='proof-heading-1',pattern=r'^Proof\.',statement_kind='proof',scope_role='proof')
    parent_group={'self_ref':'#/groups/0','label':'section','children':[
        {'$ref':'#/texts/0'},{'$ref':'#/texts/1'},{'$ref':'#/groups/1'},{'$ref':'#/texts/2'}]}
    parent_items=(parent_group,
        {'self_ref':'#/texts/0','label':'formula','text':'f(2)','orig':'f(2)','parent':{'$ref':'#/groups/0'}},
        {'self_ref':'#/texts/1','label':'formula','text':'f(x)=x','orig':'f(x)=x','parent':{'$ref':'#/groups/0'}},
        {'self_ref':'#/texts/2','label':'formula','text':'g(x)=x','orig':'g(x)=x','parent':{'$ref':'#/groups/0'}})
    child_group={'self_ref':'#/groups/1','label':'section','parent':{'$ref':'#/groups/0'},
                 'children':[{'$ref':'#/texts/3'},{'$ref':'#/texts/4'}]}
    child_items=(child_group,
        {'self_ref':'#/texts/3','label':'formula','text':'f(2)','orig':'f(2)','parent':{'$ref':'#/groups/1'}},
        {'self_ref':'#/texts/4','label':'formula','text':'g(2)','orig':'g(2)','parent':{'$ref':'#/groups/1'}})
    def make(id,group,items,ancestors):
        texts=[];pieces=[];position=0
        for item in items:
            if 'text' not in item:continue
            text=item['text'];texts.append(text);pieces.append(dict(item_ref=item['self_ref'],start=position,end=position+len(text)))
            position+=len(text)
        ref=replace(view().ref,id=id,key=f'native:{id}',section_pointer=group['self_ref'])
        health={'formula_outcomes':[{'pointer':i['self_ref'],'outcome':'succeeded'} for i in items if i.get('label')=='formula']}
        return PreparedSourceView(ref,''.join(texts),tuple(pieces),items,ancestors,health)
    parent=make(7,parent_group,parent_items,())
    child=make(8,child_group,child_items,(parent_group,))
    reader=Reader();reader.views={7:parent,8:child};reader.math_readings_batch=None
    reader.source_view=lambda id:reader.views[id]
    reader.source_views=lambda:[parent.ref,child.ref]
    cfg=NormalizeFormulaConfig(math=MathSection(native_domain_rules=(rule,)))
    declarations,issues=native_ancestor_declarations(reader,child,(rule,))
    assert issues==()
    assert [d['symbol'] for d in declarations]==['f']
    assert '#/texts/1' in declarations[0]['evidence']
    earlier=readings(parent,cfg,reader)[0]
    assert earlier.result.status is ParseOutcome.AMBIGUOUS
    child_readings=readings(child,cfg,reader)
    assert child_readings[0].result.status is ParseOutcome.OK
    assert child_readings[1].result.status is ParseOutcome.AMBIGUOUS


def test_local_proof_function_definition_does_not_escape_to_child_section():
    from corpus_structure.methods.math.native import native_ancestor_declarations
    from dataclasses import replace
    parent_group={'self_ref':'#/groups/0','label':'section','children':[
        {'$ref':'#/texts/0'},{'$ref':'#/texts/1'},{'$ref':'#/groups/1'}]}
    heading={'self_ref':'#/texts/0','label':'section_header','text':'Proof.','parent':{'$ref':'#/groups/0'}}
    formula={'self_ref':'#/texts/1','label':'formula','text':'h(x)=x','orig':'h(x)=x','parent':{'$ref':'#/groups/0'}}
    child_group={'self_ref':'#/groups/1','label':'section','parent':{'$ref':'#/groups/0'},'children':[]}
    parent=PreparedSourceView(view().ref,'Proof.h(x)=x',({'item_ref':'#/texts/0','start':0,'end':6},
        {'item_ref':'#/texts/1','start':6,'end':12}),(parent_group,heading,formula),(),
        {'formula_outcomes':[{'pointer':'#/texts/1','outcome':'succeeded'}]})
    child=PreparedSourceView(replace(view().ref,id=8,key='child',section_pointer='#/groups/1'),'',(),
        (child_group,),(parent_group,),{})
    reader=Reader();reader.source_view=lambda id:{7:parent,8:child}[id];reader.source_views=lambda:[parent.ref,child.ref]
    rule=NativeDomainRule(rule_id='proof-heading-1',pattern=r'^Proof\.',statement_kind='proof',scope_role='proof')
    assert native_ancestor_declarations(reader,child,(rule,))[0]==()


def test_context_only_parent_prepares_weak_variable_binding_for_child(monkeypatch):
    from dataclasses import replace
    from corpus_structure.methods.math.methods import MathSection
    from corpus_structure.methods.math.native import native_scope_result
    from corpus_structure.methods.math.prepared import PreparedMathInput
    rule=NativeDomainRule(rule_id='proof-heading-1',pattern=r'^Proof\.',statement_kind='proof',scope_role='proof')
    group={'self_ref':'#/groups/0','label':'section','children':[
        {'$ref':'#/texts/0'},{'$ref':'#/texts/1'},{'$ref':'#/texts/2'},{'$ref':'#/groups/1'}]}
    child_group={'self_ref':'#/groups/1','label':'section','parent':{'$ref':'#/groups/0'},
                 'children':[{'$ref':'#/texts/3'}]}
    parent_items=(group,{'self_ref':'#/texts/0','label':'text','text':'Let ','parent':{'$ref':'#/groups/0'}},
        {'self_ref':'#/texts/1','label':'formula','text':'x','orig':'x','parent':{'$ref':'#/groups/0'}},
        {'self_ref':'#/texts/2','label':'text','text':'.','parent':{'$ref':'#/groups/0'}})
    parent=PreparedSourceView(view().ref,'Let x.',tuple(dict(item_ref=pointer,start=a,end=b) for pointer,a,b in
        [('#/texts/0',0,4),('#/texts/1',4,5),('#/texts/2',5,6)]),parent_items,(),
        {'formula_outcomes':[{'pointer':'#/texts/1','outcome':'succeeded'}]})
    child=PreparedSourceView(replace(view().ref,id=8,key='child',section_pointer='#/groups/1'),'x+x',
        ({'item_ref':'#/texts/3','start':0,'end':3},),
        (child_group,{'self_ref':'#/texts/3','label':'formula','text':'x+x','orig':'x+x','parent':{'$ref':'#/groups/1'}}),
        (group,),{'formula_outcomes':[{'pointer':'#/texts/3','outcome':'succeeded'}],
                  'inline_coverage':'complete','cell_coverage':'complete'})
    class MultiReader(Reader):
        def __init__(self):self.outputs={};self.views={7:parent,8:child};self.math_readings_batch=None
        def source_view(self,id):return self.views[id]
        def source_views(self):return [child.ref]
        def ancestor_source_views(self,id):return [parent.ref] if id==8 else []
        def source_observations(self,id,method,kind):return self.outputs.get((id,method,kind),[])
        def store(self,method,result):
            for n,draft in enumerate(result.observations):
                row=SimpleNamespace(payload=draft.payload.model_dump(mode='json'),native_pointer=draft.native_pointer,
                    observation_key=f'{draft.source_view_id}:{method}:{n}',payload_hash=str(n))
                self.outputs.setdefault((draft.source_view_id,method,draft.kind),[]).append(row)
    reader=MultiReader();ctx=SimpleNamespace(reader=reader);run=SimpleNamespace(reader=reader)
    cfg=SymbolScopeConfig(math=MathSection(native_domain_rules=(rule,)),
        binders=Binders(sentence_initial=('let',)),sentences=SentenceConfig())
    parent_unit=SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW,7,parent.ref.key),context_only=True)
    with monkeypatch.context() as guard:
        guard.setattr(PreparedMathInput,'symbolic_value',lambda *a,**k:(_ for _ in ()).throw(AssertionError('strong')))
        context=native_scope_result(parent_unit,cfg,ctx)
    assert context.observations[0].payload.declarations[0].symbol=='x'
    reader.store('resolve.symbol_scope',context)
    unit=UnitView(UnitRef(TaskUnitType.SOURCE_VIEW,8,child.ref.key),run,source_view_id=8)
    mathcfg=ExtractMathConfig(math=MathSection(native_domain_rules=(rule,)))
    reader.store('extract.math',ExtractMath().run([unit],mathcfg,ctx)[0])
    reader.store('normalize.formula',NormalizeFormula().run([unit],NormalizeFormulaConfig(math=mathcfg.math),ctx)[0])
    result=SymbolScope().run([unit],cfg,ctx)[0]
    assert all(o.payload.outcome=='resolved' for o in result.observations if o.kind is ObservationKind.SCOPE)
    assert all(o.payload.binding_source_view_id==7 for o in result.observations if o.kind is ObservationKind.SCOPE)
    assert all(any(ref.role=='native_parent_context' for ref in o.input_refs)
               for o in result.observations if o.kind is ObservationKind.SCOPE)


def test_occurrence_owner_is_weak_and_normalization_reuses_retained_tree(monkeypatch):
    from corpus_structure.methods.math.prepared import PreparedMathInput
    from corpus_structure.methods.math import grammar
    from corpus_structure.semantic.native_analysis import stored_native_analysis
    reader=Reader();run=SimpleNamespace(reader=reader);ctx=SimpleNamespace(reader=reader)
    unit=UnitView(UnitRef(TaskUnitType.SOURCE_VIEW,7,reader.view.ref.key),run,source_view_id=7)
    with monkeypatch.context() as guard:
        guard.setattr(PreparedMathInput,'symbolic_value',lambda *a,**k:(_ for _ in ()).throw(AssertionError('unasked symbolic work')))
        guard.setattr(PreparedMathInput,'definedness_result',lambda *a,**k:(_ for _ in ()).throw(AssertionError('unasked definedness work')))
        weak=ExtractMath().run([unit],ExtractMathConfig(),ctx)[0]
    reader.store('extract.math',weak)
    # Neither normalization nor inspection may reconstruct the original syntax tree.
    with monkeypatch.context() as guard:
        guard.setattr(grammar,'syntax',lambda *a,**k:(_ for _ in ()).throw(AssertionError('reparsed')))
        strong=NormalizeFormula().run([unit],NormalizeFormulaConfig(),ctx)[0]
        reader.store('normalize.formula',strong)
        recorded=stored_native_analysis(reader,7,'#/texts/3')['#/texts/3']
    assert recorded['interpretation']['recognized_latex']=='x+x'
    assert recorded['normalization']['symbolic']['expression']=="Mul(Integer(2), Symbol('x'))"
    assert [row['method'] for row in recorded['observations']]==['extract.math','normalize.formula']


def test_normalization_refuses_missing_named_occurrence_owner():
    import pytest
    reader=Reader();run=SimpleNamespace(reader=reader);ctx=SimpleNamespace(reader=reader)
    unit=UnitView(UnitRef(TaskUnitType.SOURCE_VIEW,7,reader.view.ref.key),run,source_view_id=7)
    with pytest.raises(ValueError,match='one exact completed'):
        NormalizeFormula().run([unit],NormalizeFormulaConfig(),ctx)


def test_stored_analysis_refuses_cycles_and_stale_pins():
    import pytest
    from corpus_structure.semantic.native_analysis import stored_native_analysis,NativeAnalysisUnavailable
    reader=Reader()
    payload=dict(demand='symbolic',source_view_id=7,native_product=reader.view.ref.native_product.values(),
        projection_digest=reader.view.ref.projection_digest,recipe_digest=reader.view.ref.recipe_digest,
        items=[dict(pointer='#/texts/1',interpretation_ref=dict(observation_key='self',pointer='#/texts/1'))])
    row=SimpleNamespace(payload=payload,observation_key='self',task_id=1,payload_hash='hash')
    reader.outputs[('normalize.formula',ObservationKind.RECORD)]=[row]
    with pytest.raises(NativeAnalysisUnavailable,match='cycle'):
        stored_native_analysis(reader,7,'#/texts/1')
    payload['native_product']={**payload['native_product'],'content_digest':'d'*64}
    with pytest.raises(NativeAnalysisUnavailable,match='pinned source view'):
        stored_native_analysis(reader,7,'#/texts/1')


def test_scope_digest_binds_exact_ancestor_preparation_record():
    from dataclasses import replace
    reader=Reader();source=reader.view
    parent=PreparedSourceView(replace(source.ref,id=6,key='parent',section_pointer='#/groups/parent'),'',(),(),(),{})
    group={'self_ref':'#/groups/parent','label':'section','children':[{'$ref':'#/groups/0'}]}
    child=replace(source,ancestors=(group,))
    reader.source_view=lambda id:{6:parent,7:child}[id]
    reader.ancestor_source_views=lambda id:[parent.ref]
    row=SimpleNamespace(observation_key='parent-context',payload_hash='first')
    reader.source_observations=lambda id,method,kind:[row] if id==6 and kind is ObservationKind.RECORD else []
    run=SimpleNamespace(reader=reader)
    unit=UnitView(UnitRef(TaskUnitType.SOURCE_VIEW,7,child.ref.key),run,source_view_id=7)
    first=SymbolScope().input_digest(unit,SymbolScopeConfig()).bytes
    row.payload_hash='second'
    assert SymbolScope().input_digest(unit,SymbolScopeConfig()).bytes!=first
