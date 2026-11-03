"""Source-stated temporal ownership with explicit unknown validity."""

from __future__ import annotations

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import exists, select

from corpus_structure.serve.protocol import Positioned, Scope
from corpus_structure.serve.read import T
from corpus_structure.serve.results import ClaimAnswer


class OwnershipParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset: str
    date: Date
    include_candidates: bool = False
    include_suppositions: bool = False


class OwnershipRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: ClaimAnswer
    interval: dict[str, JsonValue] | None
    applicability: Literal["established", "not_applicable", "unknown"]


def applicability(
    interval: dict[str, JsonValue] | None, at: Date
) -> Literal["established", "not_applicable", "unknown"]:
    """Partial or symbolic dates remain unknown; omitted interval bounds are unbounded."""
    if interval is None:
        return "unknown"
    for name, inclusive in (("start", "start_incl"), ("end", "end_incl")):
        value = interval.get(name)
        if value is None:
            continue
        if not isinstance(value, dict) or value.get("kind") != "partial_date":
            return "unknown"
        raw = value.get("lexical")
        if not isinstance(raw, str) or len(raw) != 10:
            return "unknown"
        try:
            bound = Date.fromisoformat(raw)
        except ValueError:
            return "unknown"
        if (name == "start" and at < bound) or (name == "end" and at > bound):
            return "not_applicable"
        if at == bound:
            if interval.get(inclusive) is None:
                return "unknown"
            if interval.get(inclusive) is False:
                return "not_applicable"
    return "established"


class OwnershipAt:
    name, version = "ownership_at", "semantic-1"
    params, result = OwnershipParams, OwnershipRow

    def scope(self, ctx, p):
        return Scope.run()

    def rows(self, ctx, p, after=None):
        f, v = T["fact"], T["typed_value"]
        assets = ctx.reader.resolve(p.asset, "Asset")
        stmt = ctx.reader.fact_statement(
            predicate="toy:owns",
            include_candidates=p.include_candidates,
            include_suppositions=p.include_suppositions,
        ).where(
            exists(
                select(1).where(
                    ctx.reader.scope(v),
                    v.c.value_id == f.c.object_value_id,
                    v.c.entity_id.in_(assets),
                )
            )
        )
        for claim in ctx.reader.claims(statement=stmt, after=after):
            qualification = claim.fact.qualification
            interval = qualification.model_dump(mode="json", exclude_unset=True).get("valid_time")
            yield Positioned(
                OwnershipRow(
                    claim=claim, interval=interval, applicability=applicability(interval, p.date)
                ),
                claim.fact.occurrence_id or claim.fact.fact_id,
            )


QUERIES = (OwnershipAt(),)
