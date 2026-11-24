"""Opt-in selected-contract Docling recovery and native PDF adoption.

This file is intentionally outside default pytest filename discovery. Select it
explicitly through ci test --providers-only for the experimental v3 boundary.
"""

import json
from collections import defaultdict
from contextlib import closing

import pyarrow as pa
import pytest

from corpus_structure.ingest.pdf_build_spool import native_preparation_identity
from corpus_structure.ingest.pdf_stream_types import (
    OwnedPdfSource,
    PdfPageRecovery,
    PdfStreamRequest,
)
from corpus_structure.ingest.pdf_worker import PdfWorker
from semantic.actual_pdf_resume_support import ORIGINAL, PAGE_RANGE, prepared_pdf_resume_assets

pytestmark = [
    pytest.mark.provider_evidence,
    pytest.mark.gpu,
    pytest.mark.prerequisite("pdf_resume_assets"),
    pytest.mark.xdist_group("actual-native-pdf"),
]


class InterruptedAfterDurablePage(RuntimeError):
    pass


def _recoveries(replays):
    preparations = [item for item in replays if item.family == "native_preparation"]
    assert len(preparations) == 1
    identity = native_preparation_identity(preparations[0].path.read_bytes())
    candidates = {item.page_no: item for item in replays if item.family == "candidate_payload"}
    return tuple(
        PdfPageRecovery(item.page_no, item, candidates[item.page_no], identity)
        for item in replays
        if item.family == "page"
    )


def _records(reply):
    result = defaultdict(list)
    replays = (
        *reply.record_replays,
        *(replay for group in reply.companion_sets for replay in group.replays),
    )
    for replay in replays:
        replay.verify()
        with pa.memory_map(str(replay.path), "r") as source:
            reader = pa.ipc.open_file(source)
            for index in range(reader.num_record_batches):
                result[replay.family].extend(reader.get_batch(index).to_pylist())
    # COPY batch delivery order and JSON object member order are not record
    # identities. Retain exact stream bytes and array/ordinal order within rows.
    for rows in result.values():
        for row in rows:
            for name in ("scalars_json", "structure_json"):
                if name in row:
                    row[name] = json.loads(row[name])
        rows.sort(
            key=lambda row: json.dumps(row, sort_keys=True, default=lambda value: value.hex())
        )
    return dict(result)


def test_actual_selected_missing_page_resume_and_same_spool_rebuild(
    tmp_path,
    request,
    commit_db_engine,
    commit_writer_engine,
    commit_admitter_engine,
):
    from corpus_structure.ingest.pdf_producer_contract import standard_pdf_contract
    from corpus_structure.semantic.pdf_certification import prepare_pdf_producer_contract
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_task
    from corpus_structure.semantic.pdf_lowering import CAPTURE_OPERATION
    from semantic.current_pdf_source_support import current_pdf_recipe
    from semantic.pdf_staging_support import _private_build_factory

    recipe, assets = prepared_pdf_resume_assets()
    selected = standard_pdf_contract()
    factory = _private_build_factory(
        commit_db_engine,
        commit_writer_engine,
        tmp_path,
        request,
        admission_engine=commit_admitter_engine,
        original_path=ORIGINAL,
        kernel_recipe=current_pdf_recipe(tmp_path, capture_profile=(recipe, assets, selected)),
    )
    original = factory()
    with commit_writer_engine.begin() as conn:
        context = pdf_context_for_task(conn, original.task_id, operation=CAPTURE_OPERATION)
    contract = prepare_pdf_producer_contract(context, kind="native")
    bindings = dict(
        validation_contract=contract.validation_contract,
        lowering_identity=contract.lowering_identity,
        payload_schema=contract.payload_schema,
        producer_contract=selected.content,
        producer_custody=selected.custody(),
    )
    interrupted = []

    def stop_after_page(replay):
        interrupted.append(replay)
        if replay.family == "page":
            raise InterruptedAfterDurablePage()

    with (
        factory.maintained(original) as active,
        OwnedPdfSource.acquire(ORIGINAL, tmp_path / "owned") as source,
    ):
        with (
            closing(PdfWorker(recipe, assets=assets)) as worker,
            pytest.raises(InterruptedAfterDurablePage),
        ):
            worker.stream(
                PdfStreamRequest(
                    source,
                    spool_root=tmp_path / "interrupted",
                    record_root=tmp_path / "discarded-records",
                    release_id=original.release_id,
                    page_range=PAGE_RANGE,
                    **bindings,
                ),
                on_replay=stop_after_page,
                check_active=active,
            )
        first = _recoveries(interrupted)
        assert len(first) == 1
        preparation = next(item for item in interrupted if item.family == "native_preparation")
        assert (
            json.loads(preparation.path.read_bytes())["_preparation"]["producer_contract"]
            == selected.digest
        )
        resumed_replays = []
        with closing(PdfWorker(recipe, assets=assets)) as worker:
            resumed = worker.stream(
                PdfStreamRequest(
                    source,
                    spool_root=tmp_path / "resumed",
                    record_root=tmp_path / "resumed-records",
                    release_id=original.release_id,
                    page_range=PAGE_RANGE,
                    recovery_pages=first,
                    **bindings,
                ),
                on_replay=resumed_replays.append,
                check_active=active,
            )
        expected = set(range(PAGE_RANGE[0], PAGE_RANGE[1] + 1))
        computed = {item.page_no for item in resumed_replays if item.family == "page"}
        assert computed == expected - {first[0].page_no}
        assert {item.page_no for item in resumed.page_replays} == expected
        all_pages = first + _recoveries(resumed_replays)
        replayed = []
        with closing(PdfWorker(recipe, assets=assets)) as worker:
            rebuilt = worker.stream(
                PdfStreamRequest(
                    source,
                    spool_root=tmp_path / "rebuilt",
                    record_root=tmp_path / "rebuilt-records",
                    release_id=original.release_id,
                    page_range=PAGE_RANGE,
                    recovery_pages=all_pages,
                    **bindings,
                ),
                on_replay=replayed.append,
                check_active=active,
            )
        assert not any(item.family in {"page", "candidate_payload"} for item in replayed)
        assert rebuilt.conversion_status == resumed.conversion_status == "success"
        assert _records(rebuilt) == _records(resumed)
    _adopt_recovered_panel(factory, original, resumed, contract, tmp_path, expected)
    request.node.user_properties.append(
        (
            "provider_panel_scope",
            json.dumps(
                {
                    "identity_basis": "selected-file-contract-v3",
                    "producer_contract_digest": selected.digest,
                    "original_sha256": source.digest,
                    "physical_pages": PAGE_RANGE,
                    "restored": [first[0].page_no],
                    "computed": sorted(number for number in computed if number is not None),
                    "comparison": "exact emitted records from the same completed page spool",
                    "adoption": "new build recertified and sealed the selected pages",
                    "limits": "three selected pages, no full-book publication or GPU repeatability claim",
                },
                sort_keys=True,
            ),
        )
    )


def _adopt_recovered_panel(factory, original, reply, original_contract, root, expected):
    from corpus_structure.core.db.lifetime import BorrowerCancellation
    from corpus_structure.orchestrate.pdf_streaming import _adopt_pdf_document, _finish_frozen_pdf
    from corpus_structure.semantic.pdf_certification import prepare_pdf_producer_contract
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_task
    from corpus_structure.semantic.pdf_lowering import CAPTURE_OPERATION
    from corpus_structure.semantic.pdf_lowering_context import CapturedPdfLowering
    from corpus_structure.semantic.pdf_publication import freeze_pdf_build
    from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader, PublishedReadBudget
    from corpus_structure.semantic.pdf_replay_transport import PdfReplayBinding
    from corpus_structure.semantic.pdf_spool_recertification import recertify_pdf_recovery
    from corpus_structure.semantic.product_reference import ProductReference

    adopter = factory(case="unknown-cell-coverage")
    assert adopter.build_id != original.build_id
    with factory.writer.begin() as conn:
        context = pdf_context_for_task(conn, adopter.task_id, operation=CAPTURE_OPERATION)
    contract = prepare_pdf_producer_contract(context, kind="native")
    lowering = CapturedPdfLowering.from_document(
        json.loads(original_contract.validation_contract)["lowering"]
    )
    binding = PdfReplayBinding(original.build_id, original.release_id)
    assert reply.certification is not None and reply.access_replay is not None
    cancellation = BorrowerCancellation()
    with factory.maintained(adopter) as active:
        certificate = recertify_pdf_recovery(
            reply,
            root / "recertified",
            original=binding,
            original_lowering=lowering,
            original_lowering_identity=original_contract.lowering_identity,
            validation_contract=contract.validation_contract,
            lowering_identity=contract.lowering_identity,
            source_digest=adopter.source_digest,
            recipe_digest=adopter.recipe_digest,
            schema_digest=adopter.schema_digest,
            check_active=active,
        )
        original_values = json.loads(reply.certification.read_bytes())
        assert certificate.logical_digest == original_values["logical_digest"]
        assert certificate.stream_inventory_digest == original_values["stream_inventory_digest"]
        _adopt_pdf_document(
            factory.writer,
            adopter,
            reply.record_replays,
            reply.companion_sets,
            reply.access_replay,
            certificate,
            cancellation=cancellation,
            check_active=active,
            legacy_binding=binding,
            legacy_lowering=lowering,
        )
        with factory.writer.begin() as conn:
            frozen = freeze_pdf_build(conn, adopter, kind="native")
        publication = _finish_frozen_pdf(
            factory.writer, frozen, "native", active, cancellation=cancellation
        )
        assert publication.logical_digest == certificate.logical_digest
        factory.complete(adopter, publication)
    with factory.writer.begin() as conn:
        reader = PublishedPdfReader(
            conn,
            ProductReference(
                publication.task_id, publication.product_key, publication.logical_digest
            ),
            projection_context=factory.kernel.prepared,
            read_budget=PublishedReadBudget(100, 64 * 1024 * 1024),
        )
        assert {page.page_no for page in reader.iter_candidate_payloads()} == expected
