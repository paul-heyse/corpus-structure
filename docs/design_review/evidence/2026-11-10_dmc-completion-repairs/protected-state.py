"""Read-only protected-state capture; compare bytes before/after adoption."""
import json
from hashlib import sha256

from sqlalchemy import select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

settings = Settings()
result = {"default_project": settings.runtime.default_project}
with open_runtime_engine(settings, "dmc-completion-protected-state", purpose="read") as engine:
    with read_snapshot(engine) as conn:
        for name in ("ops.run", "ops.completed_result"):
            relation = table(name)
            key = relation.c.id if name == "ops.run" else relation.c.run_id
            rows = conn.execute(select(relation).where(key.in_((487, 491, 492, 493, 495))).order_by(key)).mappings().all()
            # String conversion is only for hashing this unchanged observation,
            # not a production encoding or a claim about semantic identity.
            result[name] = sha256(json.dumps([dict(r) for r in rows], default=str, sort_keys=True).encode()).hexdigest()
        project = table("data.project")
        result["projects"] = [dict(r) for r in conn.execute(select(project).order_by(project.c.project_id)).mappings()]
print(canonical_bytes(result).decode())
