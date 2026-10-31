"""Controlled retained-PDF inputs for real publication/CLI lifecycle; no provider qualification."""

from __future__ import annotations

import textwrap
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    GroupLabel,
    PageItem,
    ProvenanceItem,
    Size,
)
from pydantic import create_model

from corpus_structure.ingest.pdf import PdfConversion, PdfConverter, publication_payload
from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.ingest.pdf_candidates import rediscover_candidates
from corpus_structure.ingest.pdf_hierarchy import load_snapshot, snapshot
from corpus_structure.ingest.pdf_worker import PdfWorker
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    record_method,
)
from corpus_structure.semantic.pdf_contracts import (
    pdf_context_for_task,
    prepare_pdf_product,
    store_pdf_original,
    store_pdf_product,
)


class NoInferenceConverter(PdfConverter):
    def _prepare(self) -> None:
        raise AssertionError(
            "controlled retained-input acceptance forbids PDF conversion inference"
        )

    def formula_stage(self):
        raise AssertionError("controlled retained-input acceptance forbids formula inference")


def no_inference_child(connection, recipe, assets):
    from corpus_structure.ingest import pdf_worker

    pdf_worker.PdfConverter = NoInferenceConverter
    pdf_worker._native_child(connection, recipe, assets)


class NoInferenceWorker(PdfWorker):
    _child_target = staticmethod(no_inference_child)


def install_no_inference_boundary(monkeypatch, directory: Path) -> None:
    """Only acquisition is doubled; child compute, original backend and custody stay real."""
    directory.mkdir(parents=True, exist_ok=True)
    assets = PreparedPdfAssets(directory, b'{"fixture":"no-model-assets"}', (), ())
    monkeypatch.setattr(
        "corpus_structure.ingest.pdf_methods.prepare_pdf_assets", lambda recipe, **kwargs: assets
    )
    monkeypatch.setattr("corpus_structure.ingest.pdf_methods.PdfWorker", NoInferenceWorker)


def retained_document(original: bytes, sections) -> PdfConversion:
    document = DoclingDocument(name="Controlled retained native source; no inference")
    for page_number, (title, paragraphs) in enumerate(sections, 1):
        document.pages[page_number] = PageItem(
            page_no=page_number, size=Size(width=612, height=792)
        )
        group = document.add_group(label=GroupLabel.SECTION, name=title)
        document.add_heading(
            text=title,
            level=1,
            parent=group,
            prov=ProvenanceItem(
                page_no=page_number,
                bbox=BoundingBox(l=36, t=34, r=575, b=62, coord_origin=CoordOrigin.TOPLEFT),
                charspan=(0, len(title)),
            ),
        )
        y = 700
        for paragraph in paragraphs:
            lines = len(textwrap.wrap(paragraph, width=85))
            document.add_text(
                label=DocItemLabel.TEXT,
                text=paragraph,
                orig=paragraph,
                parent=group,
                prov=ProvenanceItem(
                    page_no=page_number,
                    bbox=BoundingBox(
                        l=34,
                        t=792 - y - 15,
                        r=580,
                        b=792 - y + 15 * (lines - 1) + 6,
                        coord_origin=CoordOrigin.TOPLEFT,
                    ),
                    charspan=(0, len(paragraph)),
                ),
            )
            y -= 15 * lines + 15
    pages = rediscover_candidates(original, tuple(range(1, len(sections) + 1)), parser_threads=1)
    assert all(page.has_words and page.has_vectors and not page.candidates for page in pages)
    return PdfConversion(
        sha256(original).hexdigest(),
        b'{"fixture":"controlled-native-prose-no-inference"}',
        snapshot(document),
        "success",
        (),
        (),
        (),
        None,
        inline_candidates=pages,
    )


def seed_retained_product(settings, *, domain, corpus, domains, conversion):
    """Acquire a native pin through actual admitted, claimed, restricted writer publication."""
    from sqlalchemy import select

    from corpus_structure.orchestrate.project import init_bound_project
    from corpus_structure.semantic.authored_sql import (
        admit_archived_sql,
        analyze_archived_sql,
        has_authored_sql,
    )
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import admit_release
    from corpus_structure.semantic.regeneration import prepare_pack
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    bundle, dependencies, profile, prepared = prepare_pack(domains / domain)
    source_id = f"source:acceptance:{prepared.release_id}"
    with open_runtime_engine(settings, "acceptance-native-admit", purpose="admit") as engine:
        with engine.begin() as conn:
            persist_release(conn, bundle, dependencies, profile, prepared)
            if not has_authored_sql(prepared):
                admit_release(prepared, connection=conn)
        if has_authored_sql(prepared):
            with (
                open_runtime_engine(settings, "acceptance-native-read", purpose="read") as reader,
                reader.connect() as conn,
            ):
                analyzed = analyze_archived_sql(conn, prepared.release_id)
            with engine.begin() as conn:
                admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
                admit_release(prepared, connection=conn)
    original = (
        (corpus / "toy.pdf").read_bytes()
        if domain == "toy"
        else (corpus / "fixture.pdf").read_bytes()
    )
    assert sha256(original).hexdigest() == conversion.original_digest
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    with open_runtime_engine(settings, "acceptance-native-publish", purpose="write") as engine:
        with engine.begin() as conn:
            init_bound_project(
                conn,
                domain=domain,
                corpus=corpus,
                release_id=prepared.release_id,
                realization_id=source_id,
                name="acceptance",
                domains=domains,
            )
            document_id = conn.execute(
                select(table("kb.document").c.id).where(
                    table("kb.document").c.project_id == "acceptance"
                )
            ).scalar_one()
            run = create_run(
                conn,
                project_id="acceptance",
                binding=OperationBinding(prepared.release_id, source_id, 0, b"{}"),
                kind="full",
                options={},
                code_commit="controlled-retained-input-fixture",
            )
            method = SimpleNamespace(
                name="pdf.controlled-retained-fixture",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
                unit_type="document",
                Config=create_model("ControlledRetainedPdfConfig"),
            )
            config = record_method(conn, method, "default", {}, "controlled-retained-pdf")
            task = create_task(
                conn,
                run_id=run,
                config_id=config,
                stage="ingest",
                unit_type="document",
                unit_id=document_id,
                unit_key="controlled-retained-pdf",
                input_hash=conversion.original_digest,
            )
            claim = claim_tasks(
                conn, run_id=run, config_id=config, holder="controlled-native-fixture"
            )[0]
            store_pdf_original(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder="controlled-native-fixture",
                original=original,
                recipe_bytes=conversion.recipe,
            )
        with engine.begin() as conn:
            product = prepare_pdf_product(
                publication_payload(
                    conversion,
                    product_key="controlled-native",
                    schema_digest=sha256(schema).hexdigest(),
                    section_refs=frozenset(
                        group.self_ref
                        for group in load_snapshot(conversion.native).groups
                        if str(group.label) == "section"
                    ),
                ),
                original,
                schema,
                conversion.recipe,
                context=pdf_context_for_task(conn, task),
            )
            store_pdf_product(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder="controlled-native-fixture",
                product=product,
            )
            complete_task(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder="controlled-native-fixture",
                prepared=prepared,
                observations=[],
                outcome="empty",
            )
    return {"task_id": task, "product_key": "controlled-native", "content_digest": product.digest}
