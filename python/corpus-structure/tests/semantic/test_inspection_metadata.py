from __future__ import annotations

import json
from dataclasses import replace

import pytest
import yaml

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.inspection_metadata import ARTIFACT, get_inspection
from corpus_structure.semantic.types import PreparationError, PreparedArtifact


def source_bundle():
    base = {
        "id": "https://example.org/base",
        "name": "base",
        "prefixes": {"b": "https://example.org/base/"},
        "default_prefix": "b",
        "default_range": "TextCode",
        "types": {
            "TextCode": {"base": "str", "uri": "xsd:string", "pattern": "^[A-Z]"},
            "Number": {"base": "int", "uri": "xsd:integer"},
        },
        "slots": {
            "code": {"required": True, "pattern": "Z$", "description": "reused description"},
            "amount": {"range": "Number", "minimum_value": 1},
        },
        "classes": {
            "Base": {"slots": ["code", "amount"]},
            "Refinement": {"slot_usage": {"amount": {"maximum_value": 20}}},
        },
    }
    derived = {
        "id": "https://example.org/derived",
        "name": "derived",
        "imports": ["base"],
        "prefixes": {"d": "https://example.org/derived/"},
        "default_prefix": "d",
        "classes": {
            "Derived": {
                "is_a": "Base",
                "mixins": ["Refinement"],
                "slot_usage": {
                    "code": {
                        "alias": "token",
                        "description": "local description",
                        "aliases": ["display code"],
                    },
                    "amount": {"minimum_value": 5},
                },
            }
        },
    }
    return SourceBundle(
        "derived",
        tuple(
            SourceArtifact(name, yaml.safe_dump(body).encode())
            for name, body in [("base", base), ("derived", derived)]
        ),
    )


def product(prepared):
    return next(a for a in prepared.artifacts if a.kind == ARTIFACT)


def test_source_identity_effective_constraints_and_contributors():
    bundle = source_bundle()
    release = prepare_release(bundle)
    detail = get_inspection(release)
    assert detail["status"] == "available"
    code = detail["classes"]["Derived"]["properties"]["code"]
    assert code["metadata"]["description"] == "local description"
    assert code["metadata"]["aliases"] == ("display code",)
    contributions = {(x["module"], x["path"]): x for x in code["contributors"]}
    assert contributions["base", "slots/code"]["declaration"]["required"] is True
    assert (
        contributions["derived", "classes/Derived/slot_usage/code"]["declaration"]["alias"]
        == "token"
    )
    assert contributions["base", "types/TextCode"]["declaration"]["pattern"] == "^[A-Z]"
    assert contributions["base", "slots/code"]["source_digest"] == bundle.sources[0].digest
    assert code["attribution"] == "known_contributors"
    definition = next(d for d in release.definitions if d.name == "Derived")
    prop = next(p for p in definition.properties if p.name == "code")
    assert prop.iri == "https://example.org/base/code"
    assert prop.required and set(prop.patterns) == {"Z$", "^[A-Z]"}
    amount = next(p for p in definition.properties if p.name == "amount")
    assert amount.minimum == "5" and amount.maximum == "20"
    release.validate_json("Derived", '{"token":"AZ","amount":5}')


def test_product_is_deterministic_and_changed_declaration_changes_detail():
    bundle = source_bundle()
    first = product(prepare_release(bundle))
    assert (
        first.content == product(prepare_release(SourceBundle(bundle.root, bundle.sources))).content
    )
    changed = bundle.sources[1].content.replace(b"local description", b"changed description")
    assert (
        first.content
        != product(
            prepare_release(
                SourceBundle(bundle.root, (bundle.sources[0], SourceArtifact("derived", changed)))
            )
        ).content
    )


def test_missing_and_invalid_detail_does_not_reprepare_or_remove_effective_facts():
    prepared = prepare_release(source_bundle())
    absent = tuple(a for a in prepared.artifacts if a.kind != ARTIFACT)
    current_missing = replace(prepared, artifacts=absent)
    assert get_inspection(current_missing)["status"] == "corrupt"
    manifest = json.loads(prepared.manifest)
    manifest["profile"]["compiler_version"] = "19"
    older = replace(prepared, manifest=json.dumps(manifest).encode(), artifacts=absent)
    assert get_inspection(older)["status"] == "unavailable"
    assert older.definitions == prepared.definitions
    for payload, expected in [
        (b"{", "corrupt"),
        (b'{"version":3}', "unsupported"),
        (b'{"version":1,"sources":{},"classes":{}}', "corrupt"),
    ]:
        release = replace(prepared, artifacts=(*absent, PreparedArtifact(ARTIFACT, payload)))
        assert get_inspection(release)["status"] == expected


def test_named_type_numeric_bounds_remain_outside_the_supported_profile():
    bundle = source_bundle()
    body = yaml.safe_load(bundle.sources[0].content)
    body["types"]["Number"]["minimum_value"] = 1
    changed = SourceBundle(
        bundle.root, (SourceArtifact("base", yaml.safe_dump(body).encode()), bundle.sources[1])
    )
    with pytest.raises(PreparationError, match="minimum_value"):
        prepare_release(changed)


def test_archive_product_round_trip_and_cached_detail_is_immutable():
    from corpus_structure.semantic.archive_reader import reconstruct_release
    from corpus_structure.semantic.releases import _products
    from corpus_structure.semantic.types import PreparationProfile

    bundle = source_bundle()
    prepared = prepare_release(bundle)
    opened = reconstruct_release(
        _products(prepared), prepared.manifest, bundle, PreparationProfile(), prepared.artifacts
    )
    assert product(opened).content == product(prepared).content
    assert get_inspection(opened) == get_inspection(prepared)
    assert get_inspection(opened) is get_inspection(opened)
    with pytest.raises(TypeError):
        get_inspection(opened)["classes"]["Derived"]["metadata"]["description"] = "mutated"


def test_presence_normalization_and_unsupported_defaults():
    body: dict = {
        "id": "https://example.org/presence",
        "name": "presence",
        "types": {"string": {"base": "str", "uri": "xsd:string"}},
        "classes": {
            "Thing": {
                "attributes": {
                    "id": {"identifier": True},
                    "note": {"required": False, "description": None, "aliases": []},
                }
            }
        },
    }
    bundle = SourceBundle("presence", (SourceArtifact("presence", yaml.safe_dump(body).encode()),))
    detail = get_inspection(prepare_release(bundle))["classes"]["Thing"]["properties"]
    local = next(
        item["declaration"] for item in detail["note"]["contributors"] if item["role"] == "local"
    )
    assert local["required"] is False and local["description"] is None and local["aliases"] == ()
    assert "value_presence" not in local
    assert "identifier_implies_required" in detail["id"]["normalizations"]
    body["classes"]["Thing"]["attributes"]["note"]["ifabsent"] = "string(default)"
    with pytest.raises(PreparationError, match="ifabsent"):
        prepare_release(
            SourceBundle("presence", (SourceArtifact("presence", yaml.safe_dump(body).encode()),))
        )


def test_local_attribute_marks_unused_reusable_slot_as_shadowed():
    bundle = source_bundle()
    body = yaml.safe_load(bundle.sources[1].content)
    body["classes"]["Derived"]["attributes"] = {
        "code": {"range": "TextCode", "description": "attribute"}
    }
    prepared = prepare_release(
        SourceBundle(
            bundle.root,
            (bundle.sources[0], SourceArtifact("derived", yaml.safe_dump(body).encode())),
        )
    )
    detail = get_inspection(prepared)["classes"]["Derived"]["properties"]["code"]
    global_slot = next(item for item in detail["contributors"] if item["path"] == "slots/code")
    assert global_slot["role"] == "shadowed_declaration"


def test_enum_locators_and_v1_class_detail_remain_available():
    import json
    from dataclasses import replace

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.types import PreparedArtifact

    prepared = prepare_release(source_bundle())
    artifact = next(a for a in prepared.artifacts if a.kind == ARTIFACT)
    body = json.loads(artifact.content)
    assert body["version"] == 2
    assert get_inspection(prepared)["enum_detail_status"] == "available"
    body.pop("enums")
    body["version"] = 1
    old = replace(
        prepared,
        artifacts=tuple(
            PreparedArtifact(a.kind, canonical_bytes(body)) if a.kind == ARTIFACT else a
            for a in prepared.artifacts
        ),
    )
    assert get_inspection(old)["status"] == "available"
    assert get_inspection(old)["enum_detail_status"] == "unavailable"


def test_enum_member_locator_retains_exact_source_path_and_meaning():
    source = SourceArtifact(
        "terms",
        b"""id: https://example.org/terms
name: terms
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types: {string: {base: str, uri: 'xsd:string'}}
enums:
  Category:
    permissible_values:
      first: {meaning: 'ex:First', description: selected concept}
classes:
  Thing:
    attributes:
      category: {range: Category}
""",
    )
    detail = get_inspection(prepare_release(SourceBundle("terms", (source,))))
    records = detail["enums"]["Category"]["contributors"]
    member = next(r for r in records if r["path"] == "enums/Category/permissible_values/first")
    assert member["module"] == "terms" and member["source_digest"] == source.digest
    assert member["declaration"]["meaning"] == "ex:First"


def test_invalid_enum_contributor_scalar_is_corrupt():
    prepared = prepare_release(source_bundle())
    artifact = next(a for a in prepared.artifacts if a.kind == ARTIFACT)
    body = json.loads(artifact.content)
    # Supply an existing enum universe independently when the fixture has no enum.
    if not body["enums"]:
        from corpus_structure.semantic.types import VocabularySnapshot

        prepared = replace(prepared, vocabularies=(VocabularySnapshot("Example", (), "test"),))
        body["enums"] = {"Example": {"contributors": []}}
    enum = next(iter(body["enums"]))
    module = next(iter(body["sources"]))
    body["enums"][enum]["contributors"] = [
        dict(
            module=module,
            path=[],
            source_digest=body["sources"][module]["source_digest"],
            role="enum_declaration",
            declaration={},
        )
    ]
    corrupt = replace(
        prepared,
        artifacts=tuple(
            PreparedArtifact(a.kind, canonical_bytes(body)) if a.kind == ARTIFACT else a
            for a in prepared.artifacts
        ),
    )
    assert get_inspection(corrupt)["status"] == "corrupt"
