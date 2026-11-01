"""Independent frozen visibility, reference and replay controls on actual PostgreSQL."""
import pyarrow as pa
import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.pdf_publication import (
    freeze_pdf_build, prepare_pdf_build, validate_pdf_build, seal_pdf_build,
    published_pdf_revision, adopt_pdf_companion_batch,
)
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch
from .test_pdf_staging import private_build  # noqa: F401


def stage_complete_native(engine,build,directory):
    document=DoclingDocument(name='frozen fixture')
    document.add_text(label=DocItemLabel.TEXT,text='independent expected text')
    result=StreamingPdfResult(document,PdfStreamSpool(directory/'pages'),'success',(),b'{}',())
    for replay in result.write_record_batches(directory/'records',build_id=build.build_id,
                   release_id=build.release_id,source_digest=build.source_digest):
        with pa.memory_map(str(replay.path),'r') as source:
            reader=pa.ipc.open_file(source)
            for index in range(reader.num_record_batches):
                with engine.begin() as conn:
                    adopt_pdf_batch(conn,build,f'{replay.family}:{index}',{replay.family:(reader.get_batch(index),)})
    with engine.begin() as conn:
        adopt_pdf_companion_batch(conn,build,'health',[{'conversion':'success','display_coverage':'unknown','inline_coverage':'unknown','cell_coverage':'unknown','source_scope':'whole_document'}],'health')
    return document


def test_freeze_prepare_validate_seal_and_replay(private_build,semantic_writer_engine,semantic_reader_engine,tmp_path):
    build=private_build;stage_complete_native(semantic_writer_engine,build,tmp_path)
    with semantic_writer_engine.begin() as conn:
        frozen=freeze_pdf_build(conn,build,kind="native")
        assert len(frozen.frozen_digest)==64
        assert freeze_pdf_build(conn,build,kind="native")==frozen
        prepare_pdf_build(conn,frozen)
    with semantic_reader_engine.connect() as conn:
        assert published_pdf_revision(conn,build.task_id,'native','0'*64) is None
    outcome=validate_pdf_build(semantic_writer_engine,frozen)
    assert len(outcome.logical_digest)==64
    with semantic_writer_engine.begin() as conn:
        published=seal_pdf_build(conn,frozen,'native')
        assert seal_pdf_build(conn,frozen,'native')==published
    with semantic_reader_engine.connect() as conn:
        assert published_pdf_revision(conn,build.task_id,'native',published.logical_digest)==published
        assert conn.execute(text('SELECT text FROM ops.pdf_published_item WHERE task_id=:task AND text IS NOT NULL'),dict(task=build.task_id)).scalars().all()==['independent expected text']
    with pytest.raises(DBAPIError),semantic_writer_engine.begin() as conn:
        adopt_pdf_companion_batch(conn,build,'health',[{'conversion_status':'failed'}],'late')


def test_seal_requires_validation_and_preserves_private_progress(private_build,semantic_writer_engine,tmp_path):
    build=private_build;stage_complete_native(semantic_writer_engine,build,tmp_path)
    with semantic_writer_engine.begin() as conn:
        frozen=freeze_pdf_build(conn,build,kind="native");prepare_pdf_build(conn,frozen)
    with pytest.raises(DBAPIError),semantic_writer_engine.begin() as conn:
        seal_pdf_build(conn,frozen,'native')
    with semantic_writer_engine.connect() as conn:
        assert published_pdf_revision(conn,build.task_id,'native','0'*64) is None
