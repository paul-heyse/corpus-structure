"""Native evaluated-result and source-coordinate authority boundaries."""
import pytest
from dataclasses import replace
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.domain_operations import consolidate_cut
from .test_domain_operations import fixture

def test_finished_result_refuses_new_protected_publication(semantic_db_engine,semantic_writer_engine,tmp_path):
    from corpus_structure.semantic.publication import PublicationBatch,publish_batch
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html')
    result=consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with pytest.raises(DBAPIError,match='evaluated realization is immutable'):
        publish_batch(semantic_writer_engine,PublicationBatch(prepared.release_id,'evaluated','after-finish'))
    assert consolidate_cut(semantic_writer_engine,cut,'evaluated')==result


def test_native_source_locator_is_checked_against_stored_citation(semantic_db_engine,semantic_writer_engine,tmp_path):
    import json
    from corpus_structure.semantic.domain_operations import _cut_input
    from corpus_structure.semantic.publication import publish_on_connection,EvidenceSourceRow
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html')
    inputs=_cut_input(semantic_writer_engine,cut,'hostile')
    evidence=tuple(replace(e,locator=json.dumps({**json.loads(e.locator),'locator':'invented#not-source'})) for e in inputs.batch.evidence)
    with semantic_writer_engine.begin() as conn:
        links=[]
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        span=table('kb.span')
        for eid,(oid,rid,start,end) in inputs.source_links.items():
            sid=conn.execute(pg_insert(span).values(rendition_id=rid,start_offset=start,end_offset=end).returning(span.c.id)).scalar_one()
            links.append(EvidenceSourceRow(eid,oid,rid,sid))
    batch=replace(inputs.batch,evidence=evidence,evidence_source=tuple(links))
    with pytest.raises(DBAPIError,match='evidence span is not a located citation'):
        with semantic_writer_engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn,conn.begin():
            conn.execute(text('SELECT data.begin_evaluation(:cut,:out)'),{'cut':cut,'out':'hostile'})
            publish_on_connection(conn,batch)
