"""The policy loader, the typed unit context and the compiled chains (P0-O-2, part one;
orchestration §3.10, §6).

The statistics phase 0 policy compiles against the phase 0 registry and the statistics schema
version. Each refusal names the entry: a type error, an unregistered method or configuration, a
literal outside a typed symbol's vocabulary (DA-012), and a confidence key outside
`ConfidenceSource` (DA-016). `continue` evaluates the rest of the chain.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from corpus_structure.core.vocab import ConfidenceSource, PolicyChain, TaskUnitType
from corpus_structure.orchestrate import phase0
from corpus_structure.orchestrate.policy import (
    PolicyError,
    compile_policy,
    load_policy,
    parse_policy,
    registry_configs,
    unit_language,
)
from corpus_structure.semantic.regeneration import prepare_packs
from corpus_structure.semantic.statement_types import statement_kinds
from corpus_structure.semantic.types import PreparedRelease

REPO = Path(__file__).resolve().parents[4]
STATISTICS = REPO / "domains/statistics"


@pytest.fixture(scope="module")
def stats() -> PreparedRelease:
    return prepare_packs((STATISTICS,))[3]


@pytest.fixture(scope="module")
def configs() -> dict[str, set[str]]:
    return registry_configs(phase0.registry(STATISTICS))


@pytest.fixture(scope="module")
def language(stats: PreparedRelease, configs: dict[str, set[str]]) -> Any:
    kinds = statement_kinds(stats)
    return unit_language(kinds, configs)


def policy(*entries: dict[str, Any], chain: str = "propose", **extra: Any) -> str:
    import yaml

    return yaml.safe_dump({"version": "0.1.0", "chains": {chain: list(entries)}, **extra})


def entry(when: str, key: str = "t.entry", method: str = "agent.opus/extract", **do: Any) -> dict:
    return {"key": key, "when": when, "do": {"method": method, **do}}


def thing(**unit: Any) -> dict[str, Any]:
    none = lambda m: None  # noqa: E731
    return {
        "phase": 0,
        "iteration": 0,
        "unit": type("U", (), {"kind": "unit", "statement_kind": None, "claim_bearing": False,
                               **unit})(),
        "target": type("T", (), {"kind": None, "size": None, "max_confidence": None,
                                 "margin": None})(),
        "budget": type("B", (), {"agent_packets_left": None, "llm_tokens_left": None})(),
        "ran": lambda m: False, "judged_by": lambda m: False,
        "outcome": none, "decision": none, "confidence": none,
    }  # fmt: skip


def test_the_statistics_phase0_policy_compiles_and_routes_claim_bearing_units(
    language: Any, configs: dict[str, set[str]]
) -> None:
    compiled = load_policy(STATISTICS / "policies.yaml", language, configs)
    (e,) = compiled.entries(PolicyChain.PROPOSE)
    assert (e.key, e.method, e.unit_type) == ("propose.phase0.agent_all", "agent.opus",
                                             TaskUnitType.SOURCE_VIEW)  # fmt: skip
    fired = compiled.matches(PolicyChain.PROPOSE, thing(statement_kind="theorem",
                                                         claim_bearing=True))  # fmt: skip
    assert [x.key for x in fired] == ["propose.phase0.agent_all"]
    assert compiled.matches(PolicyChain.PROPOSE, thing(statement_kind="proof")) == []


@pytest.mark.parametrize(
    ("source", "named"),
    [
        (policy(entry("unit.claim_bearing + 1")), "type_mismatch"),
        (policy(entry("unit.claimbearing")), "unknown_attribute"),
        (policy(entry("true", method="llm.judge/default")), "'llm.judge' is not registered"),
        (policy(entry("true", method="agent.opus/x")), "no configuration agent.opus/x"),
        (policy(entry("$now != null")), "nondeterministic_builtin"),
    ],
    ids=["type error", "unknown attribute", "unregistered method", "unknown configuration",
         "banned builtin"],
)  # fmt: skip
def test_a_bad_entry_fails_loading_naming_it(
    language: Any, configs: dict[str, set[str]], source: str, named: str
) -> None:
    with pytest.raises(PolicyError) as caught:
        compile_policy(parse_policy(source), language, configs)
    (problem,) = caught.value.problems
    assert problem.startswith("propose[0] t.entry:") and named in problem


@pytest.mark.parametrize(
    ("typo", "spelt"),
    [
        ("target.kind == 'alternative_grup'", "target.kind == 'alternative_group'"),
        ("decision('agent.opus') == 'maybe'", "decision('agent.opus') == 'unsure'"),
        ("confidence('agent.opus') in ['lo', 'medium']", "confidence('agent.opus') in ['low']"),
        ("outcome('agent.opus') == 'produce'", "outcome('agent.opus') == 'produced'"),
        ("unit.kind == 'paragrph'", "unit.kind == 'paragraph'"),
        ("unit.statement_kind == 'theorm'", "unit.statement_kind == 'theorem'"),
        ("ran('agent.opuss')", "ran('agent.opus')"),
    ],
)
def test_a_literal_outside_its_vocabulary_fails_and_its_spelling_compiles(
    language: Any, configs: dict[str, set[str]], typo: str, spelt: str
) -> None:
    with pytest.raises(PolicyError) as caught:
        compile_policy(parse_policy(policy(entry(typo))), language, configs)
    (problem,) = caught.value.problems
    assert "t.entry" in problem and "literal_outside_vocabulary" in problem
    compile_policy(parse_policy(policy(entry(spelt))), language, configs)


def test_decision_and_confidence_are_typed_apart(
    language: Any, configs: dict[str, set[str]]
) -> None:
    # D6 §7.1's one list mixing a decision and a confidence level cannot be checked: split, it is
    mixed = "decision('agent.opus') in ['unsure', 'low']"
    with pytest.raises(PolicyError, match="'low' is not a member of JudgmentDecision"):
        compile_policy(parse_policy(policy(entry(mixed))), language, configs)
    split = "decision('agent.opus') == 'unsure' or confidence('agent.opus') == 'low'"
    compile_policy(parse_policy(policy(entry(split))), language, configs)


def test_continue_evaluates_the_rest_of_the_chain(
    language: Any, configs: dict[str, set[str]]
) -> None:
    source = policy(
        entry("unit.claim_bearing", key="a", then="continue"),
        entry("false", key="b"),
        entry("unit.kind == 'unit'", key="c", limit=3),
        entry("true", key="d"),
    )
    compiled = compile_policy(parse_policy(source), language, configs)
    fired = compiled.matches(PolicyChain.PROPOSE, thing(claim_bearing=True))
    assert [e.key for e in fired] == ["a", "c"] and fired[1].entry.do.limit == 3
    assert [e.key for e in compiled.matches(PolicyChain.PROPOSE, thing())] == ["c"]


def test_vocabularies_of_the_file(language: Any, configs: dict[str, set[str]]) -> None:
    with pytest.raises(PolicyError, match="chains"):
        parse_policy(policy(entry("true"), chain="route"))  # not a PolicyChain member
    with pytest.raises(PolicyError, match="unit_type"):
        parse_policy(policy({**entry("true"), "unit_type": "page"}))
    with pytest.raises(PolicyError, match="the key is used twice"):
        compile_policy(parse_policy(policy(entry("true"), entry("true"))), language, configs)


def test_confidence_blocks_are_keyed_by_confidence_source(
    language: Any, configs: dict[str, set[str]]
) -> None:
    block = {
        "priors": {"agent": 0.9, "local_llm": {"supports_full": 0.6}},
        "multipliers": {"rules": {"warning": 0.7}, "verifiers": {"refuted": 0.2}},
        "caps": {"encoders": 0.5},
    }
    loaded = parse_policy(policy(entry("true"), confidence=block))
    assert (
        loaded.confidence is not None
        and str(loaded.confidence.priors[ConfidenceSource.AGENT]) == "0.9"
    )
    for section in ("priors", "multipliers", "caps"):
        bad = {**block, section: {"local_llm_full": 0.5}}  # D6's example key, not a member
        with pytest.raises(PolicyError, match=f"confidence.{section}.local_llm_full"):
            parse_policy(policy(entry("true"), confidence=bad))


@pytest.mark.parametrize("expression", [
    "target.size == null", "budget.agent_packets_left == null", 'judged_by("agent.opus")',
    'decision("agent.opus") == null', 'confidence("agent.opus") == null',
])
def test_source_execution_refuses_unavailable_capabilities(expression):
    from corpus_structure.orchestrate.policy import source_propose_language
    from corpus_structure.schema.rulelang import RuleError

    language = source_propose_language(("theorem",), ("agent.opus",))
    with pytest.raises(RuleError):
        language.compile("unavailable", expression)


def test_source_execution_preserves_available_unknown_classification():
    from types import SimpleNamespace
    from corpus_structure.orchestrate.policy import source_propose_language

    rule = source_propose_language(("theorem",), ("agent.opus",)).compile(
        "unknown", 'unit.claim_bearing == null and unit.statement_kind == null')
    assert rule.matches({"unit": SimpleNamespace(kind="source_view", claim_bearing=None, statement_kind=None)})


@pytest.mark.parametrize("chain,when", [("escalate", "true"), ("propose", "target.size == null")])
def test_source_policy_refusal_precedes_run_and_task_effects(monkeypatch, chain, when):
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from corpus_structure.methods.llm.agent_opus import AgentOpus
    from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
    from corpus_structure.orchestrate.semantic import run_source_methods
    from corpus_structure.orchestrate.policy import PolicyError

    monkeypatch.setattr("corpus_structure.semantic.contracts.require_bound_operation", lambda *args: None)
    monkeypatch.setattr("corpus_structure.semantic.contracts.execution_payload", lambda *args: None)
    monkeypatch.setattr("corpus_structure.semantic.statement_types.statement_kinds", lambda *args: ("theorem",))
    registry = MethodRegistry([AgentOpus()], MethodsFile(configs={"agent.opus": {"extract": {}}}))
    engine = MagicMock()
    with pytest.raises(PolicyError):
        run_source_methods(engine, project_id="p", prepared=SimpleNamespace(release_id="r"),
                           binding=SimpleNamespace(release_id="r"), registry=registry,
                           graph=SimpleNamespace(stages=(), policy_propose=True), method_settings=None,
                           policy_source=f'version: "1"\nchains:\n {chain}:\n  - key: unsupported\n    when: "{when}"\n    do: {{method: agent.opus/extract}}\n')
    engine.begin.assert_not_called()
    engine.connect.assert_not_called()
