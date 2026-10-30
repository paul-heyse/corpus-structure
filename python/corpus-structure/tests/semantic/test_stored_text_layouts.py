"""Stored token artifacts preserve content identity and reject corrupt source custody."""

from copy import deepcopy
from dataclasses import replace

import pytest

from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.semantic.contracts import trusted_execution_inputs
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.text_layouts import freeze_text_layouts, load_text_layouts


def test_token_artifact_roundtrip_integrity_and_historical_reconstruction():
    result = build_rendition(
        b'<p>Let <span class="math">x</span> be real.</p>',
        compile_profile(load_profile("siegrist")),
        SentenceConfig(),
        source_uri="siegrist_random/random/test/Page.html",
    )
    prepared = prepare_release(trusted_execution_inputs().schema)
    payload = freeze_text_layouts(result.text_layouts, result.content, prepared, 17)
    assert payload is not None and result.text_layouts
    assert load_text_layouts(payload, result.content, prepared, 17) == result.text_layouts
    assert load_text_layouts(None, result.content, prepared, 17) == ()
    corrupt = deepcopy(payload)
    corrupt["layouts"][0]["tokens"][0]["start"] += 1
    with pytest.raises(ValueError, match="digest differs"):
        load_text_layouts(corrupt, result.content, prepared, 17)
    with pytest.raises(ValueError, match="custody differs"):
        load_text_layouts(payload, result.content, prepared, 18)

    forged = replace(
        result.text_layouts[0],
        tokens=(
            replace(result.text_layouts[0].tokens[0], role="reference"),
            *result.text_layouts[0].tokens[1:],
        ),
    )
    with pytest.raises(ValueError, match="atom roles differ"):
        freeze_text_layouts((forged, *result.text_layouts[1:]), result.content, prepared, 17)
