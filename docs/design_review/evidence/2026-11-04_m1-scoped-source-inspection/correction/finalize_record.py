"""Finalize the separate corrected result and only its predecessor's supersession metadata."""

from datetime import date
from pathlib import Path

from corpus_evidence.model import Record
from corpus_evidence.store import Folder, content_hash, finalize, write

HERE = Path(__file__).resolve().parent.parent
OLD_ID = 'm1.scoped-source-inspection'
NEW_ID = 'm1.scoped-source-inspection-correction'
SOURCE = 'python/corpus-structure/src/corpus_structure/'
TEST = 'python/corpus-structure/tests/semantic/'
files = [SOURCE + name for name in (
    'serve/native_source.py','semantic/native_analysis.py','semantic/operations.py',
    'semantic/source_views.py','semantic/pdf_record_reader.py',
)] + [TEST + 'test_scoped_native_inspection.py']
old = Record.model_validate_json((HERE / 'records' / (OLD_ID + '.json')).read_bytes())
assert all(content_hash(HERE / ref.path) == ref.sha256 for ref in old.outputs)
record = Record.model_validate(dict(
    schema_version=1, id=NEW_ID, title='Chart parent custody and complete compact source inventory',
    group='M1', package='M1-12', finalized=date(2026,11,4), status='current',
    supersedes=[OLD_ID], superseded_by=None,
    question='Does scoped source inspection preserve valid chart parents and complete retained pointer inventory without sibling body hydration?',
    answers=['F22'],
    method='Existing protected native item statement projected to bounded placement/address scalars; exact cell-parent kind mapping; matching-corrupt inventory controls and actual read-only retained run11/run14 query/CLI/registered in-process MCP.',
    commands=[
        'uv run pytest ' + ' '.join(TEST + name for name in (
            'test_scoped_native_inspection.py','test_native_source_published.py',
            'test_native_source_budgets.py','test_mcp_source_transport.py',
        )) + " -k 'not postgresql and not source_search_preflights_selected_scalar_bytes and not native_queue_ack_refusal'",
        'uv run ruff check ' + ' '.join(files),
        'uv run pyrefly check ' + ' '.join(files),
        'uv run python docs/design_review/evidence/2026-11-04_m1-scoped-source-inspection/correction/run.py actual-final-001',
    ], agents=[], inputs=[],
    outputs=[dict(path=path) for path in (
        'correction/run.py','correction/finalize_record.py','correction/raw',
    )], depends_on=[],
    results=[
        dict(name='Final-source selected pure controls passed', value=90,unit='cases'),
        dict(name='Native database-mutating cases not selected',value=3,unit='cases'),
        dict(name='Actual retained-read comparisons passed',value=58,unit='comparisons'),
        dict(name='Formula complete MCP response',value=20859,unit='bytes'),
        dict(name='Run11 table-cell complete MCP response',value=35959,unit='bytes'),
        dict(name='Run14 table-cell complete MCP response',value=35983,unit='bytes'),
        dict(name='Unchanged shared work/response allowance',value=1048576,unit='bytes'),
    ], outcome='passed',
    conclusion='Corrected final source passes table/chart parent-kind controls, complete item/ancestor inventory checks including nonexistent pointers with matching recomputed projection digests, scoped lint/types and actual retained run11/run14 query/CLI/registered in-process MCP at unchanged 1 MiB. Only placement/address scalar inventory is transferred before selected formula hydration; existing budgets and complete SDK envelope limits remain. Original finalized conclusions/results/hashes/raw bytes are retained with supersession metadata only. Actual chart-provider/PDF journeys, native full regression, preparation-only reconstruction, accepted/five-family quality/default adoption and whole-M1 qualification remain separate coordinator obligations.',
    consumed_by=['M1-12','M1-14'],
))
folder = Folder(HERE, records={OLD_ID:old,NEW_ID:record})
finalize(folder, NEW_ID, today=date(2026,11,4))
updated = old.model_copy(update={'status':'superseded','superseded_by':NEW_ID})
write(folder, Record.model_validate(updated.model_dump()))
print('finalized ' + NEW_ID + '; predecessor supersession metadata only')
