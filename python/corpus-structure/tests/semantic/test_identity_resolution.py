"""Independent partitions and source identities for operational cannot-links."""

import pytest

from corpus_structure.semantic.domain_operations import IdentityResolutionConflict, _entity_mappings
from semantic.identity_resolution_support import release as release
from semantic.identity_resolution_support import source as source


def test_cannot_link_prevents_indirect_label_merge_and_preserves_unconstrained_ids():
    observed = source()
    mappings, _, _ = _entity_mappings(release(), [observed], "out", {}, {9: ({}, ())})
    assert mappings[9]["a"] == mappings[9]["b"]
    assert mappings[9]["a"] != mappings[9]["c"]
    observed["payload"]["identity_exclusions"] = []
    plain, _, _ = _entity_mappings(release(), [observed], "out", {}, {9: ({}, ())})
    assert len(set(plain[9].values())) == 1


def test_required_key_identity_refuses_exclusion_and_retains_structured_endpoints():
    with pytest.raises(IdentityResolutionConflict) as error:
        _entity_mappings(release(True), [source(keyed=True)], "out", {}, {9: ({}, ())})
    assert error.value.code == "identity_conflict"
    assert error.value.exclusion_id == "split"
    assert error.value.left == {"kind": "local", "target": "a"}
    assert error.value.right == {"kind": "local", "target": "c"}


def test_uncertain_exclusion_does_not_authorize_identity_constraint():
    mappings, _, _ = _entity_mappings(release(), [source(located=False)], "out", {}, {9: ({}, ())})
    assert len(set(mappings[9].values())) == 1


def test_known_entity_cannot_link_vetoes_label_match():
    observed = source()
    observed["payload"]["identity_exclusions"][0]["right"] = {
        "kind": "known",
        "target": "known:alice",
    }
    known = {
        "known:alice": {
            "class_iris": ("https://example.org/Person",),
            "label": "Alice",
            "fields": {},
        }
    }
    mappings, _, _ = _entity_mappings(release(), [observed], "out", known, {9: ({}, ())})
    assert mappings[9]["a"] != "known:alice"


def test_partition_is_independent_of_observation_arrival_and_database_ids():
    import copy

    first = source()
    second = copy.deepcopy(first)
    second["id"], second["observation_key"] = 15, "observation:other"
    left, _, _ = _entity_mappings(
        release(), [first, second], "out", {}, {9: ({}, ()), 15: ({}, ())}
    )
    right, _, _ = _entity_mappings(
        release(), [second, first], "out", {}, {9: ({}, ()), 15: ({}, ())}
    )
    assert left == right
    first["id"], second["id"] = 77, 44
    reassigned, _, _ = _entity_mappings(
        release(), [first, second], "out", {}, {77: ({}, ()), 44: ({}, ())}
    )
    assert reassigned[77] == left[9]
    assert reassigned[44] == left[15]


@pytest.mark.parametrize("recorded", ["current", "missing", "incompatible"])
def test_unicode_admission_reads_actual_release_manifest(monkeypatch, recorded):
    import json
    from dataclasses import replace
    from typing import cast

    from sqlalchemy import Connection

    from corpus_structure.semantic import unicode_identity
    from corpus_structure.semantic.refusals import SemanticOperationRefusal

    prepared = release()
    manifest = json.loads(prepared.manifest)
    if recorded == "missing":
        del manifest["libraries"]["unicode-identity"]
    elif recorded == "incompatible":
        manifest["libraries"]["unicode-identity"] = "other-recipe"
    prepared = replace(prepared, manifest=json.dumps(manifest).encode())
    connection = cast(Connection, object())
    checked = []
    monkeypatch.setattr(unicode_identity, "require_current_unicode_pair", checked.append)
    if recorded == "current":
        unicode_identity.require_unicode_identity_release(connection, prepared)
        assert checked == [connection]
    else:
        with pytest.raises(SemanticOperationRefusal):
            unicode_identity.require_unicode_identity_release(connection, prepared)
        assert checked == []
