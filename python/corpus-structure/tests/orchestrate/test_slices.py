"""Current native scopes preserve intact named sections and reject retired selectors."""

import pytest

from corpus_structure.orchestrate.slices import SliceError, records

DOCS = [{"key": "pdf:1", "mime": "application/pdf", "content_hash": "a" * 64}]


def test_native_scope_retains_sections_and_original_manifest():
    original, scope = records(
        DOCS,
        {"selected": [{"native_sections": ["1.1: Sets", "1.2: Functions", "1.1: Sets"]}]},
        slice=None,
        scope="selected",
        corpus=None,
    )
    assert original["documents"] == ["pdf:1"]
    assert scope["sections"] == ["1.1: Sets", "1.2: Functions"]
    assert scope["kind"] == "native_sections" and scope["include_descendants"] is True
    assert records(DOCS, {}, slice=None, scope=None, corpus=None)[1] is None


@pytest.mark.parametrize(
    "entries", [["page.html#u"], [{"golden_set": "old"}], [{"native_sections": []}]]
)
def test_current_scope_refuses_html_reference_sets_and_empty_sections(entries):
    with pytest.raises(SliceError):
        records(DOCS, {"selected": entries}, slice="selected", scope=None, corpus=None)


def test_current_source_refuses_retired_non_pdf_acquisition():
    with pytest.raises(SliceError, match="PDF originals"):
        records([{"mime": "text/html"}], {}, slice=None, scope=None, corpus=None)
