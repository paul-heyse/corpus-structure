"""Receipt hashes for final immutable authored bytes; no semantic mutation."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text())
log=(root/'validation-003.log').read_text()
assert 'passed all11units frozen-contract-source-coordinates' in log
assert '\nfailed unit-' not in log
manifest['validation']={'outcome':'passed','command':'uv run python docs/design_review/evidence/2026-11-04_m1-independent-references/author-B-v3/validate.py','receipt':'validation-003.log','date':'2026-11-04','scope':'All eleven final authored batches; exact frozen release, schema/family roles, identities, source coordinates and evaluation cut. No quality or agreement claim.','earlier_attempts_retained':['validation-001.log','validation-002.log']}
manifest['coverage']={'native_items_inspected':822,'projected_pieces_inspected':1869,'limitations_retained':126,'units':11,'origins':3,'five_families_inspected':True}
manifest['output_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(root.iterdir()) if f.is_file() and f.name!='manifest.json'}
(root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print(json.dumps({'outcome':'passed','records':sum(manifest['counts_total'].values()),'output_files_hashed':len(manifest['output_sha256']),'manifest_sha256':hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()},sort_keys=True))
