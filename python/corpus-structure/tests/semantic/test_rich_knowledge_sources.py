"""Current rich preparation consumes explicit inputs without execution-catalog acquisition."""

from pathlib import Path

import pytest

from corpus_structure.semantic.analysis_contracts import acquire_analysis_context_profile
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.rich_knowledge_sources import (
    RICH_CONTRACT_INPUT, RULE_INPUT, rich_knowledge_declarations, rich_knowledge_inputs,
    rich_policy_inputs,
)
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.record_contracts_support import release_inputs


def test_actual_rich_composition_captures_schema_policy_and_nominal_members_without_legacy_catalog(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("current rich composition must not acquire an execution catalog")
    monkeypatch.setattr("corpus_structure.semantic.contracts.compile_execution_model", refuse)
    monkeypatch.setattr("corpus_structure.semantic.contracts.bound_execution_model", refuse)
    root = Path(__file__).resolve().parents[4]
    bundle, deps = rich_knowledge_inputs(
        release_inputs()[0], ResolvedDependencies(),
        domain_rules=(root / "domains/statistics/schema/rules.yaml").read_bytes(),
        core_rules=(root / "domains/core/schema/rules.yaml").read_bytes(),
        context_profile=acquire_analysis_context_profile(),
    )
    assert {"data_operation_rich_proposals", "source-readings"} <= {source.name for source in bundle.sources}
    assert {RULE_INPUT, RICH_CONTRACT_INPUT, "operation/scientific-policy.json"} <= {source.name for source in deps.artifacts}
    model = compile_data_operations(bundle, declarations=rich_knowledge_declarations(deps))
    assert len(derive_member_kinds(model, "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/DdoRichConsolidation")) == 11
    assert not any("execution_model" in artifact.name for artifact in deps.artifacts)


def test_policy_capture_keeps_duplicate_key_refusal_and_one_actual_archived_owner():
    profile = acquire_analysis_context_profile()
    with pytest.raises(ValueError):
        rich_policy_inputs(ResolvedDependencies(), b"rules: []\nrules: []", context_profile=profile)
    deps = rich_policy_inputs(ResolvedDependencies(), b"rules: []", context_profile=profile)
    with pytest.raises(ValueError, match="already declared"):
        rich_policy_inputs(deps, b"rules: []", context_profile=profile)
    with pytest.raises(ValueError, match="exact captured"):
        rich_knowledge_declarations(ResolvedDependencies())
