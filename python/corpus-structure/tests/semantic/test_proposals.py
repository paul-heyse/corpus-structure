"""Rich agent proposals use release vocabulary and exact independently expected evidence."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.analysis_policies import prepare_placement_policy
from corpus_structure.semantic.proposals import (
    ProposalRefused,
    locate_proposal,
    proposal_inputs,
)
from semantic.proposals_support import batch as batch
from semantic.proposals_support import frame as frame
from semantic.proposals_support import prepared as prepared


def test_new_declared_class_property_and_located_evidence_need_no_extractor_code():
    release = prepared()
    result = locate_proposal(release, batch(), frame(), placement_policy=prepare_placement_policy())
    assert result.clean
    stored = result.stored.model_dump(mode="python")
    evidence = stored["claims"][0]["evidence"][0]
    assert (evidence["start"], evidence["end"], evidence["locator"], evidence["outcome"]) == (
        2,
        16,
        "page#sentence1",
        "located",
    )
    assert stored["entities"][0]["class_iri"] == "https://example.org/Person"
    assert "https://example.org/name" in str(release.json_schema("AgentAuthoredBatch"))
    assert stored["claims"][0]["qualification"] == {"modality": "asserted", "polarity": True}


def test_same_global_property_vocabulary_does_not_allow_wrong_subject_applicability():
    release = prepared()
    raw = batch()
    raw["claims"][0]["predicate"] = "https://example.org/serial"
    with pytest.raises(ProposalRefused, match="does not apply"):
        locate_proposal(release, raw, frame(), placement_policy=prepare_placement_policy())


def test_wrong_unit_unknown_property_and_invalid_object_refuse():
    release = prepared()
    raw = batch()
    raw["unit_ref"] = "other"
    with pytest.raises(ProposalRefused, match="unit"):
        locate_proposal(release, raw, frame(), placement_policy=prepare_placement_policy())
    raw = batch()
    raw["claims"][0]["predicate"] = "https://example.org/invented"
    with pytest.raises(ValidationError):
        locate_proposal(release, raw, frame(), placement_policy=prepare_placement_policy())
    raw = batch()
    raw["claims"][0]["object"] = {"kind": "number", "number": 12}
    with pytest.raises(ProposalRefused, match="boundary"):
        locate_proposal(release, raw, frame(), placement_policy=prepare_placement_policy())


def test_unlocated_reports_are_retained_with_explicit_issue_and_no_false_evidence():
    raw = batch()
    raw["claims"][0]["evidence"][0]["quote"] = "Something wholly unrelated happened elsewhere"
    result = locate_proposal(prepared(), raw, frame(), placement_policy=prepare_placement_policy())
    assert not result.clean
    assert result.issues[0].code == "unlocated"
    evidence = result.stored.model_dump(mode="python")["claims"][0]["evidence"][0]
    assert evidence["outcome"] == "unlocated"
    assert "start" not in evidence and "end" not in evidence


def test_alternatives_unsupported_and_declared_unresolved_endpoints_survive_location():
    release = prepared()
    raw = batch()
    raw["claims"].append(
        {**raw["claims"][0], "id": "c2", "object": {"kind": "text", "text": "Alicia"}}
    )
    raw["alternatives"] = [
        {
            "id": "a",
            "members": ["c1", "c2"],
            "faithful": True,
            "reason": "Source gives both spellings",
        }
    ]
    raw["unsupported"] = [
        {
            "id": "u",
            "kind": "unsupported_relation",
            "text": "Alice is here.",
            "reason": "No admitted relation",
            "evidence": raw["claims"][0]["evidence"],
        }
    ]
    raw["entities"].append(
        {
            "id": "external",
            "class_iri": "https://example.org/Person",
            "reference": {"source_uri": "other", "description": "unresolved named person"},
        }
    )
    located = locate_proposal(release, raw, frame(), placement_policy=prepare_placement_policy())
    stored = located.stored.model_dump(mode="python")
    assert stored["alternatives"][0]["members"] == ("c1", "c2")
    assert len(stored["claims"]) == 2
    assert stored["unsupported"][0]["reason"] == "No admitted relation"
    assert stored["unsupported"][0]["evidence"][0]["start"] == 2
    assert stored["entities"][1]["reference"]["description"] == "unresolved named person"
    raw["alternatives"][0]["members"] = ["c1", "missing"]
    with pytest.raises(ProposalRefused, match="undeclared claim"):
        locate_proposal(release, raw, frame(), placement_policy=prepare_placement_policy())


def test_packet_pins_release_schema_configuration_and_guideline():
    from corpus_structure.semantic.proposals import proposal_packet

    release = prepared()
    packet = proposal_packet(
        release,
        frame(),
        guideline="Extract only source assertions.",
        configuration={"model": "declared-agent", "mode": "extract"},
    )
    assert (
        packet.hash
        == proposal_packet(
            release,
            frame(),
            guideline="Extract only source assertions.",
            configuration={"model": "declared-agent", "mode": "extract"},
        ).hash
    )
    assert (
        packet.hash
        != proposal_packet(
            release,
            frame(),
            guideline="Changed interpretation.",
            configuration={"model": "declared-agent", "mode": "extract"},
        ).hash
    )


def test_unit_packet_cap_splits_without_losing_source_text():
    from corpus_structure.semantic.proposals import proposal_packet

    release = prepared()
    packet = proposal_packet(
        release, frame(), guideline="Rules", configuration={"packet_cap_chars": 20}
    )
    unit = next(part for part in packet.parts() if part.name == "unit")
    pages = packet.part_pages(unit)
    assert len(pages) > 1 and all(len(page) <= 20 for page in pages)
    assert "".join(pages) == unit.text


def test_binary_entity_relation_preserves_declared_unresolved_endpoint():
    raw = batch()
    raw["entities"].append(
        {
            "id": "q",
            "class_iri": "https://example.org/Person",
            "reference": {"description": "Named but unresolved in this corpus"},
        }
    )
    raw["claims"][0]["predicate"] = "https://example.org/friend"
    raw["claims"][0]["object"] = {"kind": "entity", "target": "q"}
    result = locate_proposal(prepared(), raw, frame(), placement_policy=prepare_placement_policy())
    assert result.stored.model_dump()["claims"][0]["object"] == {"kind": "entity", "target": "q"}
    raw["claims"][0]["object"]["target"] = "undeclared"
    with pytest.raises(ProposalRefused, match="membership"):
        locate_proposal(prepared(), raw, frame(), placement_policy=prepare_placement_policy())


def test_model_facing_entity_choices_exclude_abstract_classes():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    domain = {
        "id": "https://example.org/x",
        "name": "x",
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "imports": ["core"],
        "classes": {
            "AbstractPerson": {"is_a": "Entity", "abstract": True, "attributes": {"name": {}}},
            "Person": {"is_a": "AbstractPerson"},
        },
    }
    release = prepare_release(
        proposal_inputs(
            SourceBundle(
                "x",
                (
                    SourceArtifact("core", core.read_bytes()),
                    SourceArtifact("x", yaml.safe_dump(domain).encode()),
                ),
            )
        )
    )
    assert "https://example.org/AbstractPerson" not in release.enum_members("AgentClassIRI")
    assert "https://example.org/Person" in release.enum_members("AgentClassIRI")


def test_boundary_source_creation_does_not_generate_full_graph_artifacts(monkeypatch):
    import corpus_structure.semantic.ontology as ontology

    def unexpected(*args, **kwargs):
        raise AssertionError("boundary source creation must not materialize unused OWL/SHACL")

    monkeypatch.setattr(ontology, "build_graph_artifacts", unexpected)
    path = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    source = SourceBundle("core", (SourceArtifact("core", path.read_bytes()),))
    result = proposal_inputs(source)
    agent = next(item for item in result.sources if item.name == "agent")
    vocabulary = yaml.safe_load(agent.content)["enums"]["AgentClassIRI"]["permissible_values"]
    assert "https://corpus-structure.dev/semantic/Entity" in vocabulary


def test_identity_exclusions_locate_and_bind_endpoints():
    from corpus_structure.methods.llm.cascade import PlacementPolicy

    release = prepared()
    proposal = batch()
    proposal["entities"].append({"id": "q", "class_iri": "https://example.org/Person"})
    proposal["identity_exclusions"] = [
        {
            "id": "different",
            "left": {"kind": "local", "target": "p"},
            "right": {"kind": "local", "target": "q"},
            "reason": "distinct source people",
            "evidence": [{"sentence": "s1", "quote": "Alice is here.", "role": "primary"}],
        }
    ]
    result = locate_proposal(release, proposal, frame(), placement_policy=PlacementPolicy())
    assert result.clean
    assert (
        result.stored.model_dump()["identity_exclusions"][0]["evidence"][0]["outcome"] == "located"
    )
    proposal["identity_exclusions"][0]["right"]["target"] = "missing"
    with pytest.raises(ProposalRefused, match="outside the bound packet"):
        locate_proposal(release, proposal, frame(), placement_policy=PlacementPolicy())


def test_identity_exclusions_use_actual_declared_schema_and_source_endpoints_without_execution_catalog():
    import json

    from corpus_structure.methods.llm.cascade import PlacementPolicy
    from corpus_structure.semantic.proposals import proposal_packet

    release = prepared()
    packet = proposal_packet(release, frame(), guideline="test", configuration={})
    assert "identity_exclusions" in json.loads(packet.schema)["properties"]
    proposal = batch()
    proposal["entities"].append({"id": "q", "class_iri": "https://example.org/Person"})
    proposal["identity_exclusions"] = [
        {
            "id": "different",
            "left": {"kind": "local", "target": "p"},
            "right": {"kind": "local", "target": "q"},
            "reason": "distinct",
            "evidence": [{"sentence": "s1", "quote": "Alice is here.", "role": "primary"}],
        }
    ]
    assert locate_proposal(release, proposal, frame(), placement_policy=PlacementPolicy()).clean
    proposal["identity_exclusions"][0]["right"]["target"] = "outside"
    with pytest.raises(ProposalRefused, match="outside the bound packet"):
        locate_proposal(release, proposal, frame(), placement_policy=PlacementPolicy())
