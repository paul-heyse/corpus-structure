from pathlib import Path
import json
from dataclasses import asdict
from sqlalchemy import select
from corpus_structure.settings import Settings
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.operations import run_view
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.identity import canonical_bytes

folder=Path(__file__).parent
with open_runtime_engine(Settings(), 'm1-recovery-source-inventory', purpose='read') as engine:
    with engine.connect() as conn:
        runs=table('ops.run')
        original=dict(conn.execute(select(runs).where(runs.c.id==14)).mappings().one())
        prepared=open_release(conn, original['release_id'])
        view=run_view(conn,14,prepared)
        refs=view.reader.source_views()
        heading=next(ref for ref in refs if ref.id==22)
        reader=published_record_reader(conn,heading.native_product,projection_context=prepared)
        section=reader.selected_native_items((heading.section_pointer,))[heading.section_pointer]
        record=dict(run14=dict(project_id=original['project_id'],release_id=original['release_id'], input_realization_id=original['input_realization_id'],input_revision=original['input_revision'],status=original['status']), heading=asdict(heading),section=section,selected_view_ids=[ref.id for ref in refs],dependencies=json.loads(original['dependencies']))
        (folder/'source-inventory.json').write_bytes(canonical_bytes(record))
        print(json.dumps(dict(run14=record['run14'],heading=record['heading'],section=section),default=str))
