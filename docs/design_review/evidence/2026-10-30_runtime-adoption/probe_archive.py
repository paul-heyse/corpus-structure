"""Read-only cold/warm opening against one explicitly bound finalized archive."""
import json
import time
from sqlalchemy import event, select
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

with open_runtime_engine(Settings(), 'efficiency-archive-observation', purpose='read') as engine:
    with engine.connect() as conn:
        release_id = conn.scalar(select(table('sem.release_finalization').c.release_id).order_by(table('sem.release_finalization').c.release_id).limit(1))
        if release_id is None:
            raise RuntimeError('a finalized archive is required')
        queries = []
        def observed(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)
        event.listen(engine, 'before_cursor_execute', observed)
        results = []
        for phase in ('cold', 'warm'):
            queries.clear()
            started = time.perf_counter()
            prepared = open_release(conn, release_id)
            results.append({'phase': phase, 'seconds': time.perf_counter()-started, 'queries': len(queries), 'payload_selects': sum('sem.release.prepared_bytes' in q for q in queries), 'release_id': prepared.release_id})
        print(json.dumps(results, indent=2))
