"""Independent finite sets and hostile direct publication under native roles."""
from __future__ import annotations

from hashlib import sha256


import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes, fact_key, occurrence_key
from corpus_structure.semantic.inference import derive, publish_inference
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    PublicationBatch, EntityRow, MembershipRow, MembershipSupportRow, EvidenceRow,
    ValueRow, RoleRow, FactRow, OccurrenceRow, SupportRow, SelectionRow,
    DerivationRow, DerivationPremiseRow, OccurrenceEstablishmentRow, publish_batch,
)
from corpus_structure.semantic.query import SnapshotBinding

R,Z,C,P,Q='release:infer','realization:infer','https://example/Thing','https://example/p','https://example/q'


def setup(admin, writer, edges, *, rules=('transitive','inverse'), contexts=None, positive=True):
    with admin.begin() as conn:
        conn.execute(insert(table('sem.release')).values(release_id=R,content_digest='test',
            profile='test',prepared_bytes=b'{}',manifest_bytes=b'{}'))
        conn.execute(insert(table('data.project')).values(project_id='p'))
        conn.execute(insert(table('data.realization')).values(realization_id=Z,project_id='p',release_id=R))
        conn.execute(insert(table('sem.class_definition')).values(release_id=R,class_id=C,name='Thing',iri=C))
        for p in (P,Q):
            conn.execute(insert(table('sem.property_definition')).values(release_id=R,property_id=p,name=p[-1],iri=p))
            conn.execute(insert(table('sem.property_applicability')).values(release_id=R,class_id=C,
                property_id=p,range_name='Thing',required=False,multivalued=True,constraint_scope='shape',
                constraints={'name':p[-1],'inlined':False}))
        for kind in rules:
            rid='rule:'+kind
            body={'kind':kind,'predicate':P,'rule_id':rid,'rule_version':'1'}
            if kind=='inverse':body['target']=Q
            conn.execute(insert(table('sem.registry_row')).values(release_id=R,kind='inference_rule',
                name=rid,body=canonical_bytes(body)))
    entities=sorted({e for edge in edges for e in edge})
    contexts=contexts or ['same']*len(edges)
    values=[ValueRow('v:'+e,'entity',entity_id=e) for e in entities]
    values += [ValueRow('modality','string',text_value='asserted'),ValueRow('polarity','boolean',boolean_value=positive)]
    roles=[]; facts=[]; occurrences=[]; supports=[]
    for i,((s,o),ctx) in enumerate(zip(edges,contexts,strict=True)):
        q='qual:'+str(i)
        values.extend((ValueRow(q,'mapping'),ValueRow('scope:'+str(i),'string',text_value=ctx)))
        roles.extend((RoleRow(q,'modality',0,'modality'),RoleRow(q,'polarity',0,'polarity'),RoleRow(q,'scope',0,'scope:'+str(i))))
        fid=fact_key(R,Z,s,P,o,{'modality':'asserted','polarity':positive,'scope':ctx})
        facts.append(FactRow(fid,s,P,'v:'+o,q))
        oid=occurrence_key(R,Z,'source',str(i))
        occurrences.append(OccurrenceRow(oid,fid,'source',str(i),'v:'+o,q))
        supports.append(SupportRow(fid,oid))
    batch=PublicationBatch(R,Z,'sources',entity=tuple(EntityRow(e) for e in entities),
        membership=tuple(MembershipRow(e,C,'stated') for e in entities),
        membership_support=tuple(MembershipSupportRow(e,C,'ev') for e in entities),
        evidence=(EvidenceRow('ev','source','page#unit','test','1'),),
        typed_value=tuple(values),value_role=tuple(roles),fact=tuple(facts),occurrence=tuple(occurrences),
        occurrence_establishment=tuple(OccurrenceEstablishmentRow(o.occurrence_id,'stated') for o in occurrences),
        support=tuple(supports),selection=tuple(SelectionRow(f.fact_id) for f in facts))
    receipt=publish_batch(writer,batch)
    return SnapshotBinding(R,Z,receipt.data_revision,'test'),batch


def compute(writer,binding):
    with writer.connect().execution_options(isolation_level='REPEATABLE READ') as conn,conn.begin():
        return derive(conn,binding)


def projected(writer):
    with writer.connect() as conn:
        return set(conn.execute(text('SELECT f.subject_id,f.property_id,v.entity_id FROM data.fact f JOIN '
            'data.typed_value v USING(release_id,realization_id) WHERE f.object_value_id=v.value_id')))


def test_interacting_rules_and_canonical_context(semantic_db_engine,semantic_writer_engine):
    binding,_=setup(semantic_db_engine,semantic_writer_engine,[('a','b'),('b','c')])
    result=compute(semantic_writer_engine,binding)
    assert len(result.batch.fact)==4
    receipt=publish_inference(semantic_writer_engine,result)
    assert projected(semantic_writer_engine)=={('a',P,'b'),('b',P,'c'),('a',P,'c'),
                                             ('b',Q,'a'),('c',Q,'b'),('c',Q,'a')}
    assert publish_inference(semantic_writer_engine,result)==receipt


def test_multiple_proofs_and_cycle_terminate(semantic_db_engine,semantic_writer_engine):
    binding,_=setup(semantic_db_engine,semantic_writer_engine,
        [('a','b'),('a','c'),('b','d'),('c','d'),('d','a')],rules=('transitive',))
    result=compute(semantic_writer_engine,binding)
    expected=fact_key(R,Z,'a',P,'d',{'modality':'asserted','polarity':True,'scope':'same'})
    assert sum(d.conclusion_fact_id==expected for d in result.batch.derivation)>=2
    publish_inference(semantic_writer_engine,result)
    assert projected(semantic_writer_engine)=={(a,P,b) for a in 'abcd' for b in 'abcd'}


@pytest.mark.parametrize('positive,contexts',[(False,None),(True,['one','two'])])
def test_negative_and_different_context_do_not_compose(semantic_db_engine,semantic_writer_engine,positive,contexts):
    binding,_=setup(semantic_db_engine,semantic_writer_engine,[('a','b'),('b','c')],
        rules=('transitive',),positive=positive,contexts=contexts)
    assert compute(semantic_writer_engine,binding).batch.fact==()


def test_direct_transport_rejects_undeclared_proof_and_stale_analysis(semantic_db_engine,semantic_writer_engine):
    binding,batch=setup(semantic_db_engine,semantic_writer_engine,[('a','b')],rules=('inverse',))
    fact=batch.fact[0].fact_id
    bad=PublicationBatch(R,Z,'bad',derivation=(DerivationRow('d',fact,'unknown','1'),),
        derivation_premise=(DerivationPremiseRow('d',0,fact),))
    with pytest.raises(DBAPIError,match='unadmitted inference'):
        publish_batch(semantic_writer_engine,bad)
    result=compute(semantic_writer_engine,binding)
    publish_batch(semantic_writer_engine,PublicationBatch(R,Z,'advance'))
    with pytest.raises(DBAPIError,match='revision changed'):
        publish_inference(semantic_writer_engine,result)


def proof(head, premises, rule='rule:symmetric'):
    did='derivation:'+sha256(canonical_bytes([rule,'1',head,premises])).hexdigest()
    return DerivationRow(did,head,rule,'1'),tuple(DerivationPremiseRow(did,i,p) for i,p in enumerate(premises))


def test_forged_cycle_and_ungrounded_alternate_proof_refuse(semantic_db_engine,semantic_writer_engine):
    binding,sources=setup(semantic_db_engine,semantic_writer_engine,[('a','b'),('c','d')],rules=('symmetric',))
    qual={'modality':'asserted','polarity':True,'scope':'same'}
    a=fact_key(R,Z,'a',P,'c',qual)
    b=fact_key(R,Z,'c',P,'a',qual)
    da,pa=proof(a,(b,))
    db,pb=proof(b,(a,))
    bad=PublicationBatch(R,Z,'cycle',fact=(FactRow(a,'a',P,'v:c','qual:0'),
        FactRow(b,'c',P,'v:a','qual:0')),derivation=(da,db),derivation_premise=pa+pb)
    with pytest.raises(DBAPIError,match='ungrounded'):
        publish_batch(semantic_writer_engine,bad)
    # A grounded head cannot launder an ungrounded premise in an additional proof.
    reverse=fact_key(R,Z,'b',P,'a',qual)
    d,ps=proof(sources.fact[0].fact_id,(reverse,))
    bad=PublicationBatch(R,Z,'alternate',fact=(FactRow(reverse,'b',P,'v:a','qual:0'),),
        derivation=(d,),derivation_premise=ps)
    with pytest.raises(DBAPIError,match='ungrounded'):
        publish_batch(semantic_writer_engine,bad)
