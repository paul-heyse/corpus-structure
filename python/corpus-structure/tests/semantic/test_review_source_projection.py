"""Portable current source projection checks derive pieces from native records."""

import base64
import json
import zlib
from contextlib import closing
from hashlib import sha256
from typing import Any

import pytest

from corpus_structure.ingest.pdf_hierarchy import section_text_recipe, section_view_key
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_record_identity import PROTOCOL, IdentityFold, record_frame
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.serve.review_source_projection import (
    load_source_proofs,
    open_proof_index,
    verify_source_projection,
)


def source_proof_fixture() -> tuple[dict[str, Any], list[dict[str, Any]], bytes, str]:
    original, schema, release = "b" * 64, "c" * 64, "release:test"
    root, first, second, nested = "#/body", "#/texts/0", "#/texts/1", "#/groups/0"
    nodes: list[dict[str, Any]] = [
        dict(self_ref=root, label="body", children=[{"$ref": p} for p in (first, second, nested)]),
        dict(self_ref=first, label="text", text="Required"),
        dict(self_ref=second, label="text", text="Retained"),
        dict(self_ref=nested, label="section"),
    ]
    records: dict[tuple[str, str], tuple[tuple[str, Any], ...]] = {
        ("@context", "@context"): (
            ("protocol", PROTOCOL),
            ("release", release),
            ("source", original),
        ),
    }
    items, targets = [], []
    for ordinal, node in enumerate(nodes):
        record = f"node-{ordinal}"
        children = node.get("children")
        items.append(
            dict(
                record_id=record,
                pointer=node["self_ref"],
                label=node["label"],
                content_layer="body",
                parent_pointer=None if not ordinal else root,
                children=children,
            )
        )
        fields = [(name + "/value", value) for name, value in node.items() if name != "children"]
        if ordinal:
            fields.extend((("parent/kind", "object"), ("parent/target", "parent")))
            records[("native", "parent")] = (("$ref/value", root),)
            targets.append((record, "parent", -1, "parent"))
        if children is not None:
            fields.extend((("children/kind", "array"), ("children/length", len(children))))
            for i, child in enumerate(children):
                target = f"child-{i}"
                key = json.dumps([record, "children", i], separators=(",", ":"))
                records[("membership", key)] = (
                    ("parent_id", record),
                    ("field_name", "children"),
                    ("ordinal", i),
                    ("target", target),
                )
                records[("native", target)] = (("$ref/value", child["$ref"]),)
                targets.append((record, "children", i, target))
        records[("native", record)] = tuple(fields)
    fold = IdentityFold("records")
    frames = [
        record_frame(schema, family, key, fields)
        for (family, key), fields in sorted(records.items())
    ]
    for frame in frames:
        fold.add(frame)
    product = ProductReference(1, "native", fold.digest().hex())
    policy = (
        b'{"content_layers":["body"],"readable_formula_originals":[],'
        b'"recipe":"native-section-text-v10"}'
    )
    recipe = section_text_recipe(product, analysis_eligible=True, policy=policy)
    value: dict[str, Any] = dict(
        consumer_release=release,
        ref=dict(
            native_product=product.values(),
            section_pointer=root,
            membership="direct",
            analysis_eligible=True,
            recipe_digest=sha256(recipe).hexdigest(),
            key=section_view_key(release, product, root, "direct", True, recipe),
        ),
        text="Required\nRetained",
        context=dict(
            items=[
                nodes[0],
                {**nodes[1], "parent": {"$ref": root}},
                {**nodes[2], "parent": {"$ref": root}},
            ],
            ancestors=[],
            pieces=[
                dict(item_ref=first, start=0, end=8, kind="native_text", source_field="text"),
                dict(start=8, end=9, kind="synthetic_separator"),
                dict(item_ref=second, start=9, end=17, kind="native_text", source_field="text"),
            ],
        ),
    )
    rows: list[dict[str, Any]] = [
        dict(
            product=product.values(),
            native_schema=schema,
            original=original,
            producer_release=release,
        ),
        dict(frames=base64.b64encode(zlib.compress(b"".join(frames))).decode()),
        dict(targets=targets),
        dict(items=items),
    ]
    return value, rows, policy, original


def test_current_review_replays_selected_prose_and_qualified_exclusions():
    value, rows, policy, original = source_proof_fixture()
    with closing(open_proof_index(":memory:")) as database:
        (proof,) = load_source_proofs(database, rows).values()
        assert verify_source_projection(value, policy, proof) == original
        value["text"] = "Retained"
        value["context"]["pieces"] = [
            dict(item_ref="#/texts/1", start=0, end=8, kind="native_text", source_field="text"),
        ]
        with pytest.raises(ValueError, match="field address inventory"):
            verify_source_projection(value, policy, proof)
        del value["context"]["items"][1]
        value["source_coverage"] = "selected_projection_only"
        with pytest.raises(ValueError, match="membership differs"):
            verify_source_projection(value, policy, proof)


def test_resealed_exclusion_cannot_reclassify_an_authenticated_prose_occurrence():
    _, rows, _, _ = source_proof_fixture()
    rows[-1]["items"][1]["content_layer"] = "furniture"
    with (
        closing(open_proof_index(":memory:")) as database,
        pytest.raises(ValueError, match="exclusion differs"),
    ):
        load_source_proofs(database, rows)


def test_current_bundle_requires_proof_and_rejects_resealed_exclusion(tmp_path):
    from corpus_structure.serve.contributions import ContributionRequest
    from corpus_structure.serve.review_bundle import ReviewSelection, write_review_bundle
    from corpus_structure.serve.review_source_projection import SECTION_TEXT_INPUT

    value, proofs, policy, original = source_proof_fixture()
    manifest = canonical_bytes({"dependencies": [[SECTION_TEXT_INPUT, sha256(policy).hexdigest()]]})
    release = "release:" + sha256(manifest).hexdigest()
    value["consumer_release"] = release
    context, ref = value["context"], value["ref"]
    native = ProductReference(**ref["native_product"])
    recipe = section_text_recipe(native, analysis_eligible=True, policy=policy)
    context["health"] = {"state": "unknown"}
    projection = {
        "text": value["text"],
        "pieces": context["pieces"],
        "items": [item["self_ref"] for item in context["items"]],
        "ancestors": [],
        "health": context["health"],
    }
    value["source_view_id"] = 1
    ref.update(
        id=1,
        document_id=1,
        key=section_view_key(release, native, ref["section_pointer"], "direct", True, recipe),
        projection_digest=sha256(canonical_bytes(projection)).hexdigest(),
    )
    contract = dict(
        release_id=release,
        definitions=[],
        registry_rows=[],
        section_text_policy=dict(
            manifest_base64=base64.b64encode(manifest).decode(),
            input_base64=base64.b64encode(policy).decode(),
        ),
    )
    selection = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    rows = [
        ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
        ("inventory", {"population": "contribution", "row": {"source_view_id": 1}}),
        ("sources", value),
        ("documents", {"id": 1, "content_hash": original}),
        ("contracts", contract),
    ]
    complete = [*rows, *(("source_proofs", proof) for proof in proofs)]
    write_review_bundle(selection, tmp_path / "complete", complete)
    value["source_coverage"] = "selected_projection_only"
    with pytest.raises(ValueError, match="exact native proof"):
        write_review_bundle(selection, tmp_path / "downgraded", rows)
    proofs[-1]["items"][1]["label"] = "section"
    with pytest.raises(ValueError, match="exclusion differs"):
        write_review_bundle(selection, tmp_path / "reclassified", complete)


def test_downstream_enclosure_and_rich_cell_reuse_the_selected_formula_field():
    from types import SimpleNamespace

    from corpus_structure.ingest.pdf_hierarchy import retained_formula_originals
    from corpus_structure.methods.source_preparation import (
        _primary_formula_enclosure,
        native_table_cell_projection,
    )

    enclosing, formula = "#/texts/0", "#/texts/1"
    nodes = {
        enclosing: dict(
            self_ref=enclosing,
            label="text",
            text="Before",
            children=[{"$ref": formula}],
        ),
        formula: dict(
            self_ref=formula,
            label="formula",
            text="r",
            orig="x+y",
            parent={"$ref": enclosing},
        ),
    }
    before = dict(item_ref=enclosing, kind="native_text", source_field="text", start=0, end=6)
    display = dict(item_ref=formula, kind="native_text", source_field="orig", start=7, end=10)
    view = SimpleNamespace(text="Before\nx+y", pieces=(before, display))
    selected = retained_formula_originals(view.pieces)
    selection = SimpleNamespace(region=formula, start=7, end=10)
    result = _primary_formula_enclosure(
        view, nodes, selection, {enclosing: [before], formula: [display]}, selected
    )
    assert result is not None
    assert result[:2] == (enclosing, (0, 10))

    table = dict(self_ref="#/tables/0", data=dict(table_cells=[{"ref": {"$ref": enclosing}}]))
    cell = native_table_cell_projection(table, 0, nodes, retained_originals=selected)
    assert cell.text == "Before\nx+y"
    assert cell.pieces[-1].source_field == "orig"
    assert cell.pieces[-1].cell_index == 0
