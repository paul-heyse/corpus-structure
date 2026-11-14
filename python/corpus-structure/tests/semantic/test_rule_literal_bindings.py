"""Independent literal controls over the exact prepared rule-policy model."""

from dataclasses import replace

import pytest
import yaml

from corpus_structure.schema.rulelang import RuleError, RuleErrorCode
from corpus_structure.semantic.domain_operations import RULE_INPUT, ReleasedRulesPolicy
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import SourceArtifact


@pytest.mark.parametrize(
    "accepted,refused,nearest",
    [
        (
            "$all([b.bind != 'free' for b in claim.bindings])",
            "$all([b.bind != 'fre' for b in claim.bindings])",
            "free",
        ),
        (
            "'location' in $enums['stat:ParameterRole']",
            "'location' in $enums['stat:ParameterRol']",
            "stat:ParameterRole",
        ),
        ("'none' in $roles_by_kind['theorem']", "'none' in $roles_by_kind['theorm']", "theorem"),
        (
            "(claim.subject.identity&['stat:canonical_name'] ?? '') == 'mu'",
            "(claim.subject.identity&['stat:canonical_nam'] ?? '') == 'mu'",
            "stat:canonical_name",
        ),
    ],
)
def test_exact_bound_literals_compile_and_nearby_unknown_literals_refuse(
    statistics_rules_policy, accepted, refused, nearest
):
    statistics_rules_policy.language.compile("literal.accepted", accepted)
    with pytest.raises(RuleError) as caught:
        statistics_rules_policy.language.compile("literal.refused", refused)
    assert caught.value.codes == {RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY}
    assert all(problem.rule == "literal.refused" for problem in caught.value.problems)
    assert all(repr(nearest) in problem.message for problem in caught.value.problems)


def test_source_model_changes_determine_binding_and_identity_vocabularies(
    statistics_pack_inputs, statistics_rules_policy
):
    bundle, dependencies, profile, _ = statistics_pack_inputs
    sources = []
    for source in bundle.sources:
        document = yaml.safe_load(source.content)
        classes = document.get("classes", {})
        if "FreeBinding" in classes:
            classes["FreeBinding"]["attributes"]["kind"]["equals_string"] = "model_free"
        if "FamilyParameter" in classes:
            classes["FamilyParameter"].setdefault("attributes", {})["release_key"] = {
                "range": "string",
                "slot_uri": "stat:release_key",
            }
            classes["FamilyParameter"]["unique_keys"]["released"] = {
                "unique_key_slots": ["release_key"],
            }
        sources.append(SourceArtifact(source.name, yaml.safe_dump(document).encode()))
    artifacts = []
    for source in dependencies.artifacts:
        if source.name == RULE_INPUT:
            document = yaml.safe_load(source.content)
            for rule in document["guideline"]:
                rule["check"] = rule["check"].replace("'free'", "'model_free'")
            source = SourceArtifact(source.name, yaml.safe_dump(document).encode())
        artifacts.append(source)
    changed = prepare_release(
        replace(bundle, sources=tuple(sources)),
        replace(dependencies, artifacts=tuple(artifacts)),
        profile,
    )
    assert changed.release_id != statistics_rules_policy.release_id
    released = ReleasedRulesPolicy(changed)
    for expression in (
        "$all([b.bind != 'model_free' for b in claim.bindings])",
        "(claim.subject.identity&['stat:release_key'] ?? '') == 'v'",
    ):
        released.language.compile("changed.accepted", expression)
        with pytest.raises(RuleError) as caught:
            statistics_rules_policy.language.compile("original.refused", expression)
        assert caught.value.codes == {RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY}
    with pytest.raises(RuleError) as caught:
        released.language.compile(
            "changed.refused", "$all([b.bind != 'free' for b in claim.bindings])"
        )
    assert caught.value.codes == {RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY}
