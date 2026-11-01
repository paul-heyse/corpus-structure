"""Finite candidate replay, selected ownership and original list identity controls."""

import pickle
from dataclasses import replace

import pyarrow.compute as pc
import pytest

from corpus_structure.ingest.pdf_candidate_source import (
    InMemoryCandidatePageSource,
    OverlayCandidatePageSource,
    candidate_from_payload,
)
from corpus_structure.ingest.pdf_candidates import CandidatePage, InlineCandidate
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool
from corpus_structure.semantic.pdf_payloads import PreparedPayloadFamily, prepare_payload_family


def page(number, texts=("x", "=", "Ω")):
    return CandidatePage(
        number,
        True,
        False,
        tuple(
            InlineCandidate(number, text, index, -0.0, index + 1, 3.5, "TOPLEFT", None, "fixture")
            for index, text in enumerate(texts)
        ),
        True,
    )


def test_candidate_spool_encodes_once_and_callbacks_keep_exact_binding(tmp_path, monkeypatch):
    family = prepare_payload_family()
    encodes = []
    original = PreparedPayloadFamily.encode

    def counted(self, value, **kwargs):
        encodes.append(value["page_no"])
        return original(self, value, **kwargs)

    monkeypatch.setattr(PreparedPayloadFamily, "encode", counted)
    observed = []
    spool = PdfStreamSpool(tmp_path / "spool", payload_family=family, on_page=observed.append)
    original_page = page(7)
    spool.capture_candidates(original_page)
    source = spool.candidate_source
    encoded = source.encoded(7)
    assert encodes == [7]
    assert observed == [spool.candidates[7]]
    assert observed[0].family == "candidate_payload"
    assert observed[0].page_no == 7
    assert observed[0].path.suffix == ".arrow"
    assert not list(spool.root.glob("candidate-*.json"))
    assert encoded.content == observed[0].path.read_bytes()
    value = family.decode(
        encoded.content,
        schema_digest=encoded.schema_digest,
        logical_digest=encoded.logical_digest,
    )
    assert value == original_page.to_wire()
    assert "font" not in value["candidates"][0]
    assert type(value["candidates"][0]["left"]) is int
    assert type(value["candidates"][0]["top"]) is float
    assert tuple(source.iter_pages()) == (original_page,)


def test_selected_batches_skip_other_replays_and_own_buffers_after_close(tmp_path):
    spool = PdfStreamSpool(tmp_path / "spool")
    spool.capture_candidates(page(2))
    spool.capture_candidates(page(7))
    spool.candidates[2].path.write_bytes(b"corrupted unselected page")
    batches = spool.candidate_source.iter_batches({7}, ("page_no", "candidates"))
    batch = next(batches)
    assert next(batches, None) is None
    spool.candidates[7].path.unlink()
    assert batch.schema.names == ["page_no", "candidates"]
    assert batch.column("page_no")[0].as_py() == 7
    candidates = pc.call_function("list_flatten", [batch.column("candidates")])
    # Original list order establishes indices before downstream filtering.
    assert [candidate["text"].as_py() for candidate in candidates] == ["x", "=", "Ω"]
    assert candidate_from_payload(candidates[2].as_py()).text == "Ω"
    with pytest.raises(ValueError, match="bytes changed"):
        spool.candidate_source.encoded(2)


def test_overlay_keeps_unchanged_ipc_and_only_hydrates_requested_pages(tmp_path):
    spool = PdfStreamSpool(tmp_path / "spool")
    spool.capture_candidates(page(2))
    spool.capture_candidates(page(7))
    base = spool.candidate_source
    replacement = page(7, ("rediscovered",))
    source = OverlayCandidatePageSource(base, {7: replacement, 9: page(9, ())})
    assert source.page_nos == (2, 7, 9)
    assert source.encoded(2).content == base.encoded(2).content
    assert tuple(source.iter_pages({7})) == (replacement,)
    assert [batch.column("page_no")[0].as_py() for batch in source.iter_batches()] == [2, 7, 9]


def test_candidate_replay_refuses_wrong_schema_or_page_binding(tmp_path):
    spool = PdfStreamSpool(tmp_path / "spool")
    spool.capture_candidates(page(7))
    replay = spool.candidates[7]
    spool.candidates[7] = replace(replay, schema_digest="0" * 64)
    with pytest.raises(ValueError, match="schema binding"):
        spool.candidate_source.encoded(7)
    spool.candidates[7] = replace(replay, page_no=8)
    with pytest.raises(ValueError, match="page binding"):
        spool.candidate_source.encoded(7)


def test_failed_candidate_adoption_does_not_admit_page(tmp_path):
    def refuse(_):
        raise RuntimeError("custody refused")

    spool = PdfStreamSpool(tmp_path / "spool", on_page=refuse)
    with pytest.raises(RuntimeError, match="custody refused"):
        spool.capture_candidates(page(7))
    assert not spool.candidates
    assert (spool.root / "candidate-000007.arrow").exists()


@pytest.mark.parametrize("kind", ("unprepared-memory", "prepared-memory", "replay", "overlay"))
def test_source_process_transfer_reprepares_exact_schema_without_validator_handles(tmp_path, kind):
    original_page = page(7)
    if kind.endswith("memory"):
        source = InMemoryCandidatePageSource((original_page,))
        if kind == "prepared-memory":
            source.payload_family.batch(original_page.to_wire())
    else:
        spool = PdfStreamSpool(tmp_path / "spool")
        spool.capture_candidates(original_page)
        source = spool.candidate_source
        if kind == "overlay":
            source = OverlayCandidatePageSource(source, {9: page(9, ("replacement",))})
    transferred = pickle.loads(pickle.dumps(source))
    assert transferred.page_nos == source.page_nos
    assert transferred.payload_family.schema_digest == source.payload_family.schema_digest
    assert list(transferred.iter_pages()) == list(source.iter_pages())
    assert transferred.encoded(7).content == source.encoded(7).content
