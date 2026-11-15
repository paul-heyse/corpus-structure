"""The actual captured rich factories compile under the current DDO owner."""

from corpus_structure.semantic.analysis_contracts import acquire_analysis_context_profile
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.record_policy_authority import record_policy_kind_declarations
from corpus_structure.semantic.rich_invocations import rich_knowledge_operation_sources
from corpus_structure.semantic.rich_knowledge_sources import (
    rich_knowledge_declarations,
    rich_knowledge_inputs,
)
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.record_contracts_support import release_inputs


def test_actual_current_rich_method_factories_and_native_effect_compile_without_legacy_catalog():
    bundle, deps = rich_knowledge_inputs(
        release_inputs()[0],
        ResolvedDependencies(),
        domain_rules=b"rules: []\n",
        context_profile=acquire_analysis_context_profile(),
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    model = compile_data_operations(
        bundle,
        declarations=(*rich_knowledge_declarations(deps), record_policy_kind_declarations()),
        python_sources=rich_knowledge_operation_sources(),
    )
    consolidate = model.operation("rich.consolidate")
    admit = model.operation("rich.admit")
    assert consolidate.profile == "derivation" and consolidate.effects == ()
    assert admit.profile == "command" and admit.capabilities.preparation == "native-publication"
    assert (
        admit.capabilities.prepared_factory.entrypoint
        == "corpus_structure.methods.rich_knowledge.RichKnowledgeAdmission.acquire_port"
    )
    assert {role.name for role in consolidate.roles if role.direction == "input"} == {
        "proposals",
        "proposal_contexts",
        "authored",
        "records",
        "readings",
        "known_universe",
        "policy",
    }
    assert [effect.name for effect in admit.effects] == ["native-rich-knowledge-admission"]
