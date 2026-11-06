"""Read-only authentication of the exact retained GS120 native adoption inputs."""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import text

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
PROJECT = 'wce-gs120-method-development-20261106'
PARENT = '763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e'


def inventory_sources():
    manifest = json.loads((EVIDENCE / 'source-manifest.json').read_bytes())
    assert manifest['parent_sha256'] == PARENT
    assert manifest['physical_pages'] == list(range(191, 311))
    with open_runtime_engine(Settings(), 'gs120-recovery-inventory', purpose='read') as engine:
        with read_snapshot(engine) as conn:
            baseline = dict(conn.execute(text(
                'SELECT r.id,r.status,r.sealed,r.release_id,c.cut_id FROM ops.run r '
                'JOIN ops.completed_result c ON c.run_id=r.id WHERE r.id=137'
            )).mappings().one())
            assert baseline['status'] == 'finished' and baseline['sealed']
            assert baseline['cut_id'] == 176
            rows = [dict(row) for row in conn.execute(text(
                'SELECT DISTINCT v.document_id,d.source_uri,d.content_hash,'
                'v.native_task_id,v.native_product_key,v.native_content_digest '
                'FROM kb.source_view v JOIN ops.run_source_view m ON m.source_view_id=v.id '
                'JOIN kb.document d ON d.id=v.document_id '
                'WHERE m.run_id=137 AND d.project_id=:project ORDER BY d.source_uri'
            ), {'project': PROJECT}).mappings()]
    by_file = {Path(row['source_uri']).name: row for row in rows}
    if len(rows) != 12 or len(by_file) != 12:
        raise ValueError('retained source run must resolve one native product per twelve cuts')
    cuts = []
    for cut in manifest['cuts']:
        row = by_file[cut['file']]
        actual = sha256((EVIDENCE / 'corpus' / cut['file']).read_bytes()).hexdigest()
        if actual != cut['sha256'] or row['content_hash'] != cut['sha256']:
            raise ValueError('original/source manifest bytes changed for ' + cut['file'])
        if row['native_product_key'] != 'organized':
            raise ValueError('recovery requires the retained organized native product')
        cuts.append({
            **cut,
            'document_id': row['document_id'],
            'source_uri': row['source_uri'],
            'native_product': {
                'task_id': row['native_task_id'],
                'product_key': row['native_product_key'],
                'content_digest': row['native_content_digest'],
            },
            'parent_pdf_sha256': PARENT,
            'original_run_id': 137,
            'original_cut_id': 176,
        })
    return {'protocol': 'gs120-recovery-native-inventory-1', 'outcome': 'passed',
            'project_id': PROJECT, 'original_completed_source': baseline,
            'parent_pdf_sha256': PARENT, 'parent_physical_pages': list(range(191, 311)),
            'cuts': cuts, 'scope': 'Original file hashes and exact retained native products; '
            'no PDF conversion, recognition, model extraction or database mutation'}


if __name__ == '__main__':
    result = inventory_sources()
    output = HERE / 'native-inputs.json'
    with output.open('xb') as stream:
        stream.write(canonical_bytes(result) + b'\n')
    print(json.dumps({'outcome': 'passed', 'cuts': len(result['cuts']),
                      'pages': len(result['parent_physical_pages']), 'output': str(output)}))
