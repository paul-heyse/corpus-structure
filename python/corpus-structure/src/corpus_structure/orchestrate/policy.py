"""Policies: the loader, the typed unit context and the compiled chains (P0-O-2, part one).

Orchestration §3.10; D6 §7.1, §7.2; ADR-0018; DA-012, DA-016. This module covers loading and
compiling; evaluating the `propose` chain in the stage runner, and the `ops.policy_rule` rows, are
the rest of P0-O-2.

**Loading.** `policies.yaml` goes through PyYAML `safe_load` into a frozen model (`PolicyFile`):
`version`, optional `budgets`, `thresholds` and `confidence`, and `chains`. A chain's name is a
`PolicyChain` member and an entry's `unit_type` a `TaskUnitType` member. An action names
`<method>/<name>` and is refused when the registry does not hold the method or `methods.yaml` lacks
the configuration ("registered methods only"). The `confidence` block's `priors`, `multipliers` and
`caps` are maps keyed by `ConfidenceSource` members (DA-016; orchestration §3.10), each value a
decimal or a map of states to decimals; any other key is refused. Phase 0 reads no block.

**Compilation.** Each entry's `when` is compiled with the rule-language helper (`schema.rulelang`)
under the unit context's language, one context per entry, so a type error, a banned builtin or a
string literal outside a typed symbol's vocabulary fails loading naming the entry. Each chain is a
rule-engine `Chain` of `(Rule, entry)` pairs with no default (`ChainEntry` has no id, so the entry
carries its key). `matches(chain, thing)` is the first match and, after a `continue` entry, the
rest of the chain from the entry after it.

**The unit context** (D6 §7.2), typed per schema version:
- `phase`, `iteration`;
- `unit`: `kind` (`SegmentKind`), `statement_kind` (the version's `StatementKind`, nullable),
  `claim_bearing`, and each unit- or segment-scope metric named, a nullable number;
- `ran(m)` and `outcome(m)` (`ObservationOutcome`), `judged_by(m)`, `decision(m)`
  (`JudgmentDecision`) and `confidence(m)` (`JudgmentConfidence`), each `m` a registered method;
- `target`: `kind` (`JudgmentTargetKind`), `size`, `max_confidence`, `margin`, nullable until phase
  1; `budget`: `agent_packets_left`, `llm_tokens_left`, nullable.
`decision(m)` and `confidence(m)` are two symbols because a judge's output has both and one list
mixing them could not be checked (R07).
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from rule_engine import Chain, Rule

from corpus_structure.core.vocab import (
    ConfidenceSource,
    JudgmentConfidence,
    JudgmentDecision,
    JudgmentTargetKind,
    ObservationOutcome,
    PolicyChain,
    PolicyThen,
    SegmentKind,
    TaskUnitType,
)
from corpus_structure.schema.rulelang import CALL, Language, RuleError, Vocabulary

# The unit type an entry takes when it names none (D6 §7.1 "Rows").
DEFAULT_UNIT_TYPE: Mapping[PolicyChain, TaskUnitType] = {
    PolicyChain.PROPOSE: TaskUnitType.SOURCE_VIEW,
    PolicyChain.ESCALATE: TaskUnitType.SOURCE_VIEW,
    PolicyChain.ADJUDICATE: TaskUnitType.ALTERNATIVE_GROUP,
    PolicyChain.IDENTITY: TaskUnitType.IDENTITY_GROUP,
    PolicyChain.GAPS: TaskUnitType.SOURCE_VIEW,
}
METHOD_FUNCTIONS = ("ran", "outcome", "judged_by", "decision", "confidence")


class PolicyError(ValueError):
    """A policy file that does not load; `problems` names each entry and what is wrong."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = list(problems)
        super().__init__("policy refused:\n  " + "\n  ".join(self.problems))


# --- The file model --------------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PolicyDo(_Strict):
    method: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.]*/[A-Za-z0-9_.-]+$")]
    limit: Annotated[int, Field(ge=1)] | None = None  # none: no cap beyond the budgets
    then: PolicyThen = PolicyThen.STOP


class PolicyEntry(_Strict):
    key: Annotated[str, Field(min_length=1)]
    when: str = "true"
    unit_type: TaskUnitType | None = None
    do: PolicyDo


type SourceValue = Decimal | dict[str, Decimal]


class ConfidenceBlock(_Strict):
    """D5 §6.3's cold-start policy data, keyed by `ConfidenceSource` members (DA-016)."""

    priors: dict[ConfidenceSource, SourceValue] = {}
    multipliers: dict[ConfidenceSource, SourceValue] = {}
    caps: dict[ConfidenceSource, SourceValue] = {}


class PolicyFile(_Strict):
    version: str
    budgets: dict[str, int] = {}
    thresholds: dict[str, Any] = {}
    confidence: ConfidenceBlock | None = None
    chains: dict[PolicyChain, tuple[PolicyEntry, ...]] = {}


def parse_policy(source: str) -> PolicyFile:
    """The file model of a `policies.yaml` text; a structural error is a `PolicyError`."""
    try:
        data = yaml.safe_load(source) or {}
    except yaml.YAMLError as error:
        raise PolicyError([f"policies.yaml is not YAML: {error}"]) from None
    try:
        return PolicyFile.model_validate(data)
    except ValidationError as error:
        raise PolicyError(
            [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors()]
        ) from None


# --- The unit context ------------------------------------------------------------------------


def _vocab(name: str, members: Iterable[str]) -> Vocabulary:
    return Vocabulary(name, frozenset(members))


def unit_language(
    statement_kinds: Collection[str],
    methods: Collection[str],
    metrics: Collection[str] = (),
    *,
    nullable_claim_bearing: bool = False,
    native_unit_kinds: Collection[str] = (),
) -> Language:
    """The unit context's language for one schema version (module doc): `statement_kinds` are the
    version's `StatementKind` members as stored, `methods` the registered method names."""
    method_names = _vocab("registered methods", methods)
    unit = {
        "kind": "string",
        "statement_kind": "string?",
        "claim_bearing": "boolean?" if nullable_claim_bearing else "boolean",
    }
    unit |= {m: "number?" for m in sorted(metrics)}
    return Language(
        objects={
            "Unit": unit,
            "Target": {
                "kind": "string?",
                "size": "number?",
                "max_confidence": "number?",
                "margin": "number?",
            },
            "Budget": {"agent_packets_left": "number?", "llm_tokens_left": "number?"},
        },
        symbols={
            "phase": "number",
            "iteration": "number",
            "unit": "Unit",
            "target": "Target",
            "budget": "Budget",
            "ran": "function(string)->boolean",
            "judged_by": "function(string)->boolean",
            "outcome": "function(string)->string?",
            "decision": "function(string)->string?",
            "confidence": "function(string)->string?",
        },
        values={
            ("Unit", "kind"): _vocab(
                "source unit kind" if native_unit_kinds else "SegmentKind",
                (*SegmentKind, *native_unit_kinds),
            ),
            ("Unit", "statement_kind"): _vocab("StatementKind", statement_kinds),
            ("Target", "kind"): _vocab("JudgmentTargetKind", JudgmentTargetKind),
            (CALL, "outcome"): _vocab("ObservationOutcome", ObservationOutcome),
            (CALL, "decision"): _vocab("JudgmentDecision", JudgmentDecision),
            (CALL, "confidence"): _vocab("JudgmentConfidence", JudgmentConfidence),
        },
        arguments={name: (method_names,) for name in METHOD_FUNCTIONS},
    )


def source_propose_language(statement_kinds: Collection[str], methods: Collection[str]) -> Language:
    """Executable source context: nullable classification exists; judgments/budgets do not."""
    from dataclasses import replace

    authored = unit_language(
        statement_kinds,
        methods,
        nullable_claim_bearing=True,
        native_unit_kinds=(TaskUnitType.SOURCE_VIEW.value,),
    )
    available = {"phase", "iteration", "unit", "ran", "outcome"}
    return replace(
        authored,
        objects={"Unit": authored.objects["Unit"]},
        symbols={k: v for k, v in authored.symbols.items() if k in available},
        values={
            k: v for k, v in authored.values.items() if k[0] == "Unit" or k == (CALL, "outcome")
        },
        arguments={k: v for k, v in authored.arguments.items() if k in available},
    )


def admit_source_policy(source: str, registry: Any, prepared: Any) -> CompiledPolicy:
    """Refuse unsupported execution before a run/task or source-registration effect."""
    from corpus_structure.methods.llm.producer import producer_binding
    from corpus_structure.semantic.statement_types import statement_kinds

    file = parse_policy(source)
    problems = [
        f"chain {chain}: not executable by source PROPOSE"
        for chain in file.chains
        if chain != PolicyChain.PROPOSE
    ]
    if problems:
        raise PolicyError(problems)
    names = registry_configs(registry)
    compiled = compile_policy(
        file, source_propose_language(statement_kinds(prepared), names), names
    )
    for entry in file.chains.get(PolicyChain.PROPOSE, ()):
        method_name, config_name = entry.do.method.split("/", 1)
        try:
            method = registry.method(method_name)
            config = registry.overlay(method_name, config_name)
            producer_binding(
                method_name,
                config.model_dump(mode="json"),
                unit=entry.unit_type or TaskUnitType.SOURCE_VIEW,
            )
            from corpus_structure.semantic.operation_results import validate_method_dimension

            validate_method_dimension(prepared, method_name, "family", str(method.family))
            validate_method_dimension(prepared, method_name, "tier", str(method.tier))
            validate_method_dimension(
                prepared,
                method_name,
                "confidence_source",
                str(method.confidence_source) if method.confidence_source is not None else None,
            )
            if method.unit_type != (entry.unit_type or TaskUnitType.SOURCE_VIEW):
                raise ValueError("action unit differs from its method")
        except (KeyError, ValueError) as error:
            problems.append(f"{entry.key}: {error}")
    if problems:
        raise PolicyError(problems)
    return compiled


# --- Compiling -------------------------------------------------------------------------------


@dataclass(frozen=True)
class CompiledEntry:
    chain: PolicyChain
    priority: int  # the entry's position in its chain
    key: str
    entry: PolicyEntry
    unit_type: TaskUnitType
    rule: Rule

    @property
    def method(self) -> str:
        return self.entry.do.method.split("/", 1)[0]


@dataclass(frozen=True)
class CompiledPolicy:
    file: PolicyFile
    chains: Mapping[PolicyChain, Chain]

    def entries(self, chain: PolicyChain) -> tuple[CompiledEntry, ...]:
        found = self.chains.get(chain)
        return tuple(e.value for e in found) if found is not None else ()

    def matches(self, chain: PolicyChain, thing: Mapping[str, Any]) -> list[CompiledEntry]:
        """The entries that fire for `thing`: the first match, and after each `continue` entry the
        first match of the rest of the chain."""
        found = self.chains.get(chain)
        out: list[CompiledEntry] = []
        while found is not None and len(found):
            hit = found.find(thing)
            if hit is None:
                break
            entry: CompiledEntry = hit.value
            out.append(entry)
            if entry.entry.do.then != PolicyThen.CONTINUE:
                break
            found = found[found.index(hit) + 1 :]
        return out


def compile_policy(
    file: PolicyFile,
    language: Language,
    configs: Mapping[str, Collection[str]],
) -> CompiledPolicy:
    """Compile every chain (module doc). `configs` maps each registered method to the names of its
    configurations in `methods.yaml`. Every problem of the file is reported together."""
    problems: list[str] = []
    keys: set[str] = set()
    chains: dict[PolicyChain, Chain] = {}
    for chain, entries in file.chains.items():
        compiled = []
        for priority, entry in enumerate(entries):
            where = f"{chain.value}[{priority}] {entry.key}"
            if entry.key in keys:
                problems.append(f"{where}: the key is used twice")
            keys.add(entry.key)
            method, name = entry.do.method.split("/", 1)
            if method not in configs:
                problems.append(f"{where}: method {method!r} is not registered")
            elif name not in configs[method]:
                problems.append(f"{where}: methods.yaml has no configuration {method}/{name}")
            try:
                rule = language.compile(entry.key, entry.when)
            except RuleError as error:
                problems += [f"{where}: [{p.code}] {p.message}" for p in error.problems]
                continue
            unit_type = entry.unit_type or DEFAULT_UNIT_TYPE[chain]
            compiled.append(CompiledEntry(chain, priority, entry.key, entry, unit_type, rule))
        chains[chain] = Chain([(e.rule, e) for e in compiled])
    if problems:
        raise PolicyError(problems)
    return CompiledPolicy(file, chains)


def load_policy(
    path: Path,
    language: Language,
    configs: Mapping[str, Collection[str]],
) -> CompiledPolicy:
    """Load and compile a pack's `policies.yaml`; an absent file is an empty policy."""
    source = path.read_text(encoding="utf-8") if path.exists() else "version: '0'\n"
    return compile_policy(parse_policy(source), language, configs)


def registry_configs(registry: Any) -> dict[str, set[str]]:
    """Each registered method's configuration names (a `MethodRegistry`'s `named()`)."""
    out: dict[str, set[str]] = {}
    for method, name in registry.named():
        out.setdefault(method, set()).add(name)
    return out


__all__ = [
    "CompiledEntry",
    "CompiledPolicy",
    "ConfidenceBlock",
    "PolicyError",
    "PolicyFile",
    "compile_policy",
    "load_policy",
    "parse_policy",
    "registry_configs",
    "unit_language",
]
