"""Independent PDF landmarks and real isolated-parser/HTTP lifecycle controls.

Scripted responses test custody and lifecycle, never model recognition quality.
"""

from __future__ import annotations

import base64
import json
import threading
import time
from contextlib import suppress
from dataclasses import replace
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

import pypdfium2
import pytest
from PIL import Image

from corpus_structure.ingest.pdf_recognition import (
    NemotronRecipe,
    PreparedRecognitionSource,
    RecognitionWorker,
    crop_transform,
    recognition_observation_values,
    render_recognition_page,
    repetition_recovery_recipe,
    repetitive_capped_page,
    transform_point,
)
from corpus_structure.semantic.pdf_integrated import prepare_integrated_pdf_product


def landmark_pdf() -> bytes:
    # Media origin is deliberately nonzero; crop clips all four media edges. Independent
    # red landmark center: absolute PDF(100,450), media-relative TOPLEFT(90,170).
    content = b"1 0 0 rg 95 445 10 10 re f\nBT /F1 12 Tf 0 1 -1 0 200 250 Tm (ROTATED) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R 5 0 R 6 0 R] /Count 4 >>",
    ]
    for rotation in (0, 90, 180, 270):
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [10 20 410 620] "
                f"/CropBox [60 120 360 520] /Rotate {rotation} "
                "/Resources << /Font << /F1 8 0 R >> >> /Contents 7 0 R >>"
            ).encode()
        )
    objects.extend(
        [
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
    )
    result = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(result)
    result += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    result += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return (
        result
        + f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )


@pytest.mark.parametrize(
    ("page_no", "pixel"), [(1, (40, 70)), (2, (330, 40)), (3, (260, 330)), (4, (70, 260))]
)
def test_independent_cropbox_rotated_landmarks(page_no, pixel):
    document = pypdfium2.PdfDocument(landmark_pdf())
    try:
        png, transform = render_recognition_page(document, page_no, 1.0)
        with Image.open(BytesIO(png)) as image:
            assert image.getpixel(pixel) == (255, 0, 0)
        assert transform_point(transform["affine"], 90, 170) == pytest.approx(pixel)
        assert (
            transform["crop_left"],
            transform["crop_top"],
            transform["crop_right"],
            transform["crop_bottom"],
        ) == (50, 100, 350, 500)
        crop = crop_transform(transform, [10, 20, 150, 200])
        assert transform_point(crop["affine"], 90, 170) == pytest.approx(
            (pixel[0] - 10, pixel[1] - 20)
        )
        text = document[page_no - 1].get_textpage()
        try:
            assert "ROTATED" in text.get_text_range()
        finally:
            text.close()
    finally:
        document.close()


@pytest.fixture
def endpoint():
    requests = []
    replies = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(body)
            reply = replies.pop(0)
            if isinstance(reply, float):
                time.sleep(reply)
                reply = "delayed"
            if isinstance(reply, int):
                self.send_response(reply)
                self.end_headers()
                return
            response = {
                "model": "actual-model-revision",
                "retained_extra": {"source": "http-control"},
                "usage": {"completion_tokens": 12},
                "choices": [{"finish_reason": "stop", "message": {"content": reply}}],
            }
            if isinstance(reply, dict):
                response["choices"] = [
                    {
                        "finish_reason": reply["finish_reason"],
                        "message": {"content": reply["raw"]},
                    }
                ]
            self.send_response(200)
            self.end_headers()
            # The cancellation control deliberately closes a live request.
            with suppress(BrokenPipeError):
                self.wfile.write(json.dumps(response).encode())

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests, replies
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def owner(tmp_path, endpoint):
    root = Path(__file__).resolve().parents[4]
    runtime = root / "services/nemotron-parse/.venv/bin/python"
    if not runtime.exists():
        runtime = Path.home() / ".cache/corpus-structure/nemotron-runtime-py312/bin/python"
    if not runtime.exists():
        pytest.skip("isolated public Nemotron parser environment unavailable")
    return RecognitionWorker(
        python=runtime,
        script=root / "services/nemotron-parse/worker.py",
        endpoint=endpoint,
        receipts=tmp_path,
        timeout_seconds=30,
    )


def test_public_triple_exact_images_raw_crops_and_replay(tmp_path, endpoint):
    url, requests, replies = endpoint
    table = "<x_100><y_200><table><tr><td>one</td></tr></table><x_700><y_800><class_Table>"
    replies.extend([table, "<x_100><y_200><x_700><y_800><class_Table>", table])
    source = PreparedRecognitionSource.prepare(landmark_pdf())
    recipe = NemotronRecipe("1" * 64, "2" * 64, render_scale=1.0)
    worker = owner(tmp_path, url)
    page = next(worker.recognize_pages(source, recipe, [2]))
    assert page.succeeded, page.result
    rows = list(page.requests())
    assert [r[0]["stage"] for r in rows] == ["fullpage", "detection", "crop"]
    for request, (row, raw, artifacts) in zip(requests, rows, strict=True):
        actual = base64.b64decode(
            request["messages"][0]["content"][1]["image_url"]["url"].split(",")[1]
        )
        assert actual == artifacts[0]
        assert request["skip_special_tokens"] is False
        assert b'"retained_extra"' in artifacts[2]
        values = recognition_observation_values(page, row, raw, source=source, recipe=recipe)
        prepared = prepare_integrated_pdf_product(
            values, source.original, recipe.to_bytes(), artifacts=artifacts
        )
        assert prepared.values()["observation"]["binding"]["weights_digest"] == "1" * 64
        assert (
            json.loads(values["observation"]["binding"]["decoding_json"])["response_model"]
            == "actual-model-revision"
        )
        receipt_digests = json.loads(values["observation"]["binding"]["decoding_json"])[
            "receipt_digests"
        ]
        assert set(receipt_digests.values()) <= {
            sha256(payload).hexdigest() for payload in artifacts
        }
        if row["ordinal"] == 0:
            assert {
                "decisions.json",
                "result.json",
                "provider-document.json",
            } <= receipt_digests.keys()
    crop_row = rows[2][0]
    with Image.open(page.directory / "page.png") as full:
        crop = full.crop(crop_row["crop"]["pixels"])
        stream = BytesIO()
        crop.save(stream, format="JPEG", quality=95)
        assert sha256(stream.getvalue()).hexdigest() == crop_row["crop"]["jpeg_digest"]
        with (
            Image.open(BytesIO(stream.getvalue())) as jpeg,
            Image.open(BytesIO(rows[2][2][0])) as submitted,
        ):
            assert jpeg.convert("RGB").tobytes() == submitted.tobytes()
    replay = next(worker.recognize_pages(source, recipe, [2]))
    assert replay.reused and len(requests) == 3
    assert replace(recipe, seed=3).digest != recipe.digest
    assert replace(recipe, render_scale=2).digest != recipe.digest
    assert replace(recipe, weights_digest="3" * 64).digest != recipe.digest


def test_later_crop_failure_preserves_prior_actual_responses(tmp_path, endpoint):
    url, requests, replies = endpoint
    table = "<x_0.1><y_0.2><table><tr><td>x</td></tr></table><x_0.7><y_0.8><class_Table>"
    replies.extend([table, table, 503])
    source = PreparedRecognitionSource.prepare(landmark_pdf())
    recipe = NemotronRecipe("1" * 64, "2" * 64, render_scale=1)
    page = next(owner(tmp_path, url).recognize_pages(source, recipe, [1]))
    assert not page.succeeded
    rows = list(page.requests())
    assert len(rows) == 3 and len(requests) == 3
    assert [r[0]["outcome"] for r in rows] == ["succeeded", "succeeded", "failed"]
    assert rows[0][1] == table.encode() == rows[1][1]
    assert rows[2][0]["http_status"] == 503
    assert (page.directory / "decisions.json").exists()


def test_zero_crop_is_real_triple_and_repeated_raw_occurrences_are_distinct(tmp_path, endpoint):
    url, requests, replies = endpoint
    raw = "<x_0.1><y_0.2>equal<x_0.8><y_0.3><class_Text>"
    replies.extend(
        [raw + raw + "malformed<class_Unknown>", "<x_0.1><y_0.2><x_0.8><y_0.3><class_Text>"]
    )
    source = PreparedRecognitionSource.prepare(landmark_pdf())
    recipe = NemotronRecipe("1" * 64, "2" * 64, render_scale=1)
    page = next(owner(tmp_path, url).recognize_pages(source, recipe, [1]))
    assert page.succeeded
    assert len(requests) == 2
    row, raw_bytes, _ = next(page.requests())
    values = recognition_observation_values(page, row, raw_bytes, source=source, recipe=recipe)
    assert [o["occurrence_id"] for o in values["occurrences"]] == ["block-0", "block-1", "block-2"]
    assert values["occurrences"][0]["text"] == values["occurrences"][1]["text"] == "equal"


def test_cancellation_terminates_owned_process_retains_admitted_request(tmp_path, endpoint):
    url, _, replies = endpoint
    replies.append(1.0)
    worker = owner(tmp_path, url)
    source = PreparedRecognitionSource.prepare(landmark_pdf())
    recipe = NemotronRecipe("1" * 64, "2" * 64, render_scale=1)

    def check():
        if list(tmp_path.glob("**/request-000.json")):
            raise InterruptedError("lease lost")

    with pytest.raises(InterruptedError, match="lease lost"):
        next(worker.recognize_pages(source, recipe, [1, 2], check_active=check))
    assert worker._process is None
    assert worker.last_page is not None and not worker.last_page.succeeded
    assert (worker.last_page.directory / "interrupted.json").exists()
    assert len(list(tmp_path.glob("**/input.json"))) == 1


def test_bounded_parallel_pages_keep_identity_independent_handles_and_parent_cancellation(
    tmp_path, endpoint
):
    url, requests, replies = endpoint
    raw = "<x_0.1><y_0.2>text<x_0.8><y_0.3><class_Text>"
    replies.extend([raw] * 8)
    worker = owner(tmp_path, url)
    source = PreparedRecognitionSource.prepare(landmark_pdf())
    recipe = NemotronRecipe("1" * 64, "2" * 64, render_scale=1)
    parent = threading.get_ident()

    def check():
        assert threading.get_ident() == parent

    results = list(
        worker.recognize_pages(source, recipe, [4, 3, 2, 1], concurrency=4, check_active=check)
    )
    assert {page.page_no for page in results} == {4, 3, 2, 1}
    assert all(page.succeeded for page in results)
    assert len(requests) == 8
    assert all(
        json.loads((page.directory / "input.json").read_bytes())["physical_page_concurrency"] == 4
        for page in results
    )

    replies.extend([1.0] * 4)

    def cancel():
        assert threading.get_ident() == parent
        if len(list(tmp_path.glob("**/attempt-00002/request-000.json"))) >= 2:
            raise InterruptedError("parent lease lost")

    with pytest.raises(InterruptedError, match="parent lease lost"):
        list(
            worker.recognize_pages(
                source, recipe, [1, 2, 3, 4], concurrency=4, check_active=cancel, reuse=False
            )
        )
    admitted = list(tmp_path.glob("**/attempt-00002/input.json"))
    assert len(admitted) <= 4
    assert len(list(tmp_path.glob("**/attempt-00002/interrupted.json"))) == len(admitted)


def test_capped_repetition_recovery_is_explicit_bounded_and_failed_receipts_replay(
    tmp_path, endpoint
):
    url, requests, replies = endpoint
    replies.append({"finish_reason": "length", "raw": "∫" * 64})
    source = PreparedRecognitionSource.prepare(landmark_pdf())
    recipe = NemotronRecipe("1" * 64, "2" * 64, render_scale=1)
    worker = owner(tmp_path, url)
    page = next(worker.recognize_pages(source, recipe, [1]))
    assert not page.succeeded
    assert repetitive_capped_page(page, minimum_run=64)
    assert not repetitive_capped_page(page, minimum_run=65)
    row, raw, artifacts = next(page.requests())
    assert row["outcome"] == "partial" and raw == ("∫" * 64).encode()
    values = recognition_observation_values(page, row, raw, source=source, recipe=recipe)
    product = prepare_integrated_pdf_product(
        values, source.original, recipe.to_bytes(), artifacts=artifacts
    )
    assert product.values()["coverage"][0]["outcome"] == "capped"
    replay = next(worker.recognize_pages(source, recipe, [1], reuse_failures=True))
    assert replay.reused and not replay.succeeded and len(requests) == 1
    alternate = repetition_recovery_recipe(recipe)
    assert alternate.digest != recipe.digest and alternate.repetition_penalty == 1.3
    assert alternate.temperature == recipe.temperature == 0
    assert alternate.mtp == recipe.mtp
    text = "<x_0.1><y_0.2>completed<x_0.8><y_0.3><class_Text>"
    replies.extend([text, text])
    recovered = next(worker.recognize_pages(source, alternate, [1]))
    assert recovered.succeeded and len(requests) == 3
    assert not repetitive_capped_page(recovered, minimum_run=64)
    assert (page.directory / "request-000.raw.txt").read_bytes() == raw


def test_completion_driven_refill_does_not_wait_for_slow_first_page(tmp_path, monkeypatch):
    from corpus_structure.ingest.pdf_recognition import RecognitionPage

    first_release = threading.Event()
    third_started = threading.Event()
    original = RecognitionWorker._recognize_pages

    def recognize(self, source, recipe, numbers, **kwargs):
        if kwargs.get("concurrency", 1) > 1:
            yield from original(self, source, recipe, numbers, **kwargs)
            return
        number = numbers[0]
        if number == 1:
            assert first_release.wait(5)
        if number == 3:
            third_started.set()
        yield RecognitionPage(number, tmp_path, {"outcome": "succeeded"}, {})

    monkeypatch.setattr(RecognitionWorker, "_recognize_pages", recognize)
    worker = owner(tmp_path, "http://unused")
    pages = worker.recognize_pages(
        PreparedRecognitionSource.prepare(landmark_pdf()),
        NemotronRecipe("1" * 64, "2" * 64),
        [1, 2, 3, 4],
        concurrency=2,
    )
    try:
        assert next(pages).page_no == 2
        # Replenishment occurs only when the consumer asks for another item.
        assert not third_started.is_set()
        assert next(pages).page_no == 3
        assert third_started.is_set()
        first_release.set()
        assert {p.page_no for p in pages} == {1, 4}
    finally:
        first_release.set()
        pages.close()


def test_owned_file_source_is_verified_without_retaining_pdf_bytes(tmp_path):
    path = tmp_path / "original.pdf"
    body = landmark_pdf()
    path.write_bytes(body)
    source = PreparedRecognitionSource.from_path(path, sha256(body).hexdigest())
    assert source.original == path.resolve()
    assert isinstance(source.original, Path)
    with pytest.raises(ValueError, match="digest"):
        PreparedRecognitionSource.from_path(path, "0" * 64)
