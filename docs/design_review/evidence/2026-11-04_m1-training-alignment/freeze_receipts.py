"""Freeze this preparation's inputs, outputs, source paths and exact library sources."""
import json
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def receipt(path,kind):
    data=path.read_bytes()
    return dict(kind=kind,path=str(path.relative_to(ROOT)),sha256=sha256(data).hexdigest(),bytes=len(data),lines=len(data.splitlines()))
rows=[dict(kind='baseline',verified_at=datetime.now(timezone.utc).isoformat(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),release='release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd',run_id=14,cut_id=13,source_views=[22,23],raw_tasks=[36,37],annotation_tasks=[34,35],reference_set=1,protected_fit_passes=[23,24],label_origin='protected C feature_fit capability only',model_revision='54785d51df8d86a0d8f2eb212fec15871aad2c4d',libraries={k:version(k) for k in ('gliner2','torch','transformers')},model_loaded=False,training=False,inference=False,db_writes=False),dict(kind='context7',library='/fastino-ai/gliner2',queries=['Native structured record training explicit character offsets, preserving full record metadata and no-record negatives','Zero-instance structured negatives preserving ChoiceField choices and field declarations'],orientation='Context7 first; installed exact 2.1.0 sources govern boundary behavior; tutorials do not settle full-pack structured choice negatives')]
for path in sorted(HERE.rglob('*')):
    if path.is_file() and path.suffix!='.py' and path.name!='freeze-receipts.jsonl' and not path.name.startswith('attempt-freeze-') and '__pycache__' not in path.parts:
        rows.append(receipt(path,'owned_artifact'))
for relative in ('methods/m1_source.py','methods/source_preparation.py','methods/record_packs.py','methods/m1_annotations.py','methods/gliner.py','semantic/source_contexts.py','semantic/record_contracts.py','evaluate/record_references.py','semantic/operations.py','semantic/runtime.py','semantic/sql/source_views.sql'):
    rows.append(receipt(ROOT/'python/corpus-structure/src/corpus_structure'/relative,'repository_source'))
for relative in ('training/data.py','training/trainer.py','processor.py','processing/word_splitter.py','processing/targets.py','processing/boundary_preprocessing.py','processing/records.py','inference/schema.py','configuration.py'):
    rows.append(receipt(ROOT/'.venv/lib/python3.14/site-packages/gliner2'/relative,'installed_library_source'))
(HERE/'freeze-receipts.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n' for row in rows))
print(json.dumps(dict(outcome='passed',receipts=len(rows),artifact='freeze-receipts.jsonl')))
