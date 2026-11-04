"""Freeze final owned experiment bytes; never load a model or access the database."""
from datetime import datetime,timezone
from hashlib import file_digest
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
OUTPUT=HERE/'freeze-receipts.json'
assert not OUTPUT.exists(),'preserve existing freeze receipt'
rows=[]
for path in sorted(HERE.rglob('*')):
    if not path.is_file() or path==OUTPUT or '__pycache__' in path.parts:continue
    with path.open('rb') as stream:checksum=file_digest(stream,'sha256').hexdigest()
    rows.append(dict(path=str(path.relative_to(HERE)),bytes=path.stat().st_size,sha256=checksum))
OUTPUT.write_text(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(),
    scope='3 loss-only forwards and exactly1 native mixed-batch optimizer step; no efficacy/adoption',
    files=rows),indent=2)+'\n')
print(json.dumps(dict(outcome='passed',files=len(rows),output=str(OUTPUT))))
