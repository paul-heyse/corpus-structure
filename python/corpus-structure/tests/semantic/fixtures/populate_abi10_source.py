"""Run only in an exported historical source tree against the caller's owned database.

The caller supplies the database URL through the environment; it is never emitted.
"""

from __future__ import annotations

import base64
import json
import os
from hashlib import sha256
from pathlib import Path

from semantic.test_operations import setup
from semantic.test_parsing_products import _native_build
from sqlalchemy import create_engine, text

from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.semantic import contracts
from corpus_structure.semantic.operations import complete_task, seal_cut
from corpus_structure.semantic.parsing_products import (
    prepare_parsing_product,
    store_parsing_product,
)


def main() -> None:
    root = Path(os.environ["CS_ABI10_SOURCE_ROOT"])
    assert Path(contracts.__file__).is_relative_to(root)
    assert contracts.EXECUTION_COMPILER_VERSION == "10"
    engine = create_engine(os.environ["CS_ABI10_DATABASE_URL"])
    writer = create_engine(os.environ["CS_ABI10_WRITER_URL"])
    try:
        prepared = setup(engine, observations=True, composed=True)
        original = b"<p>A &amp; B <em>retained</em> source.</p>"
        result = build_rendition(
            original,
            compile_profile(load_profile("siegrist")),
            SentenceConfig(),
            source_uri="siegrist_random/random/test/Archive.html",
        )
        assert result.parsing_product is not None
        product = prepare_parsing_product(result.parsing_product.values(), original)
        with writer.begin() as conn:
            run, task, attempt, rendition = _native_build(
                conn, prepared, original, root, content=result.content
            )
            store_parsing_product(
                conn, task_id=task, attempt=attempt, holder="fixture", product=product
            )
            complete_task(
                conn,
                task_id=task,
                attempt=attempt,
                holder="fixture",
                prepared=prepared,
                outcome="empty",
                observations=[],
            )
            seal_cut(conn, run, "abi10-source-final", final=True)
            registry = conn.execute(
                text(
                    "SELECT convert_from(body,'UTF8')::jsonb->'inputs'->>'compiler_version' "
                    "FROM sem.registry_row WHERE release_id=:release AND kind='execution_model'"
                ),
                dict(release=prepared.release_id),
            ).scalar_one()
            assert registry == "10"
        receipt = dict(
            source_revision=os.environ["CS_ABI10_SOURCE_REVISION"],
            source_export_digest=os.environ["CS_ABI10_EXPORT_DIGEST"],
            execution_model_id=prepared.execution_model_id,
            manifest_digest=sha256(prepared.manifest).hexdigest(),
            release_id=prepared.release_id,
            run_id=run,
            task_id=task,
            attempt=attempt,
            rendition_id=rendition,
            compiler_version=registry,
            original_base64=base64.b64encode(original).decode(),
            payload_base64=base64.b64encode(product.payload).decode(),
            product_digest=product.digest,
            contract_digest=product.contract_digest,
            original_digest=sha256(original).hexdigest(),
            producer_file=str(Path(contracts.__file__).relative_to(root)),
        )
        Path(os.environ["CS_ABI10_RECEIPT"]).write_text(json.dumps(receipt, sort_keys=True))
    finally:
        writer.dispose()
        engine.dispose()


if __name__ == "__main__":
    main()
