"""Compare native/Python canonical projection on actual retained provider reports."""
import json
from pathlib import Path
from sqlalchemy import text
from corpus_structure.settings import Settings
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralProductReport
from corpus_structure.semantic.structural_admission import structural_statement, structural_claim_id

raw = Path(__file__).with_name('raw')
checks = []
with open_runtime_engine(Settings(), 'pce-public-projection-control', purpose='maintenance') as engine:
    with engine.connect() as conn:
        conn.execute(text('SET TRANSACTION READ ONLY'))
        for kind in ('normal','mean','comparison','dossier'):
            report = StructuralProductReport.model_validate_json((raw/f'production-{kind}-005.json').read_bytes())
            payload = canonical_bytes(report.model_dump(mode='json',exclude_none=True)).decode()
            row = conn.execute(text("SELECT data.structural_public_statement(CAST(:body AS jsonb)) statement, 'structural:'||encode(sha256(convert_to(data.canonical_json(CAST(:body AS jsonb)-'retrieval_report'),'UTF8')),'hex') product"), {'body':payload}).mappings().one()
            assert row['product'] == report.product_id, kind
            assert canonical_bytes(row['statement']) == canonical_bytes(structural_statement(report)), kind
            checks.append({'kind':kind,'product_id':report.product_id,'claim_id':structural_claim_id(row['statement']),'outcome':'passed'})
result={'outcome':'passed','native_head':'semantic_pce_structpub_20261105','checks':checks,'quality_claim':'projection parity only; not semantic assessment'}
with (raw/'public-projection-147.json').open('x') as out: out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
