"""Published metadata composition preserves graph-selection and coverage fences."""

from copy import deepcopy
from typing import cast

import pytest

from corpus_structure.semantic.characterization import (
    LayerManifest,
    LayerReport,
    _published_layer_manifest,
    validate_layer,
    validate_published_view,
    validate_view,
)
from corpus_structure.semantic.product_reference import ProductReference

from .test_characterization import layer_payload
from .test_characterization import prepared as prepared


def test_manifest_cannot_be_created_from_untrusted_caller_metadata(prepared):
    layer = validate_layer(prepared, layer_payload(prepared))
    with pytest.raises(ValueError, match="protected"):
        LayerManifest(layer.reference(17), layer.content, object())


def test_published_view_keeps_scope_dependencies_and_full_validator_distinct(prepared):
    report = validate_layer(prepared, layer_payload(prepared))
    pin = report.reference(17)
    header = {
        key: value
        for key, value in report.payload.items()
        if key
        not in {
            "occurrences",
            "annotations",
            "memberships",
            "roles",
            "terms",
            "choices",
            "native_runs",
        }
    }
    manifest = _published_layer_manifest(pin, header)
    payload = dict(
        format="enriched-document-view-v1",
        release_id=prepared.release_id,
        base_document=report.payload["base_document"],
        source_scope=report.payload["source_scope"],
        layers=[pin.values()],
        profile="selected_layers",
        coverage=report.payload["coverage"],
    )
    assert validate_published_view(prepared, payload, {pin: manifest}).payload["layers"] == [
        pin.values()
    ]
    with pytest.raises(ValueError, match="full layer validation"):
        validate_view(prepared, payload, cast(dict[ProductReference, LayerReport], {pin: manifest}))
    with pytest.raises(ValueError, match="authenticated"):
        validate_published_view(
            prepared, payload, cast(dict[ProductReference, LayerManifest], {pin: report})
        )
    forged = deepcopy(payload)
    forged["coverage"][0]["reason"] = "unsupported coverage assertion"
    with pytest.raises(ValueError, match="coverage"):
        validate_published_view(prepared, forged, {pin: manifest})
    with pytest.raises(ValueError, match="missing layer"):
        validate_published_view(prepared, payload, {})
    changed = deepcopy(header)
    changed["dependencies"] = [dict(task_id=90, product_key="missing", content_digest="f" * 64)]
    with pytest.raises(ValueError, match="dependency closure"):
        validate_published_view(prepared, payload, {pin: _published_layer_manifest(pin, changed)})
