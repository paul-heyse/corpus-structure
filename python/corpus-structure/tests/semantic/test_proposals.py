"""Rich agent proposals use release vocabulary and exact independently expected evidence."""

from functools import cache
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError
from sqlalchemy import create_engine

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.proposals import (
    ProposalFrame,
    ProposalRefused,
    ProposalSentence,
    locate_proposal,
    proposal_inputs,
)


@cache
def prepared(*, composed=False):
    path = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    domain = {
        "id": "https://example.org/domain",
        "name": "domain",
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "imports": ["core"],
        "classes": {
            "Person": {
                "is_a": "Entity",
                "attributes": {"name": {"range": "string"}, "friend": {"range": "Person"}},
            },
            "Machine": {"is_a": "Entity", "attributes": {"serial": {"range": "string"}}},
        },
    }
    source = SourceBundle(
        "domain",
        (
            SourceArtifact("core", path.read_bytes()),
            SourceArtifact("domain", yaml.safe_dump(domain).encode()),
        ),
    )
    if composed:
        from corpus_structure.semantic.composed import composed_dependencies
        from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

        return prepare_release(
            proposal_inputs(source),
            composed_dependencies(ResolvedDependencies()),
            PreparationProfile(version="semantic-2"),
        )
    return prepare_release(proposal_inputs(source))


def batch() -> dict[str, Any]:
    return {
        "unit_ref": "page#one",
        "entities": [{"id": "p", "class_iri": "https://example.org/Person", "label": "Alice"}],
        "statements": [{"id": "s", "kind": "narrative", "anchor": "page#one"}],
        "claims": [
            {
                "id": "c1",
                "subject": "p",
                "predicate": "https://example.org/name",
                "object": {"kind": "text", "text": "Alice"},
                "qualification": {"modality": "asserted", "polarity": True},
                "establishment": "stated",
                "statement": "s",
                "statement_role": "conclusion",
                "evidence": [{"sentence": "s1", "quote": "Alice is here.", "role": "primary"}],
            }
        ],
        "alternatives": [],
        "unsupported": [],
    }


def frame():
    return ProposalFrame(
        "page#one", "😀 Alice is here.", (ProposalSentence("s1", "page#sentence1", 2, 16),)
    )


def test_new_declared_class_property_and_located_evidence_need_no_extractor_code():
    release = prepared()
    result = locate_proposal(release, batch(), frame())
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
        locate_proposal(release, raw, frame())


def test_wrong_unit_unknown_property_and_invalid_object_refuse():
    release = prepared()
    raw = batch()
    raw["unit_ref"] = "other"
    with pytest.raises(ProposalRefused, match="unit"):
        locate_proposal(release, raw, frame())
    raw = batch()
    raw["claims"][0]["predicate"] = "https://example.org/invented"
    with pytest.raises(ValidationError):
        locate_proposal(release, raw, frame())
    raw = batch()
    raw["claims"][0]["object"] = {"kind": "number", "number": 12}
    with pytest.raises(ProposalRefused, match="boundary"):
        locate_proposal(release, raw, frame())


def test_unlocated_reports_are_retained_with_explicit_issue_and_no_false_evidence():
    raw = batch()
    raw["claims"][0]["evidence"][0]["quote"] = "Something wholly unrelated happened elsewhere"
    result = locate_proposal(prepared(), raw, frame())
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
    located = locate_proposal(release, raw, frame())
    stored = located.stored.model_dump(mode="python")
    assert stored["alternatives"][0]["members"] == ("c1", "c2")
    assert len(stored["claims"]) == 2
    assert stored["unsupported"][0]["reason"] == "No admitted relation"
    assert stored["unsupported"][0]["evidence"][0]["start"] == 2
    assert stored["entities"][1]["reference"]["description"] == "unresolved named person"
    raw["alternatives"][0]["members"] = ["c1", "missing"]
    with pytest.raises(ProposalRefused, match="undeclared claim"):
        locate_proposal(release, raw, frame())


def test_served_packet_pins_release_schema_configuration_and_complete_part_reading():
    from corpus_structure.intervene.semantic import ProposalSession
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
    session = ProposalSession(release, packet, 1, 1, "agent:test")
    with pytest.raises(ProposalRefused, match="read every"):
        session.check(batch(), packet_hash=packet.hash, schema_hash=packet.schema_hash)
    for part in session.manifest()["parts"]:
        for page in range(1, part["pages"] + 1):
            assert isinstance(session.read(part["name"], page), str)
    checked = session.check(batch(), packet_hash=packet.hash, schema_hash=packet.schema_hash)
    assert checked.clean
    with pytest.raises(ProposalRefused, match="packet/schema"):
        session.check(batch(), packet_hash="stale", schema_hash=packet.schema_hash)
    with (
        create_engine("sqlite://").connect() as conn,
        pytest.raises(ProposalRefused, match="served session"),
    ):
        session.commit(conn, locate_proposal(release, batch(), frame()))


def test_unit_packet_cap_splits_without_losing_source_text_and_requires_every_page():
    from corpus_structure.intervene.semantic import ProposalSession
    from corpus_structure.semantic.proposals import proposal_packet

    release = prepared()
    packet = proposal_packet(
        release, frame(), guideline="Rules", configuration={"packet_cap_chars": 20}
    )
    unit = next(part for part in packet.parts() if part.name == "unit")
    pages = packet.part_pages(unit)
    assert len(pages) > 1 and all(len(page) <= 20 for page in pages)
    assert "".join(pages) == unit.text
    session = ProposalSession(release, packet, 1, 1, "agent:test")
    for part in packet.parts():
        for page in range(1, len(packet.part_pages(part)) + 1):
            if part.name != "unit" or page == 1:
                session.read(part.name, page)
    with pytest.raises(ProposalRefused, match="read every"):
        session.check(batch(), packet_hash=packet.hash, schema_hash=packet.schema_hash)
    for page in range(2, len(pages) + 1):
        session.read("unit", page)
    assert session.check(batch(), packet_hash=packet.hash, schema_hash=packet.schema_hash).clean


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
    result = locate_proposal(prepared(), raw, frame())
    assert result.stored.model_dump()["claims"][0]["object"] == {"kind": "entity", "target": "q"}
    raw["claims"][0]["object"]["target"] = "undeclared"
    with pytest.raises(ProposalRefused, match="membership"):
        locate_proposal(prepared(), raw, frame())


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
    release = prepared(composed=True)
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
    result = locate_proposal(release, proposal, frame())
    assert result.clean
    assert (
        result.stored.model_dump()["identity_exclusions"][0]["evidence"][0]["outcome"] == "located"
    )
    proposal["identity_exclusions"][0]["right"]["target"] = "missing"
    with pytest.raises(ProposalRefused, match="outside the bound packet"):
        locate_proposal(release, proposal, frame())


def test_identity_exclusions_require_composed_profile():
    import json

    from corpus_structure.semantic.proposals import proposal_packet

    packet = proposal_packet(prepared(), frame(), guideline="test", configuration={})
    assert "identity_exclusions" not in json.loads(packet.schema)["properties"]
    composed_packet = proposal_packet(
        prepared(composed=True), frame(), guideline="test", configuration={}
    )
    assert "identity_exclusions" in json.loads(composed_packet.schema)["properties"]
    proposal = batch()
    proposal["identity_exclusions"] = [
        {
            "id": "different",
            "left": {"kind": "local", "target": "p"},
            "right": {"kind": "known", "target": "known:other"},
            "reason": "distinct",
            "evidence": [{"sentence": "s1", "quote": "Alice is here.", "role": "primary"}],
        }
    ]
    with pytest.raises(ProposalRefused, match="semantic-2"):
        locate_proposal(prepared(), proposal, frame())
