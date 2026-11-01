"""Independent integrated-PDF contract and protected PostgreSQL lineage examples.

All observations are retained fixture bytes: these tests run no recognizer or model inference.
"""

from base64 import b64decode
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import create_model
from sqlalchemy import event, insert, select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
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
    store_pdf_product,
    trusted_pdf_context,
)
from corpus_structure.semantic.pdf_integrated import (
    prepare_integrated_pdf_product,
    store_integrated_pdf_product,
)
from corpus_structure.semantic.pdf_storage import (
    NativeDocumentUnavailable,
    read_native_items,
    read_pdf_product,
    trace_pdf_occurrence,
)

from .test_operations import setup

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


def test_retained_observation_preserves_partial_and_no_response(native_source, pdf13_context):
    partial = observation(native_source, outcome="partial")
    product = prepare(partial, native_source, context=pdf13_context)
    assert [o["occurrence_id"] for o in product.values()["occurrences"]] == ["block-0", "block-1"]
    assert product.values()["coverage"][0]["outcome"] == "partial"
    assert product.values()["health"]["source_fidelity"] == "unassessed"
    assert native_source.original not in product.artifacts
    assert {IMAGE, RESPONSE, native_source.recipe} <= set(product.artifacts)
    failed = observation(native_source, outcome="failed")
    failed["occurrences"] = []
    failed["coverage"][0]["outcome"] = "unknown"
    for name in ("raw_response_digest", "finish_reason", "usage_json"):
        del failed["observation"][name]
    failed["observation"].update(
        usage_availability="unavailable", diagnostic="provider disconnected"
    )
    retained = prepare_integrated_pdf_product(
        failed,
        native_source.original,
        native_source.recipe,
        artifacts=(IMAGE,),
        context=pdf13_context,
    )
    assert "raw_response_digest" not in retained.values()["observation"]
    assert retained.values()["observation"]["diagnostic"] == "provider disconnected"


@pytest.mark.parametrize(
    "change",
    [
        "empty_companions",
        "missing_coverage",
        "missing_decision",
        "wrong_kind",
        "exact_glyph",
        "opaque_region",
        "out_of_bounds_region",
        "wrong_region_page",
        "missing_region_page",
        "forged_text",
        "missing_local_endpoint",
        "duplicate_occurrence",
        "duplicate_endpoint",
        "missing_structural",
        "missing_recognition",
    ],
)
def test_invalid_selected_meaning_refuses(
    native_source,
    independent_integrated,
    pdf13_context,
    change,
):
    mutate_selected(independent_integrated, change)
    with pytest.raises(ValueError):
        prepare(independent_integrated, native_source, context=pdf13_context)


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


@pytest.mark.parametrize(
    "change",
    [
        "complete_partial",
        "fine_image",
        "exact_range",
        "image_bytes",
        "unknown_health",
        "unknown_transform",
        "no_response_success",
        "wrong_observation_page",
    ],
)
def test_invalid_recognition_refuses(native_source, pdf13_context, change):
    value = observation(native_source, outcome="partial")
    if change == "complete_partial":
        value["coverage"][0]["outcome"] = "complete"
    elif change == "fine_image":
        value["observation"]["image"]["precision"] = "cell"
    elif change == "exact_range":
        value["occurrences"][0].update(start=0, end=5)
    elif change == "image_bytes":
        value["observation"]["image"]["artifact_digest"] = "0" * 64
    elif change == "unknown_health":
        value["health"]["magic_complete"] = True
    elif change == "unknown_transform":
        value["observation"]["image"]["transform"]["magic_exact"] = True
    elif change == "wrong_observation_page":
        value["occurrences"][0]["page_no"] = 2
    elif change == "no_response_success":
        value["observation"]["outcome"] = "succeeded"
        del value["observation"]["raw_response_digest"]
    with pytest.raises(ValueError):
        prepare(value, native_source, context=pdf13_context)


def test_reconciliation_operations_are_qualified(pdf13_context):
    for operation in ("map_pdf_observation", "compare_pdf_occurrences", "select_pdf_integration"):
        bound = pdf13_context.execution.require_operation(operation)
        assert bound.implementation == operation
        assert "partial" in bound.outcomes


@pytest.fixture
def pdf13_db(semantic_db_engine, semantic_writer_engine, native_source, tmp_path):
    prepared = setup(semantic_db_engine, observations=True, composed=True)
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
            )
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
        return SimpleNamespace(task=task, run=run, attempt=claim.attempt)

    job = create()
    native = prepare_pdf_product(source.payload, source.original, source.schema, source.recipe)
    with semantic_writer_engine.begin() as conn:
        store_pdf_product(
            conn, task_id=job.task, attempt=job.attempt, holder=HOLDER, product=native
        )
    observations = []
    for key, role in (("pass-a", "A"), ("pass-b", "B")):
        product = prepare(observation(source, key=key, pass_role=role), source)
        with semantic_writer_engine.begin() as conn:
            store_integrated_pdf_product(
                conn, task_id=job.task, attempt=job.attempt, holder=HOLDER, product=product
            )
        observations.append(product)
    inputs = [
        pin(job.task, "native", native.digest, "structural"),
        *[pin(job.task, p.values()["product_key"], p.digest, "recognition") for p in observations],
    ]
    return SimpleNamespace(
        source=source,
        prepared=prepared,
        job=job,
        native=native,
        observations=observations,
        inputs=inputs,
        create=create,
        writer=semantic_writer_engine,
        admin=semantic_db_engine,
    )


def publish(db, product, *, attempt=None):
    with db.writer.begin() as conn:
        return store_integrated_pdf_product(
            conn,
            task_id=db.job.task,
            attempt=db.job.attempt if attempt is None else attempt,
            holder=HOLDER,
            product=product,
        )


def raw_publish(conn, db, value, product):
    return conn.execute(
        text(
            "SELECT ops.publish_integrated_pdf("
            ":task,:attempt,:holder,:contract,:payload,:artifacts)"
        ),
        {
            "task": db.job.task,
            "attempt": db.job.attempt,
            "holder": HOLDER,
            "contract": product.contract_digest,
            "payload": canonical_bytes(value),
            "artifacts": list(product.artifacts),
        },
    ).scalar_one()


def test_selected_cell_traces_two_observations_original_and_policy_reuse(
    pdf13_db, semantic_reader_engine
):
    db = pdf13_db
    product = prepare(integrated(db.source, db.inputs), db.source)
    transmitted = []

    def capture_publication(conn, clause, multiparams, params, options):
        if "ops.publish_integrated_pdf(" in str(clause):
            transmitted.extend(params["artifacts"])

    event.listen(db.writer, "before_execute", capture_publication)
    try:
        assert publish(db, product) == product.digest
    finally:
        event.remove(db.writer, "before_execute", capture_publication)
    assert db.source.original not in transmitted
    assert {IMAGE, RESPONSE, db.source.recipe} <= set(transmitted)
    assert publish(db, product) == product.digest
    with semantic_reader_engine.connect() as conn:
        before = (
            conn.execute(
                select(table("ops.pdf_product").c.content_digest).where(
                    table("ops.pdf_product").c.kind == "recognition_observation"
                )
            )
            .scalars()
            .all()
        )
        native = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="native",
            content_digest=db.native.digest,
            include_body=True,
        )
        assert native["body"] == db.native.values()
        assert native["identity"]["content_digest"] == sha256(db.native.payload).hexdigest()
        assert read_native_items(
            conn, task_id=db.job.task, product_key="selected", content_digest=product.digest
        )
        assert {
            o["occurrence_id"] for o in native["occurrences"]
        } == ITEM_IDS | CELL_IDS | REGION_IDS
        selected = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="selected",
            content_digest=product.digest,
            occurrence_id=CELL,
        )
        assert "body" not in selected
        assert selected["descriptor"]["health"]["source_fidelity"] == "unassessed"
        assert "content" not in selected["descriptor"]
        assert [o["occurrence_id"] for o in selected["occurrences"]] == [CELL]
        assert selected["occurrences"][0]["body"]["native_value"]["text"] == "equal"
        assert len(selected["inputs"]) == 3
        endpoints = selected["relations"][0]["endpoints"]
        assert {(e["target_product_key"], e["occurrence_id"], e["role"]) for e in endpoints} == {
            ("native", CELL, "input"),
            ("selected", CELL, "output"),
            ("pass-a", "block-0", "evidence"),
            ("pass-b", "block-0", "evidence"),
        }
        trace = trace_pdf_occurrence(
            conn,
            task_id=db.job.task,
            product_key="selected",
            content_digest=product.digest,
            occurrence_id=CELL,
        )
        assert trace["complete"] is True
        metadata = {p["product_key"]: p for p in trace["products"]}
        assert set(metadata) == {"selected", "native", "pass-a", "pass-b"}
        assert metadata["native"]["content_digest"] == db.native.digest
        assert metadata["selected"]["content_digest"] == product.digest
        for key, role, previous in zip(
            ("pass-a", "pass-b"), ("A", "B"), db.observations, strict=True
        ):
            descriptor = metadata[key]["descriptor"]
            assert metadata[key]["content_digest"] == previous.digest
            assert descriptor["observation"]["pass_role"] == role
            assert descriptor["observation"]["binding"]["provider"] == "fixture-provider"
            assert descriptor["observation"]["binding"]["weights_digest"] == "1" * 64
            assert descriptor["observation"]["raw_response_digest"] == sha256(RESPONSE).hexdigest()
            image = descriptor["observation"]["image"]
            assert image["artifact_digest"] == sha256(IMAGE).hexdigest()
            assert (image["page_no"], image["width"], image["height"], image["encoding"]) == (
                1,
                4,
                6,
                "png",
            )
            assert image["transform"]["status"] == "unknown"
        for item in metadata.values():
            assert (
                not {"content", "document", "occurrences", "relations"} & item["descriptor"].keys()
            )
        assert {(n["product_key"], n["occurrence_id"]) for n in trace["nodes"]} == {
            ("selected", CELL),
            ("native", CELL),
            ("pass-a", "block-0"),
            ("pass-b", "block-0"),
        }
        assert {n["artifact_digest"] for n in trace["nodes"]} == {
            sha256(db.source.original).hexdigest()
        }
        original = next(n for n in trace["nodes"] if n["kind"] == "native")
        assert original["body"]["native_value"]["bbox"] == {
            "l": 10.0,
            "t": 100.0,
            "r": 60.0,
            "b": 120.0,
            "coord_origin": "TOPLEFT",
        }
        with pytest.raises(ValueError, match="limit"):
            trace_pdf_occurrence(
                conn,
                task_id=db.job.task,
                product_key="selected",
                content_digest=product.digest,
                occurrence_id=CELL,
                limit=3,
            )
        with pytest.raises(NativeDocumentUnavailable):
            read_pdf_product(
                conn, task_id=db.job.task, product_key="selected", content_digest="0" * 64
            )
        with pytest.raises(NativeDocumentUnavailable):
            trace_pdf_occurrence(
                conn,
                task_id=db.job.task,
                product_key="selected",
                content_digest=product.digest,
                occurrence_id="missing",
            )
    changed = integrated(db.source, db.inputs)
    changed["product_key"] = "selected-policy-v2"
    for relation in changed["relations"]:
        relation["policy"] = "retain-native-v2"
    revised = prepare(changed, db.source)
    assert revised.digest != product.digest
    publish(db, revised)
    with semantic_reader_engine.connect() as conn:
        after = (
            conn.execute(
                select(table("ops.pdf_product").c.content_digest).where(
                    table("ops.pdf_product").c.kind == "recognition_observation"
                )
            )
            .scalars()
            .all()
        )
        assert sorted(after) == sorted(before)
        old = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="selected",
            content_digest=product.digest,
            occurrence_id=CELL,
        )
        assert old["relations"][0]["body"]["policy"] == "retain-native-v1"
        page = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="selected",
            content_digest=product.digest,
            limit=1,
        )
        following = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="selected",
            content_digest=product.digest,
            after=page["cursor"],
            limit=100,
        )
        assert len(page["occurrences"]) == 1
        assert {
            o["occurrence_id"] for o in page["occurrences"] + following["occurrences"]
        } == ITEM_IDS | CELL_IDS


def test_direct_publication_cannot_bypass_meaning_or_task_fence(pdf13_db):
    db = pdf13_db
    value = integrated(db.source, db.inputs)
    product = prepare(value, db.source)
    for index, change in enumerate(
        (
            "empty_companions",
            "missing_coverage",
            "missing_decision",
            "wrong_kind",
            "exact_glyph",
            "opaque_region",
            "out_of_bounds_region",
            "wrong_region_page",
            "missing_region_page",
            "forged_text",
            "missing_local_endpoint",
            "duplicate_occurrence",
            "duplicate_endpoint",
        )
    ):
        invalid = deepcopy(value)
        invalid["product_key"] = f"invalid-{index}"
        mutate_selected(invalid, change)
        with db.writer.begin() as conn, pytest.raises(DBAPIError) as refused, conn.begin_nested():
            raw_publish(conn, db, invalid, product)
        assert getattr(refused.value.orig, "sqlstate", None) in {"23514", "23503", "23505"}
    with pytest.raises(DBAPIError):
        publish(db, product, attempt=db.job.attempt + 1)
    with pytest.raises(DBAPIError), db.writer.begin() as conn:
        store_integrated_pdf_product(
            conn,
            task_id=db.job.task,
            attempt=db.job.attempt,
            holder="another-holder",
            product=product,
        )
    forged = replace(product, payload=canonical_bytes({**value, "product_key": "forged"}))
    with pytest.raises(ValueError, match="immutable prepared"):
        publish(db, forged)
    publish(db, product)
    mutated = deepcopy(value)
    mutated["health"]["validation_report"] = "changed after publication"
    with pytest.raises(DBAPIError), db.writer.begin() as conn:
        raw_publish(conn, db, mutated, product)
    assert publish(db, product) == product.digest
    extra = b"already-retained-but-not-in-this-product"
    unrelated = observation(db.source, key="pass-unrelated")
    unrelated["observation"]["raw_response_digest"] = sha256(extra).hexdigest()
    retained_extra = prepare_integrated_pdf_product(
        unrelated, db.source.original, db.source.recipe, artifacts=(IMAGE, extra)
    )
    publish(db, retained_extra)
    with pytest.raises(DBAPIError), db.writer.begin() as conn:
        conn.execute(
            text(
                "SELECT ops.publish_integrated_pdf("
                ":task,:attempt,:holder,:contract,:payload,:artifacts)"
            ),
            {
                "task": db.job.task,
                "attempt": db.job.attempt,
                "holder": HOLDER,
                "contract": product.contract_digest,
                "payload": product.payload,
                "artifacts": [*product.artifacts, extra],
            },
        )
    with db.admin.connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM ops.pdf_product "
                    "WHERE product_key LIKE 'invalid-%' OR product_key='forged'"
                )
            ).scalar_one()
            == 0
        )


def test_inputs_require_exact_extant_same_original_and_project_pins(pdf13_db):
    db = pdf13_db
    other_original = b"%PDF-1.7\ndifferent source"
    other = db.create(original=other_original, name="other-original")
    other_source = SimpleNamespace(**vars(db.source))
    other_source.original = other_original
    other_source.payload = deepcopy(db.source.payload)
    other_source.payload["artifact_digest"] = sha256(other_original).hexdigest()
    foreign_native = prepare_pdf_product(
        other_source.payload, other_original, db.source.schema, db.source.recipe
    )
    with db.writer.begin() as conn:
        store_pdf_product(
            conn, task_id=other.task, attempt=other.attempt, holder=HOLDER, product=foreign_native
        )
    with db.admin.begin() as conn:
        conn.execute(insert(table("data.project")).values(project_id="foreign"))
        conn.execute(
            insert(table("data.realization")).values(
                project_id="foreign", realization_id="foreign-z", release_id=db.prepared.release_id
            )
        )
    foreign = db.create(project="foreign", name="foreign-project")
    with db.writer.begin() as conn:
        store_pdf_product(
            conn, task_id=foreign.task, attempt=foreign.attempt, holder=HOLDER, product=db.native
        )
    cases = [
        pin(db.job.task, "native", "0" * 64, "structural"),
        pin(db.job.task, "not-published", "a" * 64, "structural"),
        pin(db.job.task, "attempt-self", "a" * 64, "structural"),
        pin(other.task, "native", foreign_native.digest, "structural"),
        pin(foreign.task, "native", db.native.digest, "structural"),
    ]
    for index, invalid_pin in enumerate(cases):
        value = integrated(db.source, [invalid_pin, *db.inputs[1:]])
        value["product_key"] = "attempt-self" if index == 2 else f"bad-custody-{index}"
        product = prepare(value, db.source)
        with pytest.raises(DBAPIError) as refused:
            publish(db, product)
        assert getattr(refused.value.orig, "sqlstate", None) in {"23514", "P0002"}
    missing = integrated(db.source, db.inputs)
    missing["product_key"] = "missing-external-occurrence"
    missing["relations"][0]["endpoints"][0]["occurrence_id"] = "not-a-native-occurrence"
    with pytest.raises(DBAPIError) as refused:
        publish(db, prepare(missing, db.source))
    assert getattr(refused.value.orig, "sqlstate", None) == "23503"


def test_forward_migration_backfills_structural_edges_without_rewriting_native(
    semantic_database_at,
    native_settings,
    native_source,
    tmp_path,
):
    """Produce a real pre-PDF13 archive with historical source, then migrate it."""
    import base64
    import json
    import os
    import subprocess
    import sys
    import tarfile
    from pathlib import Path

    from corpus_structure.semantic.migrations import upgrade
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_task
    from corpus_structure.semantic.types import PreparationError
    from native_test_support import principal_engine

    historical = "bdd51c27e1c4c1443703720084156367ed7b4864"
    repository = Path(__file__).resolve().parents[4]
    exported = tmp_path / "pre-pdf13"
    exported.mkdir()
    archive = tmp_path / "pre-pdf13.tar"
    with archive.open("wb") as output:
        subprocess.run(
            [
                "git",
                "archive",
                "--format=tar",
                historical,
                "python/corpus-structure/src",
                "python/corpus-structure/tests/semantic/test_operations.py",
                "python/corpus-structure/tests/semantic/__init__.py",
                "sources",
            ],
            cwd=repository,
            stdout=output,
            check=True,
        )
    with tarfile.open(archive) as retained:
        retained.extractall(exported, filter="data")
    fixture = tmp_path / "native-fixture.json"
    fixture.write_bytes(
        canonical_bytes(
            {
                "payload": native_source.payload,
                "original": base64.b64encode(native_source.original).decode(),
                "recipe": base64.b64encode(native_source.recipe).decode(),
                "schema": base64.b64encode(native_source.schema).decode(),
            }
        )
    )
    script = tmp_path / "populate.py"
    script.write_text("""import base64
import json
import os
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

from pydantic import create_model
from sqlalchemy import create_engine

from semantic.test_operations import setup
from corpus_structure.semantic.operations import (
    OperationBinding, create_run, record_method, register_document, create_task, claim_tasks,
)
from corpus_structure.semantic.pdf_contracts import (
    prepare_pdf_product, store_pdf_original, store_pdf_product,
)

value = json.loads(Path(os.environ["PDF13_FIXTURE"]).read_text())
original, recipe, schema = (base64.b64decode(value[k]) for k in ("original", "recipe", "schema"))
admin = create_engine(os.environ["PDF13_ADMIN"])
writer = create_engine(os.environ["PDF13_WRITER"])
prepared = setup(admin, observations=True, composed=True)
product = prepare_pdf_product(value["payload"], original, schema, recipe)
with writer.begin() as conn:
    run = create_run(
        conn, project_id="p", binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
        kind="full", options={}, code_commit="historical-pdf13-fixture",
    )
    method = SimpleNamespace(
        name="pdf13.old", version="1", family="ingest", tier="deterministic",
        confidence_source=None, unit_type="document", Config=create_model("OldPdfFixture"),
    )
    config = record_method(conn, method, "default", {}, "old-pdf-fixture")
    path = Path(os.environ["PDF13_FIXTURE"]).with_suffix(".pdf")
    path.write_bytes(original)
    document = register_document(
        conn, project_id="p", source_uri="old.pdf", original_path=str(path),
        original=original, mime="application/pdf",
    )
    task = create_task(
        conn, run_id=run, config_id=config, stage="ingest", unit_type="document",
        unit_id=document, unit_key="old.pdf", input_hash=sha256(original).hexdigest(),
    )
    claim = claim_tasks(conn, run_id=run, config_id=config, holder="old-pdf-fixture")[0]
    store_pdf_original(
        conn, task_id=task, attempt=claim.attempt, holder="old-pdf-fixture",
        original=original, recipe_bytes=recipe,
    )
    store_pdf_product(
        conn, task_id=task, attempt=claim.attempt, holder="old-pdf-fixture", product=product,
    )
    child = deepcopy(product.values())
    child.update(
        product_key="historical-child", parent_task_id=task,
        parent_product_key="native", parent_digest=product.digest,
    )
    derived = prepare_pdf_product(child, original, schema, recipe)
    store_pdf_product(
        conn, task_id=task, attempt=claim.attempt, holder="old-pdf-fixture", product=derived,
    )
Path(os.environ["PDF13_RECEIPT"]).write_text(json.dumps({
    "task": task, "attempt": claim.attempt,
    "native_digest": product.digest, "child_digest": derived.digest,
}))
writer.dispose()
admin.dispose()
""")
    receipt_path = tmp_path / "historical-receipt.json"
    with semantic_database_at("semantic_0055") as engine:
        writer = principal_engine(native_settings, "write", engine.url.database)
        try:
            completed = subprocess.run(
                [sys.executable, str(script)],
                cwd=exported,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "PYTHONPATH": os.pathsep.join(
                        (
                            str(exported / "python/corpus-structure/src"),
                            str(exported / "python/corpus-structure/tests"),
                        )
                    ),
                    "PDF13_FIXTURE": str(fixture),
                    "PDF13_RECEIPT": str(receipt_path),
                    "PDF13_ADMIN": engine.url.render_as_string(hide_password=False),
                    "PDF13_WRITER": writer.url.render_as_string(hide_password=False),
                },
            )
            assert completed.returncode == 0, completed.stdout + completed.stderr
            receipt = json.loads(receipt_path.read_text())
            with engine.begin() as conn:
                before = conn.execute(
                    text(
                        "SELECT product_key,content_digest,contract_digest,payload "
                        "FROM ops.native_document_product "
                        "WHERE task_id=:task ORDER BY product_key"
                    ),
                    {"task": receipt["task"]},
                ).all()
                upgrade(conn)
                after = conn.execute(
                    text(
                        "SELECT product_key,content_digest,contract_digest,payload "
                        "FROM ops.native_document_product "
                        "WHERE task_id=:task ORDER BY product_key"
                    ),
                    {"task": receipt["task"]},
                ).all()
                assert after == before
                assert conn.execute(
                    text(
                        "SELECT product_key,role,input_task_id,"
                        "input_product_key,input_content_digest "
                        "FROM ops.pdf_product_input WHERE task_id=:task"
                    ),
                    {"task": receipt["task"]},
                ).all() == [
                    (
                        "historical-child",
                        "structural",
                        receipt["task"],
                        "native",
                        receipt["native_digest"],
                    )
                ]
                assert (
                    conn.execute(
                        text(
                            "SELECT count(*) FROM ops.pdf_product "
                            "WHERE kind='recognition_observation'"
                        )
                    ).scalar_one()
                    == 0
                )
                assert (
                    conn.execute(
                        text(
                            "SELECT count(*) FROM kb.pdf_occurrence "
                            "WHERE task_id=:task AND kind='cell'"
                        ),
                        {"task": receipt["task"]},
                    ).scalar_one()
                    == 4
                )
                context = pdf_context_for_task(conn, receipt["task"])
                assert "PdfIntegratedProduct" not in {d.name for d in context.boundary.definitions}
                old = read_pdf_product(
                    conn,
                    task_id=receipt["task"],
                    product_key="native",
                    content_digest=receipt["native_digest"],
                    include_body=True,
                )
                assert old["body"]["document"] == native_source.payload["document"]
                with pytest.raises(PreparationError):
                    prepare(observation(native_source), native_source, context=context)
            with writer.begin() as conn:
                archived_native = prepare_pdf_product(
                    old["body"],
                    native_source.original,
                    native_source.schema,
                    native_source.recipe,
                    context=context,
                )
                assert (
                    store_pdf_product(
                        conn,
                        task_id=receipt["task"],
                        attempt=receipt["attempt"],
                        holder="old-pdf-fixture",
                        product=archived_native,
                    )
                    == receipt["native_digest"]
                )
        finally:
            writer.dispose()


def test_partial_observation_cannot_support_complete_integrated_coverage(pdf13_db):
    db = pdf13_db
    value = integrated(db.source, db.inputs)
    value["product_key"] = "false-complete"
    value["coverage"][0].update(
        outcome="complete", supports=[{"input_index": 1, "coverage_id": "page-1-table"}]
    )
    # The pin and coverage id exist, and scope/family agree: only the required outcome
    # is stronger than its retained evidence. This must fail at cross-product admission.
    product = prepare(value, db.source)
    with pytest.raises(DBAPIError) as refused:
        publish(db, product)
    assert getattr(refused.value.orig, "sqlstate", None) == "23514"
    value["coverage"][0]["supports"][0]["coverage_id"] = "nonexistent-coverage"
    with pytest.raises(DBAPIError):
        publish(db, prepare(value, db.source))


def test_failed_later_pass_retains_earlier_observations(pdf13_db, semantic_reader_engine):
    db = pdf13_db
    failed = observation(db.source, key="pass-c-failed", pass_role="C", outcome="failed")
    failed["occurrences"] = []
    failed["coverage"][0]["outcome"] = "unknown"
    for name in ("raw_response_digest", "finish_reason", "usage_json"):
        del failed["observation"][name]
    failed["observation"].update(
        usage_availability="unavailable", diagnostic="connection closed before response"
    )
    product = prepare_integrated_pdf_product(
        failed, db.source.original, db.source.recipe, artifacts=(IMAGE,)
    )
    publish(db, product)
    with semantic_reader_engine.connect() as conn:
        retained = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="pass-c-failed",
            content_digest=product.digest,
            include_body=True,
        )
        assert retained["occurrences"] == []
        assert retained["coverage"][0]["body"]["outcome"] == "unknown"
        assert retained["body"]["observation"]["outcome"] == "failed"
        assert "raw_response_digest" not in retained["body"]["observation"]
        for previous in db.observations:
            old = read_pdf_product(
                conn,
                task_id=db.job.task,
                product_key=previous.values()["product_key"],
                content_digest=previous.digest,
                include_body=True,
            )
            assert old["body"]["observation"]["raw_response_digest"] == sha256(RESPONSE).hexdigest()
            assert old["body"]["observation"]["outcome"] == "succeeded"
            assert {o["occurrence_id"] for o in old["occurrences"]} == {"block-0", "block-1"}


def test_integrated_roundtrip_preserves_full_distinct_inventory(
    native_source,
    independent_integrated,
    pdf13_context,
):
    product = prepare(independent_integrated, native_source, context=pdf13_context)
    actual = product.values()
    assert {o["occurrence_id"] for o in actual["occurrences"]} == ITEM_IDS | CELL_IDS
    assert actual["content"]["document"] == native_source.payload["document"]
    repeated = [o for o in actual["occurrences"] if o["kind"] == "cell"]
    assert [o["text"] for o in repeated] == ["equal", "equal"]
    assert [o["cell_index"] for o in repeated] == [0, 1]
    ambiguity = next(r for r in actual["relations"] if r["kind"] == "correspondence")
    assert ambiguity["relation_id"] == "ambiguous-equal-spelling"
    assert ambiguity["outcome"] == "ambiguous"
    assert [(e["input_index"], e["occurrence_id"]) for e in ambiguity["endpoints"]] == [
        (1, "block-0"),
        (1, "block-1"),
        (2, "block-0"),
        (2, "block-1"),
    ]
    assert actual["health"]["source_fidelity"] == "unassessed"


def test_scoped_companion_does_not_materialize_bookwide_coverage(pdf13_db, semantic_reader_engine):
    from corpus_structure.semantic.pdf_storage import read_pdf_manifest

    db = pdf13_db
    values = integrated(db.source, db.inputs)
    values["product_key"] = "bookwide-coverage"
    values["coverage"].extend(
        {
            "coverage_id": f"book-page-{page:04d}",
            "scope": f"page:{page}",
            "family": "table",
            "discovery_policy": "fixture-book-page-output",
            "outcome": "partial",
            "detail": "Independent page output scope, no source absence claim",
            "supports": [],
        }
        for page in range(3, 1590)
    )
    product = prepare(values, db.source)
    publish(db, product)
    with semantic_reader_engine.connect() as conn:
        scoped = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="bookwide-coverage",
            content_digest=product.digest,
            occurrence_id=CELL,
            row_budget=20,
        )
        assert len(scoped["inputs"]) == 3
        assert all(c["body"]["scope"] in {"whole_document", "page:1"} for c in scoped["coverage"])
        after = ""
        all_rows = []
        while True:
            page = read_pdf_manifest(
                conn,
                task_id=db.job.task,
                product_key="bookwide-coverage",
                content_digest=product.digest,
                collection="coverage",
                after=after,
                limit=137,
            )
            all_rows.extend(page["rows"])
            if page["cursor"] is None:
                break
            after = page["cursor"]
        assert {r["coverage_id"] for r in all_rows} == {
            c["coverage_id"] for c in values["coverage"]
        }
        assert len(all_rows) == len(values["coverage"])


def test_artifact_byte_pages_require_exact_input_custody(pdf13_db, semantic_reader_engine):
    from corpus_structure.semantic.pdf_storage import read_pdf_artifact

    db = pdf13_db
    values = integrated(db.source, db.inputs)
    values["product_key"] = "artifact-pages"
    artifact = bytes(range(256)) * 600
    product = prepare_integrated_pdf_product(
        values,
        db.source.original,
        db.source.recipe,
        artifacts=(artifact,),
        native_schema=db.source.schema,
    )
    publish(db, product)
    args = dict(task_id=db.job.task, product_key="artifact-pages", content_digest=product.digest)
    with semantic_reader_engine.connect() as conn:
        offset = 0
        parts = []
        while True:
            page = read_pdf_artifact(
                conn, **args, artifact_digest=sha256(artifact).hexdigest(), offset=offset
            )
            assert len(page["content"]) <= 65536 and page["total_bytes"] == len(artifact)
            parts.append(page["content"])
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
        assert b"".join(parts) == artifact
        # The selected product's actual observation inputs retain exact submitted bytes.
        assert (
            read_pdf_artifact(conn, **args, artifact_digest=sha256(IMAGE).hexdigest())["content"]
            == IMAGE
        )
        with pytest.raises(NativeDocumentUnavailable, match="custody"):
            read_pdf_artifact(conn, **args, artifact_digest="0" * 64)
        with pytest.raises(ValueError, match="byte length"):
            read_pdf_artifact(
                conn, **args, artifact_digest=sha256(artifact).hexdigest(), offset=len(artifact) + 1
            )


def test_qualified_read_abi_survives_helper_bytes_but_refuses_unknown_binding(
    pdf13_db, semantic_reader_engine, monkeypatch
):
    from corpus_structure.semantic import pdf_contracts

    db = pdf13_db
    product = prepare(integrated(db.source, db.inputs), db.source)
    publish(db, product)
    load = pdf_contracts.pdf_context_for_task
    unsupported = False

    def archived_context(conn, task):
        context = load(conn, task)
        execution = context.execution
        return replace(
            context,
            execution=replace(
                execution,
                implementation_digests=tuple(
                    (name, "0" * 64 if name in {"pdf/storage.py", "pdf/integrated.py"} else digest)
                    for name, digest in execution.implementation_digests
                ),
                implementations=tuple(
                    replace(binding, version="unsupported-v2")
                    if unsupported and binding.id == "read_pdf_product"
                    else binding
                    for binding in execution.implementations
                ),
            ),
        )

    monkeypatch.setattr(pdf_contracts, "pdf_context_for_task", archived_context)
    with semantic_reader_engine.connect() as conn:
        result = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="selected",
            content_digest=product.digest,
            occurrence_id=CELL,
        )
        assert result["occurrences"][0]["body"]["native_value"]["text"] == "equal"
        unsupported = True
        with pytest.raises(NativeDocumentUnavailable, match="ABI is unsupported"):
            read_pdf_product(
                conn,
                task_id=db.job.task,
                product_key="selected",
                content_digest=product.digest,
                occurrence_id=CELL,
            )
