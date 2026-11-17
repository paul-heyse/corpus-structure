"""Actual Docling page-subset recovery; no native DDO publication claim."""

import json
from collections import defaultdict
from contextlib import closing

import pyarrow as pa
import pytest

from corpus_structure.ingest.pdf_build_spool import native_preparation_identity
from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource, PdfPageRecovery
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


def test_actual_missing_page_resume_and_same_spool_rebuild(tmp_path, request):
    from corpus_structure.semantic.pdf_certification import prepare_pdf_producer_contract
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context

    recipe, assets = prepared_pdf_resume_assets()
    contract = prepare_pdf_producer_contract(trusted_pdf_context(), kind="native")
    bindings = dict(
        validation_contract=contract.validation_contract,
        lowering_identity=contract.lowering_identity,
        payload_schema=contract.payload_schema,
    )
    interrupted = []

    def stop_after_page(replay):
        interrupted.append(replay)
        if replay.family == "page":
            raise InterruptedAfterDurablePage()

    with OwnedPdfSource.acquire(ORIGINAL, tmp_path / "owned") as source:
        with (
            closing(PdfWorker(recipe, assets=assets)) as worker,
            pytest.raises(InterruptedAfterDurablePage),
        ):
            worker.stream(
                source,
                spool_root=tmp_path / "interrupted",
                record_root=tmp_path / "discarded-records",
                build_id="controlled-recovery",
                release_id="controlled-release",
                on_replay=stop_after_page,
                page_range=PAGE_RANGE,
                **bindings,
            )
        first = _recoveries(interrupted)
        assert len(first) == 1
        resumed_replays = []
        with closing(PdfWorker(recipe, assets=assets)) as worker:
            resumed = worker.stream(
                source,
                spool_root=tmp_path / "resumed",
                record_root=tmp_path / "resumed-records",
                build_id="controlled-recovery",
                release_id="controlled-release",
                on_replay=resumed_replays.append,
                page_range=PAGE_RANGE,
                recovery_pages=first,
                **bindings,
            )
        expected = set(range(PAGE_RANGE[0], PAGE_RANGE[1] + 1))
        computed = {item.page_no for item in resumed_replays if item.family == "page"}
        assert computed == expected - {first[0].page_no}
        assert {item.page_no for item in resumed.page_replays} == expected
        all_pages = first + _recoveries(resumed_replays)
        replayed = []
        with closing(PdfWorker(recipe, assets=assets)) as worker:
            rebuilt = worker.stream(
                source,
                spool_root=tmp_path / "rebuilt",
                record_root=tmp_path / "rebuilt-records",
                build_id="controlled-recovery",
                release_id="controlled-release",
                on_replay=replayed.append,
                page_range=PAGE_RANGE,
                recovery_pages=all_pages,
                **bindings,
            )
        assert not any(item.family in {"page", "candidate_payload"} for item in replayed)
        assert rebuilt.conversion_status == resumed.conversion_status == "success"
        assert _records(rebuilt) == _records(resumed)
    request.node.user_properties.append(
        (
            "provider_panel_scope",
            json.dumps(
                {
                    "original_sha256": source.digest,
                    "physical_pages": PAGE_RANGE,
                    "restored": [first[0].page_no],
                    "computed": sorted(number for number in computed if number is not None),
                    "comparison": "exact emitted records from the same completed page spool",
                    "limits": "no uninterrupted-versus-resumed GPU equality or native DDO publication claim",
                },
                sort_keys=True,
            ),
        )
    )
