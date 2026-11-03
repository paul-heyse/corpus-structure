"""Independent expectations for released subsets, projections and source attribution."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.domain_operations import CandidateContextIndex, _entity_mappings, _project_cut
from corpus_structure.semantic.identity import claim_source_item
from corpus_structure.semantic.refusals import SemanticOperationRefusal, SemanticReason, semantic_failure_fields
from corpus_structure.semantic.rule_views import project_rule_value
from corpus_structure.semantic.unicode_identity import identity_casefold

from .test_identity_resolution import release as identity_release, source
from .test_proposals import batch, frame, prepared


def test_source_subset_is_narrower_than_storage_and_generated_boundary():
    release = prepared()
    assert release.source_establishments() == {"stated", "agent_asserted"}
    assert release.enum_members("Establishment") == {"stated", "agent_asserted", "derived"}
    raw = batch()
    raw["claims"][0]["establishment"] = "derived"
    with pytest.raises(ValidationError):
        release.validate_python("AgentAuthoredBatch", raw)


def test_expression_projection_keeps_declared_enum_and_expression_form():
    release = prepared()
    expression = {"kind": "expression", "form": "formula", "language": "latex", "expression": "x = y"}
    view = project_rule_value(release, "Value", expression)
    assert (view.value_kind, view.declared_range, view.expression_form) == ("expression", "Value", "formula")
    assert view.defined_symbol == "x" and view.reading_status == "unavailable"
    enum = project_rule_value(release, "StatementRole", {"kind": "text", "text": "premise"})
    assert enum.enum_id == "StatementRole" and enum.v == "premise"
    assert enum.declared_range == "StatementRole"
    assert project_rule_value(release, "Value", {"kind": "missing", "reason": "unknown"}).reading_status == "missing"
    assert project_rule_value(release, "Value", None) is None


def test_candidate_indexes_preserve_global_premises_and_duplicate_symbol_owners():
    release = prepared()
    candidates = (
        SimpleNamespace(occurrence_id="a", statement="s", statement_role="premise", statement_kind="theorem"),
        SimpleNamespace(occurrence_id="b", statement="s", statement_role="premise", statement_kind="theorem"),
        SimpleNamespace(occurrence_id="g", statement="other", statement_role="premise", statement_kind="assumption"),
        SimpleNamespace(occurrence_id="x", statement="other", statement_role="conclusion", statement_kind="theorem"),
    )
    index = CandidateContextIndex.prepare(release, candidates, {"a": {"v", "self"}, "b": {"v"}})
    assert index.statement_premises(candidates[0]) == ("b", "g")
    assert index.statement_premises(candidates[3]) == ("g",)
    assert index.given_by_others("a") == ("v",)
    assert index.given_by_others("b") == ("self", "v")


def test_ambiguous_anchors_and_incomplete_keys_have_explicit_provisional_decisions():
    observed = source()
    observed["payload"]["identity_exclusions"] = []
    known = {key: {"class_iris": ("https://example.org/Person",), "label": "Alice", "fields": {}}
             for key in ("known:one", "known:two")}
    mappings, _, _, decisions = _entity_mappings(identity_release(), [observed], "out", known, {9: ({}, ())})
    assert all(row.basis == "global_label" and row.outcome == "ambiguous_anchor" for row in decisions)
    assert all(row.entity_id == mappings[9][row.local_id] for row in decisions)
    assert len(set(mappings[9].values())) == 3
    assert all('"known:one"' in row.candidates and '"known:two"' in row.candidates for row in decisions)
    incomplete = source()
    incomplete["payload"]["identity_exclusions"] = []
    _, _, _, decisions = _entity_mappings(identity_release(True), [incomplete], "out", {}, {9: ({}, ())})
    assert all(row.basis == "declared_key" and row.outcome == "incomplete_key" for row in decisions)


def test_each_attribute_keeps_own_qualification_and_support_without_claim_borrowing():
    from corpus_structure.semantic.proposals import locate_proposal

    release = prepared()
    raw = batch()
    raw["statements"] = []
    raw["claims"][0].pop("statement")
    raw["claims"][0].pop("statement_role")
    evidence = raw["claims"][0]["evidence"][0]
    raw["entities"][0]["attributes"] = [
        {"predicate": "https://example.org/name", "value": {"kind": "text", "text": "Alice"},
         "qualification": {"modality": "supposed", "polarity": False}, "establishment": "agent_asserted",
         "evidence": [dict(evidence), {**evidence, "role": "supporting"}]}
    ]
    located = locate_proposal(release, raw, frame())
    payload = located.stored.model_dump(mode="python", exclude_unset=True)
    observation = {"id": 9, "observation_key": "observation:attributes", "payload_definition": "AgentStoredBatch", "payload": payload}
    descriptor = {"math": {}, "content": {"macros": {}}, "text": frame().text,
                  "source_uri": "doc:test", "provider": "agent.test", "version": "7", "frame": frame(),
                  "rendition_id": 1, "rendition_key": "rendition:test", "page": None}
    job = {"id": 1, "project_id": "project:test", "release_id": release.release_id,
           "input_realization_id": "in", "input_revision": 0}
    cut = _project_cut(release, job, {"id": 1}, [observation], {9: descriptor}, [], [], "out", {}, {})
    attribute_occurrences = [row for row in cut.batch.occurrence if row.item.startswith("entities/")]
    assert len(attribute_occurrences) == 1  # no generated id or display-only label occurrence
    attribute = attribute_occurrences[0]
    support = [row for row in cut.batch.occurrence_evidence if row.occurrence_id == attribute.occurrence_id]
    claim = next(row for row in cut.batch.occurrence if row.item == "claims/0")
    claim_support = {row.evidence_id for row in cut.batch.occurrence_evidence if row.occurrence_id == claim.occurrence_id}
    assert len(support) == 2 and not claim_support.intersection(row.evidence_id for row in support)
    qual_roles = {row.role: row.child_value_id for row in cut.batch.value_role if row.parent_value_id == attribute.report_qualification_value_id}
    values = {row.value_id: row for row in cut.batch.typed_value}
    assert values[qual_roles["modality"]].text_value == "supposed"
    assert values[qual_roles["polarity"]].boolean_value is False
    establishment = next(row for row in cut.batch.occurrence_establishment if row.occurrence_id == attribute.occurrence_id)
    assert establishment.establishment == "agent_asserted"


def test_reason_identity_does_not_depend_on_human_wording():
    reason = SemanticReason("missing_operands", "scientific_policy", "release:test", ("occ:1",), detail="operand absent")
    first, second = (SemanticOperationRefusal(reason), SemanticOperationRefusal(replace(reason, detail="no operand")))
    assert first.reason == second.reason == "missing_operands"
    assert semantic_failure_fields(first)["semantic_reason"]["references"] == ("occ:1",)


@pytest.mark.parametrize("text,expected", [("Straße", "strasse"), ("Σςσ", "σσσ"), ("İIı", "i\u0307iı"), ("ﬃ", "ffi"), ("É", "é"), ("E\u0301", "e\u0301")])
def test_default_casefold_has_no_implicit_normalization(text, expected):
    assert identity_casefold(text) == expected


@pytest.mark.parametrize("value", ["a\0b", "\ud800"])
def test_identity_refuses_strings_outside_the_qualified_database_domain(value):
    with pytest.raises(SemanticOperationRefusal, match="unsupported interpretation"):
        identity_casefold(value)


def test_ordinary_addresses_keep_their_own_mechanical_abi():
    assert [claim_source_item(i) for i in (0, 9, 12)] == ["claims/0", "claims/9", "claims/12"]
    with pytest.raises(ValueError):
        claim_source_item(True)


def test_renamed_display_properties_follow_authored_order():
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release

    raw = b'''id: https://example.org/display
name: display
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types: {string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}}
classes:
  Thing:
    attributes:
      id: {identifier: true}
      caption: {annotations: {cs:role: display, cs:display_order: 2}}
      alternate_names: {multivalued: true, annotations: {cs:role: display, cs:display_order: 3}}
'''
    release = prepare_release(SourceBundle("display", (SourceArtifact("display", raw),)))
    assert [prop.name for prop in release.display_properties("Thing")] == ["caption", "alternate_names"]
    assert [prop.name for prop in release.display_properties("https://example.org/Thing")] == ["caption", "alternate_names"]


def test_ungrounded_identity_cycle_retains_explicit_dependencies():
    release = identity_release(True)
    definition = next(d for d in release.definitions if d.name == "Person")
    definition = replace(definition, properties=tuple(replace(p, range="Person") if p.name == "serial" else p for p in definition.properties))
    release = replace(release, definitions=tuple(definition if d.name == "Person" else d for d in release.definitions))
    observed = source(keyed=True)
    observed["payload"]["identity_exclusions"] = []
    for entity, target in zip(observed["payload"]["entities"], ("b", "c", "a"), strict=True):
        entity["attributes"][0]["value"] = {"kind": "entity", "target": target}
    mappings, _, _, decisions = _entity_mappings(release, [observed], "out", {}, {9: ({}, ())})
    assert len(set(mappings[9].values())) == 3
    assert all(row.basis == "declared_key" and row.outcome == "ungrounded_cycle" for row in decisions)
    assert {row.dependencies for row in decisions} == {'[[9,"a"]]', '[[9,"b"]]', '[[9,"c"]]'}


def test_unexpected_comparison_value_error_remains_a_failure(monkeypatch):
    import pyarrow as pa
    from corpus_structure.semantic import domain_operations as owner
    from corpus_structure.semantic import scientific_evidence

    release = prepared()
    definition = next(d for d in release.definitions if d.name == "Person")
    prop = next(p for p in definition.properties if p.name == "name")
    definition = replace(definition, properties=tuple(replace(p, constraint_scope="accepted_value") if p == prop else p for p in definition.properties))
    policy = object.__new__(owner.ReleasedRulesPolicy)
    policy.prepared = release
    policy.definitions = {"Person": definition}
    policy.metadata = {("Person", prop.iri): {"cs:role": "predicate"}}
    policy.comparison_projection = SimpleNamespace(partition=lambda *args: ({}, {}, {}))
    candidate = owner.ClaimCandidate("fact:a", "occ:a", "source", "a", "entity:p", "Person", prop.iri,
                                    "one", {}, "stated", None, None, None, (), 1, {})
    inputs = SimpleNamespace(candidates=(candidate, replace(candidate, fact_id="fact:b", occurrence_id="occ:b", object="two")),
                             batch=SimpleNamespace(occurrence=()))
    scope = SimpleNamespace(connection=SimpleNamespace(from_arrow=lambda table: table),
                            operation_disagreements=lambda relation: SimpleNamespace(to_arrow_table=lambda: pa.table({"key": pa.array([], type=pa.string())})))

    class BrokenComparator:
        def __init__(self, *args, **kwargs):
            pass

        def compare(self, *args, **kwargs):
            raise ValueError("programming defect injected")

    monkeypatch.setattr(scientific_evidence, "SemanticComparator", BrokenComparator)
    with pytest.raises(ValueError, match="programming defect injected"):
        policy.scientific_decisions(inputs, scope)
