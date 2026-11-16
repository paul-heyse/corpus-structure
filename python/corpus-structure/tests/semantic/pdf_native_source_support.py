"""Independent native PDF payload data, without a run/task/database seed."""

from base64 import b64decode
from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_integrated import prepare_integrated_pdf_product

IMAGE = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAQAAAAGCAIAAABrW6giAAAAFElEQVR4nGP8//8/"
    "AwwwMSABcjgA5T4DCWUMPAMAAAAASUVORK5CYII="
)


@pytest.fixture
def native_source():
    return make_native_source(b"%PDF-1.7\nindependent integrated lineage original")


def make_native_source(original: bytes):
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
        first_text["page_no"] = 1
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
