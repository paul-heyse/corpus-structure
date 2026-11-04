"""Freeze the bounded native target-conditioning evidence without model/DB access."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / 'freeze-receipts.json'
assert not OUTPUT.exists(), 'preserve existing freeze receipt'
files = [dict(path=str(path.relative_to(HERE)), bytes=path.stat().st_size,
              sha256=sha256(path.read_bytes()).hexdigest())
         for path in sorted(HERE.rglob('*')) if path.is_file() and path != OUTPUT
         and '__pycache__' not in path.parts]
OUTPUT.write_text(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(),
    scope='metadata-only native target construction; no model/forward/loss/training/DB',
    files=files), indent=2) + '\n')
print(json.dumps(dict(outcome='passed', files=len(files), output=str(OUTPUT))))
