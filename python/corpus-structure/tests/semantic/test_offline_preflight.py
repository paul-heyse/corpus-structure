"""Independent known truncation cases for the standalone consumer."""

import json
import runpy
from hashlib import sha256
from pathlib import Path

import pytest


def package(tmp_path, schema, **overrides):
    content = json.dumps(schema).encode()
    (tmp_path / "schema.json").write_bytes(content)
    manifest = dict(
        version=1,
        mode="validation",
        dialect="https://json-schema.org/draft/2020-12/schema",
        entry="schema.json",
        schema_digest=sha256(content).hexdigest(),
        release_id="release:test",
        limitations=["structural_preflight_only"],
    )
    manifest.update(overrides)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))


@pytest.mark.parametrize(
    ("schema", "overrides", "message"),
    [
        ({"$schema": "https://example.invalid/dialect"}, {}, "schema dialect"),
        ({}, {"mode": "serialization"}, "portable contract profile"),
        ({"$vocabulary": {"urn:unknown:required": True}}, {}, "custom vocabulary"),
        ({"$defs": {"unused": {"$ref": "https://example.invalid/schema"}}}, {}, "offline resource"),
        ({"$dynamicRef": "#root"}, {}, "dynamic reference"),
        ({}, {"schema_digest": "0" * 64}, "schema digest"),
    ],
)
def test_unsupported_or_unauthenticated_package_refuses(tmp_path, schema, overrides, message):
    script = runpy.run_path(str(Path(__file__).parents[4] / "examples/offline_interpretation.py"))
    package(tmp_path, schema, **overrides)
    with pytest.raises(ValueError, match=message):
        script["preflight"](tmp_path, {})


def test_local_reference_closure_includes_unused_branches_and_anchors(tmp_path):
    from referencing.exceptions import Unresolvable

    script = runpy.run_path(str(Path(__file__).parents[4] / "examples/offline_interpretation.py"))
    package(tmp_path, {"$defs": {"unused": {"$ref": "#/$defs/missing"}}})
    with pytest.raises(Unresolvable):
        script["preflight"](tmp_path, {})
    package(
        tmp_path,
        {"$defs": {"number": {"$anchor": "number", "type": "integer"}}, "$ref": "#number"},
    )
    assert script["preflight"](tmp_path, 7)["outcome"] == "passed"
    answer = script["preflight"](tmp_path, "7")
    assert answer["outcome"] == "failed" and answer["errors"][0]["instance_path"] == []


def test_nested_union_truncation_is_not_complete(tmp_path):
    script = runpy.run_path(str(Path(__file__).parents[4] / "examples/offline_interpretation.py"))
    schema = {"$schema": script["DIALECT"], "oneOf": [{"const": i} for i in range(60)]}
    content = json.dumps(schema).encode()
    (tmp_path / "schema.json").write_bytes(content)
    manifest = dict(
        version=1,
        mode="validation",
        dialect=script["DIALECT"],
        entry="schema.json",
        schema_digest=sha256(content).hexdigest(),
        release_id="release:test",
        limitations=["structural_preflight_only"],
    )
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    result = script["preflight"](tmp_path, "invalid")
    assert result["outcome"] == "failed"
    assert result["inventory_complete"] is True
    assert len(result["errors"][0]["causes"]) == 50
    assert result["errors"][0]["detail_complete"] is False
    assert result["complete"] is False
    manifest["version"] = True
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="unsupported portable contract profile"):
        script["preflight"](tmp_path, "invalid")
