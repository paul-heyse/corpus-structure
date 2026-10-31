"""Source-only reference fixtures and completed-cut forced sampling scope."""

import json
from pathlib import Path

import pytest
import yaml

from corpus_structure.core.evidence import RenditionContent
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.locators import parse as parse_locator
from corpus_structure.evaluate.sampling import GoldenSetError, PoolUnit, sample
from corpus_structure.evaluate.semantic import ReferenceError, _forced_slice_units
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


class ArchivedSource:
    """Only the archived bytes read by the scope resolver; no native enforcement claim."""

    def __init__(self, contents):
        self.contents = contents

    def scalar(self, statement):
        ids = [value for value in statement.compile().params.values() if isinstance(value, int)]
        if ids:
            return self.contents[ids[0]].model_dump(mode="json")
        return (ROOT / "domains/statistics/slices.yaml").read_bytes()


def test_forced_trace_scope_records_core_units_outside_completed_cut(trace_source):
    batches, contents = trace_source
    by_page = {page: i for i, page in enumerate(contents, start=1)}
    source = ArchivedSource({by_page[page]: content for page, content in contents.items()})
    pool = [
        {
            "unit_key": batch["unit_ref"],
            "rendition_id": by_page[parse_locator(batch["unit_ref"]).page],
        }
        for batch in batches
    ]
    forced, outside = _forced_slice_units(source, "archived", pool, ("trace", "core12"))
    assert set(forced) == {batch["unit_ref"] for batch in batches}
    excluded = {item["locator"]: item["reason"] for item in outside}
    assert excluded["special/Normal.html#rel2"] == "source_unit_outside_completed_cut"
    assert excluded["special/Gamma.html#dfn4"] == "source_page_outside_completed_cut"
    assert len(excluded) == 8
    with pytest.raises(GoldenSetError, match="forced units exceed"):
        sample([PoolUnit(key, "source", None) for key in forced], 1, 0, forced)
    assert set(
        sample([PoolUnit(key, "source", None) for key in forced], 5, 0, forced).units
    ) == set(forced)


def test_unresolvable_forced_locator_on_acquired_page_is_a_refusal(trace_source):
    batches, contents = trace_source

    class InvalidPolicy(ArchivedSource):
        def scalar(self, statement):
            ids = [value for value in statement.compile().params.values() if isinstance(value, int)]
            if ids:
                return super().scalar(statement)
            return yaml.safe_dump({"slices": {"bad": ["special/Normal.html#missing"]}}).encode()

    source = InvalidPolicy({1: contents["special/Normal.html"]})
    pool = [{"unit_key": batches[3]["unit_ref"], "rendition_id": 1}]
    with pytest.raises(ReferenceError, match="absent or ambiguous on its source page"):
        _forced_slice_units(source, "archived", pool, ("bad",))


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
