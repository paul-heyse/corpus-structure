"""The in-process DuckDB 2.0 engine of the pool's set steps (pool and interchange §3.2; ADR-0021).

`DuckDBEngine` serves `steps.Engine` with SQL over the step inputs and must be set-equal with
`PythonEngine` (`pool/harness.py`). It holds one in-memory connection per pass, creates no
persistent database and pins the session time zone to UTC. Each step registers its Arrow inputs
by their relation names (`cs.relation`: `linkable`, `keyed_claims`, `view_claims`, …), runs one
query, unregisters them, and returns the result conformed to the step's declared schema
(`steps.as_schema`), which re-attaches the JSON tag DuckDB's Arrow output drops.

DuckDB 2.0's rules (`docs/libraries/duckdb_2.md` §3.5 to §3.7): Arrow comes only from relations
(`con.sql(…).to_arrow_table()`), so no `execute()` result is left open on the connection; a busy
connection used from another thread raises, so an engine belongs to one thread.

Determinism (TM §10): every result is a set with an explicit `ORDER BY` key (nulls first where
the reference sorts them first); list aggregates are `DISTINCT … ORDER BY`; string order is
DuckDB's default binary collation, which is code point order for UTF-8, as Python's. Evidence items
are rebuilt as JSON text with their keys sorted (`json_keys`, `string_agg … ORDER BY`), the
reference's canonical form.

No phase 0 step is a fixed point per key, so none uses `WITH RECURSIVE … USING KEY`; merges under
cannot-links (phase 2, probe Q-7) are where it fits.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import duckdb
import pyarrow as pa

from corpus_structure.pool.contract import REFERENCE_ALIASES, REFERENCE_ENTITIES, conform
from corpus_structure.pool.steps import (
    ALTERNATIVE_OF,
    DISAGREEMENTS,
    FUSED,
    KEYED_CLAIMS,
    LINKABLE,
    LINKS,
    MEANINGS,
    REFERENCE_CLASS,
    SAME_SLOT,
    VIEW_FACTS,
    ViewSpec,
    as_schema,
    pool_relation,
    view_inputs,
)

_LINKS = """
WITH refkeys AS (
    SELECT DISTINCT e.type, a.normalized, e.key
    FROM reference_aliases a JOIN reference_entities e ON e.id = a.entity_id
), found AS (
    SELECT DISTINCT l.entity, r.key
    FROM linkable l JOIN refkeys r ON r.type = l.type AND r.normalized = l.normalized
)
SELECT entity, key, count(*) OVER (PARTITION BY entity) AS matches
FROM found ORDER BY entity, key
"""

_FUSE = """
WITH items AS (
    SELECT key, unnest(CAST(evidence AS JSON[])) AS item FROM keyed_claims
), canon AS (
    SELECT DISTINCT key, (
        SELECT '{' || string_agg(
            to_json(k) || ':' || json_extract(item, '$."' || k || '"')::VARCHAR, ',' ORDER BY k
        ) || '}'
        FROM unnest(json_keys(item)) AS t(k)
    ) AS text
    FROM items
), ordered AS (
    SELECT key, text,
           json_extract(text, '$.start')::BIGINT AS s, json_extract(text, '$.end')::BIGINT AS e,
           json_extract_string(text, '$.role') AS r,
           coalesce(json_extract(text, '$.coarse')::BOOLEAN, false) AS co
    FROM canon
), evidence AS (
    SELECT key, '[' || string_agg(text, ',' ORDER BY s, e, r, co, text) || ']' AS evidence
    FROM ordered GROUP BY key
), grouped AS (
    SELECT key, list(DISTINCT observation_id ORDER BY observation_id) AS supports,
           count(*) AS candidates
    FROM keyed_claims GROUP BY key
)
SELECT g.key, g.supports, coalesce(v.evidence, '[]') AS evidence, g.candidates
FROM grouped g LEFT JOIN evidence v USING (key) ORDER BY g.key
"""

_DISAGREEMENTS = """
WITH d AS (SELECT DISTINCT key, meaning FROM meanings),
     k AS (SELECT key FROM d GROUP BY key HAVING count(*) > 1)
SELECT d.key, d.meaning FROM d JOIN k USING (key) ORDER BY d.key, d.meaning NULLS FIRST
"""

_FACTS = "coalesce(list(DISTINCT {v} ORDER BY {v}) FILTER (WHERE {v} IS NOT NULL), []::VARCHAR[])"
_VIEWS = f"""
WITH pairs AS (
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
     AND e.type <> '{REFERENCE_CLASS}'
    LEFT JOIN view_identity i ON s.attr = 'identity' AND i.entity = e.entity AND i.slot = s.slot
), declared AS (
    SELECT t.claim, t.view, {_FACTS.format(v="p.v")} AS facts
    FROM target t LEFT JOIN projected p ON p.view = t.view AND p.m = t.m
    GROUP BY t.claim, t.view
)
SELECT claim, view, facts FROM (SELECT * FROM generic UNION ALL SELECT * FROM declared)
ORDER BY claim, view
"""
_SPECS = pa.schema(
    [(name, pa.string()) for name in
     ("view", "source", "match_source", "match_claim", "head", "attr", "slot")]
)  # fmt: skip
_APPLIES = pa.schema([("view", pa.string()), ("predicate", pa.string())])


class DuckDBEngine:
    """The DuckDB 2.0 implementation of the set steps (module doc); close it after the pass."""

    name = "duckdb"

    def __init__(self) -> None:
        self.con = duckdb.connect(":memory:")
        self.con.sql("SET TimeZone = 'UTC'")

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> DuckDBEngine:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @contextmanager
    def _registered(self, *tables: pa.Table) -> Iterator[None]:
        names = []
        try:
            for table in tables:
                name = (table.schema.metadata or {})[b"cs.relation"].decode()
                self.con.register(name, table)
                names.append(name)
            yield
        finally:
            for name in names:
                self.con.unregister(name)

    def _run(self, sql: str, schema: pa.Schema, *tables: pa.Table) -> pa.Table:
        with self._registered(*tables):
            return as_schema(self.con.sql(sql).to_arrow_table(), schema)

    def alias_links(
        self, linkable: pa.Table, reference_entities: pa.Table, reference_aliases: pa.Table
    ) -> pa.Table:
        return self._run(
            _LINKS,
            LINKS,
            conform(linkable, LINKABLE),
            pool_relation(reference_entities, REFERENCE_ENTITIES),
            pool_relation(reference_aliases, REFERENCE_ALIASES),
        )

    def fuse(self, claims: pa.Table) -> pa.Table:
        return self._run(_FUSE, FUSED, conform(claims, KEYED_CLAIMS))

    def disagreements(self, meanings: pa.Table) -> pa.Table:
        return self._run(_DISAGREEMENTS, DISAGREEMENTS, conform(meanings, MEANINGS))

    def views(
        self, claims: pa.Table, entities: pa.Table, identity: pa.Table, alternatives: pa.Table,
        specs: Sequence[ViewSpec],
    ) -> pa.Table:
        inputs = view_inputs(claims, entities, identity, alternatives, specs)
        rows: list[dict[str, Any]] = [
            {"view": s.name, "source": s.source, "match_source": s.match_source,
             "match_claim": s.match_claim, "head": s.head, "attr": s.attr, "slot": s.slot}
            for s in specs
        ]  # fmt: skip
        applies = [{"view": s.name, "predicate": p} for s in specs for p in sorted(s.applies_to)]
        spec_table = pa.Table.from_pylist(rows, schema=_SPECS).replace_schema_metadata(
            {b"cs.relation": b"view_specs"}
        )
        applies_table = pa.Table.from_pylist(applies, schema=_APPLIES).replace_schema_metadata(
            {b"cs.relation": b"view_applies"}
        )
        return self._run(_VIEWS, VIEW_FACTS, *inputs, spec_table, applies_table)
