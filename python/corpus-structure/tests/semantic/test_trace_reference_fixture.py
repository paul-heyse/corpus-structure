"""Source-only reference fixtures and completed-cut forced sampling scope."""

import json
from pathlib import Path

import pytest

from corpus_structure.core.evidence import RenditionContent
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.locators import parse as parse_locator
from corpus_structure.evaluate.sampling import GoldenSetError, PoolUnit, sample
from corpus_structure.semantic.proposals import ProposalFrame, ProposalSentence, locate_proposal
from corpus_structure.semantic.regeneration import prepare_pack

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def trace_source():
    batches = json.loads((ROOT / "fixtures/trace/semantic-trace-reference.json").read_bytes())
    archive = json.loads((ROOT / "fixtures/trace/archived-renditions.json").read_bytes())
    content = {
        page: RenditionContent.model_validate(value["content"])
        for page, value in archive["pages"].items()
    }
    return batches, content


def test_trace_reference_is_well_typed_and_independently_source_located(trace_source):
    batches, contents = trace_source
    _, _, _, prepared = prepare_pack(ROOT / "domains/statistics")
    for batch in batches:
        page = parse_locator(batch["unit_ref"]).page
        content = contents[page]
        index = LocatorIndex(content, page)
        sentences = []
        for claim in batch["claims"]:
            for citation in claim["evidence"]:
                matching = [
                    (segment, locator)
                    for segment, locator in index
                    if segment.kind.value == "sentence"
                    and content.canonical_text[segment.start : segment.end] == citation["quote"]
                ]
                assert len(matching) == 1
                segment, locator = matching[0]
                sentences.append(
                    ProposalSentence(citation["sentence"], str(locator), segment.start, segment.end)
                )
        frame = ProposalFrame(batch["unit_ref"], content.canonical_text, tuple(sentences))
        located = locate_proposal(prepared, batch, frame)
        assert located.clean, located.issues


def test_explicit_forced_trace_sample_cannot_enlarge_its_selected_source_pool(trace_source):
    batches, _ = trace_source
    forced = {batch["unit_ref"] for batch in batches}
    pool = [PoolUnit(key, "source", None) for key in forced]
    with pytest.raises(GoldenSetError, match="forced units exceed"):
        sample(pool, 1, 0, forced)
    assert set(sample(pool, len(pool), 0, forced).units) == forced
    with pytest.raises(GoldenSetError, match="forced units outside the pool"):
        sample(pool, len(pool), 0, (*forced, "special/Gamma.html#dfn4"))


def test_repeated_evaluation_rewrite_preserves_dated_qualification_and_exact_decimal():
    from corpus_structure.evaluate.semantic_values import rewrite_references

    _, _, _, prepared = prepare_pack(ROOT / "domains/toy")
    value = {
        "modality": "asserted",
        "polarity": True,
        "valid_time": {
            "kind": "validity_interval",
            "start": {"kind": "date", "date": "2020-07-01"},
            "end": {"kind": "date", "date": "2020-07-01"},
            "start_incl": True,
            "end_incl": True,
        },
    }
    first = rewrite_references(prepared, "Qualification", value, {})
    assert first == value
    assert rewrite_references(prepared, "Qualification", first, {}) == value
    quantity = {"kind": "quantity", "number": "12.3400", "unit": "kg", "basis": "dry-mass"}
    rewritten = rewrite_references(prepared, "Value", quantity, {})
    assert rewritten == quantity
    assert rewrite_references(prepared, "Value", rewritten, {}) == quantity
