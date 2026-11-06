"""Independent integrated-PDF contract and protected PostgreSQL lineage examples.

All observations are retained fixture bytes: these tests run no recognizer or model inference.
"""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest
from sqlalchemy import event, insert, select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_contracts import prepare_pdf_product
from corpus_structure.semantic.pdf_integrated import (
    prepare_integrated_pdf_product,
    store_pdf_observation,
)
from corpus_structure.semantic.pdf_storage import (
    NativeDocumentUnavailable,
    read_native_items,
    read_pdf_product,
    trace_pdf_occurrence,
)

from .pdf_integration_support import (
    CELL,
    CELL_IDS,
    HOLDER,
    IMAGE,
    ITEM_IDS,
    REGION_IDS,
    RESPONSE,
    _publish_record_document,
    _publish_record_values,
    integrated,
    mutate_selected,
    observation,
    pin,
    prepare,
    publish,
)
from .pdf_integration_support import (
    independent_integrated as independent_integrated,
)
from .pdf_integration_support import (
    native_source as native_source,
)
from .pdf_integration_support import (
    pdf13_context as pdf13_context,
)
from .pdf_integration_support import (
    pdf13_db as pdf13_db,
)


def test_materialized_integrated_content_enforces_released_metadata_affinity(
    independent_integrated, native_source, pdf13_context
):
    # Valid native runtime metadata remains input-qualified after integration. The
    # outer product owns kind; its content envelope deliberately has no kind field.
    independent_integrated["content"]["runtime_report"] = {
        "packages": [],
        "bindings": [],
        "effective_options": "{}",
    }
    with pytest.raises(ValueError, match="qualified input graph"):
        prepare(independent_integrated, native_source, context=pdf13_context)


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


def test_selected_cell_traces_two_observations_original_and_policy_reuse(
    pdf13_db, semantic_reader_engine
):
    from docling_core.types.doc import DoclingDocument

    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.product_reference import ProductReference

    db = pdf13_db
    product = prepare(integrated(db.source, db.inputs), db.source)
    transmitted = []

    def capture_publication(conn, clause, multiparams, params, options):
        def values(value):
            if isinstance(value, (bytes, bytearray, memoryview)):
                yield bytes(value)
            elif isinstance(value, dict):
                for child in value.values():
                    yield from values(child)
            elif isinstance(value, (tuple, list)):
                for child in value:
                    yield from values(child)

        # Generated calls bind immutable values into the Core statement itself.
        # Explicit execution parameters still take precedence when supplied.
        transmitted.extend(values({**(clause.compile().params or {}), **params}))
        transmitted.extend(values(multiparams))

    event.listen(db.writer, "before_execute", capture_publication)
    try:
        digest = publish(db, product)
    finally:
        event.remove(db.writer, "before_execute", capture_publication)
    assert db.source.original not in transmitted
    assert IMAGE not in transmitted and RESPONSE not in transmitted
    assert db.source.recipe in transmitted
    assert publish(db, product) == digest
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
            content_digest=db.native_digest,
            include_body=True,
        )
        original = db.native.values()
        body = native["body"]
        assert DoclingDocument.model_validate(body["document"]).model_dump(
            mode="json", by_alias=True, exclude_computed_fields=True
        ) == DoclingDocument.model_validate(original["document"]).model_dump(
            mode="json", by_alias=True, exclude_computed_fields=True
        )
        assert {key: value for key, value in body.items() if key not in {"document", "health"}} == {
            key: value
            for key, value in original.items()
            if key not in {"document", "health", "items", "regions"}
        }
        # Empty outcome inventory is represented by no formula-outcome companion rows.
        assert original["health"]["formula_outcomes"] == []
        assert body["health"] == {
            key: value for key, value in original["health"].items() if key != "formula_outcomes"
        }
        actual_items = read_native_items(
            conn,
            task_id=db.job.task,
            product_key="native",
            content_digest=db.native_digest,
            projection_context=db.prepared,
        )
        item_fields = (
            "pointer",
            "ordinal",
            "parent_pointer",
            "label",
            "content_layer",
            "section_pointer",
            "text",
        )
        assert [{key: row.get(key) for key in item_fields} for row in actual_items] == [
            {key: row.get(key) for key in item_fields} for row in original["items"]
        ]
        record_reader = published_record_reader(
            conn,
            ProductReference(db.job.task, "native", db.native_digest),
            projection_context=db.prepared,
        )
        assert record_reader is not None
        actual_regions = record_reader.selected_regions(
            tuple(row["pointer"] for row in actual_items)
        )
        assert [
            {key: row[key] for key in original["regions"][0]} for row in actual_regions
        ] == sorted(original["regions"], key=lambda row: (row["pointer"], row["region_index"]))
        assert native["identity"]["content_digest"] == db.native_digest
        assert read_native_items(
            conn,
            task_id=db.job.task,
            product_key="selected",
            content_digest=digest,
            projection_context=db.prepared,
        )
        assert {
            o["occurrence_id"] for o in native["occurrences"]
        } == ITEM_IDS | CELL_IDS | REGION_IDS
        selected = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="selected",
            content_digest=digest,
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
            content_digest=digest,
            occurrence_id=CELL,
        )
        assert trace["complete"] is True
        metadata = {p["product_key"]: p for p in trace["products"]}
        assert set(metadata) == {"selected", "native", "pass-a", "pass-b"}
        assert metadata["native"]["content_digest"] == db.native_digest
        assert metadata["selected"]["content_digest"] == digest
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
        with pytest.raises(ValueError, match="exceeds requested row budget"):
            trace_pdf_occurrence(
                conn,
                task_id=db.job.task,
                product_key="selected",
                content_digest=digest,
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
                content_digest=digest,
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
            content_digest=digest,
            occurrence_id=CELL,
        )
        assert old["relations"][0]["body"]["policy"] == "retain-native-v1"
        page = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="selected",
            content_digest=digest,
            limit=1,
        )
        following = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="selected",
            content_digest=digest,
            after=page["cursor"],
            limit=100,
        )
        assert len(page["occurrences"]) == 1
        assert {
            o["occurrence_id"] for o in page["occurrences"] + following["occurrences"]
        } == ITEM_IDS | CELL_IDS


def test_integrated_preparation_and_native_task_fences_are_explicit(pdf13_db):
    db = pdf13_db
    value = integrated(db.source, db.inputs)
    product = prepare(value, db.source)
    sibling = deepcopy(value)
    sibling["product_key"] = "valid-integration-premise"
    assert publish(db, prepare(sibling, db.source))
    python_refusals = {
        "empty_companions": "selected content occurrence inventory is incomplete or ambiguous",
        "missing_coverage": (
            "coverage requires independently identified scope/family/policy/results"
        ),
        "missing_decision": "every selected occurrence requires a governing integration decision",
        "wrong_kind": "selected occurrence kind differs from native label",
        "exact_glyph": "selected item address/precision differs from native custody",
        "out_of_bounds_region": "selected region differs from retained native page/geometry",
        "wrong_region_page": "selected region differs from retained native page/geometry",
        "missing_region_page": "PDF region requires its physical page",
        "forged_text": "selected occurrence text differs from Docling content",
        "missing_local_endpoint": "local endpoint is not an existing output occurrence",
        "duplicate_endpoint": "duplicate relationship endpoint",
    }
    for index, (change, message) in enumerate(python_refusals.items()):
        invalid = deepcopy(value)
        invalid["product_key"] = f"invalid-{index}"
        mutate_selected(invalid, change)
        # The DB-free frozen-union validator owns these semantic refusals. This
        # does not claim they reached the later native publication guard.
        with pytest.raises(ValueError, match=message):
            _publish_record_values(db, invalid)
    for change, message in (
        ("opaque_region", "parsing record shape differs: PdfProductOccurrence"),
        ("duplicate_occurrence", "changed companion duplicate"),
    ):
        invalid = deepcopy(value)
        invalid["product_key"] = "invalid-" + change
        mutate_selected(invalid, change)
        with pytest.raises(DBAPIError) as caught:
            _publish_record_values(db, invalid)
        assert isinstance(caught.value.orig, psycopg.Error)
        assert (caught.value.orig.sqlstate, caught.value.orig.diag.message_primary) == (
            "23514",
            message,
        )
    for attempt, holder in ((db.job.attempt + 1, HOLDER), (db.job.attempt, "another-holder")):
        with pytest.raises(DBAPIError) as caught:
            publish(db, product, attempt=attempt, holder=holder)
        assert isinstance(caught.value.orig, psycopg.Error)
        assert (caught.value.orig.sqlstate, caught.value.orig.diag.message_primary) == (
            "P0004",
            "stale private PDF build owner",
        )
    forged = replace(product, payload=canonical_bytes({**value, "product_key": "forged"}))
    with pytest.raises(ValueError, match="immutable prepared"):
        publish(db, forged)
    digest = publish(db, product)
    mutated = deepcopy(value)
    mutated["health"]["validation_report"] = "changed after publication"
    with pytest.raises(ValueError, match="frozen/published"):
        _publish_record_values(db, mutated)
    assert publish(db, product) == digest
    # The narrowed observation retainer cannot publish the removed aggregate document shape.
    with db.writer.begin() as conn, pytest.raises(ValueError):
        store_pdf_observation(
            conn, task_id=db.job.task, attempt=db.job.attempt, holder=HOLDER, product=product
        )
    with db.admin.connect() as conn:
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM ops.pdf_published_revision "
                    "WHERE product_key LIKE 'invalid-%' OR product_key='forged'"
                )
            )
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
    other_digest = _publish_record_document(db, foreign_native, job=other, source=other_source)
    with db.admin.begin() as conn:
        conn.execute(insert(table("data.project")).values(project_id="foreign"))
        conn.execute(
            insert(table("data.realization")).values(
                project_id="foreign", realization_id="foreign-z", release_id=db.prepared.release_id
            )
        )
    foreign = db.create(project="foreign", name="foreign-project")
    foreign_digest = _publish_record_document(db, db.native, job=foreign)
    cases = [
        pin(db.job.task, "native", "0" * 64, "structural"),
        pin(db.job.task, "not-published", "a" * 64, "structural"),
        pin(db.job.task, "attempt-self", "a" * 64, "structural"),
        pin(other.task, "native", other_digest, "structural"),
        pin(foreign.task, "native", foreign_digest, "structural"),
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
    assert getattr(refused.value.orig, "sqlstate", None) == "23514"
    assert "companion endpoint outside admitted occurrence inventory" in str(refused.value.orig)


def test_partial_observation_cannot_support_complete_integrated_coverage(pdf13_db):
    db = pdf13_db
    value = integrated(db.source, db.inputs)
    for defect in ("outcome", "missing", "scope", "family"):
        invalid = deepcopy(value)
        invalid["product_key"] = f"false-complete-{defect}"
        coverage = invalid["coverage"][0]
        coverage.update(
            outcome="complete",
            supports=[
                {
                    "input_index": 1,
                    "coverage_id": "nonexistent-coverage"
                    if defect == "missing"
                    else "page-1-table",
                }
            ],
        )
        if defect in {"scope", "family"}:
            coverage[defect] = "page:2" if defect == "scope" else "text"
        with pytest.raises(DBAPIError) as refused:
            publish(db, prepare(invalid, db.source))
        assert getattr(refused.value.orig, "sqlstate", None) == "23514"
        assert "coverage support differs from exact input coverage scope/family/outcome" in str(
            refused.value.orig
        )

    # A native producer can independently qualify complete coverage without inherited
    # support; integrated completeness must cite that exact admitted assessment.
    native = deepcopy(db.source.payload)
    native["product_key"] = "native-complete-seed"
    native["coverage"] = [
        dict(
            coverage_id="native-table-complete",
            scope="page:1",
            family="table",
            discovery_policy="fixture-native-full-page",
            outcome="complete",
            detail="independent native producer assessment",
            supports=[],
        )
    ]
    native_digest = _publish_record_values(db, native)
    selected = integrated(
        db.source,
        [pin(db.job.task, native["product_key"], native_digest, "structural"), *db.inputs[1:]],
    )
    for outcome in ("complete", "partial"):
        selected["product_key"] = f"mixed-evidence-{outcome}"
        selected["coverage"][0].update(
            outcome=outcome,
            supports=[
                {"input_index": 0, "coverage_id": "native-table-complete"},
                {"input_index": 1, "coverage_id": "page-1-table"},
            ],
        )
        assert publish(db, prepare(selected, db.source))
    selected["product_key"] = "complete-plus-invalid-edge"
    selected["coverage"][0].update(outcome="complete")
    selected["coverage"][0]["supports"][1]["coverage_id"] = "absent-even-with-complete-witness"
    with pytest.raises(DBAPIError) as refused:
        publish(db, prepare(selected, db.source))
    assert getattr(refused.value.orig, "sqlstate", None) == "23514"
    assert "coverage support differs from exact input coverage scope/family/outcome" in str(
        refused.value.orig
    )


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
    digest = publish(db, product)
    with semantic_reader_engine.connect() as conn:
        retained = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="pass-c-failed",
            content_digest=digest,
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


def test_retained_recognition_page_callback_uses_observation_only_native_port(
    pdf13_db, semantic_reader_engine, tmp_path
):
    import json

    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.ingest.pdf_recognition import (
        NemotronRecipe,
        PreparedRecognitionSource,
        RecognitionPage,
    )
    from corpus_structure.ingest.pdf_recognition_methods import _retain_page
    from corpus_structure.semantic.operations import BoundReader
    from corpus_structure.semantic.pdf_integrated import PreparedPdfOriginal
    from corpus_structure.semantic.product_reference import ProductReference

    db = pdf13_db
    directory = tmp_path / "retained-request"
    directory.mkdir()
    raw = b"<x_0.1><y_0.2>retained page<x_0.8><y_0.3><class_Text>"
    (directory / "submitted.png").write_bytes(IMAGE)
    (directory / "response.txt").write_bytes(raw)
    (directory / "request-000.json").write_text(
        json.dumps(
            dict(
                ordinal=0,
                stage="fullpage",
                outcome="succeeded",
                submitted_image="submitted.png",
                submitted_digest=sha256(IMAGE).hexdigest(),
                width=4,
                height=6,
                raw_response="response.txt",
                prompt="Independent retained request fixture",
                settings={},
                finish_reason="stop",
            )
        )
    )
    page = RecognitionPage(
        1,
        directory,
        {"outcome": "succeeded"},
        dict(
            status="unknown",
            normalization="unknown",
            source_space="pdf_points",
            target_space="submitted_pixels",
        ),
    )
    recipe = NemotronRecipe("1" * 64, "2" * 64)
    unit = UnitRef(TaskUnitType.DOCUMENT, db.job.document)

    def retain(ref, product):
        assert ref == unit
        assert product.values()["kind"] == "recognition_observation"
        return ProductReference(db.job.task, product.values()["product_key"], publish(db, product))

    with db.writer.connect() as conn:
        reader = BoundReader(conn, db.job.run, db.prepared, analysis=False)
        reader.source_tasks[db.job.document] = db.job.task
        context: Any = SimpleNamespace(reader=reader, retain_pdf_observation=retain)
        retained = _retain_page(
            page,
            unit,
            PreparedRecognitionSource.prepare(db.source.original),
            recipe,
            PreparedPdfOriginal(db.source.original),
            context,
        )
    assert len(retained) == 1
    reference, observed, response = retained[0]
    assert (
        response == raw
        and observed["observation"]["raw_response_digest"] == sha256(raw).hexdigest()
    )
    with semantic_reader_engine.connect() as conn:
        stored = read_pdf_product(conn, **reference, include_body=True)
    assert stored["body"] == observed
    assert stored["occurrences"][0]["body"]["text"] == "retained page"


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
    digest = publish(db, product)
    with semantic_reader_engine.connect() as conn:
        scoped = read_pdf_product(
            conn,
            task_id=db.job.task,
            product_key="bookwide-coverage",
            content_digest=digest,
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
                content_digest=digest,
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
    retained_response = observation(db.source, key="artifact-response")
    retained_response["observation"]["raw_response_digest"] = sha256(artifact).hexdigest()
    evidence = prepare_integrated_pdf_product(
        retained_response, db.source.original, db.source.recipe, artifacts=(IMAGE, artifact)
    )
    publish(db, evidence)
    values["inputs"].append(pin(db.job.task, "artifact-response", evidence.digest, "recognition"))
    product = prepare_integrated_pdf_product(
        values,
        db.source.original,
        db.source.recipe,
        artifacts=(),
        native_schema=db.source.schema,
    )
    digest = publish(db, product)
    args = dict(task_id=db.job.task, product_key="artifact-pages", content_digest=digest)
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
    digest = publish(db, product)
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
            content_digest=digest,
            occurrence_id=CELL,
        )
        assert result["occurrences"][0]["body"]["native_value"]["text"] == "equal"
        unsupported = True
        with pytest.raises(NativeDocumentUnavailable, match="ABI is unsupported"):
            read_pdf_product(
                conn,
                task_id=db.job.task,
                product_key="selected",
                content_digest=digest,
                occurrence_id=CELL,
            )
