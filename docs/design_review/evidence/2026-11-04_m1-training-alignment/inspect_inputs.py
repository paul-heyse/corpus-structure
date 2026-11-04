"""Read only authorized feature-fit labels and run-14 source/configuration metadata."""
from pathlib import Path
import json
from sqlalchemy import text
from corpus_structure.settings import Settings
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.evaluate.record_references import read_fitting_references
from corpus_structure.semantic.identity import canonical_bytes

HERE = Path(__file__).resolve().parent
with open_runtime_engine(Settings(), 'm1-training-alignment-fit', purpose='fit') as engine, engine.connect() as conn:
    refs = read_fitting_references(conn, set_id=1)
    (HERE / 'feature-fit-protected.json').write_bytes(canonical_bytes(refs))
    print('fit rows', len(refs), 'keys', [list(x) for x in refs])
with open_runtime_engine(Settings(), 'm1-training-alignment-source', purpose='read') as engine, engine.connect() as conn:
    rows = conn.execute(text('SELECT t.id,t.unit_id,t.input_hash,c.* FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id WHERE t.run_id=14 AND t.id IN (34,35,36,37) ORDER BY t.id')).mappings().all()
    (HERE / 'task-configs.json').write_text(json.dumps([dict(x) for x in rows], default=str, indent=2))
    print('configs', [(x['id'],list(x)) for x in rows])
