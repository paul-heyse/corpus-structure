"""Retained PDF observation/selection inputs and committed native scenario mechanics.

No recognizer/model is invoked. Test-specific mutations and expected outcomes stay with cases.
"""

from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import create_model

from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    create_run,
    create_task,
    record_method,
)
from corpus_structure.semantic.original_documents import register_original_document
from corpus_structure.semantic.pdf_contracts import (
    prepare_pdf_product,
    store_pdf_original,
    trusted_pdf_context,
)
from corpus_structure.semantic.pdf_integrated import (
    prepare_integrated_pdf_product,
    store_pdf_observation,
)
from semantic.operation_scenario_support import prepare_operation_scenario
from semantic.pdf_native_source_support import (
    CELL, CELL_IDS, IMAGE, ITEM_IDS, REGION_IDS, RESPONSE, independent_integrated, integrated,
    mutate_selected, native_source, observation, pdf13_context, pin, prepare,
)

HOLDER = "pdf13-fixture"






@pytest.fixture
def pdf13_db(commit_db_engine, commit_writer_engine, native_source, tmp_path):
    prepared = prepare_operation_scenario(commit_db_engine, observations=True, composed=True)
    source = native_source

    def create(*, project="p", original=None, name="source"):
        original = source.original if original is None else original
        with commit_writer_engine.begin() as conn:
            run = create_run(
                conn,
                project_id=project,
                binding=OperationBinding(
                    prepared.release_id, "z" if project == "p" else "foreign-z", 0, b"{}"
                ),
                kind="full",
                options={},
                code_commit="pdf13-independent-test",
            )
            config = record_method(
                conn,
                SimpleNamespace(
                    name="pdf13.fixture",
                    version="1",
                    family="ingest",
                    tier="deterministic",
                    confidence_source=None,
                    unit_type="document",
                    Config=create_model("IntegratedPdfFixture"),
                ),
                "default",
                {},
                "pdf13-fixture",
                prepared=prepared,
            )
            path = tmp_path / f"{project}-{name}.pdf"
            path.write_bytes(original)
            document = register_original_document(
                conn,
                prepared=prepared,
                project_id=project,
                source_uri=f"file:{name}",
                original_path=str(path),
                original=original,
                mime="application/pdf",
            )
            task = create_task(
                conn,
                run_id=run,
                config_id=config,
                stage="ingest",
                unit_type="document",
                unit_id=document,
                unit_key=name,
                input_hash=sha256(original).hexdigest(),
            )
            claim = claim_tasks(conn, run_id=run, config_id=config, holder=HOLDER)[0]
            store_pdf_original(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder=HOLDER,
                original=original,
                recipe_bytes=source.recipe,
            )
        return SimpleNamespace(
            task=task, run=run, attempt=claim.attempt, claim=claim, document=document
        )

    job = create()
    native = prepare_pdf_product(source.payload, source.original, source.schema, source.recipe)
    db = SimpleNamespace(
        source=source,
        prepared=prepared,
        job=job,
        native=native,
        create=create,
        writer=commit_writer_engine,
        admin=commit_db_engine,
        directory=tmp_path / "records",
        published={},
    )
    db.native_digest = _publish_record_document(db, native)
    observations = []
    for key, role in (("pass-a", "A"), ("pass-b", "B")):
        product = prepare(observation(source, key=key, pass_role=role), source)
        publish(db, product)
        observations.append(product)
    db.observations = observations
    db.inputs = [
        pin(job.task, "native", db.native_digest, "structural"),
        *[pin(job.task, p.values()["product_key"], p.digest, "recognition") for p in observations],
    ]
    return db


def _publish_record_document(db, product, *, job=None, source=None, attempt=None, holder=HOLDER):
    job = job or db.job
    if product.values().get("kind") == "integrated" and not product._validated:
        raise ValueError("publication requires an immutable prepared bundle")
    reuse = (
        job.task,
        attempt or job.attempt,
        holder,
        product.values()["product_key"],
        product.digest,
    )
    if reuse not in db.published:
        db.published[reuse] = _publish_record_values(
            db, product.values(), job=job, source=source, attempt=attempt, holder=holder
        )
    else:
        from corpus_structure.semantic.pdf_record_reader import published_record_reader
        from corpus_structure.semantic.product_reference import ProductReference

        with db.writer.connect() as conn:
            retained = published_record_reader(
                conn,
                ProductReference(job.task, product.values()["product_key"], db.published[reuse]),
            )
            assert retained is not None
            assert retained.revision["logical_digest"] == db.published[reuse]
    return db.published[reuse]


def _publish_record_values(db, outer, *, job=None, source=None, attempt=None, holder=HOLDER):
    """Submit actual record/companion inputs directly to the released publication validators."""
    from docling_core.types.doc import DoclingDocument

    from corpus_structure.core.method import PdfRecordPublicationDraft
    from corpus_structure.orchestrate.pdf_streaming import publish_pdf_record_draft

    job, source = job or db.job, source or db.source
    claim = job.claim if attempt is None else job.claim.model_copy(update={"attempt": attempt})
    kind = outer.get("kind", "native")
    content = outer["content"] if kind == "integrated" else outer
    companions = {
        family: outer.get(key, ())
        for family, key in (
            ("input", "inputs"),
            ("occurrence", "occurrences"),
            ("relation", "relations"),
            ("mapping_report", "mapping_reports"),
            ("coverage", "coverage"),
        )
        if kind == "integrated" or key in outer
    }
    if kind == "integrated":
        companions["health"] = (
            {"health": content["health"], "source_scope": content["source_scope"]},
            outer["health"],
        )
    retained = publish_pdf_record_draft(
        db.writer,
        claim,
        holder,
        PdfRecordPublicationDraft(
            document=DoclingDocument.model_validate(content["document"]),
            product_key=outer["product_key"],
            kind=kind,
            original=source.original,
            schema_bytes=source.schema,
            recipe_bytes=source.recipe,
            health=content["health"],
            source_scope=content["source_scope"],
            companions=companions,
            metadata={
                key: content[key]
                for key in (
                    "formula_outcomes",
                    "inline_candidate_pages",
                    "recognition_coverage",
                    "derivation_mappings",
                    "cell_reports",
                    "inline_alignment_reports",
                    "runtime_report",
                )
                if key in content
            },
        ),
        directory=db.directory,
        check_active=lambda: None,
    )
    return retained.logical_digest


def publish(db, product, *, attempt=None, holder=HOLDER):
    if product.values().get("kind") == "recognition_observation":
        with db.writer.begin() as conn:
            return store_pdf_observation(
                conn,
                task_id=db.job.task,
                attempt=db.job.attempt if attempt is None else attempt,
                holder=holder,
                product=product,
            )
    return _publish_record_document(db, product, attempt=attempt, holder=holder)
