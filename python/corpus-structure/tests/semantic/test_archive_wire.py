"""Independent archive-3 direction, presence and wire-location expectations."""

from copy import deepcopy
from typing import Any

import pytest

from corpus_structure.semantic.archive_wire import decode_products
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.releases import ArchiveDecodeError, _products
from corpus_structure.semantic.types import Diagnostic, PreparedRelease, RegistryRow


def prepared():
    return PreparedRelease(
        release_id="release:test",
        manifest=b"{}",
        definitions=(),
        vocabularies=(),
        registry_rows=(RegistryRow("kind", "name", b"\x00\xff"),),
        queries=(),
        artifacts=(),
        required_capabilities=("native",),
        diagnostics=(Diagnostic("bad", "field", "invalid field"),),
        _adapters=(),
    )


def wire() -> dict[str, Any]:
    return {
        "release_id": "release:test",
        "definitions": [],
        "vocabularies": [],
        "registry_rows": [{"kind": "kind", "name": "name", "body_hex": "00ff"}],
        "queries": [],
        "artifacts": [],
        "required_capabilities": ["native"],
        "diagnostics": [
            {"code": "bad", "location": "field", "message": "invalid field", "outcome": "invalid"}
        ],
    }


def test_writer_preserves_independently_specified_archive3_bytes_and_omissions():
    assert canonical_bytes(_products(prepared())) == canonical_bytes(wire())
    decoded = decode_products(wire())
    assert decoded.registry_rows[0].semantic_row() == RegistryRow("kind", "name", b"\x00\xff")
    assert decoded.execution_model_id is None
    assert decoded.diagnostics == (Diagnostic("bad", "field", "invalid field"),)


@pytest.mark.parametrize(
    "change,location",
    [
        (lambda p: p.update(release_id=True), "release_id"),
        (lambda p: p.pop("queries"), "queries"),
        (lambda p: p.update(extra=1), "products"),
        (lambda p: p.update(registry_rows="oops"), "registry_rows"),
        (lambda p: p.update(registry_rows={}), "registry_rows"),
        (lambda p: p["registry_rows"][0].update(body_hex="not hex"), "registry_rows[0].body_hex"),
        (lambda p: p["registry_rows"][0].update(body_hex=3), "registry_rows[0].body_hex"),
        (lambda p: p["registry_rows"].append([]), "registry_rows[1]"),
    ],
)
def test_wire_failures_keep_typed_locations_and_original_cause(change, location):
    payload = deepcopy(wire())
    change(payload)
    with pytest.raises(ArchiveDecodeError) as failure:
        decode_products(payload)
    assert location in str(failure.value)
    assert failure.value.__cause__ is not None
    assert failure.value.diagnostics


def test_root_shape_and_direct_hex_compatibility():
    with pytest.raises(ArchiveDecodeError, match="products"):
        decode_products([])
    payload = wire()
    payload["registry_rows"][0]["body_hex"] = "00 FF\n"
    payload["required_capabilities"] = ("native",)
    assert decode_products(payload).registry_rows[0].body_hex == b"\x00\xff"


def test_archive_error_projects_locations_through_existing_report():
    from corpus_structure.semantic.operation_reporting import validation_failure_report

    with pytest.raises(ArchiveDecodeError) as failure:
        decode_products(dict(wire(), release_id=False))
    report = validation_failure_report(failure.value).model_dump(mode="json")
    assert report["observations"][0]["model_path"] == "products.release_id"


@pytest.mark.parametrize("corruption", ["descriptor", "content", "missing", "digest"])
def test_authenticated_parts_check_artifact_identity_closure(corruption):
    import json
    from hashlib import sha256

    from corpus_structure.semantic.archive_reader import open_release_parts
    from corpus_structure.semantic.inspection_capsule import make_capsule
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import (
        PreparationProfile,
        ResolvedDependencies,
        SourceArtifact,
        SourceBundle,
    )

    bundle = SourceBundle(
        "wire",
        (
            SourceArtifact(
                "wire",
                b"""id: https://example.org/wire
name: wire
types:
  string: {base: str, uri: xsd:string}
classes:
  Thing:
    attributes:
      id: {identifier: true}
""",
            ),
        ),
    )
    release = prepare_release(bundle)
    capsule = json.loads(
        make_capsule(bundle, ResolvedDependencies(), PreparationProfile(), release)
    )
    row = capsule["release"]
    archive = json.loads(bytes.fromhex(row["prepared_bytes"]))
    if corruption == "descriptor":
        archive["products"]["artifacts"].append(deepcopy(archive["products"]["artifacts"][0]))
    elif corruption == "content":
        capsule["artifacts"].append(deepcopy(capsule["artifacts"][0]))
    elif corruption == "missing":
        capsule["artifacts"].pop()
    else:
        archive["products"]["artifacts"][0]["digest"] = "bad"
    row["prepared_bytes"] = canonical_bytes(archive)
    row["manifest_bytes"] = bytes.fromhex(row["manifest_bytes"])
    row["content_digest"] = sha256(row["prepared_bytes"]).hexdigest()

    def rows(values):
        return [dict(v, content=bytes.fromhex(v["content"])) for v in values]

    from corpus_structure.semantic.releases import ReleaseConflict

    with pytest.raises((ReleaseConflict, ValueError), match=r"artifacts|artifact digest"):
        open_release_parts(
            release.release_id, row, rows(capsule["inputs"]), rows(capsule["artifacts"])
        )


def test_fixed_tuple_hooks_preserve_arity_and_each_declared_element_type():
    from corpus_structure.semantic.archive_wire import _decode

    assert _decode(["name", 2], tuple[str, int], "pair") == ("name", 2)
    for value in (["name"], ["name", 2, 3], ["name", True], "name", {}):
        with pytest.raises(ArchiveDecodeError):
            _decode(value, tuple[str, int], "pair")
