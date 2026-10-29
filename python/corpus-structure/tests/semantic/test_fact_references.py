"""Fact references are declared semantics, checked by the native writer boundary."""
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from sqlalchemy import insert
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.consolidation import SourceItem, assemble
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import EvidenceRow, publish_batch
from corpus_structure.semantic.releases import persist_release


def fixture(admin):
    core = Path(__file__).parents[2] / 'src/corpus_structure/model/semantic/core.yaml'
    domain = {'id': 'https://example.org/references', 'name': 'references', 'imports': ['semantic_core'],
              'prefixes': {'ex': 'https://example.org/'}, 'default_prefix': 'ex',
              'classes': {'Thing': {'is_a': 'Entity', 'attributes': {'tag': {'multivalued': True}}}}}
    bundle = SourceBundle('references', (SourceArtifact('references', yaml.safe_dump(domain).encode()), SourceArtifact('semantic_core', core.read_bytes())))
    prepared = prepare_release(bundle)
    with admin.begin() as conn:
        persist_release(conn, bundle, ResolvedDependencies(), PreparationProfile(), prepared)
        conn.execute(insert(table('data.project')).values(project_id='p'))
        conn.execute(insert(table('data.realization')).values(realization_id='z', project_id='p', release_id=prepared.release_id))
    item = SourceItem('thing', 'Thing', 'tag', 'premise', {'modality': 'asserted', 'polarity': True},
                      'source', 'premise', 'stated', (EvidenceRow('ev', 'source', 'page#p', 'parser', '1'),))
    return prepared, item


def test_declared_fact_reference_resolves_in_same_publication(semantic_db_engine, semantic_writer_engine):
    prepared, premise = fixture(semantic_db_engine)
    premise_id = assemble(prepared, 'z', 'identity', (premise,)).fact[0].fact_id
    dependent = replace(premise, object='conditional', item='conditional', qualification={
        **premise.qualification, 'condition': {'kind': 'claim', 'ref': premise_id},
    })
    batch = assemble(prepared, 'z', 'valid', (replace(premise, property_name='id', object='thing', item='id'), premise, dependent))
    receipt = publish_batch(semantic_writer_engine, batch)
    assert receipt.data_revision == 1
    assert publish_batch(semantic_writer_engine, batch) == receipt


def test_native_writer_refuses_missing_fact_reference(semantic_db_engine, semantic_writer_engine):
    prepared, item = fixture(semantic_db_engine)
    dependent = replace(item, qualification={**item.qualification, 'condition': {
        'kind': 'claim', 'ref': 'fact:unavailable-in-this-realization',
    }})
    batch = assemble(prepared, 'z', 'invalid', (replace(item, property_name='id', object='thing', item='id'), dependent))
    with pytest.raises(DBAPIError, match='fact reference is outside its bound'):
        publish_batch(semantic_writer_engine, batch)


def test_copied_input_qualification_keeps_exact_fact_reference_lineage(semantic_db_engine, semantic_writer_engine):
    from sqlalchemy import select, text
    from corpus_structure.semantic.operations import OperationBinding, create_run, seal_cut
    from corpus_structure.semantic.publication import EntityInputRow, FactInputRow, SelectionRow, publish_on_connection

    prepared, premise = fixture(semantic_db_engine)
    identity = replace(premise, property_name='id', object='thing', item='id')
    premise_id = assemble(prepared, 'z', 'premise', (premise,)).fact[0].fact_id
    label = replace(premise, property_name='label', object='Conditional name', item='label', qualification={
        **premise.qualification, 'condition': {'kind': 'claim', 'ref': premise_id},
    })
    original = assemble(prepared, 'z', 'original', (identity, premise, label))
    original = replace(original, selection=tuple(SelectionRow(f.fact_id) for f in original.fact))
    publish_batch(semantic_writer_engine, original)
    with semantic_writer_engine.begin() as conn:
        run = create_run(conn, project_id='p', binding=OperationBinding(prepared.release_id, 'z', 1, b'{}'),
                         kind='full', options={}, code_commit='test')
        cut = seal_cut(conn, run, 'final', final=True)
    copied = assemble(prepared, 'out', 'copied', (identity, label))
    old_ids = {f.property_id: f.fact_id for f in original.fact}
    copied = replace(copied, occurrence=(), occurrence_establishment=(), occurrence_evidence=(), support=(),
                     selection=tuple(SelectionRow(f.fact_id) for f in copied.fact),
                     entity_input=(EntityInputRow('thing', 'z', 1, 'thing', run),),
                     fact_input=tuple(FactInputRow(f.fact_id, 'z', 1, old_ids[f.property_id], run) for f in copied.fact))
    with semantic_writer_engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn, conn.begin():
        conn.execute(text('SELECT data.begin_evaluation(:cut,:output)'), {'cut': cut, 'output': 'out'})
        receipt = publish_on_connection(conn, copied)
        assert receipt.data_revision == 1
        assert len(conn.execute(select(table('data.fact_input')).where(table('data.fact_input').c.realization_id == 'out')).all()) == 2
        assert not conn.execute(select(table('data.occurrence')).where(table('data.occurrence').c.realization_id == 'out')).first()
