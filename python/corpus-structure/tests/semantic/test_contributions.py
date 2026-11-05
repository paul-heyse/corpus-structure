"""Independent hand-specified source contribution controls."""
from dataclasses import replace
from pathlib import Path

import pytest

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.contributions import bind_contributions, contribution_identity, occurrence_identity
from corpus_structure.semantic.observations import bind_result, observation_inputs
from corpus_structure.semantic.record_contracts import anchor_identity


@pytest.fixture(scope='module')
def prepared():
    path=Path(__file__).parents[2]/'src/corpus_structure/model/semantic/core.yaml'
    return prepare_release(observation_inputs(SourceBundle('core',(SourceArtifact('core',path.read_bytes()),))))


def pieces(start=0, source='source'):
    pin=dict(source=source,native_product_task_id=1,product_key='native',product_digest='a'*64,
        projection_digest='b'*64,recipe_digest='c'*64,source_view_id=1)
    anchor=dict(pin=pin,space='native',pointer='#/texts/0',precision='exact',start=start,end=start+2,source_piece='qs')
    anchor['anchor_id']=anchor_identity(anchor)
    coordinate=dict(pin=pin,space='native',pointer='#/texts/0',text='qs qs')
    return pin,anchor,coordinate


def contribution(kind='occurrence', start=0, item='0', role='mention'):
    pin,anchor,coordinate=pieces(start)
    row=dict(contract='RetainedContributionSemantics',kind=kind,semantic_type=role,operation_key='op',item_key=item,
        pin=pin,anchors=(anchor,),occurrence_id=occurrence_identity((anchor,)),disposition='unassessed',
        standing='retained_private',score_state='missing')
    row['contribution_id']=contribution_identity(row)
    return row,coordinate


def operation(count, outcome='succeeded', **kw):
    return dict(operation_key='op',question='locate_mentions',operation_version='1',outcome=outcome,
        inspected_count=1,emitted_count=count,**kw)


def test_physical_occurrence_is_independent_of_observation_and_role(prepared):
    first,coordinate=contribution(item='first')
    repeated,_=contribution(item='second')
    elsewhere,_=contribution(start=3,item='third')
    proposal,_=contribution(kind='proposal',role='alias_candidate')
    assert first['occurrence_id']==repeated['occurrence_id']==proposal['occurrence_id']
    assert first['contribution_id']!=repeated['contribution_id']!=proposal['contribution_id']
    assert first['occurrence_id']!=elsewhere['occurrence_id']
    _,bound=bind_contributions(prepared,source='source',operations=(operation(4),),
        contributions=(first,repeated,elsewhere,proposal),coordinate_texts=(coordinate,))
    assert len(bound)==4
    assert all('score' not in row for row in bound)


def test_recordless_batch_and_empty_operation_are_distinct_from_absence(prepared):
    row,coordinate=contribution()
    ref=UnitRef(TaskUnitType.SOURCE_VIEW,1,'source')
    result=UnitResult(ref=ref,outcome=ObservationOutcome.PRODUCED,contributions=(row,),
        contribution_operations=(operation(1),),contribution_coordinate_texts=(coordinate,))
    kwargs=dict(source='source',method='extract',operation_version='1',configuration_hash='config',input_hash='input',invocation_key='invocation')
    payload=bind_result(prepared,result=result,**kwargs).model_dump(mode='python')
    assert 'records' not in payload
    assert payload['contributions'][0]['contribution_id']==row['contribution_id']
    empty=UnitResult(ref=ref,outcome=ObservationOutcome.EMPTY,contributions=(),contribution_operations=(operation(0,'empty'),))
    bound=bind_result(prepared,result=empty,**kwargs).model_dump(mode='python')
    assert bound['contributions']==()
    assert len(bound['contribution_operations'])==1
    absent=bind_result(prepared,result=replace(empty,contributions=None,contribution_operations=None),**kwargs).model_dump(mode='python')
    assert 'contributions' not in absent


def test_endpoint_closure_piece_order_and_false_zero_refuse(prepared):
    row,coordinate=contribution()
    bad=dict(row,kind='relation',endpoints=({'role':'target','contribution_id':'missing'},)*2)
    bad['contribution_id']=contribution_identity(bad)
    with pytest.raises(ValueError,match='unavailable'):
        bind_contributions(prepared,source='source',operations=(operation(1),),contributions=(bad,),coordinate_texts=(coordinate,))
    bad=dict(row,score={'kind':'integer','integer':0})
    bad['contribution_id']=contribution_identity(bad)
    with pytest.raises(ValueError,match='score availability'):
        bind_contributions(prepared,source='source',operations=(operation(1),),contributions=(bad,),coordinate_texts=(coordinate,))
    pin,a,_=pieces(3);_,b,_=pieces(0)
    bad=dict(row,anchors=(a,b),occurrence_id=occurrence_identity((a,b)))
    bad['contribution_id']=contribution_identity(bad)
    with pytest.raises(ValueError,match='reverse order'):
        bind_contributions(prepared,source='source',operations=(operation(1),),contributions=(bad,),coordinate_texts=(coordinate,))


def test_occurrence_is_stable_across_view_alias_and_native_task_identity():
    pin,a,_=pieces()
    b=dict(a,pin=dict(pin,source='another-window',source_view_id=19,native_product_task_id=9,projection_digest='d'*64))
    b['anchor_id']=anchor_identity(b)
    assert occurrence_identity((a,))==occurrence_identity((b,))


def test_unsupported_effect_refuses_preparation():
    path=Path(__file__).parents[2]/'src/corpus_structure/model/semantic/core.yaml'
    bundle=observation_inputs(SourceBundle('core',(SourceArtifact('core',path.read_bytes()),)))
    sources=tuple(SourceArtifact(s.name,s.content.replace(b'equals_string: retain_private',b'equals_string: admit_public')) if s.name=='observations' else s for s in bundle.sources)
    with pytest.raises(Exception,match='unsupported contribution effect'):
        prepare_release(SourceBundle(bundle.root,sources))
