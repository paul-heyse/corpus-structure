"""Refresh deployment admission for existing completed consumer releases without rotating them."""
from pathlib import Path
import json
from sqlalchemy import text
from corpus_structure.settings import Settings
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.publication import admit_release

settings=Settings()
with open_runtime_engine(settings,"wce-current-consumer-inventory",purpose="maintenance") as engine:
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT current_database()"))=="corpus_structure_dev"
        releases=tuple(conn.scalars(text("SELECT DISTINCT release_id FROM ops.run WHERE id IN (121,127,130,133,134,135) ORDER BY release_id")))
with open_runtime_engine(settings,"wce-current-deployment-readmission",purpose="admit") as engine:
    with engine.begin() as conn:
        principal=conn.scalar(text("SELECT current_user"))
        assert principal=="corpus_sem_admitter"
        for release in releases:
            prepared=open_release(conn,release)
            admit_release(prepared,connection=conn)
        result=dict(outcome="passed",principal=principal,release_ids=releases,release_identity_changed=False)
Path(__file__).with_name("current-cutover-admission-refresh.json").write_text(json.dumps(result,sort_keys=True)+"\n")
print(json.dumps(result),flush=True)
