"""Exact Chandra effect and replay through the native writer with controlled inference."""

import json
from contextlib import nullcontext
from hashlib import sha256
from pathlib import Path

import pytest
from docling.datamodel.base_models import VlmPrediction, VlmStopReason
from pydantic import ValidationError
from sqlalchemy import select

from corpus_structure.ingest import pdf_capacity, pdf_chandra
from corpus_structure.semantic import pdf_visual_mapping, visual_requests
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operation_results import ClaimedTask
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

from .pdf_integration_support import IMAGE, integrated, prepare, publish
from .pdf_integration_support import native_source as native_source
from .pdf_integration_support import pdf13_db as pdf13_db

_HTML = '<div data-label="Formula" data-bbox="100 200 900 800">x^2</div>'
_TRANSFORM = {
    "status": "coarse",
    "normalization": "none",
    "source_space": "pdf_points",
    "target_space": "submitted_pixels",
    "page_width": 200,
    "page_height": 300,
    "page_rotation": 0,
    "crop_left": 0,
    "crop_top": 0,
    "crop_right": 200,
    "crop_bottom": 300,
    "affine": [0.02, 0, 0, 0.02, 0, 0],
}


@pytest.mark.parametrize(
    "crop",
    [
        {"pointer": "#/pictures/0"},
        {"region_index": 0},
        {"rotation": 0},
        {"pointer": "#/pictures/0", "region_index": 0, "rotation": 45},
    ],
)
def test_visual_scope_requires_exact_crop_and_quarter_turn(crop):
    with pytest.raises(ValidationError):
        visual_requests.VisualSelection.model_validate(
            {
                "source": dict(
                    run_id=1, task_id=2, product_key="selected", content_digest="a" * 64
                ),
                "page_no": 1,
                **crop,
            }
        )


def test_visual_attempt_receipt_marks_an_interruption_without_response(tmp_path):
    claim = ClaimedTask.model_construct(
        task_id=21, run_id=9, release_id="release-test", invocation_key="invocation", attempt=2
    )
    marker, retained = visual_requests._retain_attempt_receipt(
        tmp_path,
        claim,
        b'{"recipe":"test"}',
        {"kind": "recognition_observation"},
        IMAGE,
        None,
        interrupted=True,
    )
    receipt = json.loads(marker.read_bytes())
    assert marker.read_bytes() == retained
    assert receipt["interrupted"] and receipt["attempt"] == 2
    assert receipt["invocation_key"] == "invocation"
    assert receipt["files"]["submitted.png"]["sha256"] == sha256(IMAGE).hexdigest()
    assert set(receipt["files"]) == {"observation.json", "recipe.json", "submitted.png"}
    assert sorted(path.name for path in marker.parent.iterdir()) == [
        "observation.json",
        "receipt.json",
        "recipe.json",
        "submitted.png",
    ]


def test_visual_effect_retains_raw_before_mapping_and_reuses_only_exact_inputs(
    pdf13_db,
    tmp_path,
    monkeypatch,
):
    db = pdf13_db
    integrated_values = integrated(db.source, db.inputs)
    digest = publish(db, prepare(integrated_values, db.source))
    alternate = {**integrated_values, "product_key": "another-integrated-product"}
    other_digest = publish(db, prepare(alternate, db.source))
    source = VisualEvidencePin(
        run_id=db.job.run,
        task_id=db.job.task,
        product_key="selected",
        content_digest=digest,
    )
    selection = visual_requests.VisualSelection(source=source, page_no=1)
    args = dict(
        selection=selection,
        semantic_release=db.prepared.release_id,
        realization="z",
        receipts=tmp_path / "receipts",
    )
    generation = []

    class ControlledChandra:
        prompt = "first prompt"

        def __init__(self, artifacts):
            assert artifacts == tmp_path
            self.effective_device = {"device": "controlled"}

        def identity(self):
            return {
                "packages": {"docling": "2.148.0"},
                "repository": "datalab-to/chandra-ocr-2",
                "revision": "controlled",
                "artifacts_sha256": {
                    "model.safetensors": "b" * 64,
                    "tokenizer.json": "c" * 64,
                },
                "prompt": self.prompt,
                "decode": {},
            }

        def recognize(self, image, *, before_submit):
            assert image.mode == "RGB"
            assert image.size == (4, 6)
            before_submit()
            generation.append(self.prompt)
            return VlmPrediction(text=_HTML, stop_reason=VlmStopReason.UNSPECIFIED)

        def close(self):
            pass

    def render(original, page, region, rotation):
        assert original == db.source.original
        assert (page, region, rotation) == (1, None, 0)
        return IMAGE, _TRANSFORM

    original_map = pdf_visual_mapping.map_visual_result
    products = table("ops.pdf_product")
    bodies = table("ops.pdf_product_body")
    parsing_attempts = []

    def map_with_committed_raw(*args, **kwargs):
        with db.writer.connect() as conn:
            rows = list(
                conn.execute(
                    select(bodies.c.descriptor).where(
                        bodies.c.product_key.like("chandra-inference:%")
                    )
                ).scalars()
            )
        assert any(
            row["observation"]["raw_response_digest"] == sha256(_HTML.encode()).hexdigest()
            for row in rows
        )
        parsing_attempts.append(True)
        if len(parsing_attempts) == 1:
            raise ValueError("controlled mapping failure")
        return original_map(*args, **kwargs)

    monkeypatch.setattr(pdf_capacity, "pdf_gpu_slot", lambda **_: nullcontext())
    monkeypatch.setattr(pdf_chandra, "ChandraRuntime", ControlledChandra)
    monkeypatch.setattr(pdf_visual_mapping, "render_visual_input", render)
    monkeypatch.setattr(pdf_visual_mapping, "map_visual_result", map_with_committed_raw)

    first = visual_requests.request_visual_observation(db.writer, artifacts=tmp_path, **args)
    assert first.status == "failed" and first.error == "controlled mapping failure"
    assert first.raw is not None and first.mapped is None
    assert first.attempt_receipt is not None
    marker = Path(first.attempt_receipt)
    manifest = json.loads(marker.read_bytes())
    assert (manifest["task_id"], manifest["run_id"]) == (first.raw.task_id, first.raw.run_id)
    assert (marker.parent / "submitted.png").read_bytes() == IMAGE
    assert (marker.parent / "response.html").read_text() == _HTML
    assert manifest["files"]["response.html"]["sha256"] == sha256(_HTML.encode()).hexdigest()

    replay = visual_requests.request_visual_observation(db.writer, replay=first.raw, **args)
    assert replay.status == "source_ready" and replay.raw == first.raw
    assert replay.mapped is not None and replay.cut_id is not None
    assert generation == ["first prompt"]
    assert parsing_attempts == [True, True]
    with db.writer.connect() as conn:
        descriptor = conn.execute(
            select(bodies.c.descriptor)
            .join(
                products,
                (products.c.task_id == bodies.c.task_id)
                & (products.c.product_key == bodies.c.product_key),
            )
            .where(
                products.c.task_id == replay.mapped.task_id,
                products.c.product_key == replay.mapped.product_key,
                products.c.content_digest == replay.mapped.content_digest,
            )
        ).scalar_one()
    assert descriptor["observation"]["outcome"] == "unknown"
    assert "mapped_evidence_digest" in descriptor["observation"]
    assert descriptor["health"]["source_fidelity"] == "unassessed"

    repeated = visual_requests.request_visual_observation(db.writer, artifacts=tmp_path, **args)
    assert repeated.raw == replay.raw and repeated.mapped == replay.mapped
    assert generation == ["first prompt"]
    assert parsing_attempts == [True, True]

    ControlledChandra.prompt = "changed prompt"
    changed = visual_requests.request_visual_observation(db.writer, artifacts=tmp_path, **args)
    assert changed.raw != first.raw and changed.mapped != replay.mapped
    assert generation == ["first prompt", "changed prompt"]

    other_source = source.model_copy(
        update={
            "product_key": "another-integrated-product",
            "content_digest": other_digest,
        }
    )
    other_selection = selection.model_copy(update={"source": other_source})
    with pytest.raises(ValueError, match="originating source selection"):
        visual_requests.request_visual_observation(
            db.writer,
            replay=first.raw,
            **{**args, "selection": other_selection},
        )
