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
