"""M19: the rule runner, the `validate.rules` method and the two submission entry points (P0-S-2).

Schema and rules §3.7, §3.8; D4 M19; agent interface §3.6.

`run_rules(views, compiled, site)` evaluates, for each claim view, the rules indexed under its
predicate for the site. A false `when` records nothing; a false `check` is a finding (rule id,
severity, claim id, message). The outcome carries, per rule, the count of views it evaluated (its
`when` true). One compiled rule set is shared safely across threads: `Rule.evaluate` resets its
thread-local state.

**The submission entry points** follow agent interface §3.6's order (checks, then parse, then
M19), so `propose_claims` and `write_golden` validate identically:
- `check_authored(batch_json, sentence_ids, compiled)` runs the checks on the authored form;
- `check_stored(stored, compiled, …)` runs the stored-form checks, drops each rejected item and
  the items that depend on one (`dropped_dependency`), adapts the rest (T2), builds the batch-site
  views (T4) and runs the batch-site rules, returning issues, drops and findings together.

**The method** `validate.rules` (family `validate`, unit type `run`) implements O0's contract: its
`Config` names the rules artifact by (`rules`, `rules`), which the registry resolves per run, and
its version is the runner's. Run-unit tasks are never reused. Consolidation calls the runner inside
the finalize pass; no orchestrator worker runs it (D4 M19), so its `run` refuses.
"""

from __future__ import annotations

import json
import typing
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, ValidationError

from corpus_structure.core.batch import StoredBatch
from corpus_structure.core.candidates import KeyedCandidateSet
from corpus_structure.core.keys import Drop
from corpus_structure.core.method import (
    ArtifactRef,
    Digest,
    MethodContext,
    Resources,
    SourceRunContext,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import (
    ConfidenceSource,
    DropReason,
    MethodFamily,
    MethodTier,
    TaskUnitType,
)
from corpus_structure.validate.adapter import candidates_from_batch
from corpus_structure.validate.batch import SECTIONS, BatchReport, check_batch
from corpus_structure.validate.views import ClaimView, build_views

if typing.TYPE_CHECKING:
    from corpus_structure.schema.compile import CompiledSchema

RUNNER_VERSION = "1"


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    claim: str
    message: str


@dataclass(frozen=True)
class RuleOutcome:
    site: str
    findings: tuple[Finding, ...]
    evaluated: Mapping[str, int]  # rule id -> views its `when` held for

    def by_rule(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for f in self.findings:
            out.setdefault(f.rule, set()).add(f.claim)
        return out


class RuleEvaluationError(RuntimeError):
    """A compiled rule raised on a view: a defect of the rule or the view, never a finding."""


def run_rules(views: Iterable[ClaimView], compiled: CompiledSchema, site: str) -> RuleOutcome:
    """The findings of the version's rules declared at `site` over the views (module doc)."""
    index = compiled.rules.index(site)
    evaluated: dict[str, int] = {r.id: 0 for rules in index.values() for r in rules}
    findings = []
    for view in views:
        thing = {"claim": view}
        for rule in index.get(view.predicate, ()):
            try:
                if not rule.when[site].matches(thing):
                    continue
                evaluated[rule.id] += 1
                ok = rule.check[site].matches(thing)
            except Exception as error:  # rule-engine's evaluation errors and view defects
                raise RuleEvaluationError(f"{rule.id} on {view.id}: {error}") from error
            if not ok:
                findings.append(Finding(rule.id, rule.severity, view.id, rule.description))
    return RuleOutcome(site, tuple(findings), evaluated)


# --- The submission entry points --------------------------------------------------------------


def check_authored(
    batch_json: str | Mapping[str, Any], sentence_ids: Iterable[str], compiled: CompiledSchema
) -> BatchReport:
    """The authored-form checks against the frame's sentence ids."""
    return check_batch(batch_json, compiled, "model", sentence_ids=sentence_ids)


@dataclass(frozen=True)
class StoredOutcome:
    report: BatchReport
    drops: tuple[Drop, ...]
    candidates: KeyedCandidateSet | None
    rules: RuleOutcome | None
    errors: Sequence[str] = field(default_factory=tuple)
    batch: StoredBatch | None = None  # the accepted items, as stored (what a proposal records)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(
            f for f in (self.rules.findings if self.rules else ()) if f.severity == "warning"
        )


def _refs(node: Any) -> set[str]:
    """Every local ref an item names (subject, object, statement, entity qualifiers, bindings,
    claim nodes, identity, alternative members)."""
    out: set[str] = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("subject", "statement", "ref", "entity", "claim") and isinstance(v, str):
                out.add(v)
            elif k == "refs" and isinstance(v, list):
                out |= {r for r in v if isinstance(r, str)}
            else:
                out |= _refs(v)
    elif isinstance(node, list):
        for v in node:
            out |= _refs(v)
    return out


def accepted_items(raw: dict[str, Any], report: BatchReport) -> tuple[dict[str, Any], list[Drop]]:
    """The batch without its rejected items and without the items that depend on one."""
    rejected = set(report.rejected_paths())
    drops: list[Drop] = []
    gone: set[str] = set()
    for sec, i in sorted(rejected, key=lambda p: (SECTIONS.index(str(p[0])), p[1])):
        ref = raw[sec][i].get("local_ref") if isinstance(raw[sec][i], dict) else None
        if ref:
            gone.add(ref)
    changed = True
    while changed:  # dependents of a dropped item, to a fixpoint
        changed = False
        for sec in ("entities", "claims"):
            for i, item in enumerate(raw.get(sec, [])):
                ref = item.get("local_ref") if isinstance(item, dict) else None
                if (sec, i) in rejected or ref in gone:
                    continue
                identity = set(item.get("identity", {}).values()) if sec == "entities" else set()
                depends = (identity if sec == "entities" else _refs(item)) & gone
                if depends:
                    gone.add(str(ref))
                    rejected.add((sec, i))
                    drops.append(
                        Drop(DropReason.DROPPED_DEPENDENCY, str(ref), tuple(sorted(depends)))
                    )
                    changed = True
    out = {k: v for k, v in raw.items() if k not in SECTIONS}
    for sec in SECTIONS:
        items = [it for i, it in enumerate(raw.get(sec, [])) if (sec, i) not in rejected]
        if sec == "alternatives":
            kept = []
            for a in items:
                refs = [r for r in a.get("refs", []) if r not in gone]
                if len(refs) >= 2:
                    kept.append({**a, "refs": refs})
            items = kept
        out[sec] = items
    return out, drops


def check_stored(
    stored: str | Mapping[str, Any] | StoredBatch,
    compiled: CompiledSchema,
    *,
    canonical_text: str | None = None,
    unit_ranges: Sequence[tuple[int, int]] | None = None,
) -> StoredOutcome:
    """The stored-form checks, the adapter, the batch-site views and rules (module doc)."""
    if isinstance(stored, StoredBatch):
        raw: Any = stored.model_dump(mode="json", by_alias=True)
    elif isinstance(stored, str):
        try:
            raw = json.loads(stored)
        except json.JSONDecodeError:
            raw = stored
    else:
        raw = json.loads(json.dumps(stored))
    report = check_batch(
        raw, compiled, "stored", canonical_text=canonical_text, unit_ranges=unit_ranges
    )
    if not isinstance(raw, dict) or any(len(i.path) < 2 for i in report.issues):
        return StoredOutcome(report, (), None, None)  # the envelope itself is refused
    accepted, drops = accepted_items(raw, report)
    try:
        batch = compiled.batches.validate(json.dumps(accepted), "stored")
    except ValidationError as error:  # never expected after the checks; reported, not raised
        return StoredOutcome(
            report, tuple(drops), None, None, tuple(str(e) for e in error.errors())
        )
    candidates = candidates_from_batch(batch, compiled)
    views = build_views(candidates, compiled, "batch")
    return StoredOutcome(
        report, tuple(drops), candidates, run_rules(views, compiled, "batch"), batch=batch
    )


# --- The method -------------------------------------------------------------------------------


class RulesConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rules: Annotated[str, ArtifactRef("rules", "rules")] = ""


class RulesMethod:
    """`validate.rules`, M19 (module doc)."""

    name = "validate.rules"
    version = RUNNER_VERSION
    family = MethodFamily.VALIDATE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = ConfidenceSource.RULES
    Config = RulesConfig
    resources = Resources()

    def select(self, run: SourceRunContext, cfg: RulesConfig) -> Iterable[UnitRef]:
        return [UnitRef(TaskUnitType.RUN)]

    def input_digest(self, unit: UnitView, cfg: RulesConfig) -> Digest:
        return Digest(f"{self.name}|{self.version}|{cfg.rules}".encode())

    def run(
        self, units: Sequence[UnitView], cfg: RulesConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        raise RuntimeError(
            "validate.rules runs inside consolidation's finalize pass (D4 M19); "
            "no orchestrator worker runs it"
        )
