# S6 DDL fixes

Source: `docs/design/D3-database.md` (sha256 `fe27c41d9d617086…`), 9 DDL blocks and 7 query blocks extracted by `code/s6_extract_ddl.py` into `code/s6_ddl.sql` and `code/s6_queries_d3.sql`. The applied copy is `code/s6_ddl_applied.sql`; D3 is not edited.

## F1: regconfig literal in the BM25 index predicate

- **Error or gap:** `CREATE INDEX segment_bm25 …` fails with SQLSTATE 22P02 `invalid input syntax for type oid: "english"` (applied as the non-superuser cs_s6_app, PostgreSQL 18.6, 2026-10-28).
- **Fix:** Cast the literal: `ts_config = 'english'::regconfig`.
- **Reason:** `regconfig` has no `=` operator of its own; `regconfig = unknown` resolves to `oid = oid`, so the untyped literal is read as an oid. The same cast is needed wherever a query repeats the predicate (D3 §5's BM25 query), and the query must repeat it in the same form for the planner to prove the partial index's predicate (see `results/s6/bm25.md`). The column `DEFAULT 'english'` is fine: an assignment cast applies there. A `text` column with a CHECK would avoid the cast but lose the type's validation of configuration names.
- **Kind:** error

```sql
-- D3
  WHERE kind IN ('paragraph','heading','list_item','math_display') AND ts_config = 'english';
-- copy
  WHERE kind IN ('paragraph','heading','list_item','math_display') AND ts_config = 'english'::regconfig;
```

## F2: kb.segment.kind checked against the D1 §3.2 list

- **Error or gap:** Applies, but the column comment says the kind is "checked against a list in the migration" and the block has no CHECK, so a migration generated from this DDL would not check it.
- **Fix:** A CHECK with the D1 §3.2 kinds (every kind S1 emits on the four pages is in it).
- **Reason:** D3 §1 makes closed value sets `text` with `CHECK`; the BM25 partial index's kind list relies on the kind vocabulary being closed. Exercised by the constraint sweep (`results/s6/constraints.tsv`).
- **Kind:** gap

```sql
-- D3
  kind         text NOT NULL,                    -- D1 §3.2; checked against a list in the migration
-- copy
  kind         text NOT NULL CHECK (kind IN ('document','section','unit','paragraph','list','list_item','details',
                    'math_display','math_inline','heading','table','table_row','table_cell','caption','footnote',
                    'figure','sentence','email_message','quoted_block','signature')),   -- D1 §3.2
```

