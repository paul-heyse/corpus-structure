from contextlib import closing
from ctypes import c_ushort

import pytest
from pypdfium2 import PdfDocument, raw

from corpus_structure.ingest.pdf_recognition import crop_transform, render_affine
from corpus_structure.semantic.visual_routing import (
    StudyRegion,
    VisualRouteCrop,
    VisualRouteReason,
    _decide,
    _disagreements,
    _Observation,
    _original_blank_body,
    _PageSignals,
    _readings,
    _Region,
    _scoped_attempt,
)
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

_PIN = VisualEvidencePin(run_id=1, task_id=2, product_key="retained", content_digest="1" * 64)
_BASE = _PIN.model_copy(update={"task_id": 1, "product_key": "structural"})
_REGION = VisualRouteCrop(pointer="#/tables/0", region_index=0)
_FRAME = (200, 200)


def _image(*, crop=(0, 0, 200, 200), rotation=0):
    return {
        "width": 400,
        "height": 400,
        "transform": render_affine(
            media=(0, 0, *_FRAME), crop=crop, rotation=rotation, width=400, height=400
        ),
    }


def _layout(raw):
    image = _image()
    return _Observation(_PIN, image, _readings(raw, image))


def _region(box=(40, 40, 160, 80), address=_REGION):
    return _Region("table", address, box, _FRAME)


@pytest.mark.parametrize(
    ("native", "selected", "action", "reason", "pins"),
    [
        (True, False, "repair", "incumbent_structure", (_BASE, _PIN)),
        (False, False, "recognize", "missing_structure", (_PIN,)),
        (False, True, "skip", "no_supported_trigger", ()),
    ],
)
def test_positioned_table_gap_is_distinct_from_unrelated_same_kind(
    native, selected, action, reason, pins
):
    unrelated = _region((40, 120, 160, 150))
    result = _decide(
        151,
        _PageSignals(
            [_region() if selected else unrelated],
            [_region() if native else unrelated],
            True,
            layout=_layout(b"<x_0.2><y_0.2><x_0.8><y_0.4><class_Table>"),
            structural=_BASE,
        ),
    )
    assert result.page_no == 151
    assert result.action == action
    assert result.reasons[0].code == reason
    assert result.reasons[0].inputs == pins


def test_unassessed_page_is_unresolved_even_with_no_detected_gap():
    route = _decide(506, _PageSignals([], [], False))
    assert route.action == "unresolved"
    assert route.reasons[0].code == "unassessed"


def test_study_presence_only_resolves_the_witnessed_layout_gap():
    layout = _layout(
        b"<x_0.2><y_0.2><x_0.8><y_0.4><class_Table>\n<x_0.2><y_0.6><x_0.8><y_0.8><class_Table>"
    )
    omitted = VisualRouteReason(code="omitted_crop", inputs=(_PIN,), crop=_REGION)
    signals = _PageSignals(
        [_region((40, 120, 160, 160))],
        [],
        True,
        layout=layout,
        requests=[omitted],
        study_regions=(StudyRegion("table", (40, 40, 160, 80), _FRAME),),
    )
    repaired = _decide(151, signals)
    assert repaired.reasons == (omitted,)
    assert repaired.crop == _REGION

    # A study replacement may relocate the archive occurrence, but it cannot
    # give the now-unmatched provider reading a published crop address.
    signals.study_regions = (StudyRegion("table", (40, 40, 160, 80), _FRAME, replaces=_REGION),)
    relocated = _decide(151, signals)
    assert [reason.code for reason in relocated.reasons] == ["omitted_crop", "missing_structure"]
    assert relocated.reasons[-1].crop is None
    assert relocated.crop is None


def test_retained_layout_requires_qualified_positions_for_every_block():
    box = b"<x_0.2><y_0.2><x_0.8><y_0.4>"
    assert _layout(box + b"<class_Page-header>").readings[0].kind == "Page-header"
    assert _layout(box + b"<class_Table>").readings[0].box == (40, 40, 160, 80)
    assert _layout(box + b"<class_Table>\n<class_Table>").readings == ()
    assert _layout(b"<class_Table>").readings == ()
    assert _layout(b"<x_.><y_0><x_1><y_1><class_Table>").readings == ()
    assert _layout(b"").readings == ()


def test_crop_disagreement_needs_same_scope_and_preserves_exact_crop():
    whole = _layout(b"<x_0.2><y_0.2>4 & 10<x_0.8><y_0.4><class_Table>")
    image = _image()
    image.update(
        width=240, height=80, transform=crop_transform(image["transform"], (80, 80, 320, 160))
    )
    raw = b"<x_0><y_0>7 & 10<x_1><y_1><class_Table>"
    cropped = _Observation(_BASE, image, _readings(raw, image))
    reasons = _disagreements(whole, cropped, [_region()])
    assert [(reason.code, reason.crop) for reason in reasons] == [("located_disagreement", _REGION)]
    assert reasons[0].inputs == (_PIN, _BASE)
    assert _disagreements(whole, whole, [_region()]) == []
    assert _scoped_attempt(image, [_region()]) == _REGION
    assert (
        _scoped_attempt(
            image, [_region(), _region(address=_REGION.model_copy(update={"region_index": 1}))]
        )
        is None
    )
    scoped = _PageSignals([_region()], [], True, requests=reasons)
    assert _decide(151, scoped).crop == _REGION
    scoped.requests.append(VisualRouteReason(code="incomplete_request", inputs=(_PIN,)))
    assert _decide(151, scoped).crop is None


def test_rotated_cropbox_never_invents_native_crop_address():
    image = _image(crop=(25, 20, 180, 170), rotation=90)
    assert _readings(b"<x_0.2><y_0.2><x_0.8><y_0.4><class_Table>", image) == ()
    assert _scoped_attempt(image, [_region()]) is None


def test_verified_blank_uses_original_objects_not_an_empty_provider_result():
    layout = _layout(b"<x_0.03><y_0.03><x_0.5><y_0.13><class_Page-header>")
    # The rectangle's drawing object contradicts the otherwise identical furniture-only B.
    for body in (False, True):
        with PdfDocument.new() as pdf, closing(pdf.new_page(*_FRAME)) as page:
            header = raw.FPDFPageObj_NewTextObj(pdf.raw, b"Helvetica", 12)
            value = tuple(map(ord, "Running header\0"))
            assert raw.FPDFText_SetText(header, (c_ushort * len(value))(*value))
            raw.FPDFPageObj_Transform(header, 1, 0, 0, 1, 12, 180)
            raw.FPDFPage_InsertObject(page.raw, header)
            if body:
                rectangle = raw.FPDFPageObj_CreateNewRect(25, 90, 10, 10)
                raw.FPDFPage_InsertObject(page.raw, rectangle)
            assert raw.FPDFPage_GenerateContent(page.raw)
            blank = _original_blank_body(page, layout, [])
        assert blank is not body
        result = _decide(1, _PageSignals([], [], False, layout=layout, blank=blank))
        assert result.reasons[0].code == ("unassessed" if body else "verified_blank_body")


def test_dispatch_coalesces_reasons_and_respects_repair_and_blank():
    from corpus_structure.semantic.visual_dispatch import visual_dispatch_selections
    from corpus_structure.semantic.visual_routing import VisualPageRoute, VisualRouteReport

    report = VisualRouteReport(
        source=_PIN,
        structural_input=_BASE,
        page_count=3,
        pages=(
            VisualPageRoute(
                page_no=1,
                action="repair",
                reasons=(VisualRouteReason(code="incumbent_structure"),),
            ),
            VisualPageRoute(
                page_no=2,
                action="recognize",
                reasons=(
                    VisualRouteReason(code="located_disagreement", crop=_REGION),
                    VisualRouteReason(code="omitted_crop", crop=_REGION),
                    VisualRouteReason(code="missing_structure"),
                ),
            ),
            VisualPageRoute(
                page_no=3,
                action="skip",
                reasons=(VisualRouteReason(code="verified_blank_body"),),
            ),
        ),
    )
    selective = visual_dispatch_selections(report, "selective")
    assert [(item.page_no, item.pointer, item.region_index) for item in selective] == [
        (2, "#/tables/0", 0),
        (2, None, None),
    ]
    assert all(item.source == _PIN for item in selective)
    assert [
        (item.page_no, item.pointer) for item in visual_dispatch_selections(report, "all-page")
    ] == [(1, None), (2, None), (3, None)]


def test_dispatch_qualifies_one_stable_retry_and_binds_the_provider_recipe(monkeypatch, tmp_path):
    from contextlib import nullcontext
    from functools import partial
    from types import SimpleNamespace

    from sqlalchemy import create_engine

    from corpus_structure.ingest import pdf_chandra
    from corpus_structure.semantic import visual_dispatch
    from corpus_structure.semantic.visual_requests import VisualGroupResult
    from corpus_structure.semantic.visual_routing import VisualPageRoute, VisualRouteReport

    routes = VisualRouteReport(
        source=_PIN,
        structural_input=_BASE,
        page_count=1,
        pages=(
            VisualPageRoute(
                page_no=1,
                action="recognize",
                reasons=(VisualRouteReason(code="missing_structure"),),
            ),
        ),
    )
    monkeypatch.setattr(visual_dispatch, "read_snapshot", lambda engine: nullcontext(None))
    monkeypatch.setattr(visual_dispatch, "_require_dispatch_cut", lambda *args: None)
    monkeypatch.setattr(visual_dispatch, "read_visual_routes", lambda *args, **kwargs: routes)
    monkeypatch.setattr(visual_dispatch, "open_release", lambda conn, release: release)
    monkeypatch.setattr(visual_dispatch, "installed_runtime_id", lambda release: "runtime")
    recipe = {"revision": "first"}
    monkeypatch.setattr(
        pdf_chandra, "ChandraRuntime", lambda artifacts: SimpleNamespace(identity=lambda: recipe)
    )
    keys = []

    def settle_group(engine, *, campaign_group, **kwargs):
        keys.append(campaign_group)
        failure = campaign_group == keys[0]
        return VisualGroupResult(
            run_id=11 if failure else 12,
            status="failed" if failure else "source_ready",
            source=_PIN,
            members=(),
        )

    monkeypatch.setattr(visual_dispatch, "request_visual_group", settle_group)
    dispatch = partial(
        visual_dispatch.dispatch_visual_work,
        create_engine("sqlite://"),
        source=_PIN,
        source_cut=1,
        semantic_release="release",
        realization="realization",
        mode="selective",
        first=1,
        limit=1,
        artifacts=tmp_path,
        receipts=tmp_path,
        nemotron_endpoint=None,
        retry_failed=True,
    )
    first = dispatch()
    assert first.retried_failed_runs == (11,)
    assert first.groups[0].run_id == 12
    assert len(set(keys)) == 2
    repeated = dispatch()
    assert repeated == first and keys[2:] == keys[:2]
    recipe["revision"] = "second"
    changed = dispatch()
    assert keys[-1] not in keys[:2] and changed.retried_failed_runs == ()
