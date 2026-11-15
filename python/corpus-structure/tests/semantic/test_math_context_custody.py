"""Current mathematical acquisition and memoization use explicit semantic context."""

import inspect
import sys
from collections import OrderedDict
from dataclasses import replace

import pytest
import yaml

from corpus_structure.methods.math import grammar
from corpus_structure.semantic.analysis_policies import (
    analysis_policy_sources,
    compile_analysis_policies,
)
from corpus_structure.semantic.math_context import (
    AnalysisContextProfile,
    acquire_analysis_context_profile,
    prepare_interpretation_context,
)


def test_standalone_context_and_real_parser_do_not_import_a_legacy_catalog(monkeypatch):
    monkeypatch.setitem(sys.modules, "corpus_structure.semantic.contracts", None)
    monkeypatch.setattr(grammar, "_STANDALONE_CONTEXTS", OrderedDict())
    monkeypatch.setattr(grammar, "_MEMO", OrderedDict())
    context = prepare_interpretation_context(
        context_profile=acquire_analysis_context_profile(), macros={}
    )
    result = grammar.parse("x+1")
    assert context.profile.grammar_recipe == "extended-lark-3"
    assert result.failure is None
    assert result.kind == "formula"
    assert tuple(item.name for item in result.occurrences) == ("x",)
    assert grammar.parse("x+1") is result


def test_explicit_policy_contexts_do_not_reuse_or_displace_each_others_results(monkeypatch):
    monkeypatch.setattr(grammar, "_MEMO", OrderedDict())
    baseline = acquire_analysis_context_profile()
    sources = tuple(
        source for source in analysis_policy_sources() if source.name.startswith("analysis/")
    )
    changed = []
    for source in sources:
        if source.name == "analysis/policy.yaml":
            record = yaml.safe_load(source.content)
            record["mathematical"]["builtin_functions"] = []
            source = replace(source, content=yaml.safe_dump(record).encode())
        changed.append(source)
    policies = compile_analysis_policies(tuple(changed))
    proposed = AnalysisContextProfile(policies.mathematical, baseline.implementation_digests)
    old = prepare_interpretation_context(macros={}, context_profile=baseline).grammar_context
    new = prepare_interpretation_context(macros={}, context_profile=proposed).grammar_context
    first = grammar.parse("x+1", context=old)
    second = grammar.parse("x+1", context=new)
    assert old.key() != new.key()
    assert second is not first
    assert first.failure is second.failure is None
    assert first.kind == second.kind == "formula"
    assert tuple(item.name for item in first.occurrences) == ("x",)
    assert tuple(item.name for item in second.occurrences) == ("x",)
    assert grammar.parse("x+1", context=old) is first
    assert grammar.parse("x+1", context=new) is second


def test_preparation_requires_captured_context_and_preserves_it_without_reacquisition(monkeypatch):
    from corpus_structure.semantic import math_context

    captured = acquire_analysis_context_profile()
    with pytest.raises(TypeError, match="context_profile"):
        inspect.signature(prepare_interpretation_context).bind(macros={})
    monkeypatch.setitem(sys.modules, "corpus_structure.semantic.contracts", None)
    monkeypatch.setitem(sys.modules, "corpus_structure.semantic.analysis_contracts", None)
    monkeypatch.setattr(
        math_context,
        "acquire_analysis_context_profile",
        lambda: (_ for _ in ()).throw(AssertionError("ambient acquisition")),
    )
    context = prepare_interpretation_context(context_profile=captured, macros={})
    assert context.profile is captured.profile
    assert context.implementation_digests == captured.implementation_digests
    assert context.model_id == captured.model_id
    assert "Gamma" in context.grammar_context.functions
