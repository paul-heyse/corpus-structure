"""Exact Chandra effect and replay through the native writer with controlled inference."""

import json
from contextlib import nullcontext
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from docling.datamodel.base_models import VlmPrediction, VlmStopReason
from PIL import Image
from pydantic import ValidationError
from sqlalchemy import select, text

from corpus_structure.ingest import pdf_capacity, pdf_chandra
from corpus_structure.orchestrate import commands
from corpus_structure.semantic import pdf_visual_mapping, visual_requests
from corpus_structure.semantic.domain_operations import DomainOperationRefused
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operation_results import ClaimedTask
from corpus_structure.semantic.operations import OperationConflict, end_source_run
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


def test_visual_nomination_keeps_empty_decision_and_refuses_a_forged_source_cut(
    pdf13_db, tmp_path, monkeypatch
):
    from functools import partial

    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic import visual_dispatch
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.operations import (
        OperationBinding,
        complete_task,
        create_run,
        seal_cut,
    )
    from corpus_structure.semantic.visual_routing import (
        VisualPageRoute,
        VisualRouteReason,
        VisualRouteReport,
    )

    db = pdf13_db
    digest = publish(db, prepare(integrated(db.source, db.inputs), db.source))
    source = VisualEvidencePin(
        run_id=db.job.run, task_id=db.job.task, product_key="selected", content_digest=digest
    )
    with db.writer.begin() as conn:
        complete_task(
            conn,
            task_id=db.job.task,
            attempt=db.job.attempt,
            holder=db.job.claim.holder,
            prepared=db.prepared,
            observations=(),
            outcome="empty",
        )
        cut = seal_cut(conn, db.job.run, "source-ready")
    routes = VisualRouteReport(
        source=source,
        structural_input=None,
        page_count=1,
        pages=(
            VisualPageRoute(
                page_no=1, action="unresolved", reasons=(VisualRouteReason(code="unassessed"),)
            ),
        ),
    )
    monkeypatch.setattr(visual_dispatch, "read_visual_routes", lambda *args, **kwargs: routes)
    dispatch = partial(
        visual_dispatch.dispatch_visual_work,
        db.writer,
        source=source,
        source_cut=cut,
        semantic_release=db.prepared.release_id,
        realization="z",
        mode="selective",
        first=1,
        limit=1,
        artifacts=tmp_path,
        receipts=tmp_path,
        nemotron_endpoint=None,
    )
    result = dispatch()
    assert result.groups == ()
    assert dispatch(nomination_run_id=result.nomination_run_id) == result
    runs = table("ops.run")
    with db.writer.connect() as conn:
        options = conn.scalar(select(runs.c.options).where(runs.c.id == result.nomination_run_id))
    assert options["visual_nomination"]["selections"] == []
    other_routes = routes.model_copy(
        update={"pages": (routes.pages[0].model_copy(update={"action": "skip"}),)}
    )
    other_nomination = {
        **options["visual_nomination"],
        "routes": other_routes.model_dump(mode="json"),
    }
    claimed_digest = sha256(canonical_bytes(other_nomination)).hexdigest()
    with db.writer.begin() as conn:
        collision = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(db.prepared.release_id, "z", 0, b"{}"),
            kind="slice",
            options={**options, "visual_nomination_id": claimed_digest},
            code_commit=visual_requests.VISUAL_REQUEST_CODE_COMMIT,
            prepared=db.prepared,
        )
        seal_cut(conn, collision, "visual-nomination", final=True)
    monkeypatch.setattr(visual_dispatch, "read_visual_routes", lambda *args, **kwargs: other_routes)
    other = dispatch()
    assert other.nomination_run_id not in {collision, result.nomination_run_id}
    assert dispatch(nomination_run_id=other.nomination_run_id) == other
    options["visual_nomination"]["demand"]["source_cut"] = cut + 100000
    with (
        pytest.raises(
            DBAPIError, match="visual nomination differs from its exact source-ready cut"
        ),
        db.writer.begin() as conn,
    ):
        create_run(
            conn,
            project_id="p",
            binding=OperationBinding(db.prepared.release_id, "z", 0, b"{}"),
            kind="slice",
            options=options,
            code_commit=visual_requests.VISUAL_REQUEST_CODE_COMMIT,
            prepared=db.prepared,
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
    (marker.parent / "submitted.png").write_bytes(b"changed")
    with pytest.raises(visual_requests.OperationConflict, match="differs from its hash"):
        visual_requests._recover_attempt_receipt(
            tmp_path, claim.model_copy(update={"attempt": 3}), None, b"", b'{"recipe":"test"}', None
        )


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

    monkeypatch.setattr(pdf_capacity, "pdf_gpu_slot", lambda check_active=None: nullcontext())
    monkeypatch.setattr(pdf_chandra, "ChandraRuntime", ControlledChandra)

    def recognize_controlled(runtime, pixels, *, check_active, before_submit):
        check_active()
        with Image.open(BytesIO(pixels)) as image:
            return runtime.recognize(image, before_submit=before_submit)

    monkeypatch.setattr(pdf_chandra, "recognize_supervised", recognize_controlled)
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

    from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
    from corpus_structure.semantic.query import ReadLimit
    from corpus_structure.serve.native_source import NativeSourceRequest
    from corpus_structure.serve.pdf_visual_evidence import (
        MAX_VISUAL_EVIDENCE_ROWS,
        VisualCellGroup,
        VisualEvidenceArtifact,
        VisualPicture,
        VisualSourceRegion,
        VisualTable,
        VisualTableCell,
        VisualText,
        _read_mapped_locator,
    )

    caption_count = 192
    formula_count = 96
    picture_count = MAX_VISUAL_EVIDENCE_ROWS - caption_count - formula_count - 4
    final_picture = f"picture-{picture_count - 1}"
    inside = VisualSourceRegion(left=120, top=120, right=140, bottom=140)
    outside = VisualSourceRegion(left=10, top=10, right=20, bottom=20)
    near_limit = VisualEvidenceArtifact(
        page_no=1,
        rows=(
            *(
                VisualPicture(
                    occurrence_id=f"picture-{n}",
                    source_region=inside if n == picture_count - 1 else outside,
                )
                for n in range(picture_count)
            ),
            *(
                VisualText(
                    occurrence_id=f"description-{n}",
                    parent_occurrence_id=f"picture-{n}",
                    kind="picture_description",
                    text="Rare histogram" if n == 0 else f"Unrelated description {n}",
                    source_region=outside,
                )
                for n in range(caption_count)
            ),
            VisualText(
                occurrence_id="description",
                parent_occurrence_id=final_picture,
                kind="picture_description",
                text="Rare histogram",
                source_region=inside,
            ),
            VisualTable(
                occurrence_id="rich-table",
                num_rows=1,
                num_cols=1,
                cells=(
                    VisualTableCell(
                        text="formula",
                        start_row_offset_idx=0,
                        end_row_offset_idx=1,
                        start_col_offset_idx=0,
                        end_col_offset_idx=1,
                        content_occurrence_id="group",
                    ),
                ),
            ),
            VisualCellGroup(
                occurrence_id="group", parent_occurrence_id="rich-table", native_label="text"
            ),
            *(
                VisualText(
                    occurrence_id=f"formula-{n}",
                    parent_occurrence_id="group",
                    kind="formula",
                    text=f"x^{n}",
                )
                for n in range(formula_count)
            ),
        ),
    )
    with monkeypatch.context() as patch:
        patch.setattr(pdf_visual_mapping, "map_visual_result", lambda *args, **kwargs: near_limit)
        patch.setattr(ControlledChandra, "prompt", "near-limit")
        large = visual_requests.request_visual_observation(db.writer, artifacts=tmp_path, **args)
    assert large.mapped is not None
    mapped_digest = sha256(near_limit.artifact_bytes()).hexdigest()
    request = NativeSourceRequest(
        **source.model_dump(),
        view="visual_evidence",
        page_no=1,
        evidence=large.mapped,
        occurrence_id=final_picture,
    )
    with db.writer.connect() as conn:
        (item,), following = _read_mapped_locator(
            conn, large.mapped, mapped_digest, request, (), PublishedReadBudget(2, 1024), 0
        )
    assert item.occurrence_id == request.occurrence_id and following is None
    with db.writer.connect() as conn:
        cell = request.model_copy(
            update={"occurrence_id": "rich-table", "cell_index": 0, "limit": 2}
        )
        items, following = _read_mapped_locator(
            conn, large.mapped, mapped_digest, cell, (), PublishedReadBudget(104, 2048), 0
        )
        assert [entry.occurrence_id for entry in items] == ["group", "formula-0"]
        assert following is not None
        items, _ = _read_mapped_locator(
            conn, large.mapped, mapped_digest, cell, (), PublishedReadBudget(104, 2048), following
        )
        assert [entry.occurrence_id for entry in items] == ["formula-1", "formula-2"]
        with pytest.raises(ReadLimit, match="row-work budget"):
            _read_mapped_locator(
                conn, large.mapped, mapped_digest, cell, (), PublishedReadBudget(7, 2048), 0
            )
        figure = request.model_copy(
            update={
                "occurrence_id": None,
                "visual_query": "Rare histogram",
                "visual_kind": "picture",
                "limit": 1,
            }
        )
        (matched,), following = _read_mapped_locator(
            conn, large.mapped, mapped_digest, figure, (), PublishedReadBudget(205, 131072), 0
        )
        assert matched.occurrence_id == "picture-0" and following is not None
        (matched,), following = _read_mapped_locator(
            conn,
            large.mapped,
            mapped_digest,
            figure,
            (),
            PublishedReadBudget(205, 131072),
            following,
        )
        assert matched.occurrence_id == final_picture and following is None
        (matched,), following = _read_mapped_locator(
            conn, large.mapped, mapped_digest, figure, (inside,), PublishedReadBudget(4, 2048), 0
        )
        assert matched.occurrence_id == final_picture and following is None
        touching = inside.model_copy(update={"left": inside.right, "right": 160})
        assert _read_mapped_locator(
            conn, large.mapped, mapped_digest, figure, (touching,), PublishedReadBudget(4, 2048), 0
        ) == ((), None)
        with pytest.raises(ReadLimit, match="byte budget"):
            _read_mapped_locator(
                conn, large.mapped, mapped_digest, figure, (), PublishedReadBudget(205, 8), 0
            )
    generation.remove("near-limit")

    repeated = visual_requests.request_visual_observation(db.writer, artifacts=tmp_path, **args)
    assert repeated.raw == replay.raw and repeated.mapped == replay.mapped
    assert generation == ["first prompt"]
    assert parsing_attempts == [True, True]

    ControlledChandra.prompt = "changed prompt"
    changed = visual_requests.request_visual_observation(db.writer, artifacts=tmp_path, **args)
    assert changed.raw != first.raw and changed.mapped != replay.mapped
    assert generation == ["first prompt", "changed prompt"]

    # Interrupt after response custody and before publication, then recover the
    # originating receipt under a new claim on exactly the same task and run.
    ControlledChandra.prompt = "response before interruption"
    settle = visual_requests._settle
    interrupted = []

    def interrupt_once(*values, **options):
        if not interrupted:
            interrupted.append(values[2])
            raise KeyboardInterrupt
        return settle(*values, **options)

    monkeypatch.setattr(visual_requests, "_settle", interrupt_once)
    with pytest.raises(KeyboardInterrupt):
        visual_requests.request_visual_observation(db.writer, artifacts=tmp_path, **args)
    claim = interrupted[0]
    with db.admin.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.execute(
            text(
                "UPDATE ops.task SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:id"
            ),
            {"id": claim.task_id},
        )
    recovered = visual_requests.resume_visual_observation(
        db.writer,
        claim.run_id,
        project="p",
        receipts=args["receipts"],
        nemotron_endpoint=None,
        prepare_only=False,
        select_result=False,
        activate_release=False,
    )
    assert (
        isinstance(recovered, visual_requests.VisualRequestResult)
        and recovered.status == "source_ready"
    )
    assert recovered.run_id == claim.run_id
    assert recovered.raw is not None and recovered.raw.task_id == claim.task_id
    assert recovered.mapped is not None
    assert generation == ["first prompt", "changed prompt", "response before interruption"]
    with db.writer.connect() as conn:
        progress = commands.bound_status(conn, recovered.run_id, project_id="p").run
        assert progress is not None and progress.readiness == "source_ready"
        assert progress.supervisor == "waiting"
        retained = conn.scalar(
            select(bodies.c.descriptor).where(
                bodies.c.task_id == claim.task_id, bodies.c.product_key == recovered.raw.product_key
            )
        )
    assert (
        json.loads(retained["observation"]["binding"]["decoding_json"])["provider_attempt"][
            "attempt"
        ]
        == claim.attempt
    )
    with pytest.raises(DomainOperationRefused, match="no evaluated realization"):
        commands.finalize_bound_run(db.writer, recovered.run_id, "wrong-effect")

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


def test_visual_group_resumes_after_first_settlement_and_reuses_exact_tasks(
    pdf13_db, tmp_path, monkeypatch
):
    from contextlib import contextmanager

    from corpus_structure.serve.pdf_visual_evidence import visual_observation_manifest

    db = pdf13_db
    digest = publish(db, prepare(integrated(db.source, db.inputs), db.source))
    source = VisualEvidencePin(
        run_id=db.job.run, task_id=db.job.task, product_key="selected", content_digest=digest
    )
    requests = (
        visual_requests.VisualSelection(source=source, page_no=1),
        visual_requests.VisualSelection(
            source=source, page_no=1, pointer="#/tables/0", region_index=0, rotation=90
        ),
        visual_requests.VisualSelection(
            source=source, page_no=1, pointer="#/tables/0", region_index=0, rotation=180
        ),
    )
    attempts = []
    sessions = []

    class ControlledRuntime:
        def __init__(self, artifacts):
            assert artifacts == tmp_path
            self.effective_device = {"device": "controlled"}

        def identity(self):
            return {
                "repository": "datalab-to/chandra-ocr-2",
                "revision": "controlled",
                "packages": {"docling": "2.148.0"},
                "artifacts_sha256": {
                    "model.safetensors": "b" * 64,
                    "tokenizer.json": "c" * 64,
                },
                "prompt": "group test",
                "decode": {},
            }

    @contextmanager
    def session(runtime):
        sessions.append(runtime)

        def recognize(pixels, *, check_active, before_submit):
            check_active()
            before_submit()
            attempts.append(pixels)
            return VlmPrediction(text=_HTML, stop_reason=VlmStopReason.UNSPECIFIED)

        yield recognize

    interrupt = True
    competing_request = True
    fail_rotation = None

    def render(original, page, region, rotation):
        nonlocal interrupt, competing_request
        assert original == db.source.original
        if competing_request:
            competing_request = False
            with pytest.raises(OperationConflict, match="active visual request"):
                visual_requests.request_visual_group(db.writer, **args)
        if rotation == 90 and interrupt:
            interrupt = False
            raise KeyboardInterrupt
        if rotation == fail_rotation:
            raise ValueError("controlled visual preparation failure")
        return IMAGE, _TRANSFORM

    monkeypatch.setattr(pdf_capacity, "pdf_gpu_slot", lambda check_active=None: nullcontext())
    monkeypatch.setattr(
        pdf_capacity, "suspend_resident_nemotron", lambda endpoint, check_active=None: nullcontext()
    )
    monkeypatch.setattr(pdf_chandra, "ChandraRuntime", ControlledRuntime)
    monkeypatch.setattr(pdf_chandra, "supervised_chandra", session)
    monkeypatch.setattr(pdf_visual_mapping, "render_visual_input", render)

    args = dict(
        selections=requests,
        semantic_release=db.prepared.release_id,
        realization="z",
        receipts=tmp_path / "receipts",
        artifacts=tmp_path,
        campaign_group="a" * 64,
    )
    with pytest.raises(KeyboardInterrupt):
        visual_requests.request_visual_group(db.writer, **args)
    runs = table("ops.run")
    with db.writer.connect() as conn:
        run_id = conn.scalar(select(runs.c.id).where(runs.c.options.has_key("visual_group")))
    assert run_id is not None
    with db.writer.connect() as conn:
        manifest = visual_observation_manifest(conn, source, page_no=1, after_task=0, limit=10)
    assert len(manifest.observations) == 2
    first = manifest.observations[-1]
    assert first.mapped is not None
    with pytest.raises(OperationConflict, match="differs from the retained campaign group"):
        visual_requests.request_visual_group(db.writer, **{**args, "selections": requests[::-1]})
    regrouped = {**args, "selections": requests[1:], "campaign_group": "c" * 64}
    with pytest.raises(OperationConflict, match=f"pending campaign demand in run {run_id}"):
        visual_requests.request_visual_group(db.writer, **regrouped)
    with db.writer.connect() as conn:
        assert (
            conn.scalar(
                select(runs.c.id).where(runs.c.options["visual_campaign_group"].astext == "c" * 64)
            )
            is None
        )
    settled_only = visual_requests.request_visual_group(
        db.writer, **{**args, "selections": requests[:1], "campaign_group": "d" * 64}
    )
    assert settled_only.members[0].mapped == first.mapped
    resumed = visual_requests.request_visual_group(db.writer, **args)
    assert resumed.run_id == run_id
    assert resumed.status == "source_ready" and resumed.cut_id is not None
    assert resumed.members[0].mapped == first.mapped
    assert len(attempts) == 3 and len(sessions) == 2
    after_cut = visual_requests.request_visual_group(db.writer, **regrouped)
    assert after_cut.members[0].mapped == resumed.members[1].mapped

    recovered = visual_requests.request_visual_group(db.writer, **args)
    assert recovered.run_id == resumed.run_id and recovered.cut_id == resumed.cut_id
    assert [member.task_id for member in recovered.members] == [
        member.task_id for member in resumed.members
    ]
    assert [member.mapped for member in recovered.members] == [
        member.mapped for member in resumed.members
    ]
    assert len(attempts) == 3 and len(sessions) == 2

    replay = visual_requests.request_visual_group(db.writer, **{**args, "campaign_group": None})
    assert replay.status == "source_ready"
    assert replay.run_id != resumed.run_id
    assert [member.raw for member in replay.members] == [member.raw for member in resumed.members]
    assert [member.mapped for member in replay.members] == [
        member.mapped for member in resumed.members
    ]
    assert len(attempts) == 3 and len(sessions) == 2

    cancelled = {**args, "campaign_group": "b" * 64}
    interrupt = True
    with pytest.raises(KeyboardInterrupt):
        visual_requests.request_visual_group(db.writer, **cancelled)
    with db.writer.begin() as conn:
        cancelled_id = conn.execute(
            select(runs.c.id).where(runs.c.options["visual_campaign_group"].astext == "b" * 64)
        ).scalar_one()
        end_source_run(conn, cancelled_id, prepared=db.prepared)
    with pytest.raises(OperationConflict, match=f"run {cancelled_id} was cancelled"):
        visual_requests.request_visual_group(db.writer, **cancelled)
    assert len(attempts) == 3 and len(sessions) == 2

    fail_rotation = 270
    failed_scope = requests[1].model_copy(update={"rotation": fail_rotation})
    failure_args = {**args, "selections": (failed_scope,), "campaign_group": "e" * 64}
    failed = visual_requests.request_visual_group(db.writer, **failure_args)
    assert failed.status == "failed"
    assert failed.members[0].error == "controlled visual preparation failure"
    assert visual_requests.request_visual_group(db.writer, **failure_args) == failed

    def cancel_before_failure(conn, run_id, *, failure, prepared):
        with db.writer.begin() as canceller:
            end_source_run(canceller, run_id, prepared=prepared)
        return end_source_run(conn, run_id, failure=failure, prepared=prepared)

    monkeypatch.setattr(visual_requests, "end_source_run", cancel_before_failure)
    race_args = {**failure_args, "campaign_group": "f" * 64}
    with pytest.raises(OperationConflict, match=r"visual group run .* was cancelled"):
        visual_requests.request_visual_group(db.writer, **race_args)
    with db.writer.connect() as conn:
        raced = conn.execute(
            select(runs.c.id, runs.c.status).where(
                runs.c.options["visual_campaign_group"].astext == "f" * 64
            )
        ).one()
    assert raced.status == "cancelled"
    with pytest.raises(OperationConflict, match=f"run {raced.id} was cancelled"):
        visual_requests.request_visual_group(db.writer, **race_args)

    # An inference-only settlement is reusable even when every dependency that
    # could start a new recognition is deliberately unavailable.
    fail_rotation = None
    mapping_recovery = {**failure_args, "campaign_group": "1" * 64}
    start_task = visual_requests._start_task

    def interrupt_mapping(conn, run_id, prepared, document_id, selection, step, *args, **kwargs):
        if step == "mapping":
            raise KeyboardInterrupt
        return start_task(conn, run_id, prepared, document_id, selection, step, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(visual_requests, "_start_task", interrupt_mapping)
        with pytest.raises(KeyboardInterrupt):
            visual_requests.request_visual_group(db.writer, **mapping_recovery)

    def unavailable(*args, **kwargs):
        pytest.fail("mapping replay tried to acquire recognition inputs")

    with monkeypatch.context() as patch:
        patch.setattr(pdf_chandra, "ChandraRuntime", unavailable)
        patch.setattr(pdf_visual_mapping, "render_visual_input", unavailable)
        patch.setattr(visual_requests, "_read_visual_original", unavailable)
        recovered_mapping = visual_requests.request_visual_group(db.writer, **mapping_recovery)
    assert recovered_mapping.status == "source_ready"
    assert recovered_mapping.members[0].raw is not None
    assert recovered_mapping.members[0].mapped is not None


def test_visual_group_reopens_only_the_lost_worker(tmp_path, monkeypatch):
    from contextlib import ExitStack, contextmanager

    events = []

    @contextmanager
    def handoff(endpoint, *, check_active):
        events.append("lease")
        try:
            yield
        finally:
            events.append("restore")

    @contextmanager
    def session(runtime):
        generation = events.count("start") + 1
        events.append("start")

        def recognize(pixels, *, check_active, before_submit):
            check_active()
            before_submit()
            if generation == 1:
                raise pdf_chandra.ChandraWorkerLost("controlled lost pipe")
            return pixels

        try:
            yield recognize
        finally:
            events.append("close")

    def active():
        pass

    monkeypatch.setattr(pdf_capacity, "suspend_resident_nemotron", handoff)
    monkeypatch.setattr(pdf_chandra, "ChandraRuntime", lambda _: object())
    monkeypatch.setattr(pdf_chandra, "supervised_chandra", session)
    with ExitStack() as stack:
        group = visual_requests._GroupInference(tmp_path, None, stack)
        with pytest.raises(pdf_chandra.ChandraWorkerLost, match="lost pipe"):
            group.recognize(b"first", check_active=active, before_submit=active)
        assert group.recognize(b"second", check_active=active, before_submit=active) == b"second"
    assert events == ["lease", "start", "close", "start", "close", "restore"]
