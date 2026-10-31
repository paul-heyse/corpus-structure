"""Stored token artifacts preserve content identity and reject corrupt source custody."""

import json
from pathlib import Path
from copy import deepcopy
from dataclasses import replace

import pytest

from pydantic import TypeAdapter
from corpus_structure.core.evidence import RenditionContent
from corpus_structure.ingest.sentences import TextLayout
from corpus_structure.semantic.contracts import trusted_execution_inputs
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.text_layouts import freeze_text_layouts, load_text_layouts


def test_token_artifact_roundtrip_integrity_and_historical_reconstruction():
    archive = json.loads((Path(__file__).with_name("fixtures") / "retained-html-inputs.json").read_bytes())["layouts"]
    content = RenditionContent.model_validate(archive["content"])
    layouts = TypeAdapter(tuple[TextLayout, ...]).validate_python(archive["layouts"])
    prepared = prepare_release(trusted_execution_inputs().schema)
    payload = freeze_text_layouts(layouts, content, prepared, 17)
    assert payload is not None and layouts
    assert load_text_layouts(payload, content, prepared, 17) == layouts
    assert load_text_layouts(None, content, prepared, 17) == ()
    corrupt = deepcopy(payload)
    corrupt["layouts"][0]["tokens"][0]["start"] += 1
    with pytest.raises(ValueError, match="digest differs"):
        load_text_layouts(corrupt, content, prepared, 17)
    with pytest.raises(ValueError, match="custody differs"):
        load_text_layouts(payload, content, prepared, 18)

    forged = replace(
        layouts[0],
        tokens=(
            replace(layouts[0].tokens[0], role="reference"),
            *layouts[0].tokens[1:],
        ),
    )
    with pytest.raises(ValueError, match="atom roles differ"):
        freeze_text_layouts((forged, *layouts[1:]), content, prepared, 17)
