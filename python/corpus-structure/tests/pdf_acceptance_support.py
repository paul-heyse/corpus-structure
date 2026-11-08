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

    def forbidden_recognition(*args, **kwargs):
        raise AssertionError("controlled retained-input acceptance forbids recognition inference")

    monkeypatch.setattr(
        "corpus_structure.ingest.pdf_recognition_methods.RecognitionWorker", forbidden_recognition
    )
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


def seed_retained_integrated_product(
    settings, *, domain, corpus, domains, conversion, observation, raw_response, artifacts
):
    """Publish controlled native/layout evidence and its exact selected integrated product."""
    from semantic.method_dimensions_support import prepare_fixture_pack
    from sqlalchemy import select

    from corpus_structure.orchestrate.project import init_bound_project
    from corpus_structure.semantic.authored_sql import (
        admit_archived_sql,
        analyze_archived_sql,
        has_authored_sql,
    )
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import admit_release
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    bundle, dependencies, profile, prepared = prepare_fixture_pack(
        domains / domain, "pdf.controlled-retained-fixture"
    )
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
            config = record_method(
                conn, method, "default", {}, "controlled-retained-pdf", prepared=prepared
            )
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
        from corpus_structure.ingest.pdf_record_product import native_publication_draft
        from corpus_structure.orchestrate.pdf_streaming import publish_pdf_record_draft

        raw_pin = publish_pdf_record_draft(
            engine,
            claim,
            "controlled-native-fixture",
            native_publication_draft(
                conversion, product_key="controlled-native", original=original, schema_bytes=schema
            ),
            directory=settings.paths.data_dir / "controlled-records",
            check_active=lambda: None,
        )
        with engine.begin() as conn:
            from corpus_structure.ingest.pdf_reconciliation import select_pdf_integration
            from corpus_structure.semantic.pdf_integrated import (
                prepare_integrated_pdf_product,
                store_pdf_observation,
            )

            context = pdf_context_for_task(conn, task)
            evidence = prepare_integrated_pdf_product(
                observation, original, conversion.recipe, artifacts=artifacts, context=context
            )
            store_pdf_observation(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder="controlled-native-fixture",
                product=evidence,
            )
            selected = select_pdf_integration(
                product.values(),
                {
                    "task_id": task,
                    "product_key": "controlled-native",
                    "content_digest": raw_pin.logical_digest,
                    "role": "structural",
                },
                [
                    (
                        {
                            "task_id": task,
                            "product_key": observation["product_key"],
                            "content_digest": evidence.digest,
                            "role": "recognition",
                        },
                        evidence.values(),
                        raw_response,
                    )
                ],
                original,
                conversion.recipe,
                schema,
                context=context,
                product_key="controlled-integrated",
            )
        from corpus_structure.core.method import PdfRecordPublicationDraft

        selected_values = selected.values()
        content = selected_values["content"]
        selected_pin = publish_pdf_record_draft(
            engine,
            claim,
            "controlled-native-fixture",
            PdfRecordPublicationDraft(
                document=DoclingDocument.model_validate(content["document"]),
                product_key="controlled-integrated",
                kind="integrated",
                original=original,
                schema_bytes=schema,
                recipe_bytes=conversion.recipe,
                health=content["health"],
                companions={
                    **{
                        family: selected_values.get(
                            {
                                "input": "inputs",
                                "occurrence": "occurrences",
                                "relation": "relations",
                                "mapping_report": "mapping_reports",
                            }.get(family, family),
                            (),
                        )
                        for family in (
                            "input",
                            "occurrence",
                            "relation",
                            "mapping_report",
                            "coverage",
                        )
                    },
                    "health": (
                        {"health": content["health"], "source_scope": content["source_scope"]},
                        selected_values["health"],
                    ),
                },
                metadata={
                    kind: content[kind]
                    for kind in (
                        "inline_candidate_pages",
                        "recognition_coverage",
                        "derivation_mappings",
                        "cell_reports",
                        "inline_alignment_reports",
                        "runtime_report",
                    )
                    if kind in content
                },
            ),
            directory=settings.paths.data_dir / "controlled-records",
            check_active=lambda: None,
        )
        with engine.begin() as conn:
            complete_task(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder="controlled-native-fixture",
                prepared=prepared,
                observations=[],
                outcome="empty",
            )
    return {
        "task_id": task,
        "product_key": "controlled-integrated",
        "content_digest": selected_pin.logical_digest,
    }


def write_controlled_pdf(path: Path, paragraphs: tuple[str, ...]) -> bytes:
    """Use the existing authored PDF builder; no converter or recognizer is involved."""
    import runpy

    builder = runpy.run_path(str(Path(__file__).resolve().parents[3] / "fixtures/toy/build_pdf.py"))
    builder["write_pdf"](path, ((paragraphs[0], paragraphs[1:]),))
    return path.read_bytes()


def publish_controlled_pdf_views(
    engine, *, prepared, run_id, document_id, original, paragraphs, keys=None, source_claim=None
):
    """Retain authored sections; a supplied claim leaves terminal settlement with its owner."""
    from dataclasses import replace
    from tempfile import TemporaryDirectory

    from semantic.native_record_fixtures import publish_native_record_fixture

    from corpus_structure.ingest.pdf_section_views import published_section_drafts
    from corpus_structure.semantic.operation_results import MethodConfigId, RunId
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.source_views import load_source_view, store_source_view

    document = DoclingDocument(name="Controlled source reports; no inference")
    root = document.add_group(label=GroupLabel.SECTION, name="People")
    sections = [root]
    for index in range(1, len(paragraphs)):
        sections.append(
            document.add_group(
                label=GroupLabel.SECTION,
                name="Other" if index == 1 else f"Other {index}",
                parent=root,
            )
        )
    for index, paragraph in enumerate(paragraphs):
        document.add_text(
            label=DocItemLabel.TEXT,
            text=paragraph,
            orig=paragraph,
            parent=sections[min(index, len(sections) - 1)],
        )
    conversion = PdfConversion(
        sha256(original).hexdigest(),
        b'{"fixture":"controlled-native-report-v1"}',
        snapshot(document),
        "success",
        (),
        (),
        (),
        None,
    )
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    with engine.begin() as conn:
        if source_claim is None:
            config = record_method(
                conn,
                SimpleNamespace(
                    name="pdf.controlled-source",
                    version="1",
                    family="ingest",
                    tier="deterministic",
                    confidence_source=None,
                    unit_type="document",
                    Config=create_model("ControlledSource"),
                ),
                "default",
                {},
                "controlled-source-config",
                prepared=prepared,
            )
            task = create_task(
                conn,
                run_id=run_id,
                config_id=config,
                stage="ingest",
                unit_type="document",
                unit_id=document_id,
                unit_key="controlled-source",
                input_hash=conversion.original_digest,
            )
            claim = claim_tasks(
                conn,
                run_id=RunId(run_id),
                config_id=MethodConfigId(config),
                holder="controlled-source",
            )[0]
        else:
            claim = source_claim
            task = claim.task_id
        store_pdf_original(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder=claim.holder,
            original=original,
            recipe_bytes=conversion.recipe,
        )
        payload = publication_payload(
            conversion,
            product_key="native",
            schema_digest=sha256(schema).hexdigest(),
            section_refs=frozenset(section.self_ref for section in sections),
        )
        product = prepare_pdf_product(
            payload, original, schema, conversion.recipe, context=pdf_context_for_task(conn, task)
        )
    with TemporaryDirectory(prefix="controlled-native-views-") as directory:
        published = publish_native_record_fixture(
            engine,
            Path(directory),
            task_id=task,
            attempt=claim.attempt,
            holder=claim.holder,
            product=product,
            document=document,
        )
    with engine.begin() as conn:
        reader = published_record_reader(
            conn,
            ProductReference(task, "native", published.logical_digest),
            projection_context=prepared,
        )
        if reader is None:
            raise AssertionError("controlled source has no published record binding")
        views = []
        for index, (key, section) in enumerate(
            zip(keys if keys is not None else (None,) * len(sections), sections, strict=True)
        ):
            membership = "descendants" if index == 0 and len(sections) > 1 else "direct"
            (draft,) = published_section_drafts(
                reader,
                document_id=document_id,
                selections=(section.self_ref,),
                membership=membership,
                scope=None,
                consumer_release=prepared.release_id,
            )
            if key is not None:
                draft = replace(draft, key=key)
            view_id = store_source_view(
                conn,
                run_id=run_id,
                task_id=task,
                attempt=claim.attempt,
                holder=claim.holder,
                draft=draft,
                position=index,
            )
            views.append(load_source_view(conn, view_id))
        if source_claim is None:
            complete_task(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder=claim.holder,
                prepared=prepared,
                observations=[],
                outcome="empty",
            )
        return tuple(views)


def independent_pdf_address(conn, run_id, key, *, start=None, end=None, pointer=None):
    """Author expected transport fields from immutable pins and explicit test coordinates.

    No producer frame, stored locator, citation or source-address implementation is read.
    """
    import json

    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table

    views, selected = table("kb.source_view"), table("ops.run_source_view")
    row = conn.execute(
        select(views.c.id, views.c.native_content_digest, views.c.projection_digest)
        .join(selected, selected.c.source_view_id == views.c.id)
        .where(selected.c.run_id == run_id, views.c.key == key)
    ).one()
    address = {"product_digest": row.native_content_digest}
    address.update(
        {"pointer": pointer}
        if pointer is not None
        else {
            "source_view_id": row.id,
            "projection_digest": row.projection_digest,
            "start": start,
            "end": end,
        }
    )
    return "pdf:" + json.dumps(address, sort_keys=True, separators=(",", ":"))


def native_evidence_sources(inputs):
    from corpus_structure.semantic.domain_operations import NativeEvidenceLink
    from corpus_structure.semantic.publication import EvidenceSourceRow

    result = []
    for evidence_id, link in inputs.source_links.items():
        assert isinstance(link, NativeEvidenceLink)
        result.append(
            EvidenceSourceRow(
                evidence_id,
                link.observation_id,
                None,
                source_view_id=link.source_view_id,
                native_address=link.native_address,
            )
        )
    return tuple(result)
