"""Read-only preservation witness for the preceding operational target, never the defaults."""

import json

from sqlalchemy import text

from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

settings = Settings(database={
    "url": "postgresql://corpus_sem_writer@/corpus_efficiency_20261030"
           "?host=/var/run/postgresql&port=5434",
})
result = {}
with open_runtime_engine(settings, "parsing-previous-preservation", purpose="maintenance") as engine:
    with engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        for name in ("data.project", "ops.run", "ops.completed_result",
                     "eval.reference_evaluation", "eval.reference_pass"):
            count, digest = conn.execute(text(
                "SELECT count(*), md5(string_agg(row_value, E'\\n' ORDER BY row_value)) "
                f"FROM (SELECT to_jsonb(t)::text AS row_value FROM {name} t) records"
            )).one()
            result[name] = dict(count=count, digest=digest)
        result["native_revision"] = conn.scalar(text("SELECT version_num FROM public.semantic_alembic_version"))
print(json.dumps(result, indent=2))
