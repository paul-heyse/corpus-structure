"""Read-only diagnosis of residual native page provenance, not deployed source adoption."""
from __future__ import annotations
import json
from pathlib import Path
from sqlalchemy import text
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
inputs = json.loads((HERE / 'native-inputs.json').read_bytes())
rows = []
with open_runtime_engine(Settings(), 'gs120-residual-readonly-preview', purpose='maintenance') as engine:
    with read_snapshot(engine) as conn:
        for cut in inputs['cuts']:
            native = cut['native_product']
            # The ordinary root scope wrapper is intentionally awaiting deployment. This
            # read-only diagnostic inspects the already-owned immutable relational view;
            # it does not establish new source-view admission or native guard success.
            selected = conn.execute(text(
                'SELECT n.pointer,n.label,n.native_json FROM '
                'ops.read_pdf_published_revision(:task,:key,:digest) p '
                'CROSS JOIN LATERAL ops.read_pdf_published_section_nodes_rows('
                "p.build_id,p.build_id,'#/body','direct') n WHERE n.role='selected' ORDER BY n.ordinal"
            ), {'task': native['task_id'], 'key': native['product_key'], 'digest': native['content_digest']}).mappings().all()
            page_map = {p['excerpt_physical_page']: p['parent_physical_page'] for p in cut['pages']}
            page_nodes = []
            for node in selected:
                pages = sorted({page_map[prov['page_no']] for prov in node['native_json'].get('prov', ()) if prov.get('page_no') in page_map})
                if pages:
                    page_nodes.append({'pointer': node['pointer'], 'label': node['label'], 'parent_pages': pages})
            rows.append({'file': cut['file'], 'native_product': native, 'residual_members': len(selected),
                         'residual_parent_pages': sorted({p for row in page_nodes for p in row['parent_pages']}),
                         'located_nodes': page_nodes})
covered = {page for row in rows for page in row['residual_parent_pages']}
old_missing = {211,212,221,222,231,232,251,252,253,254,261,262,263,264,281,291,292,301}
result = {'protocol': 'gs120-residual-provenance-preview-1', 'outcome': 'passed',
          'cuts': rows, 'old_missing_parent_pages': sorted(old_missing),
          'old_missing_pages_present_in_retained_residual_native': sorted(old_missing & covered),
          'old_missing_pages_not_found_in_retained_residual_native': sorted(old_missing - covered),
          'scope': 'Read-only native provenance diagnosis only. Current source adoption, root guard/read/publish and semantic coverage remain not_run.'}
with (HERE / 'residual-provenance-preview.json').open('xb') as output:
    output.write(canonical_bytes(result) + b'\n')
print(json.dumps({key: value for key, value in result.items() if key != 'cuts'}))
