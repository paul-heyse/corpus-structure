"""Owned semantic set kernels and the typed operation views they consume.

These projections use occurrence/fact identifiers supplied by the bound operation.
They are independent of the retired pool's storage or reference-class vocabulary.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

import pyarrow as pa


def _schema(name: str, *fields: pa.Field) -> pa.Schema:
    return pa.schema(fields, metadata={b"cs.relation": name.encode()})


VIEW_CLAIMS = _schema(
    "view_claims",
    pa.field("claim", pa.string(), nullable=False),
    pa.field("predicate", pa.string(), nullable=False),
    pa.field("subject", pa.string(), nullable=False),
    pa.field("object", pa.string()),
    pa.field("statement", pa.string()),
)
VIEW_ENTITIES = _schema(
    "view_entities",
    pa.field("entity", pa.string(), nullable=False),
    pa.field("key", pa.string()),
    pa.field("type", pa.string(), nullable=False),
    pa.field("label", pa.string(), nullable=False),
    pa.field("symbol", pa.string()),
)
VIEW_IDENTITY = _schema(
    "view_identity",
    pa.field("entity", pa.string(), nullable=False),
    pa.field("slot", pa.string(), nullable=False),
    pa.field("value", pa.string(), nullable=False),
)
VIEW_ALTERNATIVES = _schema(
    "view_alternatives",
    pa.field("group", pa.string(), nullable=False),
    pa.field("claim", pa.string(), nullable=False),
)
VIEW_FACTS = _schema(
    "view_facts",
    pa.field("claim", pa.string(), nullable=False),
    pa.field("view", pa.string(), nullable=False),
    pa.field("facts", pa.list_(pa.field("item", pa.string(), nullable=False)), nullable=False),
)
VIEW_SPECS = pa.schema(
    [
        (name, pa.string())
        for name in ("view", "source", "match_source", "match_claim", "head", "attr", "slot")
    ]
)
VIEW_APPLIES = pa.schema([("view", pa.string()), ("predicate", pa.string())])
SAME_SLOT, ALTERNATIVE_OF = "same_slot", "alternative_of"
PROJECTED = ("id", "key", "type", "label", "symbol")
type Side = Literal["subject", "object"]


@dataclass(frozen=True)
class ViewSpec:
    name: str
    applies_to: frozenset[str]
    source: str
    match_source: Side
    match_claim: Side
    head: Side
    attr: str
    slot: str | None = None

    def __post_init__(self) -> None:
        if not self.name or self.name in {SAME_SLOT, ALTERNATIVE_OF}:
            raise ValueError("declared view shadows a generic fact or has no name")
        if (
            self.match_source not in {"subject", "object"}
            or self.match_claim not in {"subject", "object"}
            or self.head not in {"subject", "object"}
        ):
            raise ValueError("view sides must be subject or object")
        if not (
            (self.attr in PROJECTED and self.slot is None)
            or (self.attr == "identity" and self.slot)
        ):
            raise ValueError("unsupported view projection")

    @classmethod
    def from_declaration(
        cls, name: str, declaration: Mapping[str, Any], applies_to: Iterable[str]
    ) -> ViewSpec:
        head, _, rest = str(declaration["project"]).partition(".")
        attr, _, slot = rest.partition(".")
        if head not in ("subject", "object") or not (
            (attr in PROJECTED and not slot) or (attr == "identity" and slot)
        ):
            raise ValueError(f"view {name}: cannot project {declaration['project']!r}")
        selected_head: Side = "subject" if head == "subject" else "object"
        match = declaration["match"]
        return cls(
            name,
            frozenset(applies_to),
            str(declaration["source"]),
            match["source"],
            match["claim"],
            selected_head,
            attr,
            slot or None,
        )


DISAGREEMENTS_SQL = """
WITH d AS (SELECT DISTINCT key, meaning FROM meanings),
     k AS (SELECT key FROM d GROUP BY key HAVING count(*) > 1)
SELECT d.key, d.meaning FROM d JOIN k USING (key) ORDER BY d.key, d.meaning NULLS FIRST
"""
FUSE_SQL = """
WITH evidence_items AS (
    SELECT DISTINCT fact_id, unnest(evidence) AS item FROM candidate_input
), evidence_sets AS (
    SELECT fact_id, list(item ORDER BY item) AS evidence
    FROM evidence_items GROUP BY fact_id
), support_sets AS (
    SELECT fact_id, coalesce(list(DISTINCT occurrence_id ORDER BY occurrence_id)
        FILTER (WHERE occurrence_id IS NOT NULL), []) AS supports,
        count(*) AS candidates FROM candidate_input GROUP BY fact_id
) SELECT s.*, coalesce(e.evidence, []) AS evidence
  FROM support_sets s LEFT JOIN evidence_sets e USING (fact_id) ORDER BY fact_id
"""
_FACTS = "coalesce(list(DISTINCT {v} ORDER BY {v}) FILTER (WHERE {v} IS NOT NULL), []::VARCHAR[])"
VIEWS_MACRO_NAME = "semantic_operation_views"
VIEWS_INPUTS = (
    "view_claims",
    "view_entities",
    "view_identity",
    "view_alternatives",
    "view_specs",
    "view_applies",
)
VIEWS_MACRO_SQL = f"""
CREATE TEMP MACRO {VIEWS_MACRO_NAME}(claims_source, entities_source, identity_source,
                                    alternatives_source, specs_source, applies_source) AS TABLE
WITH view_claims AS (SELECT * FROM query_table(claims_source)),
view_entities AS (SELECT * FROM query_table(entities_source)),
view_identity AS (SELECT * FROM query_table(identity_source)),
view_alternatives AS (SELECT * FROM query_table(alternatives_source)),
view_specs AS (SELECT * FROM query_table(specs_source)),
view_applies AS (SELECT * FROM query_table(applies_source)),
pairs AS (
    SELECT DISTINCT a.claim, b.claim AS other
    FROM view_alternatives a
    JOIN view_alternatives b ON b."group" = a."group" AND b.claim <> a.claim
    WHERE b.claim IN (SELECT claim FROM view_claims)
), generic AS (
    SELECT c.claim, '{SAME_SLOT}' AS view, {_FACTS.format(v="d.claim")} AS facts
    FROM view_claims c LEFT JOIN view_claims d
      ON d.predicate = c.predicate AND d.subject = c.subject
     AND d.statement IS NOT DISTINCT FROM c.statement AND d.claim <> c.claim
    GROUP BY c.claim
    UNION ALL
    SELECT c.claim, '{ALTERNATIVE_OF}' AS view, {_FACTS.format(v="p.other")} AS facts
    FROM view_claims c LEFT JOIN pairs p ON p.claim = c.claim
    GROUP BY c.claim
), target AS (
    SELECT DISTINCT s.view, c.claim,
           CASE s.match_claim WHEN 'subject' THEN c.subject ELSE c.object END AS m
    FROM view_specs s JOIN view_applies a ON a.view = s.view
    JOIN view_claims c ON c.predicate = a.predicate
), projected AS (
    SELECT s.view, CASE s.match_source WHEN 'subject' THEN d.subject ELSE d.object END AS m,
           CASE s.attr WHEN 'id' THEN e.entity WHEN 'key' THEN e.key WHEN 'type' THEN e.type
                       WHEN 'label' THEN e.label WHEN 'symbol' THEN e.symbol
                       WHEN 'identity' THEN i.value END AS v
    FROM view_specs s JOIN view_claims d ON d.predicate = s.source
    JOIN view_entities e
      ON e.entity = CASE s.head WHEN 'subject' THEN d.subject ELSE d.object END
    LEFT JOIN view_identity i ON s.attr = 'identity' AND i.entity = e.entity AND i.slot = s.slot
), declared AS (
    SELECT t.claim, t.view, {_FACTS.format(v="p.v")} AS facts
    FROM target t LEFT JOIN projected p ON p.view = t.view AND p.m = t.m
    GROUP BY t.claim, t.view
)
SELECT claim, view, facts FROM (SELECT * FROM generic UNION ALL SELECT * FROM declared)
ORDER BY claim, view
"""
