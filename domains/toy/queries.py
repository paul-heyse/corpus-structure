"""Ownership applicability, implemented entirely by the toy pack (C4)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import select

from corpus_structure.core.db import metadata
from corpus_structure.serve.protocol import Positioned, QueryContext, Scope


class OwnershipParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset: str
    date: Date
    include_candidates: bool = False
    include_suppositions: bool = False


class OwnershipRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    claim: dict[str, JsonValue]
    interval: dict[str, JsonValue] | None
    applicability: Literal["established", "not_applicable", "unknown"]
    evidence: list[dict[str, JsonValue]]


def applicability(interval: dict[str, JsonValue] | None, at: Date) -> str:
    """Partial or symbolic dates remain unknown; omitted interval bounds are unbounded."""
    if interval is None:
        return "unknown"
    for name, inclusive in (("start", "start_incl"), ("end", "end_incl")):
        value = interval.get(name)
        if value is None:
            continue
        if not isinstance(value, dict) or value.get("t") != "date":
            return "unknown"
        raw = value.get("v")
        if not isinstance(raw, str) or len(raw) != 10:
            return "unknown"
        try:
            bound = Date.fromisoformat(raw)
        except ValueError:
            return "unknown"
        if (name == "start" and at < bound) or (name == "end" and at > bound):
            return "not_applicable"
        if at == bound and interval.get(inclusive) is False:
            return "not_applicable"
    return "established"


class OwnershipAt:
    name, version = "ownership_at", "1"
    params, result = OwnershipParams, OwnershipRow

    def scope(self, ctx: QueryContext, p: OwnershipParams) -> Scope:
        return Scope.run()

    def rows(
        self, ctx: QueryContext, p: OwnershipParams, after: JsonValue = None
    ) -> Iterator[Positioned]:
        e, c = metadata.tables["kb.entity"], metadata.tables["kb.claim"]
        matches = (
            ctx.entities(key=p.asset) if p.asset.startswith("ent:") else ctx.entities(label=p.asset)
        )
        assets = select(e.c.id).where(
            e.c.run_id == ctx.run_id,
            e.c.type == "toy:Asset",
            e.c.key.in_([x["key"] for x in matches]),
        )
        stmt = ctx.reader.claim_statement(
            predicate="toy:owns",
            include_candidates=p.include_candidates,
            include_suppositions=p.include_suppositions,
        ).where(c.c.object_entity_id.in_(assets))
        for claim in ctx.reader.claims(statement=stmt, after=after):
            interval = claim["qualifiers"].get("core:valid_time")
            row = OwnershipRow.model_validate(
                {
                    "key": claim["key"],
                    "claim": claim,
                    "interval": interval,
                    "applicability": applicability(interval, p.date),
                    "evidence": claim["evidence"],
                }
            )
            yield Positioned(row, claim["key"])


QUERIES = (OwnershipAt(),)
