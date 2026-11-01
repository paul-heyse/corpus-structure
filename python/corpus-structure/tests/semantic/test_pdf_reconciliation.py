"""Independent retained coordinate/token examples; no model inference or fixtures as oracle."""

from hashlib import sha256

import pytest

from corpus_structure.ingest.pdf_reconciliation import (
    compare_pdf_occurrences,
    map_pdf_observation,
    select_pdf_integration,
)

from . import test_pdf_integrated as integration_fixtures
from .test_pdf_integrated import observation, pin

native_source = integration_fixtures.native_source
pdf13_db = integration_fixtures.pdf13_db


def recognized(source, raw, *, role="A", page=1):
    value = observation(source, pass_role=role)
    value["observation"]["raw_response_digest"] = sha256(raw).hexdigest()
    value["observation"]["image"].update(page_no=page, width=200, height=300)
    value["observation"]["image"]["transform"] = {
        "status": "coarse",
        "normalization": "none",
        "source_space": "pdf_points",
        "target_space": "submitted_pixels",
        "page_width": 200.0,
        "page_height": 300.0,
        "page_rotation": 0,
        "crop_left": 0.0,
        "crop_top": 0.0,
        "crop_right": 200.0,
        "crop_bottom": 300.0,
        "affine": [1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
    }
    value["occurrences"] = [
        {
            "occurrence_id": f"block-{i}",
            "kind": "text",
            "address_space": "recognized_text",
            "precision": "block",
            "page_no": page,
        }
        for i in range(raw.count(b"<class_"))
    ]
    value["coverage"][0].update(scope=f"page:{page}", family="nemotron-pass-" + role)
    return value


def integrate(source, raw, *, policy=None):
    obs = recognized(source, raw)
    return select_pdf_integration(
        source.payload,
        pin(1, "native", "0" * 64, "structural"),
        [(pin(2, "a", "1" * 64, "recognition"), obs, raw)],
        source.original,
        source.recipe,
        source.schema,
        policy=policy,
    ).values()


def test_mapper_repeated_equal_occurrences_and_raw_geometry(native_source):
    raw = (
        b"<x_0.05><y_0.033333>equal<x_0.3><y_0.066666><class"
        b"_Text><x_0.05><y_0.133333>equal<x_0.3><y_0.166666>"
        b"<class_Text>"
    )
    mapped = map_pdf_observation(recognized(native_source, raw), raw)
    assert len(mapped.document.texts) == 2
    assert mapped.origins == {"#/texts/0": "block-0", "#/texts/1": "block-1"}
    assert mapped.document.texts[0].prov[0].bbox.l == 10
    assert mapped.document.texts[0].prov[0].bbox.t == pytest.approx(9.9999)
    assert mapped.document.texts[0].prov[0].charspan == (0, 0)


def test_crop_transform_is_inverted_with_independent_expected_points(native_source):
    raw = b"<x_0.2><y_0.1>crop<x_0.8><y_0.9><class_Text>"
    obs = recognized(native_source, raw)
    obs["observation"]["image"].update(width=100, height=200)
    # x_pixels=2*x_pdf-40; y_pixels=2*y_pdf-60.
    obs["observation"]["image"]["transform"].update(
        crop_left=20.0,
        crop_top=30.0,
        crop_right=70.0,
        crop_bottom=130.0,
        affine=[2.0, 0.0, 0.0, 2.0, -40.0, -60.0],
    )
    box = map_pdf_observation(obs, raw).document.texts[0].prov[0].bbox
    assert (box.l, box.t, box.r, box.b) == (30.0, 40.0, 60.0, 120.0)


def test_mapper_keeps_table_spans_chart_metadata_and_inline_math(native_source):
    raw = (
        b"<x_0.1><y_0.2>\\begin{tabular}{cc}\\multicolumn{2}{c"
        b"}{Header} \\\\ 1 & 2\\end{tabular}<x_0.9><y_0.5><clas"
        b's_Table><x_0.1><y_0.6><chart type="line"><title>Sp'
        b"eed</title>\\n| t | m/s |\\n|---|---|\\n|1|2|<x_0.9><"
        b"y_0.9><class_Chart><x_0.1><y_0.05>Value $x+1$ foll"
        b"ows<x_0.9><y_0.1><class_Text>"
    ).replace(rb"\n", b"\n")
    doc = map_pdf_observation(recognized(native_source, raw), raw).document
    assert doc.tables[0].data.table_cells[0].col_span == 2
    assert doc.pictures[0].meta.tabular_chart.chart_data.num_rows >= 1
    assert any(t.label == "formula" and t.text == "x+1" for t in doc.texts)
    assert all(not getattr(c, "bbox", None) for c in doc.tables[0].data.table_cells)


def test_selection_replace_preserves_original_alternative_and_replay(native_source):
    raw = b"<x_0.05><y_0.033333>corrected<x_0.3><y_0.066666><class_Text>"
    first = integrate(native_source, raw)
    assert first == integrate(native_source, raw)
    assert any(t["text"] == "corrected" for t in first["content"]["document"]["texts"])
    decisions = [r for r in first["relations"] if r["outcome"] == "replaced"]
    assert decisions and any(
        e.get("input_index") == 0 and e["role"] == "alternative" for e in decisions[0]["endpoints"]
    )
    assert all(o["precision"] != "glyph" for o in first["occurrences"])


def test_policy_remapping_reuses_raw_and_retains_conflict(native_source):
    raw = b"<x_0.05><y_0.033333>corrected<x_0.3><y_0.066666><class_Text>"
    policy = {
        "policy_id": "pdf-integration-v1",
        "conflict_action": "unresolved",
        "unmatched_action": "add",
        "specialized_crop_precedence": True,
    }
    result = integrate(native_source, raw, policy=policy)
    assert [t["text"] for t in result["content"]["document"]["texts"]] == ["equal", "equal"]
    assert any(r["outcome"] == "unresolved" for r in result["relations"])


def test_generated_inline_formula_has_parent_grounding_not_fake_glyph_box(native_source):
    raw = rb"<x_0.5><y_0.5>Value $x+1$ follows<x_0.95><y_0.6><class_Text>"
    result = integrate(native_source, raw)
    formula = next(o for o in result["occurrences"] if o["kind"] == "formula")
    assert formula["precision"] == "inherited"
    assert formula["grounding_pointer"] != formula["pointer"]
    assert "start" not in formula and "end" not in formula
    node = result["content"]["document"]["texts"][int(formula["pointer"].split("/")[-1])]
    assert node["prov"] == []


def test_failure_layout_unknown_and_truncation_dispositions(native_source):
    raw = b"<x_0.2><y_0.1>unknown<x_0.8><y_0.2><class_Alien><x_0.2>broken<class_Text>tail"
    mapped = map_pdf_observation(recognized(native_source, raw), raw)
    assert [d["outcome"] for d in mapped.dispositions] == ["unsupported", "unsupported", "dropped"]
    assert not mapped.document.body.children
    layout = map_pdf_observation(recognized(native_source, raw, role="B"), raw)
    assert layout.dispositions[0]["reason"] == "layout_pass"
    obs = recognized(native_source, raw)
    obs["observation"]["outcome"] = "failed"
    assert not map_pdf_observation(obs, raw).document.body.children
    with pytest.raises(ValueError, match="differs"):
        map_pdf_observation(obs, raw + b"changed")


def test_text_syntax_and_symbolic_comparison_are_distinct():
    plain = compare_pdf_occurrences("x+1", "1+x")
    assert not plain["text_equal"] and "equivalent" not in plain
    syntax = compare_pdf_occurrences("x+1", "1+x", mathematical=True)
    assert "syntax" in syntax and "equivalent" not in syntax
    symbolic = compare_pdf_occurrences("x+1", "1+x", mathematical=True, symbolic=True)
    assert symbolic["equivalent"] is True


@pytest.mark.parametrize(
    ("coords", "image_size", "affine", "expected", "frame"),
    [
        (
            "0.1,0.1,1.2,0.2",
            (200, 300),
            [1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            (20.0, 30.0, 200.0, 60.0),
            "content_normalized",
        ),
        (
            "100,100,900,200",
            (200, 300),
            [1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            (20.0, 30.0, 180.0, 60.0),
            "quantized_1000",
        ),
        (
            "100,150,1100,2400",
            (2000, 3000),
            [10.0, 0.0, 0.0, 10.0, 0.0, 0.0],
            (10.0, 15.0, 110.0, 240.0),
            "submitted_pixels",
        ),
    ],
)
def test_vendor_coordinate_units_and_clipping_are_attributed(
    native_source, coords, image_size, affine, expected, frame
):
    left, top, right, bottom = coords.split(",")
    raw = f"<x_{left}><y_{top}>units<x_{right}><y_{bottom}><class_Text>".encode()
    obs = recognized(native_source, raw)
    obs["observation"]["image"].update(width=image_size[0], height=image_size[1])
    obs["observation"]["image"]["transform"]["affine"] = affine
    mapped = map_pdf_observation(obs, raw)
    box = mapped.document.texts[0].prov[0].bbox
    assert (box.l, box.t, box.r, box.b) == expected
    assert mapped.dispositions[0]["coordinate_frame"] == frame
    if frame == "content_normalized":
        assert mapped.dispositions[0]["normalization"] == "clipped"


def test_added_paragraph_preserves_native_section_and_reading_order(native_source):
    from docling_core.types.doc import DoclingDocument, GroupLabel

    from corpus_structure.ingest.pdf import PdfConversion, publication_payload
    from corpus_structure.ingest.pdf_hierarchy import snapshot

    doc = DoclingDocument.model_validate(native_source.payload["document"])
    original = list(doc.body.children)
    section = doc.add_group(label=GroupLabel.SECTION, name="Native section")
    doc.body.children = [section.get_ref()]
    section.children = original
    for ref in original:
        ref.resolve(doc).parent = section.get_ref()
    native_source.payload = publication_payload(
        PdfConversion(
            sha256(native_source.original).hexdigest(),
            native_source.recipe,
            snapshot(doc),
            "success",
            (),
            (),
            (),
            None,
        ),
        product_key="native",
        schema_digest=sha256(native_source.schema).hexdigest(),
        section_refs=frozenset({section.self_ref}),
        include_application_metadata=False,
    )
    raw = b"<x_0.05><y_0.23>middle<x_0.3><y_0.26><class_Text>"
    result = integrate(native_source, raw)
    selected = DoclingDocument.model_validate(result["content"]["document"])
    added = next(n for n in selected.texts if n.text == "middle")
    assert added.parent is not None
    assert added.parent.cref == section.self_ref
    children = [r.resolve(selected) for r in selected.groups[0].children]
    assert [getattr(n, "text", str(n.label)) for n in children] == [
        "equal",
        "equal",
        "middle",
        "table",
    ]
    assert (
        result["content"]["items"][
            next(
                i
                for i, r in enumerate(result["content"]["items"])
                if r["pointer"] == added.self_ref
            )
        ]["section_pointer"]
        == section.self_ref
    )


def test_chart_values_have_individually_attributed_coarse_parent_witnesses(native_source):
    raw = (
        b'<x_0.6><y_0.5><chart type="line">\n| Time | Speed ('
        b"m/s) |\n|---|---|\n|1|2|<x_0.95><y_0.9><class_Chart>"
    )
    result = integrate(native_source, raw)
    cells = [
        o
        for o in result["occurrences"]
        if "/meta/tabular_chart/chart_data/table_cells/" in o["occurrence_id"]
    ]
    assert [o["text"] for o in cells] == ["Time", "Speed (m/s)", "1", "2"]
    assert all(
        o["precision"] == "inherited" and o["grounding_pointer"] == o["pointer"] for o in cells
    )
    assert all(o["region"]["precision"] == "inherited" for o in cells)
    for cell in cells:
        decision = next(
            r
            for r in result["relations"]
            if r["relation_id"] == "decision:" + cell["occurrence_id"]
        )
        assert decision["endpoints"][0]["occurrence_id"] == "block-0"


def test_caption_association_is_relocated_across_raw_blocks_and_existing_items(native_source):
    raw = (
        rb"<x_0.05><y_0.333333>\begin{tabular}{cc}1 & 2\end{tabular}<x_0.55><y_0.4><class_Table>"
        rb"<x_0.05><y_0.41>Table 1: Generated values<x_0.55><y_0.44><class_Caption>"
    )
    mapped = map_pdf_observation(recognized(native_source, raw), raw)
    assert (
        mapped.document.tables[0].captions[0].resolve(mapped.document).text
        == "Table 1: Generated values"
    )
    selected = integrate(native_source, raw)
    from docling_core.types.doc import DoclingDocument

    doc = DoclingDocument.model_validate(selected["content"]["document"])
    assert doc.tables[0].captions[0].resolve(doc).text == "Table 1: Generated values"
    assert doc.tables[0].captions[0].cref != "#/texts/0"


def test_failed_observation_without_raw_bytes_is_evidence_only(native_source):
    obs = recognized(native_source, b"")
    obs["observation"].update(outcome="failed", diagnostic="HTTP provider unavailable")
    del obs["observation"]["raw_response_digest"]
    result = map_pdf_observation(obs, b"")
    assert result.dispositions[0]["outcome"] == "evidence_only"
    assert result.dispositions[0]["reason"] == "failed"
    assert result.document.body.children == []


def test_mapped_rich_document_publishes_with_typed_chart_and_inline_lineage(
    pdf13_db, semantic_reader_engine
):
    from corpus_structure.semantic.pdf_integrated import prepare_integrated_pdf_product
    from corpus_structure.semantic.pdf_storage import read_pdf_product, trace_pdf_occurrence

    db = pdf13_db
    raw = (
        b"<x_0.05><y_0.333333>\\begin{tabular}{cc}$x+1$ & 2\\e"
        b"nd{tabular}<x_0.55><y_0.4><class_Table><x_0.6><y_0"
        b'.55><chart type="line">\n| Time | Speed (m/s) |\n|--'
        b"-|---|\n|1|2|<x_0.95><y_0.9><class_Chart><x_0.6><y_"
        b"0.2>Value $y+2$ follows<x_0.95><y_0.25><class_Text"
        b">"
    )
    obs = recognized(db.source, raw)
    obs["product_key"] = "mapped-rich-a"
    obs["observation"]["image"].update(width=4, height=6)
    obs["observation"]["image"]["transform"]["affine"] = [0.02, 0.0, 0.0, 0.02, 0.0, 0.0]
    retained = prepare_integrated_pdf_product(
        obs, db.source.original, db.source.recipe, artifacts=(integration_fixtures.IMAGE, raw)
    )
    integration_fixtures.publish(db, retained)
    selected = select_pdf_integration(
        db.native.values(),
        pin(db.job.task, "native", db.native.digest, "structural"),
        [
            (
                pin(db.job.task, "mapped-rich-a", retained.digest, "recognition"),
                retained.values(),
                raw,
            )
        ],
        db.source.original,
        db.source.recipe,
        db.source.schema,
        product_key="mapped-rich-selected",
    )
    integration_fixtures.publish(db, selected)
    values = selected.values()
    chart_cell = next(
        o for o in values["occurrences"] if "/meta/tabular_chart/" in o["occurrence_id"]
    )
    formula = next(
        o for o in values["occurrences"] if o["kind"] == "formula" and o["text"] == "y+2"
    )
    with semantic_reader_engine.connect() as conn:
        for occurrence in (chart_cell, formula):
            read = read_pdf_product(
                conn,
                task_id=db.job.task,
                product_key="mapped-rich-selected",
                content_digest=selected.digest,
                occurrence_id=occurrence["occurrence_id"],
            )
            assert read["occurrences"][0]["precision"] == "inherited"
            assert read["mapping_reports"]
            trace = trace_pdf_occurrence(
                conn,
                task_id=db.job.task,
                product_key="mapped-rich-selected",
                content_digest=selected.digest,
                occurrence_id=occurrence["occurrence_id"],
            )
            assert any(n["product_key"] == "mapped-rich-a" for n in trace["nodes"])


def test_equal_table_text_does_not_imply_equal_grid(native_source):
    import json

    raw = (
        b"<x_0.05><y_0.333333>\\begin{tabular}{c}equal \\\\ equ"
        b"al\\end{tabular}<x_0.55><y_0.4><class_Table>"
    )
    result = integrate(native_source, raw)
    decision = next(r for r in result["relations"] if r["outcome"] == "replaced")
    evidence = json.loads(decision["evidence"])
    assert evidence["comparison"]["text_equal"] is True
    assert evidence["grid_comparison"]["outcome"] == "different"
    assert evidence["grid_comparison"]["left_dimensions"] == [1, 2]
    assert evidence["grid_comparison"]["right_dimensions"] == [2, 1]
    assert decision["comparison"] == "grid"


def test_panels_from_one_chart_block_are_a_composite_reading(native_source):
    raw = (
        b'<x_0.6><y_0.5><chart type="line">\npanel: a ; line '
        b"; First panel\npanel: b ; bar ; Second panel\ntable["
        b"a]:\n|x|y|\n|---|---|\n|1|2|\ntable[b]:\n|x|z|\n|---|---"
        b"|\n|3|4|<x_0.95><y_0.9><class_Chart>"
    )
    result = integrate(native_source, raw)
    pictures = result["content"]["document"]["pictures"]
    assert [p["meta"]["tabular_chart"]["title"] for p in pictures] == [
        "First panel",
        "Second panel",
    ]
    assert not any(r["outcome"] == "unresolved" for r in result["relations"])


def test_unresolved_reading_stays_attached_after_later_crop_selection(native_source):
    observations = []
    for i, (name, role, spelling) in enumerate(
        (("first", "A", "a"), ("alternative", "A", "b"), ("crop", "C", "c")), start=1
    ):
        raw = (
            rf"<x_0.05><y_0.333333>\begin{{tabular}}{{cc}}{spelling} & {spelling}"
            r"\end{tabular}<x_0.55><y_0.4><class_Table>"
        ).encode()
        obs = recognized(native_source, raw, role=role)
        obs["product_key"] = name
        observations.append((pin(i + 1, name, str(i) * 64, "recognition"), obs, raw))
    result = select_pdf_integration(
        native_source.payload,
        pin(1, "native", "0" * 64, "structural"),
        observations,
        native_source.original,
        native_source.recipe,
        native_source.schema,
    ).values()
    unresolved = next(
        r for r in result["relations"] if r["kind"] == "decision" and r["outcome"] == "unresolved"
    )
    assert any(e["role"] == "output" for e in unresolved["endpoints"])
    assert any(
        e.get("input_index") == 2 and e["role"] == "alternative" for e in unresolved["endpoints"]
    )
    assert [
        c["text"] for c in result["content"]["document"]["tables"][0]["data"]["table_cells"]
    ] == ["c", "c"]
