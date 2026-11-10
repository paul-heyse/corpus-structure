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

from .pdf_integration_support import IMAGE, integrated, make_native_source, prepare, publish
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


@pytest.fixture
def native_source():
    from contextlib import closing

    from pypdfium2 import PdfDocument

    with PdfDocument.new() as document, BytesIO() as output:
        for _ in range(2):
            with closing(document.new_page(200, 300)):
                pass
        document.save(output)
        return make_native_source(output.getvalue())


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


def test_visual_group_renders_compatible_page_once(monkeypatch, tmp_path):
    from contextlib import ExitStack

    with BytesIO() as buffer, Image.new("RGB", (40, 60), (110, 120, 130)) as image:
        image.save(buffer, format="PDF")
        original = buffer.getvalue()
    render_page = pdf_visual_mapping.render_recognition_page
    rendered = []

    def observe_render(document, page_no, scale):
        rendered.append((page_no, scale))
        return render_page(document, page_no, scale)

    monkeypatch.setattr(pdf_visual_mapping, "render_recognition_page", observe_render)
    region = dict(
        page_no=1,
        page_width=40,
        page_height=60,
        left=5,
        top=10,
        right=20,
        bottom=35,
        origin="top_left",
    )
    with ExitStack() as lifetime:
        group = visual_requests._GroupInference(tmp_path, None, lifetime)
        whole, _ = group.render(lambda: original, 1, None, 0)
        crop, transform = group.render(lambda: original, 1, region, 90)
        assert rendered == [(1, 2)]
    with Image.open(BytesIO(whole)) as full_image, Image.open(BytesIO(crop)) as crop_image:
        assert full_image.size == (80, 120)
        assert crop_image.size == (50, 30)
    assert transform["normalization"] == "clipped"
    assert (crop, transform) == pdf_visual_mapping.render_visual_input(original, 1, region, 90)


def test_diagnostics_and_retired_campaigns_cannot_start_chandra(
    pdf13_db, semantic_reader_engine, tmp_path, monkeypatch
):
    from contextlib import contextmanager

    from sqlalchemy.exc import DBAPIError
    from typer.testing import CliRunner

    from corpus_structure.cli import managed
    from corpus_structure.cli.app import app
    from corpus_structure.semantic import runtime, visual_routing
    from corpus_structure.semantic.operations import (
        OperationBinding,
        complete_task,
        create_run,
        seal_cut,
    )
    from corpus_structure.semantic.storage_target import acquired_target
    from corpus_structure.semantic.visual_dispatch import read_visual_dispatch_progress
    from corpus_structure.semantic.visual_routing import VisualRouteReason, VisualRouteReport

    def unexpected_chandra(*args, **kwargs):
        pytest.fail(
            "diagnostics or retired work tried to initialize Chandra or acquire its GPU lease"
        )

    monkeypatch.setattr(pdf_chandra, "ChandraRuntime", unexpected_chandra)
    monkeypatch.setattr(pdf_capacity, "pdf_gpu_slot", unexpected_chandra)
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

    page_signals = visual_routing._page_signals

    def with_deficiency(*args, **kwargs):
        signals = page_signals(*args, **kwargs)
        signals.requests.append(VisualRouteReason(code="incomplete_ocr_region"))
        return signals

    @contextmanager
    def diagnostic_engine(settings, application_name, *, purpose):
        assert purpose == "read"
        yield semantic_reader_engine

    monkeypatch.setattr(visual_routing, "_page_signals", with_deficiency)
    monkeypatch.setattr(runtime, "open_runtime_engine", diagnostic_engine)
    runner = CliRunner()
    retired = runner.invoke(app, ["source", "visual-dispatch", "--help"])
    assert retired.exit_code == 2 and "No such command" in retired.output
    diagnostic = runner.invoke(
        app,
        [
            "source",
            "visual-route",
            str(source.run_id),
            "--producing-task",
            str(source.task_id),
            "--product",
            source.product_key,
            "--native-digest",
            digest,
            "--limit",
            "1",
            "--json",
        ],
    )
    assert diagnostic.exit_code == 0, diagnostic.output
    routes = VisualRouteReport.model_validate_json(diagnostic.stdout)
    assert routes.pages[0].action == "recognize"
    assert "incomplete_ocr_region" in {reason.code for reason in routes.pages[0].reasons}

    selection = visual_requests.VisualSelection(source=source, page_no=1)
    nomination = {
        "version": "visual-nomination-v2",
        "demand": {
            "source": source.model_dump(mode="json"),
            "source_cut": int(cut),
            "release": db.prepared.release_id,
            "realization": "z",
            "mode": "selective",
            "first": 1,
            "limit": 1,
            "artifacts": str(tmp_path),
        },
        "routes": routes.model_dump(mode="json"),
        "selections": [selection.scope()],
    }

    def retain(conn, options):
        return create_run(
            conn,
            project_id="p",
            binding=OperationBinding(db.prepared.release_id, "z", 0, b"{}"),
            kind="slice",
            options=options,
            code_commit=visual_requests.VISUAL_REQUEST_CODE_COMMIT,
            prepared=db.prepared,
        )

    runs, tasks = map(table, ("ops.run", "ops.task"))
    group = {
        "visual_group": {"version": "chandra-visual-group-v1", "selections": [selection.scope()]},
        "visual_recovery": {"artifacts": str(tmp_path), "replay": None},
    }
    with db.writer.begin() as conn:
        assert conn.execute(select(runs.c.id).order_by(runs.c.id)).scalars().all() == [db.job.run]
        nomination_id = retain(conn, {"visual_nomination": nomination})
        seal_cut(conn, nomination_id, "visual-nomination", final=True)
        nominated = retain(
            conn,
            {**group, "visual_campaign_group": "a" * 64, "visual_nomination_run_id": nomination_id},
        )
        legacy = retain(conn, {**group, "visual_campaign_group": "b" * 64})

    args = dict(
        selections=(selection,),
        semantic_release=db.prepared.release_id,
        realization="z",
        receipts=tmp_path,
        artifacts=tmp_path,
    )
    for run_id, reason in (
        (nomination_id, "deficiency-driven visual work is retired"),
        (nominated, "deficiency-driven visual work is retired"),
        (legacy, "legacy visual campaign lacks an explicit scope origin"),
    ):
        with pytest.raises(OperationConflict, match=reason):
            visual_requests.acquire_visual_resume(
                db.writer,
                run_id,
                project="p",
                prepare_only=False,
                select_result=False,
                activate_release=False,
            )
        with pytest.raises(OperationConflict, match=reason):
            visual_requests.request_visual_group(db.writer, **args, resume_run_id=run_id)
    for key, reason in (
        ("a" * 64, "deficiency-driven visual work is retired"),
        ("b" * 64, "legacy visual campaign lacks an explicit scope origin"),
    ):
        with pytest.raises(OperationConflict, match=reason):
            visual_requests.request_visual_group(db.writer, **args, campaign_group=key)

    with db.writer.connect() as conn:
        progress = read_visual_dispatch_progress(conn, nomination_id)
        assert progress.routes == routes
        assert [item.run_id for item in progress.groups] == [nominated]
        assert progress.groups[0].members[0].selection == selection
        assert conn.execute(select(tasks.c.run_id)).scalars().all() == [db.job.run]
        assert conn.execute(select(runs.c.id).order_by(runs.c.id)).scalars().all() == [
            db.job.run,
            nomination_id,
            nominated,
            legacy,
        ]
        visual_requests._require_no_pending_group_overlap(conn, "p", (selection,))

    store = managed.ResultStore(tmp_path / "results")
    monkeypatch.setattr(managed, "result_store", lambda ctx: store)
    with (
        store.operation("source.visual-dispatch", account=True) as receipt,
        db.writer.connect() as conn,
    ):
        account = receipt.manifest.operation_account
        assert account is not None
        account.routing = managed.RoutingProgress(
            nomination_run_id=nomination_id, group_run_ids=(nominated,)
        )
        receipt.record_target(
            acquired_target(conn, purpose="write"), None, None, db.prepared.release_id
        )
        receipt.settle("interrupted")
    history = runner.invoke(app, ["results", "show", receipt.id, "--json"])
    assert history.exit_code == 0, history.output
    historical_routing = json.loads(history.stdout)["operation_account"]["routing"]
    assert historical_routing["native_status"] == "verified"
    assert historical_routing["projection"] == progress.model_dump(mode="json")

    nomination["demand"]["source_cut"] = cut + 100000
    with (
        pytest.raises(
            DBAPIError, match="visual nomination differs from its exact source-ready cut"
        ),
        db.writer.begin() as conn,
    ):
        retain(conn, {"visual_nomination": nomination})


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
    semantic_reader_engine,
    tmp_path,
    monkeypatch,
):
    from corpus_structure.semantic.visual_routing import read_visual_routes

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
    with db.writer.connect() as conn:
        assert read_visual_routes(conn, source, first=1, limit=1).pages[0].action != "recognize"
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
        regional = request.model_copy(update={"occurrence_id": None, "visual_kind": "picture"})
        (sparse,), following = _read_mapped_locator(
            conn, large.mapped, mapped_digest, regional, (inside,), PublishedReadBudget(2, 1024), 0
        )
        assert sparse.occurrence_id == final_picture and following is None
        empty = inside.model_copy(update={"top": 145, "bottom": 155})
        assert _read_mapped_locator(
            conn, large.mapped, mapped_digest, regional, (empty,), PublishedReadBudget(2, 1024), 0
        ) == ((), None)
        with pytest.raises(ReadLimit, match="row-work budget"):
            _read_mapped_locator(
                conn,
                large.mapped,
                mapped_digest,
                regional,
                (outside,),
                PublishedReadBudget(2, 1024),
                0,
            )
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
    # The CLI adds only its observational identity to the already-owned native wire result.
    from contextlib import contextmanager

    from typer.testing import CliRunner

    from corpus_structure.cli.app import app
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.cli.output import CliState
    from corpus_structure.semantic import runtime
    from corpus_structure.settings import Settings

    native_resume = visual_requests.execute_visual_resume
    returned = []

    def observe_resume(*values, **options):
        result = native_resume(*values, **options)
        returned.append(result)
        return result

    @contextmanager
    def visual_resume_engine(settings, application_name="ci", *, purpose, **options):
        assert purpose in {"read", "write"}
        yield semantic_reader_engine if purpose == "read" else db.writer

    import typer

    from corpus_structure.cli.observations import ObservationSelection
    from corpus_structure.cli.result_inspection import inspect_result

    expected_bindings = {
        "run_id": claim.run_id,
        "project": "p",
        "release_id": db.prepared.release_id,
    }
    for label, interruption, outcome, expected_exit in (
        (
            "interrupted",
            KeyboardInterrupt("controlled visual effect interruption"),
            "interrupted",
            130,
        ),
        ("failed", RuntimeError("controlled visual effect failure"), "failed", 1),
    ):
        control_root = tmp_path / ("visual-cli-" + label)
        control_store = ResultStore(control_root)
        control_settings = Settings(
            ci_results=control_root, nemotron={"receipts": args["receipts"]}
        )
        effect_runs = []

        def stop_effect(
            *values,
            _expected_store=control_store,
            _effect_runs=effect_runs,
            _interruption=interruption,
            **options,
        ):
            # This is the real native effect boundary, after acquisition and native fences.
            # The independent retained run/release must already be durable at this point.
            (current,) = _expected_store.list(None, 10, "run.resume").results
            assert current.details["observation_bindings"] == expected_bindings
            assert values[1] == claim.run_id
            _effect_runs.append(values[1])
            raise _interruption

        with monkeypatch.context() as control:
            control.setattr(runtime, "open_runtime_engine", visual_resume_engine)
            control.setattr(visual_requests, "_execute_visual_request", stop_effect)
            response = CliRunner().invoke(
                app,
                ["run", "resume", str(claim.run_id), "--project", "p", "--json"],
                obj=CliState(settings_factory=lambda selected=control_settings: selected),
            )
            assert response.exit_code == expected_exit, response.output
            (retained_wrapper,) = control_store.list(None, 10, "run.resume").results
            context = typer.Context(
                typer.main.get_command(app),
                obj=CliState(settings_factory=lambda selected=control_settings: selected),
            )
            report = inspect_result(
                context, control_store, retained_wrapper.id, ObservationSelection()
            )
        assert effect_runs == [claim.run_id]
        assert retained_wrapper.outcome == outcome
        assert retained_wrapper.details["observation_bindings"] == expected_bindings
        assert report.bindings.run_id == claim.run_id and report.bindings.project == "p"
        assert report.bindings.release_id == db.prepared.release_id
        assert report.native.availability == "available", report.native.reason
        assert report.native.run is not None and report.native.run["run_id"] == claim.run_id
        assert report.native.run["release_id"] == db.prepared.release_id
        assert any(
            action.kind == "native_status" and action.command == f"ci status {claim.run_id}"
            for action in report.next_actions
        )
        assert generation == ["first prompt", "changed prompt", "response before interruption"]

    wrong_root = tmp_path / "visual-cli-wrong-project"
    wrong_store = ResultStore(wrong_root)
    wrong_settings = Settings(ci_results=wrong_root, nemotron={"receipts": args["receipts"]})

    def wrong_project_effect(*values, **options):
        pytest.fail("wrong-project acquisition reached a native effect")

    with monkeypatch.context() as control:
        control.setattr(runtime, "open_runtime_engine", visual_resume_engine)
        control.setattr(visual_requests, "_execute_visual_request", wrong_project_effect)
        response = CliRunner().invoke(
            app,
            ["run", "resume", str(claim.run_id), "--project", "another-project", "--json"],
            obj=CliState(settings_factory=lambda: wrong_settings),
        )
        assert (
            response.exit_code == 1
            and json.loads(response.stdout)["error"]["code"] == "OperationConflict"
        )
        (unbound,) = wrong_store.list(None, 10, "run.resume").results
        context = typer.Context(
            typer.main.get_command(app), obj=CliState(settings_factory=lambda: wrong_settings)
        )
        rejected = inspect_result(context, wrong_store, unbound.id, ObservationSelection())
    assert "observation_bindings" not in unbound.details
    assert rejected.bindings.run_id is None and rejected.bindings.release_id is None
    assert rejected.native.availability == "unavailable"
    assert not any(action.owner == "semantic_run" for action in rejected.next_actions)

    results_root = tmp_path / "visual-cli-results"
    cli_settings = Settings(ci_results=results_root, nemotron={"receipts": args["receipts"]})
    with monkeypatch.context() as cli_environment:
        cli_environment.setattr(runtime, "open_runtime_engine", visual_resume_engine)
        cli_environment.setattr(visual_requests, "execute_visual_resume", observe_resume)
        response = CliRunner().invoke(
            app,
            ["run", "resume", str(claim.run_id), "--project", "p", "--json"],
            obj=CliState(settings_factory=lambda: cli_settings),
        )
    assert response.exit_code == 0, response.output
    (recovered,) = returned
    assert isinstance(recovered, visual_requests.VisualRequestResult)
    assert recovered.status == "source_ready" and recovered.run_id == claim.run_id
    wire = json.loads(response.stdout)
    wrapper_id = wire.pop("invocation_id")
    assert wire == recovered.model_dump(mode="json")
    wrapper = ResultStore(results_root).show(wrapper_id)
    assert wrapper.action == "run.resume" and wrapper.outcome == "passed"
    assert wrapper.details["observation_bindings"] == {
        "run_id": claim.run_id,
        "project": "p",
        "release_id": db.prepared.release_id,
    }
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
    from types import SimpleNamespace

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
    recipe_revision = "controlled"

    def provider_identity():
        return {
            "repository": "datalab-to/chandra-ocr-2",
            "revision": recipe_revision,
            "packages": {"docling": "2.148.0"},
            "artifacts_sha256": {
                "model.safetensors": "b" * 64,
                "tokenizer.json": "c" * 64,
            },
            "prompt": "group test",
            "decode": {},
        }

    class ControlledRuntime:
        def __init__(self, artifacts):
            assert artifacts == tmp_path
            self.effective_device = {"device": "controlled"}

        def identity(self):
            return provider_identity()

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
    monkeypatch.setattr(pdf_chandra, "chandra_recognition_identity", provider_identity)
    monkeypatch.setattr(pdf_chandra, "supervised_chandra", session)
    monkeypatch.setattr(
        visual_requests._GroupInference,
        "render",
        lambda self, load_original, page, region, rotation: render(
            load_original(), page, region, rotation
        ),
    )

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
    acquired = visual_requests.acquire_visual_resume(
        db.writer,
        run_id,
        project="p",
        prepare_only=False,
        select_result=False,
        activate_release=False,
    )
    assert isinstance(acquired, visual_requests.VisualGroupResume)
    resumed = visual_requests.execute_visual_resume(
        acquired,
        receipts=args["receipts"],
        nemotron_endpoint=None,
    )
    assert isinstance(resumed, visual_requests.VisualGroupResult)
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
    start_task = visual_requests._start_task

    def interrupt_cancelled_mapping(
        conn, run_id, prepared, document_id, selection, step, *args, **kwargs
    ):
        if step == "mapping" and selection.rotation == 90:
            raise KeyboardInterrupt
        return start_task(conn, run_id, prepared, document_id, selection, step, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(visual_requests, "_start_task", interrupt_cancelled_mapping)
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
        patch.setattr(visual_requests._GroupInference, "render", unavailable)
        patch.setattr(visual_requests, "_read_visual_original", unavailable)
        recovered_mapping = visual_requests.request_visual_group(db.writer, **mapping_recovery)
    assert recovered_mapping.status == "source_ready"
    assert recovered_mapping.members[0].raw is not None
    assert recovered_mapping.members[0].mapped is not None

    # A new ordinary group can reuse the provider's settled raw bytes even
    # when the provider reports no completion reason.
    recipe_revision = "unspecified-completion"
    seed_args = {**failure_args, "campaign_group": "2" * 64}
    seeded = visual_requests.request_visual_group(db.writer, **seed_args)
    assert seeded.status == "source_ready" and seeded.members[0].raw is not None
    raw_pin = seeded.members[0].raw

    def pending_mapping(pin):
        return SimpleNamespace(
            id=-1,
            reused_task_id=None,
            unit_key="unpublished-mapping",
            trigger={"visual_raw": pin.model_dump(mode="json")},
        )

    with db.writer.connect() as conn:
        selection = seed_args["selections"][0]
        assert (
            visual_requests._visual_mapping_raw_pin(conn, pending_mapping(raw_pin), selection, "p")
            == raw_pin
        )
        assert (
            visual_requests._visual_mapping_raw_pin(
                conn,
                pending_mapping(raw_pin.model_copy(update={"run_id": raw_pin.run_id + 1})),
                selection,
                "p",
            )
            is None
        )
        assert (
            visual_requests._visual_mapping_raw_pin(
                conn, pending_mapping(raw_pin), requests[1], "p"
            )
            is None
        )
        assert (
            visual_requests._visual_mapping_raw_pin(
                conn, pending_mapping(raw_pin), selection, "wrong-project"
            )
            is None
        )
    attempts_before_reuse = len(attempts)
    with monkeypatch.context() as patch:
        patch.setattr(pdf_chandra, "ChandraRuntime", unavailable)
        patch.setattr(visual_requests._GroupInference, "render", unavailable)
        patch.setattr(visual_requests, "_read_visual_original", unavailable)
        reused = visual_requests.request_visual_group(
            db.writer, **{**seed_args, "campaign_group": "3" * 64}
        )
    assert reused.status == "source_ready" and reused.run_id != seeded.run_id
    assert reused.members[0].raw == seeded.members[0].raw
    assert len(attempts) == attempts_before_reuse
    with db.writer.connect() as conn:
        body, _, response = visual_requests._open_observation(conn, raw_pin, "p", selection)
    assert response == _HTML.encode()
    assert body["observation"]["outcome"] == "unknown"
    assert body["observation"]["finish_reason"] == VlmStopReason.UNSPECIFIED.value
    assert body["observation"]["diagnostic"] == "Chandra did not report a completion reason"
    recipe_revision = "changed-recognition"
    changed = visual_requests.request_visual_group(
        db.writer, **{**seed_args, "campaign_group": "4" * 64}
    )
    assert changed.members[0].raw != seeded.members[0].raw
    assert len(attempts) == attempts_before_reuse + 1


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
