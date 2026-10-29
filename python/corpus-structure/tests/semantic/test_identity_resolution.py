"""Independent partitions and source identities for operational cannot-links."""
from functools import cache
from pathlib import Path

import pytest
import yaml

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.domain_operations import IdentityResolutionConflict, _entity_mappings
from corpus_structure.semantic.proposals import proposal_inputs
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies


@cache
def release(keyed=False):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    person = {"is_a": "Entity", "annotations": {"cs:scope": "global"},
              "attributes": {"serial": {"range": "string"}}}
    if keyed:
        person["unique_keys"] = {"serial": {"unique_key_slots": ["serial"]}}
    domain = {"id": "https://example.org/identity", "name": "identity", "imports": ["core"],
              "prefixes": {"ex": "https://example.org/"}, "default_prefix": "ex",
              "classes": {"Person": person}}
    bundle = SourceBundle("domain", (SourceArtifact("core", core.read_bytes()),
        SourceArtifact("domain", yaml.safe_dump(domain).encode())))
    return prepare_release(proposal_inputs(bundle), composed_dependencies(ResolvedDependencies()),
                           PreparationProfile(version="semantic-2"))


def source(*, keyed=False, located=True):
    entities = [{"id": name, "class_iri": "https://example.org/Person", "label": "Alice",
                 "attributes": [{"predicate": "https://example.org/serial",
                                 "value": {"kind": "text", "text": "same"}}] if keyed else []}
                for name in ("a", "b", "c")]
    evidence = {"sentence": "s", "quote": "Two distinct people", "role": "primary",
                "placement": "exact", "outcome": "located" if located else "unlocated",
                "matches": 1, "picked": False, "locator": "doc#s", "start": 0, "end": 19}
    return {"id": 9, "observation_key": "observation:stable", "payload_definition": "AgentStoredBatch",
            "payload": {"unit_ref": "u", "entities": entities,
                        "identity_exclusions": [{"id": "split", "left": {"kind": "local", "target": "a"},
                            "right": {"kind": "local", "target": "c"}, "reason": "distinct",
                            "evidence": [evidence]}]}}


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
    observed["payload"]["identity_exclusions"][0]["right"] = {"kind": "known", "target": "known:alice"}
    known = {"known:alice": {"class_iris": ("https://example.org/Person",), "label": "Alice", "fields": {}}}
    mappings, _, _ = _entity_mappings(release(), [observed], "out", known, {9: ({}, ())})
    assert mappings[9]["a"] != "known:alice"
