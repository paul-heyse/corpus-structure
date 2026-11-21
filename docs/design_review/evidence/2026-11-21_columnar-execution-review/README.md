# Columnar execution review: expressibility and fidelity checks

**Tested · 2026-11-21.** The [columnar execution review](../../../functional_reviews/columnar-execution-outside-postgresql_2026-11-21.md)
cites these checks as **[F]**. They answer two questions for it: whether the row operations found
outside PostgreSQL can be written as DuckDB 2.0 typed expressions without SQL text, and where a
DuckDB or PyArrow result would differ silently from today's Python result.

`uv run python docs/design_review/evidence/2026-11-21_columnar-execution-review/columnar_fidelity.py`
ran on CPython 3.14.10 with duckdb 2.0.0 and pyarrow 26.0.0. It uses synthetic rows in memory,
reads no repository data and opens no PostgreSQL connection. `columnar_fidelity.out` is its
output. Each line prints `SAME` or `DIFF`; a `DIFF` is a finding, not a failure.

| Group | What it shows |
|---|---|
| E1–E8 | Containment join, ordinal within parent, previous-end gap, running sum, integer range frame, gaps-and-islands, first-per-key, ASOF join and bag difference all work as expression objects |
| O1–O3 | UTF-8 byte order agrees across DuckDB, PyArrow, SQLite `BINARY` and Python; a JSON-text key orders differently from its parts; NULLs sort last by default |
| I1–I4 | DuckDB JSON equals the canonical bytes for strings and integers with sorted fields, and differs for floats and decimals |
| S1–S5 | Regular-expression classes, edit distance, `bool_and` over no rows, float sums and dense unions differ from the Python equivalents |
| X1–X2 | An Arrow extension type over text returns from DuckDB as plain text and sorts as text |

**Limits.** These are behaviours of the two libraries on small inputs. They are not a comparison
against production functions and carry no timing. The review's comparisons against production
functions were made during the review and not retained. No evidence record is written: the result
informs a Proposed review, not an accepted decision.
