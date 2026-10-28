"""S6-A: fixes applied to the extracted D3 DDL in the copy ``code/s6_ddl_applied.sql``.

Each fix: ``id``, ``short``, the exact ``old`` text (must occur once in ``s6_ddl.sql``), its ``new``
text, the ``error`` that called for it, the ``fix``, the ``reason`` and its ``kind``
(``error``: the DDL does not apply; ``gap``: applies but contradicts D3's own prose or a brief
requirement). Filled as the DDL is applied; D3 itself is never edited.
"""

FIXES: list[dict] = [
    {
        "id": "F1",
        "short": "regconfig literal in the BM25 index predicate",
        "kind": "error",
        "old": "  WHERE kind IN ('paragraph','heading','list_item','math_display') AND ts_config = 'english';",
        "new": "  WHERE kind IN ('paragraph','heading','list_item','math_display') AND ts_config = 'english'::regconfig;",
        "error": "`CREATE INDEX segment_bm25 …` fails with SQLSTATE 22P02 `invalid input syntax for type oid: \"english\"` "
                 "(applied as the non-superuser cs_s6_app, PostgreSQL 18.6, 2026-10-28).",
        "fix": "Cast the literal: `ts_config = 'english'::regconfig`.",
        "reason": "`regconfig` has no `=` operator of its own; `regconfig = unknown` resolves to `oid = oid`, so the "
                  "untyped literal is read as an oid. The same cast is needed wherever a query repeats the predicate "
                  "(D3 §5's BM25 query), and the query must repeat it in the same form for the planner to prove the "
                  "partial index's predicate (see `results/s6/bm25.md`). The column `DEFAULT 'english'` is fine: an "
                  "assignment cast applies there. A `text` column with a CHECK would avoid the cast but lose the "
                  "type's validation of configuration names.",
    },
    {
        "id": "F2",
        "short": "kb.segment.kind checked against the D1 §3.2 list",
        "kind": "gap",
        "old": "  kind         text NOT NULL,                    -- D1 §3.2; checked against a list in the migration\n",
        "new": "  kind         text NOT NULL CHECK (kind IN ('document','section','unit','paragraph','list','list_item','details',\n"
               "                    'math_display','math_inline','heading','table','table_row','table_cell','caption','footnote',\n"
               "                    'figure','sentence','email_message','quoted_block','signature')),   -- D1 §3.2\n",
        "error": "Applies, but the column comment says the kind is \"checked against a list in the migration\" and the "
                 "block has no CHECK, so a migration generated from this DDL would not check it.",
        "fix": "A CHECK with the D1 §3.2 kinds (every kind S1 emits on the four pages is in it).",
        "reason": "D3 §1 makes closed value sets `text` with `CHECK`; the BM25 partial index's kind list relies on the "
                  "kind vocabulary being closed. Exercised by the constraint sweep (`results/s6/constraints.tsv`).",
    },
]
