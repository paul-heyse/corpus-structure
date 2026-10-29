"""Independent native checks of publication under real restricted logins."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import fact_key, occurrence_key
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    EntityRow, EvidenceRow, FactRow, MembershipRow, MembershipSupportRow,
    OccurrenceRow, PublicationBatch, RoleRow, SelectionRow, SupportRow, ValueRow,
    publish_batch, publish_on_connection,
)

R='release:test'
Z='realization:test'
C='https://example/Thing'
P='https://example/label'


def seed(engine, *, scope='accepted_value', unique=False):
    with engine.begin() as conn:
        conn.execute(insert(table('sem.release')).values(release_id=R,content_digest='test',profile='test',prepared_bytes=b'{}',manifest_bytes=b'{}'))
        conn.execute(insert(table('sem.class_definition')).values(release_id=R,class_id=C,name='Thing',iri=C))
        conn.execute(insert(table('sem.property_definition')).values(release_id=R,property_id=P,name='label',iri=P))
        conn.execute(insert(table('sem.property_applicability')).values(release_id=R,class_id=C,property_id=P,range_name='string',required=False,multivalued=False,constraint_scope=scope,constraints={'name':'label','inlined':False,'case_policy':'casefold'}))
        if unique:
            conn.execute(insert(table('sem.identity_slot')).values(release_id=R,class_id=C,group_id='0',position=0,property_id=P))
        conn.execute(insert(table('data.project')).values(project_id='p'))
        conn.execute(insert(table('data.realization')).values(realization_id=Z,release_id=R,project_id='p'))


def batch(identity='b', *, entity='e', label='Straße', selected=True):
    f=fact_key(R,Z,entity,P,label,{})
    o1=occurrence_key(R,Z,'source','1'+identity)
    o2=occurrence_key(R,Z,'source','2'+identity)
    return PublicationBatch(R,Z,identity,
        entity=(EntityRow(entity),),
        membership=(MembershipRow(entity,C,'source assertion'),),
        typed_value=(ValueRow('v'+identity,'string',text_value=label),),
        fact=(FactRow(f,entity,P,'v'+identity),),
        occurrence=(OccurrenceRow(o1,f,'source','1'+identity),OccurrenceRow(o2,f,'source','2'+identity)),
        support=(SupportRow(f,o1),SupportRow(f,o2)),
        selection=(SelectionRow(f),) if selected else (),
        evidence=(EvidenceRow('evidence'+identity,'urn:source','line:1','test','1'),),
        membership_support=(MembershipSupportRow(entity,C,'evidence'+identity),))


def test_batch_is_immutable_and_numeric_receipt_encoding():
    value=PublicationBatch(R,Z,'b',typed_value=(ValueRow('n','decimal',decimal_lexical='100',numeric_value=Decimal('1E+2')),))
    assert b'"100"' in value.content
    with pytest.raises(FrozenInstanceError):
        value.batch_id='other'
    with pytest.raises(TypeError):
        PublicationBatch(R,Z,'b',entity=[EntityRow('e')])


def test_native_copy_atomic_idempotent_distinct_occurrences(semantic_db_engine,semantic_writer_engine):
    seed(semantic_db_engine)
    candidate=batch()
    first=publish_batch(semantic_writer_engine,candidate)
    assert first.data_revision==1
    assert publish_batch(semantic_writer_engine,candidate)==first
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM data.occurrence'))==2
        assert conn.scalar(text('SELECT count(*) FROM data.fact'))==1
        assert conn.scalar(text('SELECT count(*) FROM data.support'))==2
        assert conn.scalar(text('SELECT count(*) FROM data.batch'))==1
        assert bytes(conn.scalar(text('SELECT content FROM data.batch')))==candidate.content
    with pytest.raises(DBAPIError):
        publish_batch(semantic_writer_engine,replace(candidate,entity=(EntityRow('wrong'),)))


def test_native_rejects_bad_identity_and_leaves_no_partial_state(semantic_db_engine,semantic_writer_engine):
    seed(semantic_db_engine)
    candidate=batch()
    bad=replace(candidate,occurrence=(replace(candidate.occurrence[0],occurrence_id='forged'),))
    with pytest.raises(DBAPIError):
        publish_batch(semantic_writer_engine,bad)
    with semantic_db_engine.connect() as conn:
        for name in ('entity','typed_value','fact','occurrence','batch'):
            assert conn.scalar(text(f'SELECT count(*) FROM data.{name}'))==0
        assert conn.scalar(text('SELECT data_revision FROM data.realization'))==0


def test_native_null_missing_range_and_nested_scope_fk(semantic_db_engine,semantic_writer_engine):
    seed(semantic_db_engine)
    candidate=batch()
    for value in (ValueRow('vb','null'),ValueRow('vb','string'),ValueRow('vb','entity',entity_id='foreign-entity')):
        with pytest.raises(DBAPIError):
            publish_batch(semantic_writer_engine,replace(candidate,typed_value=(value,),fact=(replace(candidate.fact[0],object_value_id='vb'),)))
    with pytest.raises(DBAPIError):
        publish_batch(semantic_writer_engine,replace(candidate,value_role=(RoleRow('vb','item',0,'foreign-value'),)))


def test_restricted_role_cannot_bypass_or_replace_stage(semantic_db_engine,semantic_writer_engine,semantic_reader_engine):
    seed(semantic_db_engine)
    for engine,statement in ((semantic_writer_engine,"INSERT INTO data.entity VALUES ('x','y','z')"),(semantic_writer_engine,'CREATE TEMP TABLE sp_entity(entity_id text)'),(semantic_reader_engine,'SELECT data.begin_stage()')):
        with pytest.raises(DBAPIError),engine.begin() as conn:
            conn.execute(text(statement))
    with semantic_writer_engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn,conn.begin():
        conn.execute(text('SELECT data.begin_stage()'))
        for statement in ('DROP TABLE pg_temp.sp_entity','ALTER TABLE pg_temp.sp_entity ADD COLUMN hidden text','CREATE TRIGGER malicious BEFORE INSERT ON pg_temp.sp_entity EXECUTE FUNCTION pg_catalog.suppress_redundant_updates_trigger()','SELECT data.begin_stage()'):
            with pytest.raises(DBAPIError),conn.begin_nested():
                conn.execute(text(statement))
    with semantic_db_engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn,conn.begin():
        conn.execute(text('CREATE TEMP TABLE sp_entity(entity_id text)'))
        with pytest.raises(DBAPIError),conn.begin_nested():
            conn.execute(text('SELECT data.begin_stage()'))


def test_selected_value_cardinality_retains_unselected_conflicts(semantic_db_engine,semantic_writer_engine):
    seed(semantic_db_engine)
    publish_batch(semantic_writer_engine,batch())
    publish_batch(semantic_writer_engine,batch('conflict',label='Other',selected=False))
    with pytest.raises(DBAPIError):
        publish_batch(semantic_writer_engine,PublicationBatch(R,Z,'select-conflict',selection=(SelectionRow(fact_key(R,Z,'e',P,'Other',{})),)))
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM data.fact'))==2
        assert conn.scalar(text('SELECT count(*) FROM data.selection'))==1
        assert conn.scalar(text('SELECT count(*) FROM data.occurrence'))==4


def test_concurrent_casefold_unique_candidates_have_independent_expected_state(semantic_db_engine,semantic_writer_engine):
    seed(semantic_db_engine,unique=True)
    barrier=Barrier(2)
    def attempt(candidate):
        barrier.wait(timeout=10)
        try:
            return publish_batch(semantic_writer_engine,candidate)
        except DBAPIError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(attempt,batch('a',entity='a',label='Straße')),pool.submit(attempt,batch('b',entity='b',label='STRASSE'))]
        results=[f.result(timeout=30) for f in futures]
    assert sum(result is not None for result in results)==1
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM data.entity'))==1
        assert conn.scalar(text('SELECT count(*) FROM data.batch'))==1
        assert conn.scalar(text('SELECT count(*) FROM data.occurrence'))==2


def test_connection_api_never_commits_and_requires_serializable(semantic_db_engine,semantic_writer_engine):
    seed(semantic_db_engine)
    with semantic_writer_engine.connect() as conn,conn.begin():
        with pytest.raises(DBAPIError),conn.begin_nested():
            publish_on_connection(conn,batch())
    with semantic_writer_engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn:
        with conn.begin():
            assert publish_on_connection(conn,batch()).data_revision==1
            conn.rollback()
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM data.batch'))==0


def test_serialization_retry_restages_same_immutable_batches(semantic_db_engine,semantic_writer_engine,monkeypatch):
    from corpus_structure.semantic import publication
    from sqlalchemy import event
    seed(semantic_db_engine)
    barrier=Barrier(2)
    original=publication.stage_batch
    seen=[]
    states=[]
    def staged(conn,candidate):
        seen.append((id(candidate),candidate.batch_id,candidate.content))
        original(conn,candidate)
        if sum(item[1]==candidate.batch_id for item in seen)==1:
            barrier.wait(timeout=10)
    def failed(context):
        states.append(getattr(context.original_exception,'sqlstate',None))
    monkeypatch.setattr(publication,'stage_batch',staged)
    event.listen(semantic_writer_engine,'handle_error',failed)
    candidates=(batch('a',entity='a'),batch('b',entity='b'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda candidate:publish_batch(semantic_writer_engine,candidate),candidates))
    assert {receipt.data_revision for receipt in results}=={1,2}
    assert '40001' in states
    assert len(seen)>=3
    for candidate in candidates:
        assert all(item==(id(candidate),candidate.batch_id,candidate.content) for item in seen if item[1]==candidate.batch_id)
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM data.batch'))==2
        assert conn.scalar(text('SELECT count(*) FROM data.occurrence'))==4


def test_ambiguous_committed_connection_loss_resolves_exact_receipt(semantic_db_engine,semantic_writer_engine,monkeypatch):
    import psycopg
    seed(semantic_db_engine)
    original=semantic_writer_engine.dialect.do_commit
    commits=[]
    def committed_then_lost(driver):
        original(driver)
        commits.append(1)
        if len(commits)==1:
            raise psycopg.OperationalError('injected connection loss after server commit')
    monkeypatch.setattr(semantic_writer_engine.dialect,'do_commit',committed_then_lost)
    candidate=batch()
    assert publish_batch(semantic_writer_engine,candidate).data_revision==1
    assert len(commits)==1
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM data.batch'))==1
        assert conn.scalar(text('SELECT count(*) FROM data.occurrence'))==2


def test_native_recursive_record_shape_and_entity_reference(semantic_db_engine,semantic_writer_engine):
    seed(semantic_db_engine)
    record='https://example/Record'
    with semantic_db_engine.begin() as conn:
        conn.execute(insert(table('sem.class_definition')).values(release_id=R,class_id=record,name='Record',iri=record))
        conn.execute(insert(table('sem.property_definition')).values(release_id=R,property_id='https://example/target',name='target',iri='https://example/target'))
        conn.execute(insert(table('sem.property_applicability')).values(release_id=R,class_id=record,property_id='https://example/target',range_name='Thing',required=True,multivalued=False,constraint_scope='shape',constraints={'name':'target','inlined':False}))
        conn.execute(table('sem.property_applicability').update().where(table('sem.property_applicability').c.class_id==C).values(range_name='Record',constraints={'name':'label','inlined':True}))
    candidate=batch()
    key=fact_key(R,Z,'e',P,{'target':'e'},{})
    candidate=replace(candidate,typed_value=(ValueRow('record','record',datatype=record),ValueRow('ref','entity',entity_id='e')),value_role=(RoleRow('record','target',0,'ref'),),fact=(FactRow(key,'e',P,'record'),),occurrence=(),support=(),selection=(SelectionRow(key),))
    assert publish_batch(semantic_writer_engine,candidate).data_revision==1
    for value in (ValueRow('bad','string',text_value='e',datatype=record),ValueRow('bad','record',datatype=record)):
        bad=replace(candidate,batch_id='bad',typed_value=(value,),value_role=(),fact=(FactRow('forged','e',P,'bad'),),selection=())
        with pytest.raises(DBAPIError):
            publish_batch(semantic_writer_engine,bad)


def test_native_identity_vectors_scalars_unicode_and_exact_decimals(semantic_db_engine,semantic_writer_engine):
    import json
    from datetime import UTC, date, datetime
    from corpus_structure.semantic.identity import _meaning, canonical_bytes
    seed(semantic_db_engine)
    values=(
        ('unicode',ValueRow('unicode','string',text_value='é𝄞\n\t\\"\u2028'), 'é𝄞\n\t\\"\u2028'),
        ('integer',ValueRow('integer','integer',text_value='9'*4000), int('9'*4000)),
        ('decimal',ValueRow('decimal','decimal',decimal_lexical='0.'+'0'*17000+'1'), Decimal('0.'+'0'*17000+'1')),
        ('date',ValueRow('date','date',text_value='2026-10-29'),date(2026,10,29)),
        ('datetime',ValueRow('datetime','datetime',text_value='2026-10-29T12:34:56.123456+00:00'),datetime(2026,10,29,12,34,56,123456,tzinfo=UTC)),
        ('float',ValueRow('float','float',text_value=(1.5).hex()),1.5),
        ('subnormal',ValueRow('subnormal','float',text_value=float.fromhex('0x0.0000000000001p-1022').hex()),float.fromhex('0x0.0000000000001p-1022')),
        ('negative-zero',ValueRow('negative-zero','float',text_value=(-0.0).hex()),-0.0),
        ('boolean',ValueRow('boolean','boolean',boolean_value=False),False),
    )
    candidate=PublicationBatch(R,Z,'vectors',typed_value=tuple(row for _,row,_ in values))
    publish_batch(semantic_writer_engine,candidate)
    with semantic_db_engine.begin() as conn:
        conn.execute(text('SET LOCAL ROLE corpus_sem_publisher'))
        for value_id,_,semantic in values:
            actual=conn.scalar(text('SELECT data.canonical_json(data.value_meaning(:r,:z,:v))'),{'r':R,'z':Z,'v':value_id})
            assert actual.encode()==canonical_bytes(_meaning(semantic))
            assert json.loads(actual)==_meaning(semantic)
    for value in (ValueRow('bad','float',text_value='0x1.0000000000000p+1024'),ValueRow('bad','float',text_value='0x0.0000000000000p-1022'),ValueRow('bad','datetime',text_value='2026-10-29T12:34:56.000000+00:00'),ValueRow('bad','datetime',text_value='2026-10-29T24:00:00+00:00'),ValueRow('bad','decimal',decimal_lexical='1.0')):
        with pytest.raises(DBAPIError):
            publish_batch(semantic_writer_engine,PublicationBatch(R,Z,'bad',typed_value=(value,)))


def test_native_bound_comparison_is_lossless_beyond_numeric_capacity(semantic_db_engine,semantic_writer_engine):
    seed(semantic_db_engine)
    huge='9'*150000
    with semantic_db_engine.begin() as conn:
        conn.execute(table('sem.property_applicability').update().values(range_name='decimal',constraints={'name':'label','native_minimum':huge,'native_maximum':huge}))
    candidate=batch()
    fact=fact_key(R,Z,'e',P,Decimal(huge),{})
    candidate=replace(candidate,typed_value=(ValueRow('huge','decimal',decimal_lexical=huge),),fact=(FactRow(fact,'e',P,'huge'),),occurrence=(),support=(),selection=(SelectionRow(fact),))
    assert publish_batch(semantic_writer_engine,candidate).data_revision==1
    with semantic_db_engine.begin() as conn:
        conn.execute(text('SET LOCAL ROLE corpus_sem_publisher'))
        assert conn.scalar(text("SELECT data.compare_decimal(:a,:b)"),{'a':huge,'b':'1'+huge})==-1
        assert conn.scalar(text("SELECT data.compare_decimal(:a,:b)"),{'a':'-'+huge,'b':'-1'+huge})==1


def test_native_constraints_prepares_datatype_aliases_and_scientific_bounds():
    import yaml
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.publication import admit_release, native_constraints
    source={'id':'https://example/alias','name':'alias','prefixes':{'ex':'https://example/'},'default_prefix':'ex','types':{'decimal':{'base':'Decimal'},'Amount':{'typeof':'decimal'},'Cost':{'typeof':'Amount'}},'classes':{'Thing':{'attributes':{'cost':{'range':'Cost','minimum_value':'1e10'}}}}}
    prepared=prepare_release(SourceBundle('alias',(SourceArtifact('alias',yaml.safe_dump(source).encode()),)))
    admit_release(prepared)
    constraints=native_constraints(prepared)
    assert constraints['https://example/Thing','https://example/cost']['native_range']=='decimal'
    assert constraints['https://example/Thing','https://example/cost']['native_minimum']=='10000000000'
