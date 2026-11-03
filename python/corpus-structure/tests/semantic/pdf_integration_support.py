"""Retained PDF observation/selection inputs and committed native scenario mechanics.

No recognizer/model is invoked. Test-specific mutations and expected outcomes stay with cases.
"""

from base64 import b64decode
from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
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
    register_document,
)
from corpus_structure.semantic.pdf_contracts import (
    prepare_pdf_product,
    store_pdf_original,
    trusted_pdf_context,
)
from corpus_structure.semantic.pdf_integrated import (
    prepare_integrated_pdf_product,
    store_pdf_observation,
)

from .operation_scenario_support import prepare_operation_scenario

HOLDER = "pdf13-fixture"


IMAGE = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAQAAAAGCAIAAABrW6giAAAAFElEQVR4nGP8//8/"
    "AwwwMSABcjgA5T4DCWUMPAMAAAAASUVORK5CYII="
)


RESPONSE = b'{"blocks":[{"text":"equal"},{"text":"equal"}]}'


CELL = "#/tables/0/data/table_cells/0"


ITEM_IDS = {"#/body", "#/furniture", "#/texts/0", "#/texts/1", "#/tables/0"}


CELL_IDS = {CELL, "#/tables/0/data/table_cells/1"}


REGION_IDS = {
    "#/texts/0/prov/0",
    "#/texts/0/prov/1",
    "#/texts/1/prov/0",
    "#/tables/0/prov/0",
}


@pytest.fixture(scope="module")
def pdf13_context():
    return trusted_pdf_context()


@pytest.fixture
def native_source():
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        PageItem,
        ProvenanceItem,
        Size,
        TableCell,
        TableData,
    )

    from corpus_structure.ingest.pdf import PdfConversion, publication_payload
    from corpus_structure.ingest.pdf_hierarchy import snapshot

    original = b"%PDF-1.7\nindependent integrated lineage original"
    recipe = b'{"fixture":"native-retained"}'
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    doc = DoclingDocument(name="Repeated occurrences and a table")
    doc.pages[1] = PageItem(page_no=1, size=Size(width=200, height=300))
    for top in (10, 40):
        doc.add_text(
            label=DocItemLabel.TEXT,
            text="equal",
            orig="equal",
            prov=ProvenanceItem(
                page_no=1,
                bbox=BoundingBox(l=10, t=top, r=60, b=top + 10, coord_origin="TOPLEFT"),
                charspan=(0, 5),
            ),
        )
    doc.pages[2] = PageItem(page_no=2, size=Size(width=200, height=300))
    doc.texts[0].prov.append(
        ProvenanceItem(
            page_no=2,
            bbox=BoundingBox(l=80, t=140, r=120, b=150, coord_origin="TOPLEFT"),
            charspan=(0, 5),
        )
    )
    cells = [
        TableCell(
            text="equal",
            bbox=BoundingBox(
                l=10 + col * 50, t=100, r=60 + col * 50, b=120, coord_origin="TOPLEFT"
            ),
            start_row_offset_idx=0,
            end_row_offset_idx=1,
            start_col_offset_idx=col,
            end_col_offset_idx=col + 1,
        )
        for col in (0, 1)
    ]
    doc.add_table(
        data=TableData(num_rows=1, num_cols=2, table_cells=cells),
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=10, t=100, r=110, b=120, coord_origin="TOPLEFT"),
            charspan=(0, 0),
        ),
    )
    conversion = PdfConversion(
        sha256(original).hexdigest(), recipe, snapshot(doc), "success", (), (), (), None
    )
    payload = publication_payload(
        conversion,
        product_key="native",
        schema_digest=sha256(schema).hexdigest(),
        include_application_metadata=False,
    )
    return SimpleNamespace(original=original, recipe=recipe, schema=schema, payload=payload)


def observation(source, *, key="pass-a", outcome="succeeded", pass_role="A") -> dict[str, Any]:
    result = {
        "version": 1,
        "kind": "recognition_observation",
        "product_key": key,
        "artifact_digest": sha256(source.original).hexdigest(),
        "recipe_digest": sha256(source.recipe).hexdigest(),
        "inputs": [],
        "occurrences": [
            {
                "occurrence_id": f"block-{i}",
                "kind": "text",
                "address_space": "recognized_text",
                "precision": "block",
                "text": "equal",
            }
            for i in (0, 1)
        ],
        "relations": [],
        "coverage": [
            {
                "coverage_id": "page-1-table",
                "scope": "page:1",
                "family": "table",
                "discovery_policy": "fixture-full-page",
                "outcome": "partial",
                "detail": "two observed blocks; mapping remains coarse",
                "supports": [],
            }
        ],
        "health": {
            "execution_outcome": outcome,
            "mapping_outcome": "coarse",
            "source_fidelity": "unassessed",
            "validation_report": "fixture-admitted",
        },
        "observation": {
            "binding": {
                "provider": "fixture-provider",
                "package_identity": "fixture==1",
                "source_identity": "fixture-source-v1",
                "weights_digest": "1" * 64,
                "tokenizer_digest": "2" * 64,
                "prompt_digest": "3" * 64,
                "decoding_json": '{"temperature":0}',
                "seed": "17",
                "render_policy": "fixture-render",
                "crop_policy": "whole-page",
                "merge_policy": "ordered-blocks",
            },
            "image": {
                "artifact_digest": sha256(IMAGE).hexdigest(),
                "page_no": 1,
                "width": 4,
                "height": 6,
                "encoding": "png",
                "precision": "unknown",
                "transform": {
                    "status": "unknown",
                    "normalization": "unknown",
                    "source_space": "pdf_points",
                    "target_space": "submitted_pixels",
                },
            },
            "pass_role": pass_role,
            "raw_response_digest": sha256(RESPONSE).hexdigest(),
            "finish_reason": "stop",
            "usage_availability": "available",
            "usage_json": '{"output_tokens":12}',
            "outcome": outcome,
        },
    }
    return result


def pin(task, key, digest, role) -> dict[str, Any]:
    return {"task_id": task, "product_key": key, "content_digest": digest, "role": role}


def integrated(source, inputs) -> dict[str, Any]:
    occurrences: list[dict[str, Any]] = [
        {
            "occurrence_id": pointer,
            "kind": "item",
            "address_space": "selected_item",
            "precision": "item",
            "pointer": pointer,
        }
        for pointer in sorted(ITEM_IDS)
    ]
    occurrences.extend(
        {
            "occurrence_id": pointer,
            "kind": "cell",
            "address_space": "native_cell",
            "precision": "cell",
            "pointer": "#/tables/0",
            "cell_index": index,
            "text": "equal",
        }
        for index, pointer in enumerate(sorted(CELL_IDS))
    )
    relations: list[dict[str, Any]] = []
    for index, occurrence in enumerate(occurrences):
        oid = occurrence["occurrence_id"]
        endpoints = [
            {"role": "input", "input_index": 0, "occurrence_id": oid},
            {"role": "output", "occurrence_id": oid},
        ]
        if oid == CELL:
            endpoints.extend(
                {"role": "evidence", "input_index": n, "occurrence_id": "block-0"} for n in (1, 2)
            )
        relations.append(
            {
                "relation_id": f"selection-{index}",
                "kind": "decision",
                "outcome": "selected",
                "comparison": "grid" if oid in CELL_IDS else "text",
                "policy": "retain-native-v1",
                "evidence": "independent fixture decision",
                "endpoints": endpoints,
            }
        )
    relations.append(
        {
            "relation_id": "ambiguous-equal-spelling",
            "kind": "correspondence",
            "outcome": "ambiguous",
            "comparison": "text",
            "policy": "retain-ambiguity-v1",
            "evidence": "equal spelling cannot identify a source occurrence",
            "endpoints": [
                {"role": "input", "input_index": 1, "occurrence_id": "block-0"},
                {"role": "input", "input_index": 1, "occurrence_id": "block-1"},
                {"role": "input", "input_index": 2, "occurrence_id": "block-0"},
                {"role": "input", "input_index": 2, "occurrence_id": "block-1"},
            ],
        }
    )
    result = observation(source, key="selected")
    del result["observation"]
    result.update(
        kind="integrated",
        inputs=inputs,
        occurrences=occurrences,
        relations=relations,
        content=deepcopy(source.payload),
    )
    return result


def prepare(value, source, *, context=None):
    return prepare_integrated_pdf_product(
        value,
        source.original,
        source.recipe,
        artifacts=(IMAGE, RESPONSE),
        native_schema=source.schema,
        context=context,
    )


@pytest.fixture
def independent_integrated(native_source):
    return integrated(
        native_source,
        [
            pin(41, "native", "a" * 64, "structural"),
            pin(41, "pass-a", "b" * 64, "recognition"),
            pin(41, "pass-b", "c" * 64, "recognition"),
        ],
    )


@pytest.fixture
def pdf13_db(semantic_db_engine, semantic_writer_engine, native_source, tmp_path):
    prepared = prepare_operation_scenario(semantic_db_engine, observations=True, composed=True)
    source = native_source

    def create(*, project="p", original=None, name="source"):
        original = source.original if original is None else original
        with semantic_writer_engine.begin() as conn:
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
            prepared=prepared)
            path = tmp_path / f"{project}-{name}.pdf"
            path.write_bytes(original)
            document = register_document(
                conn,
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
        writer=semantic_writer_engine,
        admin=semantic_db_engine,
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


def mutate_selected(value, change):
    first_text = next(o for o in value["occurrences"] if o["occurrence_id"] == "#/texts/0")
    if change == "empty_companions":
        value["occurrences"], value["relations"] = [], []
    elif change == "missing_coverage":
        value["coverage"] = []
    elif change == "missing_decision":
        value["relations"] = value["relations"][1:]
    elif change == "wrong_kind":
        first_text["kind"] = "formula"
    elif change == "exact_glyph":
        first_text.update(precision="glyph", start=0, end=5, text="equal")
    elif change == "opaque_region":
        first_text["region"] = {"box": [10, 10, 60, 20]}
    elif change == "out_of_bounds_region":
        first_text["region"] = {
            "address_space": "pdf_points",
            "precision": "item",
            "normalization": "none",
            "origin": "top_left",
            "left": 10,
            "top": 10,
            "right": 201,
            "bottom": 20,
        }
    elif change in {"wrong_region_page", "missing_region_page"}:
        first_text["region"] = {
            "address_space": "pdf_points",
            "precision": "item",
            "normalization": "none",
            "origin": "top_left",
            "left": 80,
            "top": 140,
            "right": 120,
            "bottom": 150,
        }
        if change == "wrong_region_page":
            first_text["page_no"] = 1  # This exact box belongs to page 2, never page 1.
    elif change == "forged_text":
        first_text["text"] = "different"
    elif change == "missing_local_endpoint":
        value["relations"][0]["endpoints"][1]["occurrence_id"] = "absent-output"
    elif change == "duplicate_occurrence":
        value["occurrences"].append(deepcopy(first_text))
    elif change == "duplicate_endpoint":
        value["relations"][0]["endpoints"].append(deepcopy(value["relations"][0]["endpoints"][0]))
    elif change == "missing_structural":
        value["inputs"][0]["role"] = "alternative"
    elif change == "missing_recognition":
        for item in value["inputs"][1:]:
            item["role"] = "alternative"
    else:
        raise AssertionError(change)
