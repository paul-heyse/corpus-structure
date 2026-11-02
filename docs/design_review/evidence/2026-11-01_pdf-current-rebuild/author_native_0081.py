"""Normal rollback-only native authoring API, explicitly retiring the frozen8-arg reader.

The CLI intentionally has no retirement selector; this uses its same candidate/plugin path
with the already-supported explicit retirement parameter, never an inferred removal.
"""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from alembic.autogenerate import render_python_code
from sqlalchemy.engine import make_url

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.migrations import current_revision
from corpus_structure.semantic.native_candidate import (
    candidate_admission_sql,
    current_native_state,
    prepare_series_candidate,
    series_native_definitions,
)
from corpus_structure.semantic.native_objects import NativeIdentity
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.companion_export import _publish_directory
from corpus_structure.settings import Settings

DATABASE = "cs_sem_pdf68_author_20261101_44132f1db0"
OUT = Path("build/pdf81-source-freeze")
OLD = NativeIdentity("function", "ops", "read_pdf_frozen_rows", (
    "text", "bigint", "bigint", "text", "text", "text", "jsonb", "integer",
))


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    settings = Settings()
    url = make_url(settings.database.url).set(database=DATABASE)
    selected = settings.model_copy(update={"database": settings.database.model_copy(
        update={"url": url.render_as_string(hide_password=False)}
    )})
    with open_runtime_engine(selected, "pdf81-native-authoring", purpose="maintenance") as engine:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                predecessor = current_revision(conn)
                assert predecessor == "semantic_pdf_evidence_20261101", predecessor
                assert OLD in {item.identity for item in current_native_state(conn)}
                script, authoring = prepare_series_candidate(
                    conn, owned_authoring=True, retire=frozenset({OLD}),
                )
                upgrade = script.upgrade_ops
                assert upgrade is not None
                native = [item for item in upgrade.ops if isinstance(item, NativeTransitionOp)]
                ordinary = len(upgrade.ops) - len(native)
                assert ordinary == 0, ordinary
                admission = candidate_admission_sql(conn, series_native_definitions(conn), authoring.desired)
                rendered = render_python_code(upgrade)
                source = "from alembic import op\nimport sqlalchemy as sa\nfrom corpus_structure.semantic import alembic_native\n\ndef upgrade():\n" + rendered + "\n"
                compile(source, "native_candidate.py", "exec")
                products = {
                    "native_candidate.py": source.encode(),
                    "native_operations.json": canonical_bytes(dict(
                        version=1, predecessor=predecessor,
                        operations=[item.payload() for item in native],
                        desired=[item.payload() for item in authoring.desired],
                    )),
                    "native_admission.sql": admission.encode(),
                }
            finally:
                transaction.rollback()
    OUT.parent.mkdir(exist_ok=True, parents=True)
    with TemporaryDirectory(prefix=".native-candidate-", dir=OUT.parent) as directory:
        prepared = Path(directory) / "candidate"
        prepared.mkdir()
        for name,content in products.items():
            (prepared/name).write_bytes(content)
        _publish_directory(prepared,OUT)
    print(json.dumps(dict(database=DATABASE, predecessor=predecessor, output=str(OUT), desired_objects=len(authoring.desired), native_operations=len(native), ordinary_operations=ordinary, explicit_retirement=OLD.payload(), products=[dict(kind=name,hash=sha256(content).hexdigest())for name,content in products.items()])))


if __name__ == "__main__":
    main()
