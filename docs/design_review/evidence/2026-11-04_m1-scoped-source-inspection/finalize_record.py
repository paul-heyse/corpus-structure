"""Finalize only this evidence folder through the existing evidence store API."""

from datetime import date
from pathlib import Path

from corpus_evidence.model import Record
from corpus_evidence.store import Folder, finalize

HERE = Path(__file__).resolve().parent
SOURCE = 'python/corpus-structure/src/corpus_structure/'
TEST = 'python/corpus-structure/tests/semantic/'
FILES = [SOURCE + p for p in (
    'serve/native_source.py', 'semantic/native_analysis.py',
    'semantic/operations.py', 'semantic/source_views.py',
)] + [TEST + 'test_scoped_native_inspection.py']
record = Record.model_validate(dict(
    schema_version=1,
    id='m1.scoped-source-inspection',
    title='Scoped ordinary formula and cell native inspection',
    group='M1', package='M1-12', finalized=date(2026,11,4),
    status='current', supersedes=[], superseded_by=None,
    question='Can ordinary 1 MiB source inspection retain exact formula/cell custody without full-view or sibling-cell context inflation?',
    answers=['F22'],
    method='Existing exact occurrence and selected source-reference readers; retained projection/recipe validation; focused pure controls and actual read-only query/CLI/registered in-process MCP over old pinned runs 11 and 14.',
    commands=[
        'uv run pytest ' + ' '.join(TEST + name for name in (
            'test_scoped_native_inspection.py','test_native_source_published.py',
            'test_native_source_budgets.py','test_mcp_source_transport.py',
        )) + " -k 'not postgresql and not source_search_preflights_selected_scalar_bytes and not native_queue_ack_refusal'",
        'uv run ruff check ' + ' '.join(FILES),
        'uv run pyrefly check ' + ' '.join(FILES),
        'uv run python docs/design_review/evidence/2026-11-04_m1-scoped-source-inspection/run.py actual-002',
    ],
    agents=[], inputs=[],
    outputs=[dict(path=name) for name in ('run.py','finalize_record.py','raw')],
    depends_on=['2026-11-04_m1-actual-consumers/m1.actual-candidate-consumers124'],
    results=[
        dict(name='Final-source selected pure controls passed',value=82,unit='cases'),
        dict(name='Native database-mutating cases deliberately not selected',value=3,unit='cases'),
        dict(name='Final-source actual retained-read comparisons passed',value=58,unit='comparisons'),
        dict(name='Actual formula complete MCP envelope',value=20859,unit='bytes'),
        dict(name='Actual run11 cell complete MCP envelope',value=35959,unit='bytes'),
        dict(name='Actual run14 cell complete MCP envelope',value=35983,unit='bytes'),
        dict(name='Request byte-work and response allowance',value=1048576,unit='bytes'),
    ],
    outcome='passed',
    conclusion='Final-source focused controls and actual retained run11/run14 query, CLI and registered in-process MCP reads pass at unchanged 1 MiB. Compact source projection/recipe bytes are charged and validated; exact formula health, selected observations and cell-plus-parent custody retain their bindings and support endpoints. Typed small-budget refusals remain. Existing analytical full-view consumers and API v4 work/egress meaning remain. Historical larger-budget/failure receipts remain unchanged. Native127 integration, complete source-context execution, five-family source quality, accepted-reading/default adoption and whole-M1 qualification are separate coordinator obligations.',
    consumed_by=['M1-12','M1-14'],
))
folder = Folder(HERE, records={record.id:record})
finalize(folder, record.id, today=date(2026,11,4))
print('finalized ' + HERE.name + '/' + record.id)
