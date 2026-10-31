"""Historical full-corpus inputs remain readable after retiring HTML production."""

import json
from pathlib import Path

from archived_source import archived_rendition

from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.vocab import SegmentKind


def test_all_retained_corpus_inputs_have_bounded_nested_segments_and_stable_locators():
    archive = Path(__file__).resolve().parents[4] / "fixtures/trace/archived-renditions.json"
    pages = json.loads(archive.read_bytes())["pages"]
    assert len(pages) == 78
    for page in pages:
        content = archived_rendition(page)
        locator = LocatorIndex(content, page)
        for segment in content.document.walk():
            assert 0 <= segment.start <= segment.end <= len(content.canonical_text)
            for child in segment.children:
                assert segment.start <= child.start <= child.end <= segment.end
            if segment.kind is not SegmentKind.SENTENCE:
                assert locator.resolve(str(locator.generate(segment))) is segment
