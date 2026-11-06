"""Purpose-bound read-only custody/config inspection; never executes a method."""
import json
from datetime import datetime, timezone

from sqlalchemy import text

from corpus_structure.methods.artifact_identity import ArtifactIdentityConfig
from corpus_structure.orchestrate.registry import canonical_numbers
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

SQL = """
SELECT r.id AS run_id, r.status AS run_status, r.sealed,
       t.id AS task_id, t.status AS task_status, cfg.id AS method_config_id,
       m.name AS method, m.version AS method_version, cfg.params,
       (SELECT count(*) FROM ops.task_result tr WHERE tr.task_id=t.id) AS result_count
FROM ops.run r JOIN ops.task t ON t.run_id=r.id
JOIN ops.method_config cfg ON cfg.id=t.method_config_id
JOIN ops.method m ON m.id=cfg.method_id
WHERE r.id=181 AND t.id=1067
"""
with open_runtime_engine(Settings(), 'gs120-artifact-abi-read-only', purpose='evaluate') as engine:
    with engine.connect() as conn, conn.begin():
        conn.exec_driver_sql('SET TRANSACTION READ ONLY')
        row = dict(conn.execute(text(SQL)).mappings().one())
params = row.pop('params')
typed = ArtifactIdentityConfig.model_validate(params)
assert canonical_numbers(typed.model_dump(mode='json')) == params
print(json.dumps({'outcome': 'passed', 'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'database_writes': 'not_run', 'metadata': row, 'stored_scalars': {k: params[k] for k in ('title_threshold', 'policy')}, 'typed_scalars': {k: typed.model_dump(mode='json')[k] for k in ('title_threshold', 'policy')}, 'canonical_roundtrip_exact': True, 'limits': 'Only actual metadata/config inspected; no accepted result exists and no rejected completion payload is claimed.'}, indent=2))
