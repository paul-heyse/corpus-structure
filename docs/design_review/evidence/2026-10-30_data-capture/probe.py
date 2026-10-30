"""Run the bounded real-store capacity case and retain its declared observations."""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[4]
command = ["uv", "run", "pytest", "-q", "-s",
           "python/corpus-structure/tests/semantic/test_capture_capacity.py"]
result = subprocess.run(command, cwd=root, capture_output=True, text=True)
folder = Path(__file__).parent
(folder / "run.log").write_text(result.stdout + result.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
observations = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{"rows"')]
assert len(observations) == 1
record = dict(observations=observations,
              versions={name: importlib.metadata.version(name) for name in
                        ("pyarrow", "duckdb", "adbc-driver-postgresql", "psycopg", "pgpq")},
              command=" ".join(command),
              boundary="real PostgreSQL/ADBC capture, normalization, hash and Parquet closure; model/store setup excluded")
(folder / "result.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
