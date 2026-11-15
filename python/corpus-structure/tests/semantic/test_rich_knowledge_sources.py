"""Current rich preparation consumes explicit inputs without execution-catalog acquisition."""

from pathlib import Path

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.math_context import acquire_analysis_context_profile
from corpus_structure.semantic.rich_knowledge_sources import (
    RICH_CONTRACT_INPUT,
    RULE_INPUT,
    rich_knowledge_declarations,
    rich_knowledge_inputs,
    rich_knowledge_schema_inputs,
    rich_policy_inputs,
)
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.record_contracts_support import release_inputs


def test_actual_rich_composition_captures_schema_policy_and_nominal_members_without_legacy_catalog(
    monkeypatch,
):
    def refuse(*args, **kwargs):
        raise AssertionError("current rich composition must not acquire an execution catalog")

    monkeypatch.setattr("corpus_structure.semantic.contracts.compile_execution_model", refuse)
    monkeypatch.setattr("corpus_structure.semantic.contracts.bound_execution_model", refuse)
    root = Path(__file__).resolve().parents[4]
    bundle, deps = rich_knowledge_inputs(
        release_inputs()[0],
        ResolvedDependencies(),
        domain_rules=(root / "domains/statistics/schema/rules.yaml").read_bytes(),
        core_rules=(root / "domains/core/schema/rules.yaml").read_bytes(),
        context_profile=acquire_analysis_context_profile(),
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    assert {
        "data_operation_rich_proposals",
        "source-readings",
        "data_operation_reading_resolution",
        "data_operation_candidate_inspection",
    } <= {source.name for source in bundle.sources}
    assert {RULE_INPUT, RICH_CONTRACT_INPUT, "operation/scientific-policy.json"} <= {
        source.name for source in deps.artifacts
    }
    model = compile_data_operations(bundle, declarations=rich_knowledge_declarations(deps))
    prefix = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"
    assert set(derive_member_kinds(model, prefix + "DdoRichConsolidation")) == {
        prefix + name
        for name in (
            "DdoRichScalarValue",
            "DdoRichEntityValue",
            "DdoRichRecordValue",
            "DdoRichCollectionValue",
            "DdoRichCasefoldText",
            "DdoRichQualificationMeaning",
            "DdoRichEntity",
            "DdoRichFact",
            "DdoRichOccurrence",
            "DdoRichSourceReadingAssertion",
            "DdoRichAlternative",
            "DdoRichAssessment",
            "DdoRichDiagnostic",
            "DdoRichIdentityResolution",
            "DdoRichIdentityExclusion",
            "DdoRichOccurrenceDecision",
        )
    }
    assert not any("execution_model" in artifact.name for artifact in deps.artifacts)
    from pydantic import ValidationError

    from corpus_structure.semantic import prepare_release
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource

    prepared = prepare_release(bundle, deps)
    current = DeclaredRecordSource(
        "original:document",
        "a" * 64,
        "#/groups/3",
        "descendants",
        SubjectContext(
            "actual-project",
            "actual-source",
            "original:document",
            b'{"page":1}',
            subject_definition="original-source-view",
        ),
        "product:source",
        "member:source",
        "kind:source",
    ).pin()
    checked = prepared.validate_python("RecordSourcePin", current).model_dump(
        mode="python", exclude_unset=True
    )
    assert checked == current
    fields = {prop.name for prop in prepared.index.definitions["RecordSourcePin"].properties}
    assert {
        "format",
        "source_product",
        "subject_definition",
        "document",
        "analyzed_scope_meaning",
        "kind_contract",
    } <= fields
    assert (
        not {"source_view_id", "native_product_task_id", "product_digest", "recipe_digest"} & fields
    )
    with pytest.raises(ValidationError):
        prepared.validate_python(
            "RecordSourcePin",
            {
                "source": "old-source",
                "native_product_task_id": 7,
                "source_view_id": 8,
                "product_key": "old",
                "product_digest": "a" * 64,
                "projection_digest": "b" * 64,
                "recipe_digest": "c" * 64,
            },
        )


def test_policy_capture_keeps_duplicate_key_refusal_and_one_actual_archived_owner():
    profile = acquire_analysis_context_profile()
    with pytest.raises(ValueError):
        rich_policy_inputs(ResolvedDependencies(), b"rules: []\nrules: []", context_profile=profile)
    deps = rich_policy_inputs(ResolvedDependencies(), b"rules: []", context_profile=profile)
    with pytest.raises(ValueError, match="already declared"):
        rich_policy_inputs(deps, b"rules: []", context_profile=profile)
    with pytest.raises(ValueError, match="exact captured"):
        rich_knowledge_declarations(ResolvedDependencies())


def test_schema_augmentation_consumes_already_captured_policy_without_a_second_policy_owner():
    from corpus_structure.semantic import prepare_release

    root = Path(__file__).resolve().parents[4]
    policy = rich_policy_inputs(
        ResolvedDependencies(),
        (root / "domains/statistics/schema/rules.yaml").read_bytes(),
        (root / "domains/core/schema/rules.yaml").read_bytes(),
        context_profile=acquire_analysis_context_profile(),
    )
    bundle, dependencies = rich_knowledge_schema_inputs(
        release_inputs()[0],
        policy,
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    assert sum(artifact.name == RULE_INPUT for artifact in dependencies.artifacts) == 1
    assert all(artifact in dependencies.artifacts for artifact in policy.artifacts)
    prepared = prepare_release(bundle, dependencies)
    assert {prop.name for prop in prepared.index.definitions["RecordSourcePin"].properties} >= {
        "format",
        "source_product",
        "analyzed_scope_meaning",
    }
    from corpus_structure.semantic.rich_rules import RichRulePolicy

    rules = RichRulePolicy(prepared)
    assert rules.rules and rules.version == "semantic-domain-3"


def test_rich_policy_refs_resolve_exact_captured_profile_and_checked_kind_owners():
    from corpus_structure.semantic import prepare_release
    from corpus_structure.semantic.rich_policy_binding import (
        require_rich_policy,
        rich_context_profile,
        rich_policy_value,
    )

    root = Path(__file__).resolve().parents[4]
    profile = acquire_analysis_context_profile()
    bundle, deps = rich_knowledge_inputs(
        release_inputs()[0],
        ResolvedDependencies(),
        domain_rules=(root / "domains/statistics/schema/rules.yaml").read_bytes(),
        core_rules=(root / "domains/core/schema/rules.yaml").read_bytes(),
        context_profile=profile,
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    prepared = prepare_release(bundle, deps)
    model = compile_data_operations(bundle, declarations=rich_knowledge_declarations(deps))
    policy = rich_policy_value(prepared, model)
    contracts = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    assert (
        policy.qualification_contract
        == contracts[prepared.qualification_definition("StatisticsQualification").iri]
    )
    assert policy.statement_contract == contracts[prepared.index.definitions["SourceStatement"].iri]
    assert rich_context_profile(prepared) == profile

    assert policy.allowed_domain_contracts
    narrower = rich_policy_value(
        prepared, model, allowed_domain_contracts=(policy.allowed_domain_contracts[0],)
    )
    assert require_rich_policy(prepared, model, narrower) == narrower
    with pytest.raises(ValueError, match="Entity-class contract"):
        rich_policy_value(
            prepared, model, allowed_domain_contracts=(policy.qualification_contract,)
        )
    assert require_rich_policy(prepared, model, policy.model_dump(mode="python")) == policy
    with pytest.raises(ValueError, match="checked captured"):
        require_rich_policy(prepared, model, policy.model_copy(update={"rules_digest": "f" * 64}))


def test_rich_augmentation_preserves_exact_captured_current_observations(monkeypatch):
    from corpus_structure.semantic import observations, prepare_release
    from corpus_structure.semantic.declared_record_sources import declared_record_inputs

    current = declared_record_inputs(release_inputs()[0])
    captured = next(source.content for source in current.sources if source.name == "observations")
    assert b"declared-native-source-v1" in captured
    # This acquisition already has its actual schema authority. Reopening an
    # installed observation default would be a second owner, not a valid merge.
    monkeypatch.setattr(
        observations, "_MODEL", Path("unavailable-installed-observation-default.yaml")
    )
    bundle, dependencies = rich_knowledge_schema_inputs(
        current,
        ResolvedDependencies(),
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    actual = [source.content for source in bundle.sources if source.name == "observations"]
    assert actual == [captured]
    prepared = prepare_release(bundle, dependencies)
    fields = {prop.name for prop in prepared.index.definitions["RecordSourcePin"].properties}
    assert {"format", "source_product", "subject_definition", "analyzed_scope_meaning"} <= fields
    assert not {"source_view_id", "native_product_task_id", "recipe_digest"} & fields
    conflicting = captured.replace(b"declared-native-source-v1", b"incompatible-pin-v2")
    assert conflicting != captured
    with pytest.raises(ValueError, match="reserved observation module"):
        observations.observation_inputs(current, model_content=conflicting)
