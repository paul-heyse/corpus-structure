"""Native occurrence context follows the admitted SourceStatement class hierarchy."""
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import insert,select
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import PreparationProfile,ResolvedDependencies,SourceArtifact,SourceBundle,prepare_release
from corpus_structure.semantic.consolidation import SourceItem,assemble
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import EvidenceRow,OccurrenceContextRow,publish_batch
from corpus_structure.semantic.query import QuerySpec,read_session
from corpus_structure.semantic.releases import persist_release

ROOT=Path(__file__).resolve().parents[4]

@pytest.mark.parametrize('context_kind',('descendant','unrelated'))
def test_typed_toy_statement_descendant_is_admitted_but_unrelated_class_is_refused(semantic_db_engine,semantic_writer_engine,semantic_reader_engine,context_kind):
    bundle=SourceBundle('toy_semantic',(
        SourceArtifact('toy_semantic',(ROOT/'domains/toy/semantic.yaml').read_bytes()),
        SourceArtifact('semantic_core',(ROOT/'python/corpus-structure/src/corpus_structure/model/semantic/core.yaml').read_bytes()),
    ))
    dependencies=ResolvedDependencies()
    prepared=prepare_release(bundle,dependencies)
    with semantic_db_engine.begin() as conn:
        persist_release(conn,bundle,dependencies,PreparationProfile(),prepared)
        conn.execute(insert(table('data.project')).values(project_id='statement-inheritance'))
        conn.execute(insert(table('data.realization')).values(project_id='statement-inheritance',release_id=prepared.release_id,realization_id='typed-context'))
    evidence=(EvidenceRow('native-evidence','urn:native-source','line:1','independent-native','1'),)
    qualification={'modality':'asserted','polarity':True}
    items=tuple(SourceItem('statement','ToySourceStatement',name,value,qualification,'native-source',name,'stated',evidence,'ToyQualification') for name,value in (('id','statement'),('locator','page#one'),('statement_kind','toy:clause')))
    items+= (SourceItem('other','Source','id','other',qualification,'native-source','other-id','stated',evidence,'ToyQualification'),)
    batch=assemble(prepared,'typed-context','typed-statement',items)
    target='statement' if context_kind=='descendant' else 'other'
    batch=replace(batch,occurrence_context=(OccurrenceContextRow(batch.occurrence[0].occurrence_id,target,'conclusion'),))
    if context_kind=='unrelated':
        with pytest.raises(DBAPIError,match='occurrence statement lacks SourceStatement membership'):
            publish_batch(semantic_writer_engine,batch)
        with semantic_reader_engine.connect() as conn:
            assert conn.scalar(select(table('data.batch').c.batch_id).where(table('data.batch').c.realization_id=='typed-context')) is None
        return
    assert publish_batch(semantic_writer_engine,batch).data_revision==1
    toy=next(d.iri for d in prepared.definitions if d.name=='ToySourceStatement')
    with semantic_reader_engine.connect() as conn:
        classes=tuple(conn.execute(select(table('data.membership').c.class_id).where(table('data.membership').c.realization_id=='typed-context',table('data.membership').c.entity_id=='statement')).scalars())
        assert classes==(toy,) # No fabricated base membership makes the native guard pass.
    with read_session(semantic_reader_engine,'typed-context') as reader:
        cls=reader.class_handle('ToySourceStatement')
        kinds=reader.query(QuerySpec(cls,reader.property_handle(cls,'statement_kind'),'fact'))
        assert [row.object for row in kinds.rows]==['toy:clause']
