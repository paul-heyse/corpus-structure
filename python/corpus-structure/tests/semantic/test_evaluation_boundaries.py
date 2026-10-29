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


def test_unknown_occurrence_source_cannot_bypass_normalized_context(semantic_db_engine, semantic_writer_engine, tmp_path):
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from corpus_structure.semantic.domain_operations import _cut_input
    from corpus_structure.semantic.identity import occurrence_key
    from corpus_structure.semantic.publication import EvidenceSourceRow, publish_on_connection

    prepared, run, cut = fixture(semantic_db_engine, semantic_writer_engine, tmp_path / 'source.html')
    inputs = _cut_input(semantic_writer_engine, cut, 'hostile')
    target = next(row for row in inputs.batch.occurrence if row.item == 'claims/0')
    forged = occurrence_key(prepared.release_id, 'hostile', 'unknown-source', target.item)
    with semantic_writer_engine.begin() as conn:
        links = []
        span = table('kb.span')
        for evidence_id, (observation, rendition, start, end) in inputs.source_links.items():
            span_id = conn.execute(pg_insert(span).values(rendition_id=rendition, start_offset=start, end_offset=end).returning(span.c.id)).scalar_one()
            links.append(EvidenceSourceRow(evidence_id, observation, rendition, span_id))
    original = inputs.batch
    batch = replace(original,
        occurrence=tuple(replace(row, occurrence_id=forged, source='unknown-source') if row.occurrence_id == target.occurrence_id else row for row in original.occurrence),
        occurrence_establishment=tuple(replace(row, occurrence_id=forged) if row.occurrence_id == target.occurrence_id else row for row in original.occurrence_establishment),
        support=tuple(replace(row, occurrence_id=forged) if row.occurrence_id == target.occurrence_id else row for row in original.support),
        occurrence_evidence=tuple(replace(row, occurrence_id=forged) if row.occurrence_id == target.occurrence_id else row for row in original.occurrence_evidence),
        occurrence_context=tuple(row for row in original.occurrence_context if row.occurrence_id != target.occurrence_id),
        occurrence_evidence_role=tuple(row for row in original.occurrence_evidence_role if row.occurrence_id != target.occurrence_id),
        evidence_source=tuple(links),
    )
    with pytest.raises(DBAPIError, match='evaluated occurrence source differs from its bound observation'):
        with semantic_writer_engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn, conn.begin():
            conn.execute(text('SELECT data.begin_evaluation(:cut,:out)'), {'cut': cut, 'out': 'hostile'})
            publish_on_connection(conn, batch)
            conn.execute(text('SELECT data.finish_evaluation(:cut,:out,:batch)'), {'cut': cut, 'out': 'hostile', 'batch': batch.batch_id})
    with semantic_writer_engine.connect() as conn:
        assert not conn.execute(select(table('data.realization')).where(table('data.realization').c.realization_id == 'hostile')).first()
        assert conn.execute(select(table('ops.run').c.result_realization_id).where(table('ops.run').c.id == run)).scalar_one() is None


def test_finished_result_cannot_contain_an_unbacked_selected_fact(semantic_db_engine, semantic_writer_engine, tmp_path):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from corpus_structure.semantic.consolidation import SourceItem, assemble
    from corpus_structure.semantic.domain_operations import _cut_input
    from corpus_structure.semantic.publication import EvidenceRow, EvidenceSourceRow, SelectionRow, publish_on_connection

    prepared, run, cut = fixture(semantic_db_engine, semantic_writer_engine, tmp_path / 'source.html')
    inputs = _cut_input(semantic_writer_engine, cut, 'hostile')
    candidate = inputs.candidates[0]
    draft = SourceItem(candidate.subject, candidate.class_name, 'name', 'Alice',
                       {'modality': 'supposed', 'polarity': True}, 'not-a-source', 'bare', 'stated',
                       (EvidenceRow('unused', 'unused', 'unused', 'unused', '1'),))
    extra = assemble(prepared, 'hostile', 'extra', (draft,))
    with semantic_writer_engine.begin() as conn:
        links = []
        span = table('kb.span')
        for evidence_id, (observation, rendition, start, end) in inputs.source_links.items():
            span_id = conn.execute(pg_insert(span).values(rendition_id=rendition, start_offset=start, end_offset=end).returning(span.c.id)).scalar_one()
            links.append(EvidenceSourceRow(evidence_id, observation, rendition, span_id))
    batch = replace(inputs.batch,
        typed_value=tuple(sorted(set(inputs.batch.typed_value + extra.typed_value), key=lambda row: row.value_id)),
        value_role=tuple(sorted(set(inputs.batch.value_role + extra.value_role), key=lambda row: (row.parent_value_id, row.role, row.position))),
        fact=inputs.batch.fact + extra.fact,
        selection=(SelectionRow(extra.fact[0].fact_id),), evidence_source=tuple(links),
    )
    with pytest.raises(DBAPIError, match='evaluated fact has no source support, admitted proof or bound input lineage'):
        with semantic_writer_engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn, conn.begin():
            conn.execute(text('SELECT data.begin_evaluation(:cut,:out)'), {'cut': cut, 'out': 'hostile'})
            publish_on_connection(conn, batch)
            conn.execute(text('SELECT data.finish_evaluation(:cut,:out,:batch)'), {'cut': cut, 'out': 'hostile', 'batch': batch.batch_id})
