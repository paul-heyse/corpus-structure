"""Forward parsing migrations retain pre-product source and rendition identities."""

from hashlib import sha256

from sqlalchemy import insert, select, text

from corpus_structure.core.evidence import (
    RenditionContent,
    Segment,
    content_digest,
    document_key,
    rendition_key,
)
from corpus_structure.core.vocab import SegmentKind
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.migrations import current_revision, head_revision, upgrade
from corpus_structure.semantic.operations import read_original


def test_forward_parsing_migrations_preserve_pre_product_sources(semantic_database_at, tmp_path):
    original = b"<p>retained historical source</p>"
    acquired = tmp_path / "original.html"
    acquired.write_bytes(original)
    content = RenditionContent(
        canonical_text="retained historical source",
        document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=26),
    )
    source_key = document_key("prior", "file:prior", sha256(original).hexdigest())
    digest = content_digest(content)
    with semantic_database_at("semantic_0040") as engine:
        with engine.begin() as conn:
            conn.execute(insert(table("data.project")).values(project_id="prior"))
            document_id = conn.execute(
                insert(table("kb.document"))
                .values(
                    project_id="prior",
                    key=source_key,
                    source_uri="file:prior",
                    content_hash=sha256(original).hexdigest(),
                    original_path=str(acquired),
                    mime="text/html",
                    meta={},
                )
                .returning(table("kb.document").c.id)
            ).scalar_one()
            conn.execute(
                insert(table("kb.rendition")).values(
                    document_id=document_id,
                    key=rendition_key(source_key, digest),
                    content_digest=digest,
                    canonical_text=content.canonical_text,
                    content=content.model_dump(mode="json"),
                    parse_status=str(content.parse_status),
                )
            )
            snapshot = conn.execute(
                text(
                    "SELECT row_to_json(d), row_to_json(r) FROM kb.document d "
                    "JOIN kb.rendition r ON r.document_id=d.id WHERE d.id=:document"
                ),
                {"document": document_id},
            ).one()
        with engine.begin() as conn:
            upgrade(conn)
            assert current_revision(conn) == head_revision()
            retained = conn.execute(
                text(
                    "SELECT row_to_json(d), row_to_json(r) FROM kb.document d "
                    "JOIN kb.rendition r ON r.document_id=d.id WHERE d.id=:document"
                ),
                {"document": document_id},
            ).one()
            assert retained == snapshot
            # Historical acquisition remains readable without inventing a parsing product
            # or claiming its bytes were already retained in the new artifact relation.
            assert read_original(conn, document_id) == original
            assert conn.execute(select(table("kb.source_artifact"))).first() is None
            assert conn.execute(select(table("ops.parsing_product"))).first() is None


def test_populated_abi10_source_survives_forward_guards(
    semantic_database_at, native_settings, tmp_path
):
    """Compile/publish with actual historical code, then read through the current boundary."""
    import base64
    import json
    import os
    import subprocess
    import sys
    import tarfile
    from pathlib import Path

    import pytest
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.contracts import execution_payload, require_bound_operation
    from corpus_structure.semantic.execution_admission import (
        ExecutionAdmissionError,
        admit_execution_release,
    )
    from corpus_structure.semantic.operations import BoundReader, OperationBinding, create_run
    from corpus_structure.semantic.parsing_products import (
        ProductReference,
        read_layered_product,
        read_parsing_product,
    )
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.types import PreparationError
    from native_test_support import principal_engine

    historical = "abd387838cfc05fdf0a1387481dec3d32df4ec68"
    repo = Path(__file__).resolve().parents[4]
    export = tmp_path / "abi10-source"
    export.mkdir()
    archive = tmp_path / "abi10-source.tar"
    with archive.open("wb") as stream:
        subprocess.run(
            [
                "git",
                "archive",
                "--format=tar",
                historical,
                "python/corpus-structure/src",
                "python/corpus-structure/tests/semantic/test_operations.py",
                "python/corpus-structure/tests/semantic/test_parsing_products.py",
                "python/corpus-structure/tests/semantic/__init__.py",
                "sources",
            ],
            cwd=repo,
            stdout=stream,
            check=True,
        )
    with tarfile.open(archive) as source:
        source.extractall(export, filter="data")
    receipt_path = tmp_path / "abi10-receipt.json"
    script = Path(__file__).with_name("fixtures") / "populate_abi10_source.py"
    with semantic_database_at("semantic_0042") as engine:
        writer = principal_engine(native_settings, "write", engine.url.database)
        environment = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                (
                    str(export / "python/corpus-structure/src"),
                    str(export / "python/corpus-structure/tests"),
                )
            ),
            "CS_ABI10_SOURCE_ROOT": str(export),
            "CS_ABI10_DATABASE_URL": engine.url.render_as_string(hide_password=False),
            "CS_ABI10_RECEIPT": str(receipt_path),
            "CS_ABI10_WRITER_URL": writer.url.render_as_string(hide_password=False),
            "CS_ABI10_SOURCE_REVISION": historical,
            "CS_ABI10_EXPORT_DIGEST": sha256(archive.read_bytes()).hexdigest(),
        }
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=export,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        writer.dispose()
        assert completed.returncode == 0, completed.stdout + completed.stderr
        receipt = json.loads(receipt_path.read_text())
        with engine.begin() as conn:
            before = conn.execute(
                text(
                    "SELECT product_digest,contract_digest,payload FROM ops.parsing_product "
                    "WHERE task_id=:task"
                ),
                dict(task=receipt["task_id"]),
            ).one()
            upgrade(conn)
            after = conn.execute(
                text(
                    "SELECT product_digest,contract_digest,payload FROM ops.parsing_product "
                    "WHERE task_id=:task"
                ),
                dict(task=receipt["task_id"]),
            ).one()
            assert before == after
            assert bytes(after.payload) == base64.b64decode(receipt["payload_base64"])
            assert after.product_digest == receipt["product_digest"]
            assert after.contract_digest == receipt["contract_digest"]
        reader = principal_engine(native_settings, "read", engine.url.database)
        admitter = principal_engine(native_settings, "admit", engine.url.database)
        try:
            with reader.begin() as conn:
                archived = open_release(conn, receipt["release_id"])
                payload = execution_payload(archived)
                assert payload is not None
                assert json.loads(payload)["inputs"]["compiler_version"] == "10"
                product = read_parsing_product(conn, task_id=receipt["task_id"])
                assert product is not None
                assert product.payload == bytes(after.payload)
                assert product.original == base64.b64decode(receipt["original_base64"])
                reference = ProductReference(
                    receipt["task_id"], "source", receipt["product_digest"]
                )
                assert read_layered_product(conn, reference) == product
                assert (
                    BoundReader(conn, receipt["run_id"], archived).parsing_product(
                        receipt["rendition_id"]
                    )
                    == product
                )
                selected = BoundReader(conn, receipt["run_id"], archived).layered_products(
                    receipt["rendition_id"], kind="source"
                )
                assert selected[0].reference == reference
            with pytest.raises(
                PreparationError, match="historical execution products are read-only"
            ):
                require_bound_operation(archived, "start_run")
            writer = principal_engine(native_settings, "write", engine.url.database)
            try:
                with (
                    writer.begin() as conn,
                    pytest.raises(DBAPIError, match="historical execution ABI is read-only"),
                    conn.begin_nested(),
                ):
                    create_run(
                        conn,
                        project_id="p",
                        binding=OperationBinding(archived.release_id, "z", 0, b"{}"),
                        kind="full",
                        options={},
                        code_commit="abi10-write-must-refuse",
                    )
            finally:
                writer.dispose()
            with (
                admitter.begin() as conn,
                pytest.raises(ExecutionAdmissionError, match="execution ABI"),
                conn.begin_nested(),
            ):
                admit_execution_release(archived, connection=conn)
        finally:
            reader.dispose()
            admitter.dispose()
