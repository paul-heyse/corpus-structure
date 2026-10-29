"""Finalize (consolidation §3.5, §3.6 step 5; D5 §8, §10): values, M19, statuses and edge rows.

- **Values, once per pass.** Every distinct formula and set value of the claims (objects,
  map-qualifier entries, condition leaves), identified by its token form and its rendition's
  macro table, is read once by the math grammar on the main thread. Its status becomes the value's
  `parse`; a timeout is `failed`, a value outcome. Every value's reading (status, kind, symbols),
  keyed by claim and value path (`("object",)`, `("qualifiers", "stat:param_values", "mean")`, a
  condition leaf's path), reaches S2's view builder as data (`validate.views.Reading`), so
  `validate` never imports the grammar.
- **M19**: one view per claim over the run's keyed candidate set (`build_views` at `finalize`, ids
  are keys), every `at: finalize` rule (`run_rules`); an error rejects the claim, every failing
  outcome becomes a `refuted` verification observation of the M19 task.
- **Statuses** in order: `rejected` by a rule error; `unsupported` for `core:unschematized`;
  `ambiguous` for alternative-group members; `accepted` otherwise. The assemble pass writes every
  claim `candidate` (`unsupported` for `core:unschematized`).
- **Edge rows** (final pass only): one `kb.claim_ref` per claim -> claim reference (a condition's
  `claim` node: `condition_premise`; a `param_of` or `param_expr_of` binding: `binding_param`)
  and one `kb.claim_entity_ref` per claim -> entity reference (an entity-ranged qualifier, a `pred`
  argument, a `variable` or `family_param` binding), each with the JSON pointer of the reference in
  the stored claim as its `path`. A reference to no row of the run (an unresolved
  `ExternalReference` as a premise) is an entity edge retaining its premise or binding role.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from corpus_structure.consolidate.assemble import (
    REFERENCE,
    STATEMENT,
    UNSCHEMATIZED,
    Inputs,
    Knowledge,
    sorted_json,
)
from corpus_structure.core import candidates as C
from corpus_structure.core.tex import token_form
from corpus_structure.core.vocab import (
    BindKind,
    ClaimRefKind,
    ClaimStatus,
    EntityRefRole,
    MathKind,
    ParseOutcome,
)
from corpus_structure.pool.steps import Engine
from corpus_structure.validate.runner import Finding, RuleOutcome, run_rules
from corpus_structure.validate.views import Reading, build_views, engine_facts

GRAMMAR_KINDS = {
    "formula": MathKind.FORMULA,
    "relation": MathKind.RELATION,
    "member": MathKind.MEMBERSHIP,
    "set_expr": MathKind.SET,
    "list": MathKind.LIST,
}
START = {"formula": "any_value", "set": "set_expr"}


@dataclass(frozen=True)
class ClaimEdge:
    claim: str
    kind: str
    path: str
    target: str


@dataclass(frozen=True)
class EntityEdge:
    claim: str
    role: str
    slot: str | None
    path: str
    entity: str


# --- Values ------------------------------------------------------------------------------------


def value_nodes(node: Any, path: tuple[str | int, ...] = ()) -> Iterator[tuple[tuple, dict]]:
    if isinstance(node, dict):
        if node.get("t") in START and isinstance(node.get("latex"), str):
            yield path, node
        for k, v in node.items():
            yield from value_nodes(v, (*path, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from value_nodes(v, (*path, i))


def read_values(knowledge: Knowledge, inputs: Inputs) -> dict[tuple[str, tuple], Reading]:
    """Parse each distinct value once, set its `parse` on the claims and return the readings."""
    from corpus_structure.methods.math import grammar  # the main thread only (D4 M11)

    cache: dict[tuple[str, str, Any], Reading] = {}
    readings: dict[tuple[str, tuple], Reading] = {}
    for key, row in sorted(knowledge.claims.items()):
        page = inputs.pages[row.rendition_id]
        table = sorted_json({k: v.model_dump(mode="json") for k, v in page.macros.items()})
        dump = row.claim.model_dump(mode="json", by_alias=True)
        for path, value in value_nodes(
            {"object": dump["object"], "qualifiers": dump.get("qualifiers", {})}
        ):
            ident = (token_form(value["latex"], page.macros), table, value["t"])
            if ident not in cache:
                result = grammar.parse(value["latex"], START[value["t"]], page.macros)  # type: ignore[arg-type]
                names = sorted({o.name for o in result.occurrences if not o.constant})
                kind = GRAMMAR_KINDS.get(result.kind or "")
                cache[ident] = Reading(result.status, kind, tuple(names))
            value["parse"] = cache[ident].status.value
            readings[key, path] = cache[ident]
        row.claim = C.CandidateClaim.model_validate({**dump, "id": key})
    return readings


# --- M19 ---------------------------------------------------------------------------------------


def run_set(knowledge: Knowledge, inputs: Inputs) -> C.KeyedCandidateSet:
    """The run's knowledge as one keyed candidate set, ids as keys, for the finalize views."""
    entities, statements, references = [], [], []
    for key, e in sorted(knowledge.entities.items()):
        if e.type == STATEMENT:
            statements.append(
                C.CandidateStatement(
                    id=key, key=key, kind=e.kind or "", anchor=(str(e.scope_segment_id),)
                )
            )
        elif e.type == REFERENCE:
            references.append(
                C.CandidateReference(
                    id=key,
                    key=key,
                    descriptor=e.descriptor or {"start": 0, "end": 1},
                    resolved_to=e.resolved_to or C.AWAITING,
                )
            )
        else:
            symbol = next((a for a, _, k in sorted(e.aliases) if k == "symbol"), None)
            entities.append(
                C.CandidateEntity(
                    id=key,
                    key=key,
                    type=e.type,
                    label=e.label,
                    scope=e.scope,
                    **({"scope_segment": str(e.scope_segment_id)} if e.scope == "local" else {}),
                    **({"symbol": symbol} if symbol else {}),
                    identity={
                        s: v_key or v_text or "" for s, (v_key, v_text) in e.identity.items()
                    },
                )
            )
    alternatives = [
        C.CandidateAlternative(refs=members, reason="alternatives")
        for _, members in sorted(knowledge.groups.items())
    ]
    return C.KeyedCandidateSet(
        renditions=tuple(sorted({p.ctx.rendition_key for p in inputs.pages.values()})),
        entities=tuple(entities),
        statements=tuple(statements),
        references=tuple(references),
        claims=tuple(r.claim for _, r in sorted(knowledge.claims.items())),
        alternatives=tuple(alternatives),
    )


def run_m19(
    knowledge: Knowledge,
    inputs: Inputs,
    readings: Mapping[tuple[str, tuple], Reading],
    engine: Engine | None = None,
) -> RuleOutcome:
    """M19 over the run's set; the pool facts are the engine's `views` step when one is given."""
    if not knowledge.claims:
        return RuleOutcome("finalize", (), {})
    cs = run_set(knowledge, inputs)
    facts = engine_facts(engine, cs, inputs.compiled) if engine is not None else None
    views = build_views(cs, inputs.compiled, "finalize", readings, facts)
    return run_rules(views, inputs.compiled, "finalize")


def set_statuses(knowledge: Knowledge, pass_: str, findings: tuple[Finding, ...]) -> Counter[str]:
    errors = {f.claim for f in findings if f.severity == "error"}
    for key, row in knowledge.claims.items():
        if pass_ == "finalize" and key in errors:
            status = ClaimStatus.REJECTED
        elif row.claim.predicate == UNSCHEMATIZED:
            status = ClaimStatus.UNSUPPORTED
        elif pass_ != "finalize":
            status = ClaimStatus.CANDIDATE
        elif key in errors:
            status = ClaimStatus.REJECTED
        elif row.group is not None:
            status = ClaimStatus.AMBIGUOUS
        else:
            status = ClaimStatus.ACCEPTED
        row.status = status.value
    return Counter(r.status for r in knowledge.claims.values())


# --- Edge rows ---------------------------------------------------------------------------------


def _pointer(path: tuple[str | int, ...]) -> str:
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in path)


def _walk(node: Any, path: tuple[str | int, ...]) -> Iterator[tuple[tuple, dict]]:
    if isinstance(node, dict):
        yield path, node
        for k, v in node.items():
            yield from _walk(v, (*path, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, (*path, i))


_BINDING_ROLE = {
    BindKind.VARIABLE.value: EntityRefRole.BINDING_VARIABLE,
    BindKind.FAMILY_PARAM.value: EntityRefRole.BINDING_FAMILY_PARAM,
}
_BINDING_CLAIM = {BindKind.PARAM_OF.value, BindKind.PARAM_EXPR_OF.value}


def edges(knowledge: Knowledge) -> tuple[list[ClaimEdge], list[EntityEdge]]:
    claims, entities = [], []
    for key, row in sorted(knowledge.claims.items()):
        dump = row.claim.model_dump(mode="json", by_alias=True)
        qualifiers = dump.get("qualifiers") or {}
        for name, value in sorted(qualifiers.items()):
            if isinstance(value, dict) and set(value) == {"ref"}:
                target = value["ref"]
                if target in knowledge.entities:
                    entities.append(
                        EntityEdge(
                            key,
                            EntityRefRole.QUALIFIER.value,
                            name,
                            _pointer(("qualifiers", name)),
                            target,
                        )
                    )
        root = {"object": dump["object"], "qualifiers": qualifiers}
        for path, node in _walk(root, ()):
            if node.get("op") == "claim" and node.get("ref") in knowledge.claims:
                claims.append(
                    ClaimEdge(
                        key, ClaimRefKind.CONDITION_PREMISE.value, _pointer(path), node["ref"]
                    )
                )
            elif node.get("op") == "claim" and node.get("ref") in knowledge.entities:
                entities.append(
                    EntityEdge(
                        key,
                        EntityRefRole.CONDITION_PREMISE.value,
                        None,
                        _pointer(path),
                        node["ref"],
                    )
                )
            if node.get("op") == "pred":
                for i, arg in enumerate(node.get("args", [])):
                    if isinstance(arg, dict) and arg.get("ref") in knowledge.entities:
                        entities.append(
                            EntityEdge(
                                key,
                                EntityRefRole.PRED_ARG.value,
                                None,
                                _pointer((*path, "args", i)),
                                arg["ref"],
                            )
                        )
            bind = node.get("bind")
            if bind in _BINDING_ROLE and node.get("entity") in knowledge.entities:
                entities.append(
                    EntityEdge(key, _BINDING_ROLE[bind].value, None, _pointer(path), node["entity"])
                )
            if bind in _BINDING_CLAIM and node.get("claim") in knowledge.claims:
                claims.append(
                    ClaimEdge(key, ClaimRefKind.BINDING_PARAM.value, _pointer(path), node["claim"])
                )
            elif bind in _BINDING_CLAIM and node.get("claim") in knowledge.entities:
                entities.append(
                    EntityEdge(
                        key, EntityRefRole.BINDING_PARAM.value, None, _pointer(path), node["claim"]
                    )
                )
    return claims, entities


def parse_failures(readings: Mapping[tuple[str, tuple], Reading]) -> int:
    return sum(1 for r in readings.values() if r.status is ParseOutcome.FAILED)
